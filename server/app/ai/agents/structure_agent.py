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
from ..types import StructureAnalysisResult, StructuralIssue
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
        
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "structure_analysis",
                "agent": "structure",
                "message": "🤖 Sending to AI for validation..."
            })

        ai_validation = await self._ai_validate_document(parsed_document, stream_callback, state)
        
        findings = {
            "type": "structure_analysis",
            "parsed_document": parsed_document,
            "confidence": ai_validation.confidence,
            "issues": ai_validation.issues,
            "recommendations": ai_validation.suggestions
        }
        
        logger.info(f"STRUCTURE AGENT: Analysis complete - {len(findings['issues'])} issues found")
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

    def _get_shared_context_prompt(self, state: PatentAnalysisState) -> str:
        """Get shared context for this agent from state."""
        shared_context = state.get("shared_context")
        if not shared_context:
            return ""

        try:
            # Get context formatted for structure agent
            context_str = shared_context.get_formatted_context_for_llm(
                agent_name="structure",
                max_chars=1000
            )
            return f"\n\n{context_str}" if context_str else ""
        except Exception as e:
            logger.warning(f"Could not get shared context: {e}")
            return ""

    async def _ai_validate_document(self, parsed_doc: Dict[str, Any], stream_callback=None, state: PatentAnalysisState = None) -> StructureAnalysisResult:
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
            
            document_summary = f"""
Title: {parsed_doc.get('title', 'Not found')}
Abstract: {parsed_doc.get('abstract', 'Not found')[:500]}
Claims ({len(parsed_doc.get('claims', []))} total):
{claims_text}

Full text preview: {parsed_doc.get('full_text', '')[:1000]}
"""

            # Get shared context (firm preferences, legal refs)
            context_addition = self._get_shared_context_prompt(state) if state else ""

            prompt = f"""Analyze this patent document for issues:

{document_summary}

Find and report:
1. Missing or incomplete required sections (title, abstract, claims)
2. Claims formatting issues (numbering, punctuation, structure)
3. Vague or indefinite language (e.g., "substantially", "about", "effective")
4. Antecedent basis problems (elements introduced with "a/an" must be referenced with "the")
5. Dependency issues in claims
6. Grammar, spelling, or clarity issues - MUST include exact misspelled word and its correction
7. Any other structural or formatting problems

For EACH issue, YOU MUST provide:
- Exact location (paragraph number if applicable, or section name)
- Specific text to find - THE ACTUAL WORDS that need changing (minimum 10-30 characters)
- Complete replacement text in proper format
- For spelling/grammar: Include the misspelled word in target.text and corrected word in replacement.text

CRITICAL FOR SPELLING/GRAMMAR: 
- target.text MUST contain the EXACT misspelled or incorrect word/phrase (e.g., "recieve" not just "spelling error")
- replacement.text MUST contain the EXACT corrected spelling (e.g., "receive")
- Do NOT report generic "check spelling" - report "Change 'recieve' to 'receive' in paragraph 3"

Respond ONLY with valid JSON in this EXACT format:
{{
  "confidence": 0.85,
  "issues": [
    {{
      "type": "clarity_issue",
      "severity": "medium",
      "description": "Vague term 'substantially' used without definition",
      "suggestion": "Define 'substantially' or use specific measurements"
    }},
    {{
      "type": "claim_issue",
      "severity": "high",
      "description": "Claim 1 missing proper antecedent basis for 'the device'",
      "suggestion": "First introduce 'a device' then refer to 'the device'"
    }}
  ],
  "recommendations": ["Add definitions section", "Review claim dependencies"]
}}

CRITICAL: 
- type MUST be EXACTLY one of: "missing_section", "format_error", "clarity_issue", or "claim_issue"
- severity MUST be EXACTLY one of: "high", "medium", or "low"
- Do NOT use any other values for these fields

IMPORTANT:
- For missing sections, provide the complete section template in replacement.text
- For punctuation fixes, provide the exact punctuation mark in replacement.text
- For antecedent basis, provide the corrected phrase in replacement.text
- Always include target.text when replacing existing content
- Use target.section to specify where in the document structure this applies
{context_addition}"""

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
                
                # Handle suggestion - can be string or dict
                suggestion_raw = issue.get('suggestion', '')
                if isinstance(suggestion_raw, dict):
                    # AI returned a dict instead of string - extract the actual text
                    logger.warning(f"AI returned dict for suggestion, extracting text: {suggestion_raw}")
                    
                    # Try multiple extraction strategies
                    suggestion = None
                    
                    # Strategy 1: Look for 'text' key
                    if 'text' in suggestion_raw:
                        suggestion = str(suggestion_raw['text'])
                    
                    # Strategy 2: Look for nested 'replacement' object
                    elif 'replacement' in suggestion_raw:
                        replacement = suggestion_raw['replacement']
                        if isinstance(replacement, dict) and 'text' in replacement:
                            suggestion = str(replacement['text'])
                        else:
                            suggestion = str(replacement)
                    
                    # Strategy 3: Look for any reasonable text field
                    elif 'content' in suggestion_raw:
                        suggestion = str(suggestion_raw['content'])
                    elif 'value' in suggestion_raw:
                        suggestion = str(suggestion_raw['value'])
                    
                    # Last resort: try to extract the first string value from the dict
                    if suggestion is None:
                        for key, value in suggestion_raw.items():
                            if isinstance(value, str) and len(value) > 10:
                                suggestion = value
                                break
                    
                    # Absolute last resort: inform user to check the raw data
                    if suggestion is None:
                        suggestion = "Please review the suggestion details in the analysis output"
                        logger.error(f"Could not extract text from suggestion dict: {suggestion_raw}")
                else:
                    suggestion = str(suggestion_raw)
                
                issues.append(StructuralIssue(
                    type=issue_type,
                    severity=severity,
                    description=issue.get('description', ''),
                    location=issue.get('target', {}).get('section') if 'target' in issue else None,
                    suggestion=suggestion
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
