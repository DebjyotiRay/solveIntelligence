import re
import openai
import os
import json
import logging
from typing import Dict, Any, List
from datetime import datetime

from .base_agent import BasePatentAgent
from ..workflow.patent_state import PatentAnalysisState
from ..utils import strip_html
from ..types import StructureAnalysisResult, StructuralIssue, TargetLocation, ReplacementText
from app.services.memory_service import get_memory_service

logger = logging.getLogger(__name__)


class DocumentStructureAgent(BasePatentAgent):
    
    def __init__(self):
        super().__init__("structure")
        self.memory = get_memory_service()  # 🚀 MEMORY INTEGRATION

    async def analyze(self, state: PatentAnalysisState, stream_callback=None) -> Dict[str, Any]:
        logger.info("STRUCTURE AGENT: Starting AI-powered analysis")
        
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "structure_analysis",
                "agent": "structure",
                "message": "📋 Parsing document..."
            })

        document = state["document"]
        document_content = document.get("content", "")
        
        clean_text = strip_html(document_content)
        logger.info(f"STRUCTURE AGENT: Cleaned text length: {len(clean_text)} chars")
        
        parsed_document = self._parse_document_sections(clean_text)
        logger.info(f"STRUCTURE AGENT: Parsed document - {len(parsed_document.get('claims', []))} claims found")
        
        # 🚀 MEMORY: Query legal knowledge for patent structure requirements
        structure_requirements = self.memory.query_legal_knowledge(
            query="patent structure requirements sections format claims abstract description",
            limit=3
        )
        logger.info(f"STRUCTURE AGENT: Retrieved {len(structure_requirements)} structure requirements from legal knowledge")
        
        # 🧠 LEARNING LOOP: Query client's past structure issues
        client_id = state.get("client_id", state.get("document_id", "default"))
        historical_context = ""
        try:
            past_analyses = self.memory.query_client_memory(
                client_id=client_id,
                query="structure analysis formatting issues claims sections",
                memory_type="analysis",
                limit=2
            )
            
            if past_analyses:
                logger.info(f"STRUCTURE AGENT: Found {len(past_analyses)} past structure analyses for client {client_id}")
                historical_context = "\n\nCLIENT'S HISTORICAL STRUCTURE PATTERNS:\n"
                for i, analysis in enumerate(past_analyses, 1):
                    memory_text = analysis.get('memory', '')
                    historical_context += f"{i}. {memory_text[:150]}\n"
                historical_context += "\nPay attention to this client's recurring structure issues.\n"
            else:
                logger.info(f"STRUCTURE AGENT: No history for client {client_id} (first analysis)")
        except Exception as e:
            logger.warning(f"Could not retrieve client history: {e}")
            historical_context = ""
        
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "structure_analysis",
                "agent": "structure",
                "message": "🤖 Sending to AI for validation with legal context..."
            })
        
        ai_validation = await self._ai_validate_document(
            parsed_document, 
            structure_requirements,
            historical_context,
            stream_callback
        )
        
        findings = {
            "type": "structure_analysis",
            "parsed_document": parsed_document,
            "confidence": ai_validation.confidence,
            "issues": ai_validation.issues,
            "recommendations": ai_validation.suggestions
        }
        
        logger.info(f"STRUCTURE AGENT: Analysis complete - {len(findings['issues'])} issues found")
        
        # 🚀 MEMORY: Store structure analysis in client memory for learning
        try:
            client_id = state.get("client_id", state.get("document_id", "default"))
            self.memory.store_client_analysis(
                client_id=client_id,
                analysis_summary=f"Structure analysis found {len(ai_validation.issues)} issues. "
                               f"Confidence: {ai_validation.confidence:.2f}. "
                               f"Issues: {', '.join([issue.type for issue in ai_validation.issues[:3]])}",
                metadata={
                    "document_id": state.get("document_id", "unknown"),
                    "analysis_type": "structure",
                    "issues_found": len(ai_validation.issues),
                    "confidence": ai_validation.confidence,
                    "timestamp": datetime.now().isoformat()
                }
            )
            logger.info(f"✓ Stored structure analysis in client memory for {client_id}")
        except Exception as e:
            logger.warning(f"Failed to store in client memory: {e}")
        
        return findings

    def _parse_document_sections(self, content: str) -> Dict[str, Any]:
        return {
            "title": self._extract_title(content),
            "abstract": self._extract_abstract(content),
            "background": self._extract_background(content),
            "summary": self._extract_summary(content),
            "detailed_description": self._extract_detailed_description(content),
            "claims": self._extract_claims(content),
            "figures": self._extract_figure_references(content),
            "word_count": len(content.split()),
            "character_count": len(content),
            "full_text": content[:3000]
        }

    def _extract_title(self, content: str) -> str:
        lines = content.split('\n')[:10]
        for line in lines:
            line = line.strip()
            if len(line) > 10 and not line.lower().startswith(('patent', 'application', 'field')):
                return line
        return "Title not found"

    def _extract_abstract(self, content: str) -> str:
        abstract_match = re.search(
            r'(?:ABSTRACT|Abstract)\s*\n(.*?)(?:\n\s*(?:BACKGROUND|Background|FIELD|Field|SUMMARY|Summary|DETAILED|Detailed))',
            content, re.DOTALL | re.IGNORECASE
        )
        return abstract_match.group(1).strip() if abstract_match else ""

    def _extract_background(self, content: str) -> str:
        background_match = re.search(
            r'(?:BACKGROUND|Background).*?\n(.*?)(?:\n\s*(?:SUMMARY|Summary|DETAILED|Detailed|CLAIMS|Claims))',
            content, re.DOTALL | re.IGNORECASE
        )
        return background_match.group(1).strip() if background_match else ""

    def _extract_summary(self, content: str) -> str:
        summary_match = re.search(
            r'(?:SUMMARY|Summary).*?\n(.*?)(?:\n\s*(?:DETAILED|Detailed|CLAIMS|Claims))',
            content, re.DOTALL | re.IGNORECASE
        )
        return summary_match.group(1).strip() if summary_match else ""

    def _extract_detailed_description(self, content: str) -> str:
        detailed_match = re.search(
            r'(?:DETAILED DESCRIPTION|Detailed Description).*?\n(.*?)(?:\n\s*(?:CLAIMS|Claims|WHAT IS CLAIMED|What is claimed))',
            content, re.DOTALL | re.IGNORECASE
        )
        return detailed_match.group(1).strip() if detailed_match else ""

    def _extract_claims(self, content: str) -> List[Dict[str, Any]]:
        claims = []
        
        claims_match = re.search(
            r'(?:CLAIMS?|What is claimed|WHAT IS CLAIMED).*?\n(.*?)(?:\n\s*$|\Z)',
            content, re.DOTALL | re.IGNORECASE
        )
        
        if not claims_match:
            return claims
            
        claims_text = claims_match.group(1)
        claim_pattern = r'(\d+)\.\s*(.*?)(?=\d+\.\s*|\Z)'
        claim_matches = re.findall(claim_pattern, claims_text, re.DOTALL)
        
        for claim_num, claim_text in claim_matches:
            claims.append({
                "number": int(claim_num),
                "text": claim_text.strip()
            })
        
        return claims

    def _extract_figure_references(self, content: str) -> List[str]:
        figure_refs = re.findall(r'(?:FIG\.?\s*\d+|Figure\s*\d+)', content, re.IGNORECASE)
        return list(set(figure_refs))


    def _is_valid_replacement(self, target: str, replacement: str) -> bool:
        """Validate replacement is meaningful and not nonsense."""
        if not target or not replacement:
            return False
        
        target_clean = target.strip().lower()
        replacement_clean = replacement.strip().lower()
        
        # Reject identical
        if target_clean == replacement_clean:
            return False
        
        # Reject duplicates
        if replacement_clean == target_clean + " " + target_clean:
            return False
        
        # Reject if target appears multiple times in replacement
        if replacement_clean.count(target_clean) > 1:
            return False
        
        # Reject too short
        if len(replacement.strip()) < 2:
            return False
        
        return True
    async def _ai_validate_document(
        self, 
        parsed_doc: Dict[str, Any],
        legal_requirements: List[Dict[str, Any]],
        historical_context: str,
        stream_callback=None
    ) -> StructureAnalysisResult:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("No OpenAI API key - skipping AI validation")
            return StructureAnalysisResult(
                status="error",
                confidence=0.5,
                issues=[],
                suggestions=[]
            )

        try:
            client = openai.OpenAI(api_key=api_key)
            
            claims_text = "\n".join([
                f"Claim {c['number']}: {c['text'][:300]}" 
                for c in parsed_doc.get('claims', [])[:5]
            ])
            
            # Format legal requirements for context
            legal_context = "\n\nLEGAL STRUCTURE REQUIREMENTS:\n"
            for i, req in enumerate(legal_requirements, 1):
                legal_context += f"{i}. {req.get('memory', '')[:200]}\n"
            
            document_summary = f"""
Title: {parsed_doc.get('title', 'Not found')}
Abstract: {parsed_doc.get('abstract', 'Not found')[:500]}
Claims ({len(parsed_doc.get('claims', []))} total):
{claims_text}

Full text preview: {parsed_doc.get('full_text', '')[:1000]}
{legal_context}{historical_context}
"""

            prompt = f"""You are a precision document auditor for patent formatting.
Identify **only mechanical, verifiable issues** with exact text replacements.

PATENT DOCUMENT:
{document_summary}

---

ANALYZE FOR:
1. Missing sections (Title, Abstract, Claims)
2. Claim formatting (numbering, structure)
3. Spelling errors (exact word + correction)
4. Punctuation errors (missing/incorrect)

OUTPUT FORMAT (JSON only):
{{
  "confidence": 0.85,
  "issues": [
    {{
      "type": "format_error",
      "severity": "medium",
      "description": "Missing period",
      "suggestion": "Add period",
      "paragraph": 2,
      "target": {{"text": "lightweight", "section": "Claims"}},
      "replacement": {{"type": "replace", "text": "lightweight."}}
    }}
  ],
  "recommendations": []
}}

---

REPLACEMENT RULES:

✓ CORRECT Examples:
  • Spelling: target="recieve" → replacement="receive"
  • Punctuation: target="device" → replacement="device."
  • Completion: target="electromagnetic and" → replacement="electromagnetic radiation and"

✗ FORBIDDEN (skip these issues entirely):
  • Duplication: target="lightweight" → replacement="lightweight lightweight" ❌
  • Duplication: target="is transparent" → replacement="is transparent is transparent" ❌
  • Adding context: target="device" → replacement="the device is capable" ❌
  • Meaning change: target="infrared" → replacement="infrared and ultraviolet" ❌

VALIDATION CHECK (before returning each issue):
- Does replacement contain target text MORE THAN ONCE? → DELETE this issue
- Does replacement add unrelated words? → DELETE this issue
- Is it a mechanical fix (spelling/punctuation only)? → KEEP this issue

Valid types: "missing_section", "format_error", "clarity_issue", "claim_issue"
Valid severities: "high", "medium", "low"

Return JSON only. If no valid issues found: {{"confidence": 1.0, "issues": [], "recommendations": []}}"""

            if stream_callback:
                await stream_callback({
                    "status": "analyzing",
                    "phase": "structure_analysis",
                    "agent": "structure",
                    "message": "🤖 AI analyzing document..."
                })

            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0
            )

            result_text = response.choices[0].message.content.strip()
            
            if result_text.startswith('```'):
                lines = result_text.split('\n')
                result_text = '\n'.join(lines[1:-1] if len(lines) > 2 else lines[1:])
                result_text = result_text.strip()
            
            result = json.loads(result_text)
            
            # Convert to typed model with validation
            issues = []
            valid_types = {'missing_section', 'format_error', 'clarity_issue', 'claim_issue'}
            valid_severities = {'high', 'medium', 'low'}
            
            for issue in result.get('issues', []):
                # Validate and default type
                issue_type = issue.get('type', 'format_error')
                if issue_type not in valid_types:
                    logger.warning(f"Invalid issue type '{issue_type}', defaulting to 'format_error'")
                    issue_type = 'format_error'
                
                # Validate and default severity
                severity = issue.get('severity', 'medium')
                if severity not in valid_severities:
                    logger.warning(f"Invalid severity '{severity}', defaulting to 'medium'")
                    severity = 'medium'
                
                # Handle suggestion - must be a string
                suggestion_value = issue.get('suggestion', '')
                if isinstance(suggestion_value, dict):
                    # AI returned a structured suggestion - convert to string
                    if 'replacement' in suggestion_value and 'text' in suggestion_value['replacement']:
                        suggestion_value = suggestion_value['replacement']['text']
                    else:
                        suggestion_value = str(suggestion_value)
                    logger.warning(f"AI returned dict for suggestion, converted to: {suggestion_value[:100]}")
                elif not isinstance(suggestion_value, str):
                    suggestion_value = str(suggestion_value)
                
                # Extract target and replacement data for "Insert Fix" button
                target = None
                if 'target' in issue and issue['target']:
                    target = TargetLocation(
                        text=issue['target'].get('text'),
                        section=issue['target'].get('section'),
                        position=issue['target'].get('position')
                    )
                
                replacement = None
                if 'replacement' in issue and issue['replacement']:
                    replacement_text = issue['replacement'].get('text', suggestion_value)
                    target_text = issue['target'].get('text') if target else None

                    # Validate replacement is meaningful
                    if target_text and self._is_valid_replacement(target_text, replacement_text):
                        replacement = ReplacementText(
                            type=issue['replacement'].get('type', 'replace'),
                            text=replacement_text
                        )
                    else:
                        logger.warning(f"Rejected nonsense replacement: '{target_text}' -> '{replacement_text}'")
                
                issues.append(StructuralIssue(
                    type=issue_type,
                    severity=severity,
                    description=issue.get('description', ''),
                    location=issue.get('target', {}).get('section') if 'target' in issue else None,
                    suggestion=suggestion_value,
                    paragraph=issue.get('paragraph'),
                    target=target,
                    replacement=replacement
                ))
            
            typed_result = StructureAnalysisResult(
                status="complete",
                confidence=result.get('confidence', 0.5),
                issues=issues,
                suggestions=result.get('recommendations', [])
            )
            
            logger.info(f"STRUCTURE AGENT: AI validation complete - confidence: {typed_result.confidence}")
            return typed_result

        except json.JSONDecodeError as e:
            logger.error(f"STRUCTURE AGENT: JSON parse error: {e}")
            return StructureAnalysisResult(
                status="error",
                confidence=0.5,
                issues=[StructuralIssue(
                    type="format_error",
                    severity="low",
                    description="AI response parsing failed",
                    suggestion="Manual review recommended"
                )],
                suggestions=[]
            )
        except Exception as e:
            logger.error(f"STRUCTURE AGENT: AI validation failed: {e}")
            return StructureAnalysisResult(
                status="error",
                confidence=0.5,
                issues=[StructuralIssue(
                    type="format_error",
                    severity="low",
                    description=f"Analysis error: {str(e)}",
                    suggestion="Manual review recommended"
                )],
                suggestions=[]
            )
