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
    """
    Legal compliance agent for patent regulatory validation.
    Simplified version focusing on essential compliance checks.
    """
    
    def __init__(self, memory):
        super().__init__("legal", memory)

    async def analyze(self, state: PatentAnalysisState, stream_callback=None) -> Dict[str, Any]:
        """
        Analyze legal compliance and regulatory requirements with memory-enhanced learning.

        Args:
            state: Current workflow state
            stream_callback: Optional callback for streaming progress updates

        Returns:
            Legal compliance analysis results
        """

        logger.info(f"\n🔍 LEGAL AGENT: ===== STARTING ANALYSIS =====")
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "parallel_analysis",
                "agent": "legal",
                "message": "🔍 Starting memory-enhanced legal compliance analysis..."
            })

        logger.info(f"⚖️  LEGAL AGENT: Document ID: {state.get('document_id', 'Unknown')}")

        # NEW: Learn from historical legal analyses
        similar_cases = state.get("similar_cases", [])
        historical_insights = self._learn_legal_patterns(similar_cases)

        if historical_insights["patterns_found"] > 0:
            logger.info(f"🧠 LEGAL AGENT: Learning from {historical_insights['patterns_found']} similar legal analyses")
            logger.info(f"🧠 LEGAL AGENT: Common legal issues: {historical_insights['common_issues'][:3]}")
            if stream_callback:
                await stream_callback({
                    
                    "status": "analyzing",
                    "phase": "parallel_analysis",
                    "agent": "legal",
                    "message": f"🧠 Applied learning from {historical_insights['patterns_found']} similar patent reviews"
                })
        
        # Get structured document from structure agent
        structure_analysis = state.get("structure_analysis", {})
        parsed_document = structure_analysis.get("parsed_document", {})
        logger.info(f"⚖️  LEGAL AGENT: Received structured document with {len(parsed_document.get('claims', []))} claims")
        logger.info(f"⚖️  LEGAL AGENT: Structure analysis keys: {list(structure_analysis.keys())}")
        logger.info(f"⚖️  LEGAL AGENT: Parsed document keys: {list(parsed_document.keys())}")
        
        # Use HTTP tools to search for relevant regulations
        logger.info(f"🔍 LEGAL AGENT: Searching for 35 USC regulations...")
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "parallel_analysis",
                "agent": "legal",
                "message": "🔍 Searching for 35 USC regulations..."
            })
        regulatory_info = await http_search_tool.search_legal_regulations("35USC", "112")
        logger.info(f"🔍 LEGAL AGENT: Regulatory search complete")
        logger.info(f"🔍 LEGAL AGENT: Found {len(regulatory_info.get('regulations', {}))} regulatory sections")
        logger.info(f"🔍 LEGAL AGENT: Regulatory info keys: {list(regulatory_info.keys())}")
        
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "parallel_analysis",
                "agent": "legal",
                "message": f"🔍 Found {len(regulatory_info.get('regulations', {}))} regulatory sections"
            })
        
        # Search for related patent prior art using HTTP tools
        title = parsed_document.get("title", "")
        logger.info(f"🔍 LEGAL AGENT: Document title: '{title}'")
        if title and title != "Title not found":
            logger.info(f"🔍 LEGAL AGENT: Searching for prior art related to: '{title}'")
            if stream_callback:
                await stream_callback({
                    "status": "analyzing",
                    "phase": "parallel_analysis",
                    "agent": "legal",
                    "message": f"🔍 Searching for prior art: '{title[:50]}...'"
                })
                
            prior_art_search = await http_search_tool.search_patents_online(title, limit=3)
            logger.info(f"🔍 LEGAL AGENT: Prior art search complete")
            logger.info(f"🔍 LEGAL AGENT: Found {prior_art_search.get('total_results', 0)} prior art patents")
            logger.info(f"🔍 LEGAL AGENT: Prior art keys: {list(prior_art_search.keys())}")
            
            if stream_callback:
                await stream_callback({
                    "status": "analyzing",
                    "phase": "parallel_analysis",
                    "agent": "legal",
                    "message": f"🔍 Prior art search complete - Found {prior_art_search.get('total_results', 0)} patents"
                })
        else:
            logger.info(f"🔍 LEGAL AGENT: No valid title found - skipping prior art search")
            prior_art_search = {"total_results": 0, "patents": []}
        
        # AI-powered comprehensive legal analysis
        logger.info(f"🤖 LEGAL AGENT: Starting comprehensive AI legal analysis...")
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "parallel_analysis", 
                "agent": "legal",
                "message": "🤖 Running AI comprehensive legal analysis..."
            })
        comprehensive_analysis = await self._ai_comprehensive_legal_analysis(
            parsed_document, 
            regulatory_info,
            prior_art_search,
            stream_callback
        )
        logger.info(f"🤖 LEGAL AGENT: AI comprehensive analysis COMPLETE")
        logger.info(f"🤖 LEGAL AGENT: Analysis keys: {list(comprehensive_analysis.keys())}")
        logger.info(f"🤖 LEGAL AGENT: Issues found: {len(comprehensive_analysis.get('issues', []))}")
        logger.info(f"🤖 LEGAL AGENT: Recommendations: {len(comprehensive_analysis.get('recommendations', []))}")
        logger.info(f"🤖 LEGAL AGENT: Conclusions: {len(comprehensive_analysis.get('conclusions', []))}")
        
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "parallel_analysis",
                "agent": "legal", 
                "message": f"🤖 Legal analysis complete - Found {len(comprehensive_analysis.get('issues', []))} issues"
            })
        
        # Extract issues and recommendations from comprehensive analysis
        all_issues = comprehensive_analysis.get("issues", [])
        all_recommendations = comprehensive_analysis.get("recommendations", [])
        all_conclusions = comprehensive_analysis.get("conclusions", [])

        logger.info(f"📊 LEGAL AGENT: Extracting final results...")
        logger.info(f"📊 LEGAL AGENT: Total issues: {len(all_issues)}")
        for i, issue in enumerate(all_issues):
            logger.info(f"📊 LEGAL AGENT: Issue {i+1}: {issue.get('description', 'no description')[:100]}...")

        # NEW: Enhance with historical successful recommendations
        if similar_cases:
            logger.info(f"💡 LEGAL AGENT: Enhancing with historical successful recommendations...")
            all_recommendations = self._enhance_with_historical_recommendations(
                all_recommendations,
                all_issues,
                similar_cases
            )
            logger.info(f"💡 LEGAL AGENT: Enhanced recommendations with historical context")
        
        logger.info(f"💡 LEGAL AGENT: Total recommendations: {len(all_recommendations)}")
        for i, rec in enumerate(all_recommendations):
            logger.info(f"💡 LEGAL AGENT: Recommendation {i+1}: {rec[:100] if isinstance(rec, str) else str(rec)[:100]}...")
        
        logger.info(f"⚖️  LEGAL AGENT: Total conclusions: {len(all_conclusions)}")
        for i, conclusion in enumerate(all_conclusions):
            logger.info(f"⚖️  LEGAL AGENT: Conclusion {i+1}: {conclusion[:100] if isinstance(conclusion, str) else str(conclusion)[:100]}...")
        
        findings = {
            "type": "legal_analysis",
            "comprehensive_analysis": comprehensive_analysis,
            "issues": all_issues,
            "recommendations": all_recommendations,
            "legal_conclusions": all_conclusions,
            "confidence": comprehensive_analysis.get("confidence", 0.5)
        }
        
        logger.info(f"\n✅ LEGAL AGENT: ===== ANALYSIS COMPLETE =====")
        logger.info(f"✅ LEGAL AGENT: Final results summary:")
        logger.info(f"   - Total Issues: {len(all_issues)}")
        logger.info(f"   - Recommendations: {len(all_recommendations)}")
        logger.info(f"   - Conclusions: {len(all_conclusions)}")
        logger.info(f"   - Confidence: {findings.get('confidence', 'N/A')}")
        
        return findings

    async def _ai_comprehensive_legal_analysis(
        self, 
        parsed_doc: Dict[str, Any], 
        regulatory_info: Dict[str, Any],
        prior_art_search: Dict[str, Any],
        stream_callback=None
    ) -> Dict[str, Any]:
        """
        Comprehensive AI analysis that synthesizes all legal aspects and generates
        holistic conclusions and recommendations.
        """
        
        logger.info(f"🤖 AI LEGAL ANALYSIS: Starting comprehensive legal analysis...")
        
        api_key = os.getenv("OPENAI_API_KEY")
        logger.info(f"🤖 AI LEGAL ANALYSIS: OpenAI API key present: {bool(api_key)}")
        if not api_key:
            logger.info(f"🤖 AI LEGAL ANALYSIS: No API key - using fallback")
            return {
                "issues": [],
                "recommendations": ["Legal review recommended"],
                "conclusions": ["Unable to perform comprehensive analysis"]
            }
        
        try:
            logger.info(f"🤖 AI LEGAL ANALYSIS: Creating OpenAI client")
            client = openai.OpenAI(api_key=api_key)
            
            # Prepare comprehensive analysis context
            logger.info(f"🤖 AI LEGAL ANALYSIS: Preparing analysis context...")
            title = parsed_doc.get("title", "")
            abstract = parsed_doc.get("abstract", "")[:300] 
            detailed_desc = parsed_doc.get("detailed_description", "")[:500]
            claims = parsed_doc.get("claims", [])
            claims_count = len(claims)
            prior_art_count = prior_art_search.get("total_results", 0)
            
            logger.info(f"🤖 AI LEGAL ANALYSIS: Context prepared - Title: '{title}', Claims: {claims_count}, Prior Art: {prior_art_count}")
            logger.info(f"🤖 AI LEGAL ANALYSIS: Abstract length: {len(abstract)}, Description length: {len(detailed_desc)}")
            
            # Prepare claims text for analysis
            logger.info(f"🤖 AI LEGAL ANALYSIS: Preparing claims text from first {min(3, len(claims))} claims")
            claims_text = ""
            for i, claim in enumerate(claims[:3]):  # First 3 claims
                claim_preview = claim.get('text', '')[:200]
                claims_text += f"Claim {claim.get('number', i+1)}: {claim_preview}\n"
                logger.info(f"🤖 AI LEGAL ANALYSIS: Added claim {claim.get('number', i+1)} ({len(claim_preview)} chars)")
            
            prompt = f"""As a patent law expert, provide a comprehensive legal analysis of this patent application:

PATENT OVERVIEW:
- Title: {title}
- Claims Count: {claims_count}
- Prior Art Found: {prior_art_count} related patents

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

Respond in JSON format:
{{
  "conclusions": ["conclusion 1", "conclusion 2", "conclusion 3"],
  "issues": [
    {{
      "type": "legal_compliance", 
      "description": "issue description", 
      "severity": "high/medium/low", 
      "suggestion": "specific actionable solution to fix this issue",
      "legal_basis": "relevant law/rule"
    }}
  ],
  "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"],
  "filing_strategy": "brief strategic guidance",
  "overall_assessment": "summary of patent's legal readiness"
}}"""

            logger.info(f"🤖 AI LEGAL ANALYSIS: Making API call to gpt-4-turbo-preview")
            logger.info(f"🤖 AI LEGAL ANALYSIS: Prompt length: {len(prompt)} chars")

            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.3
            )

            logger.info(f"🤖 AI LEGAL ANALYSIS: API call successful")
            logger.info(f"🤖 AI LEGAL ANALYSIS: Response usage: {response.usage}")
            logger.info(f"🤖 AI LEGAL ANALYSIS: Response finish_reason: {response.choices[0].finish_reason}")
            
            raw_content = response.choices[0].message.content.strip()
            logger.info(f"🤖 AI LEGAL ANALYSIS: Raw response length: {len(raw_content)}")
            logger.info(f"🤖 AI LEGAL ANALYSIS: Raw response: {raw_content[:500]}...")
            
            logger.info(f"🤖 AI LEGAL ANALYSIS: Cleaning JSON response...")
            # Remove ```json wrapper if present
            cleaned_content = raw_content
            if cleaned_content.startswith('```json'):
                cleaned_content = cleaned_content[7:]  # Remove ```json
            if cleaned_content.endswith('```'):
                cleaned_content = cleaned_content[:-3]  # Remove closing ```
            cleaned_content = cleaned_content.strip()
            logger.info(f"🤖 AI LEGAL ANALYSIS: Cleaned response length: {len(cleaned_content)}")
            
            logger.info(f"🤖 AI LEGAL ANALYSIS: Attempting JSON parse...")
            result = json.loads(cleaned_content)
            logger.info(f"🤖 AI LEGAL ANALYSIS: JSON parse successful")
            logger.info(f"🤖 AI LEGAL ANALYSIS: Parsed result keys: {list(result.keys())}")
            logger.info(f"🤖 AI LEGAL ANALYSIS: Conclusions count: {len(result.get('conclusions', []))}")
            logger.info(f"🤖 AI LEGAL ANALYSIS: Issues count: {len(result.get('issues', []))}")
            logger.info(f"🤖 AI LEGAL ANALYSIS: Recommendations count: {len(result.get('recommendations', []))}")
            
            return {
                "conclusions": result.get("conclusions", []),
                "issues": result.get("issues", []),
                "recommendations": result.get("recommendations", []),
                "filing_strategy": result.get("filing_strategy", ""),
                "overall_assessment": result.get("overall_assessment", ""),
                "comprehensive_analysis": True
            }

        except json.JSONDecodeError as e:
            logger.error(f"🚨 AI LEGAL ANALYSIS: JSON DECODE ERROR: {e}")
            logger.error(f"🚨 AI LEGAL ANALYSIS: Failed to parse response: {raw_content if 'raw_content' in locals() else 'No raw content available'}")
            return {
                "issues": [{"description": "AI legal analysis failed - JSON parsing error", "severity": "high", "legal_basis": "Analysis Error"}],
                "recommendations": ["Legal review recommended due to analysis error"],
                "conclusions": ["Comprehensive analysis failed"],
                "comprehensive_analysis": False
            }
        except Exception as e:
            logger.error(f"🚨 AI LEGAL ANALYSIS: GENERAL ERROR: {e}")
            logger.error(f"🚨 AI LEGAL ANALYSIS: Error type: {type(e).__name__}")
            import traceback
            logger.error(f"🚨 AI LEGAL ANALYSIS: Traceback: {traceback.format_exc()}")
            return {
                "issues": [{"description": f"AI legal analysis failed: {str(e)}", "severity": "high", "legal_basis": "Analysis Error"}],
                "recommendations": ["Legal review recommended due to analysis error"],
                "conclusions": ["Comprehensive analysis unavailable"],
                "comprehensive_analysis": False
            }

    def _learn_legal_patterns(self, similar_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Learn from historical legal analyses to identify common compliance issues.
        Makes the memory system useful for legal review.

        Returns:
            patterns_found: number of similar cases
            common_issues: frequently occurring legal issues
            avg_confidence: average confidence from similar cases
        """
        from collections import Counter

        if not similar_cases:
            return {
                "patterns_found": 0,
                "common_issues": [],
                "avg_confidence": 0.0
            }

        issue_types = []
        confidences = []

        for case in similar_cases:
            agent_findings = case.get("agent_findings", {})
            legal_findings = agent_findings.get("legal", {})

            if legal_findings:
                # Extract issue types
                for issue in legal_findings.get("issues", []):
                    issue_type = issue.get("type", issue.get("legal_basis", "unknown"))
                    issue_types.append(issue_type)

                # Track confidence
                confidence = legal_findings.get("confidence", 0.0)
                if confidence > 0:
                    confidences.append(confidence)

        # Identify most common legal issues
        issue_counter = Counter(issue_types)
        common_issues = [issue for issue, count in issue_counter.most_common(5)]

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "patterns_found": len(similar_cases),
            "common_issues": common_issues,
            "avg_confidence": round(avg_confidence, 2)
        }

    def _enhance_with_historical_recommendations(
        self,
        current_recommendations: List[str],
        current_issues: List[Dict[str, Any]],
        similar_cases: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Enhance recommendations by learning from successful historical cases.
        Demonstrates cross-session learning in action.

        Args:
            current_recommendations: Generated recommendations
            current_issues: Issues found in current analysis
            similar_cases: Historical similar analyses

        Returns:
            Enhanced recommendations with historical context
        """
        if not similar_cases or not current_issues:
            return current_recommendations

        # Build recommendation library from history
        issue_to_recommendations = {}

        for case in similar_cases:
            agent_findings = case.get("agent_findings", {})
            legal_findings = agent_findings.get("legal", {})

            historical_issues = legal_findings.get("issues", [])
            historical_recs = legal_findings.get("recommendations", [])

            # Map recommendations to issues
            for issue in historical_issues:
                issue_type = issue.get("type", issue.get("legal_basis", ""))
                if issue_type and historical_recs:
                    if issue_type not in issue_to_recommendations:
                        issue_to_recommendations[issue_type] = []
                    issue_to_recommendations[issue_type].extend(historical_recs)

        # Add historically successful recommendations
        enhanced_recommendations = list(current_recommendations)  # Copy

        for issue in current_issues:
            issue_type = issue.get("type", issue.get("legal_basis", ""))

            if issue_type in issue_to_recommendations:
                historical_recs = issue_to_recommendations[issue_type]

                # Pick most common recommendation
                from collections import Counter
                rec_counter = Counter([r for r in historical_recs if isinstance(r, str)])
                if rec_counter:
                    best_rec, usage_count = rec_counter.most_common(1)[0]

                    # Add if not already present
                    if best_rec not in enhanced_recommendations:
                        enhanced_recommendations.append(
                            f"{best_rec} (Historical success: used {usage_count}x)"
                        )
                        logger.info(f"💡 LEGAL AGENT: Added historical recommendation for {issue_type}")

        return enhanced_recommendations
