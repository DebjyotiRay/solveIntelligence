from typing import Dict, Any, List
from datetime import datetime
import openai
import os
import json
import logging

from .base_agent import BasePatentAgent
from ..workflow.patent_state import PatentAnalysisState
from ..tools.http_search_tools import http_search_tool

logger = logging.getLogger(__name__)


class LegalComplianceAgent(BasePatentAgent):
    
    def __init__(self):
        super().__init__("legal")

    async def analyze(self, state: PatentAnalysisState, stream_callback=None) -> Dict[str, Any]:
        """
        Analyze legal compliance and regulatory requirements with memory-enhanced learning.

        Args:
            state: Current workflow state
            stream_callback: Optional callback for streaming progress updates

        Returns:
            Legal compliance analysis results
        """

        logger.info("LEGAL AGENT: Starting analysis")
        
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "parallel_analysis",
                "agent": "legal",
                "message": "⚖️ Starting legal compliance analysis..."
            })

        structure_analysis = state.get("structure_analysis", {})
        parsed_document = structure_analysis.get("parsed_document", {})
        logger.info(f"LEGAL AGENT: Received document with {len(parsed_document.get('claims', []))} claims")
        
        regulatory_info = await http_search_tool.search_legal_regulations("35USC", "112")
        logger.info(f"LEGAL AGENT: Found {len(regulatory_info.get('regulations', {}))} regulatory sections")
        
        title = parsed_document.get("title", "")
        if title and title != "Title not found":
            prior_art_search = await http_search_tool.search_patents_online(title, limit=3)
            logger.info(f"LEGAL AGENT: Found {prior_art_search.get('total_results', 0)} prior art patents")
        else:
            prior_art_search = {"total_results": 0, "patents": []}
        
        comprehensive_analysis = await self._ai_comprehensive_legal_analysis(
            parsed_document, 
            regulatory_info,
            prior_art_search
        )
        
        logger.info(f"LEGAL AGENT: Analysis complete - {len(comprehensive_analysis.get('issues', []))} issues found")
        
        findings = {
            "type": "legal_analysis",
            "comprehensive_analysis": comprehensive_analysis,
            "issues": comprehensive_analysis.get("issues", []),
            "recommendations": comprehensive_analysis.get("recommendations", []),
            "legal_conclusions": comprehensive_analysis.get("conclusions", []),
            "confidence": comprehensive_analysis.get("confidence", 0.5)
        }
        
        return findings

    async def _ai_comprehensive_legal_analysis(
        self, 
        parsed_doc: Dict[str, Any], 
        regulatory_info: Dict[str, Any],
        prior_art_search: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {
                "issues": [],
                "recommendations": ["Legal review recommended"],
                "conclusions": ["Unable to perform analysis"],
                "confidence": 0.5
            }
        
        try:
            client = openai.OpenAI(api_key=api_key)
            
            title = parsed_doc.get("title", "")
            abstract = parsed_doc.get("abstract", "")[:300] 
            detailed_desc = parsed_doc.get("detailed_description", "")[:500]
            claims = parsed_doc.get("claims", [])
            
            claims_text = ""
            for i, claim in enumerate(claims[:3]):
                claims_text += f"Claim {claim.get('number', i+1)}: {claim.get('text', '')[:200]}\n"
            
            prompt = f"""As a patent law expert, provide a comprehensive legal analysis of this patent application:

PATENT OVERVIEW:
- Title: {title}
- Claims Count: {len(claims)}
- Prior Art Found: {prior_art_search.get('total_results', 0)} related patents

PATENT CONTENT:
- Abstract: {abstract}
- Detailed Description: {detailed_desc}
- Key Claims: {claims_text}

REGULATORY CONTEXT:
- Regulations Retrieved: {len(regulatory_info.get('regulations', {}))} sections

Analyze this patent for complete legal compliance including:

1. 35 USC 112(a) - Written Description & Enablement
2. 35 USC 112(b) - Claims Definiteness  
3. 35 USC 101 - Subject Matter Eligibility
4. Overall patentability and filing strategy

Based on this comprehensive analysis, provide:

1. LEGAL CONCLUSIONS (3-4 high-level conclusions about the patent's legal standing)
2. PRIORITY ISSUES (top 3-5 legal issues that must be addressed)  
3. STRATEGIC RECOMMENDATIONS (3-5 actionable recommendations for filing strategy)

Focus on practical legal guidance that considers all aspects together.

For EACH issue, YOU MUST provide:
- Exact location (paragraph number if applicable, claim number, or section name)
- Specific text to find - THE ACTUAL WORDS that need changing (minimum 10-30 characters)
- Complete replacement text in proper format
- For spelling/grammar: Include the exact misspelled word in target.text and corrected word in replacement.text

CRITICAL FOR SPELLING/GRAMMAR/TERMINOLOGY:
- target.text MUST contain the EXACT incorrect word/phrase (e.g., "recieve" not just "spelling error")  
- replacement.text MUST contain the EXACT corrected word/phrase (e.g., "receive")
- Do NOT report generic errors - be specific: "Change 'substancially' to 'substantially' in Claim 1"

Respond in JSON format:
{{
  "conclusions": ["conclusion 1", "conclusion 2", "conclusion 3"],
  "issues": [
    {{
      "type": "legal_compliance", 
      "description": "issue description", 
      "severity": "high/medium/low",
      "paragraph": 1,
      "suggestion": "specific actionable solution to fix this issue",
      "legal_basis": "relevant law/rule",
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
  "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"],
  "filing_strategy": "brief strategic guidance",
  "overall_assessment": "summary of patent's legal readiness",
  "confidence": 0.0-1.0
}}

IMPORTANT:
- For missing required sections, provide the complete section template in replacement.text
- For claim definiteness issues, provide the corrected claim text
- For enablement issues, provide specific language additions
- Always include target.text when replacing existing content
- Use target.section to specify where in the document structure this applies"""

            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3
            )
            
            raw_content = response.choices[0].message.content.strip()
            
            cleaned_content = raw_content
            if cleaned_content.startswith('```json'):
                cleaned_content = cleaned_content[7:]
            if cleaned_content.endswith('```'):
                cleaned_content = cleaned_content[:-3]
            cleaned_content = cleaned_content.strip()
            
            result = json.loads(cleaned_content)
            
            return {
                "conclusions": result.get("conclusions", []),
                "issues": result.get("issues", []),
                "recommendations": result.get("recommendations", []),
                "filing_strategy": result.get("filing_strategy", ""),
                "overall_assessment": result.get("overall_assessment", ""),
                "confidence": result.get("confidence", 0.7),
                "comprehensive_analysis": True
            }

        except json.JSONDecodeError as e:
            logger.error(f"LEGAL AGENT: JSON parse error: {e}")
            return {
                "issues": [{"description": "AI legal analysis failed - JSON parsing error", "severity": "high", "legal_basis": "Analysis Error"}],
                "recommendations": ["Legal review recommended due to analysis error"],
                "conclusions": ["Comprehensive analysis failed"],
                "confidence": 0.5,
                "comprehensive_analysis": False
            }
        except Exception as e:
            logger.error(f"LEGAL AGENT: Analysis error: {e}")
            return {
                "issues": [{"description": f"AI legal analysis failed: {str(e)}", "severity": "high", "legal_basis": "Analysis Error"}],
                "recommendations": ["Legal review recommended due to analysis error"],
                "conclusions": ["Comprehensive analysis unavailable"],
                "confidence": 0.5,
                "comprehensive_analysis": False
            }
