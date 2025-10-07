import re
import openai
import os
import json
import logging
from typing import Dict, Any, List

from .base_agent import BasePatentAgent
from ..workflow.patent_state import PatentAnalysisState
from ..utils import strip_html

logger = logging.getLogger(__name__)


class DocumentStructureAgent(BasePatentAgent):
    
    def __init__(self, memory=None):
        super().__init__("structure", memory)

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
        
        ai_validation = await self._ai_validate_document(parsed_document, stream_callback)
        
        findings = {
            "type": "structure_analysis",
            "parsed_document": parsed_document,
            "confidence": ai_validation.get("confidence", 0.5),
            "issues": ai_validation.get("issues", []),
            "recommendations": ai_validation.get("recommendations", [])
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

    async def _ai_validate_document(self, parsed_doc: Dict[str, Any], stream_callback=None) -> Dict[str, Any]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("No OpenAI API key - skipping AI validation")
            return {
                "confidence": 0.5,
                "issues": [],
                "recommendations": []
            }

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

Respond in JSON format:
{{
  "confidence": 0.0-1.0,
  "issues": [
    {{
      "type": "issue_type",
      "severity": "high/medium/low",
      "paragraph": 3,
      "description": "specific issue description",
      "suggestion": "how to fix it",
      "target": {{
        "text": "exact text to find and replace (if applicable)",
        "section": "section name where this applies (e.g., Claims, Abstract, etc.)",
        "position": "before/after/replace"
      }},
      "replacement": {{
        "type": "add/replace/insert",
        "text": "COMPLETE formatted text to add or replace with"
      }}
    }}
  ],
  "recommendations": ["recommendation1", "recommendation2"]
}}

IMPORTANT: 
- For missing sections, provide the complete section template in replacement.text
- For punctuation fixes, provide the exact punctuation mark in replacement.text
- For antecedent basis, provide the corrected phrase in replacement.text
- Always include target.text when replacing existing content
- Use target.section to specify where in the document structure this applies"""

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
            
            logger.info(f"STRUCTURE AGENT: AI validation complete - confidence: {result.get('confidence', 0)}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"STRUCTURE AGENT: JSON parse error: {e}")
            return {
                "confidence": 0.5,
                "issues": [{
                    "type": "analysis_error",
                    "severity": "low",
                    "description": "AI response parsing failed",
                    "suggestion": "Manual review recommended"
                }],
                "recommendations": []
            }
        except Exception as e:
            logger.error(f"STRUCTURE AGENT: AI validation failed: {e}")
            return {
                "confidence": 0.5,
                "issues": [{
                    "type": "analysis_error",
                    "severity": "low",
                    "description": f"Analysis error: {str(e)}",
                    "suggestion": "Manual review recommended"
                }],
                "recommendations": []
            }
