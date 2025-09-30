from typing import Dict, Any, List
from datetime import datetime
import openai
import os
import json

from .base_agent import BasePatentAgent
from ..workflow.patent_state import PatentAnalysisState
from ..tools.http_search_tools import http_search_tool


class LegalComplianceAgent(BasePatentAgent):
    """
    Legal compliance agent for patent regulatory validation.
    Simplified version focusing on essential compliance checks.
    """
    
    def __init__(self, memory):
        super().__init__("legal", memory)

    async def analyze(self, state: PatentAnalysisState, stream_callback=None) -> Dict[str, Any]:
        """
        Analyze legal compliance and regulatory requirements.
        
        Args:
            state: Current workflow state
            stream_callback: Optional callback for streaming progress updates
            
        Returns:
            Legal compliance analysis results
        """
        
        print(f"\n🔍 LEGAL AGENT: ===== STARTING ANALYSIS =====")
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "parallel_analysis", 
                "agent": "legal",
                "message": "🔍 Starting legal compliance analysis..."
            })
            
        print(f"⚖️  LEGAL AGENT: Document ID: {state.get('document_id', 'Unknown')}")
        
        # Get structured document from structure agent
        structure_analysis = state.get("structure_analysis", {})
        parsed_document = structure_analysis.get("parsed_document", {})
        print(f"⚖️  LEGAL AGENT: Received structured document with {len(parsed_document.get('claims', []))} claims")
        print(f"⚖️  LEGAL AGENT: Structure analysis keys: {list(structure_analysis.keys())}")
        print(f"⚖️  LEGAL AGENT: Parsed document keys: {list(parsed_document.keys())}")
        
        # Use HTTP tools to search for relevant regulations
        print(f"🔍 LEGAL AGENT: Searching for 35 USC regulations...")
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "parallel_analysis",
                "agent": "legal",
                "message": "🔍 Searching for 35 USC regulations..."
            })
        regulatory_info = await http_search_tool.search_legal_regulations("35USC", "112")
        print(f"🔍 LEGAL AGENT: Regulatory search complete")
        print(f"🔍 LEGAL AGENT: Found {len(regulatory_info.get('regulations', {}))} regulatory sections")
        print(f"🔍 LEGAL AGENT: Regulatory info keys: {list(regulatory_info.keys())}")
        
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "parallel_analysis",
                "agent": "legal",
                "message": f"🔍 Found {len(regulatory_info.get('regulations', {}))} regulatory sections"
            })
        
        # Search for related patent prior art using HTTP tools
        title = parsed_document.get("title", "")
        print(f"🔍 LEGAL AGENT: Document title: '{title}'")
        if title and title != "Title not found":
            print(f"🔍 LEGAL AGENT: Searching for prior art related to: '{title}'")
            if stream_callback:
                await stream_callback({
                    "status": "analyzing",
                    "phase": "parallel_analysis",
                    "agent": "legal",
                    "message": f"🔍 Searching for prior art: '{title[:50]}...'"
                })
                
            prior_art_search = await http_search_tool.search_patents_online(title, limit=3)
            print(f"🔍 LEGAL AGENT: Prior art search complete")
            print(f"🔍 LEGAL AGENT: Found {prior_art_search.get('total_results', 0)} prior art patents")
            print(f"🔍 LEGAL AGENT: Prior art keys: {list(prior_art_search.keys())}")
            
            if stream_callback:
                await stream_callback({
                    "status": "analyzing",
                    "phase": "parallel_analysis",
                    "agent": "legal",
                    "message": f"🔍 Prior art search complete - Found {prior_art_search.get('total_results', 0)} patents"
                })
        else:
            print(f"🔍 LEGAL AGENT: No valid title found - skipping prior art search")
            prior_art_search = {"total_results": 0, "patents": []}
        
        # AI-powered comprehensive legal analysis
        print(f"🤖 LEGAL AGENT: Starting comprehensive AI legal analysis...")
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
        print(f"🤖 LEGAL AGENT: AI comprehensive analysis COMPLETE")
        print(f"🤖 LEGAL AGENT: Analysis keys: {list(comprehensive_analysis.keys())}")
        print(f"🤖 LEGAL AGENT: Issues found: {len(comprehensive_analysis.get('issues', []))}")
        print(f"🤖 LEGAL AGENT: Recommendations: {len(comprehensive_analysis.get('recommendations', []))}")
        print(f"🤖 LEGAL AGENT: Conclusions: {len(comprehensive_analysis.get('conclusions', []))}")
        
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
        
        print(f"📊 LEGAL AGENT: Extracting final results...")
        print(f"📊 LEGAL AGENT: Total issues: {len(all_issues)}")
        for i, issue in enumerate(all_issues):
            print(f"📊 LEGAL AGENT: Issue {i+1}: {issue.get('description', 'no description')[:100]}...")
        
        print(f"💡 LEGAL AGENT: Total recommendations: {len(all_recommendations)}")
        for i, rec in enumerate(all_recommendations):
            print(f"💡 LEGAL AGENT: Recommendation {i+1}: {rec[:100] if isinstance(rec, str) else str(rec)[:100]}...")
        
        print(f"⚖️  LEGAL AGENT: Total conclusions: {len(all_conclusions)}")
        for i, conclusion in enumerate(all_conclusions):
            print(f"⚖️  LEGAL AGENT: Conclusion {i+1}: {conclusion[:100] if isinstance(conclusion, str) else str(conclusion)[:100]}...")
        
        findings = {
            "type": "legal_analysis",
            "comprehensive_analysis": comprehensive_analysis,
            "issues": all_issues,
            "recommendations": all_recommendations,
            "legal_conclusions": all_conclusions,
            "confidence": comprehensive_analysis.get("confidence", 0.5)
        }
        
        print(f"\n✅ LEGAL AGENT: ===== ANALYSIS COMPLETE =====")
        print(f"✅ LEGAL AGENT: Final results summary:")
        print(f"   - Total Issues: {len(all_issues)}")
        print(f"   - Recommendations: {len(all_recommendations)}")
        print(f"   - Conclusions: {len(all_conclusions)}")
        print(f"   - Confidence: {findings.get('confidence', 'N/A')}")
        
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
        
        print(f"🤖 AI LEGAL ANALYSIS: Starting comprehensive legal analysis...")
        
        api_key = os.getenv("OPENAI_API_KEY")
        print(f"🤖 AI LEGAL ANALYSIS: OpenAI API key present: {bool(api_key)}")
        if not api_key:
            print(f"🤖 AI LEGAL ANALYSIS: No API key - using fallback")
            return {
                "issues": [],
                "recommendations": ["Legal review recommended"],
                "conclusions": ["Unable to perform comprehensive analysis"]
            }
        
        try:
            print(f"🤖 AI LEGAL ANALYSIS: Creating OpenAI client")
            client = openai.OpenAI(api_key=api_key)
            
            # Prepare comprehensive analysis context
            print(f"🤖 AI LEGAL ANALYSIS: Preparing analysis context...")
            title = parsed_doc.get("title", "")
            abstract = parsed_doc.get("abstract", "")[:300] 
            detailed_desc = parsed_doc.get("detailed_description", "")[:500]
            claims = parsed_doc.get("claims", [])
            claims_count = len(claims)
            prior_art_count = prior_art_search.get("total_results", 0)
            
            print(f"🤖 AI LEGAL ANALYSIS: Context prepared - Title: '{title}', Claims: {claims_count}, Prior Art: {prior_art_count}")
            print(f"🤖 AI LEGAL ANALYSIS: Abstract length: {len(abstract)}, Description length: {len(detailed_desc)}")
            
            # Prepare claims text for analysis
            print(f"🤖 AI LEGAL ANALYSIS: Preparing claims text from first {min(3, len(claims))} claims")
            claims_text = ""
            for i, claim in enumerate(claims[:3]):  # First 3 claims
                claim_preview = claim.get('text', '')[:200]
                claims_text += f"Claim {claim.get('number', i+1)}: {claim_preview}\n"
                print(f"🤖 AI LEGAL ANALYSIS: Added claim {claim.get('number', i+1)} ({len(claim_preview)} chars)")
            
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

            print(f"🤖 AI LEGAL ANALYSIS: Making API call to gpt-4-turbo-preview")
            print(f"🤖 AI LEGAL ANALYSIS: Prompt length: {len(prompt)} chars")

            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.3
            )

            print(f"🤖 AI LEGAL ANALYSIS: API call successful")
            print(f"🤖 AI LEGAL ANALYSIS: Response usage: {response.usage}")
            print(f"🤖 AI LEGAL ANALYSIS: Response finish_reason: {response.choices[0].finish_reason}")
            
            raw_content = response.choices[0].message.content.strip()
            print(f"🤖 AI LEGAL ANALYSIS: Raw response length: {len(raw_content)}")
            print(f"🤖 AI LEGAL ANALYSIS: Raw response: {raw_content[:500]}...")
            
            print(f"🤖 AI LEGAL ANALYSIS: Cleaning JSON response...")
            # Remove ```json wrapper if present
            cleaned_content = raw_content
            if cleaned_content.startswith('```json'):
                cleaned_content = cleaned_content[7:]  # Remove ```json
            if cleaned_content.endswith('```'):
                cleaned_content = cleaned_content[:-3]  # Remove closing ```
            cleaned_content = cleaned_content.strip()
            print(f"🤖 AI LEGAL ANALYSIS: Cleaned response length: {len(cleaned_content)}")
            
            print(f"🤖 AI LEGAL ANALYSIS: Attempting JSON parse...")
            result = json.loads(cleaned_content)
            print(f"🤖 AI LEGAL ANALYSIS: JSON parse successful")
            print(f"🤖 AI LEGAL ANALYSIS: Parsed result keys: {list(result.keys())}")
            print(f"🤖 AI LEGAL ANALYSIS: Conclusions count: {len(result.get('conclusions', []))}")
            print(f"🤖 AI LEGAL ANALYSIS: Issues count: {len(result.get('issues', []))}")
            print(f"🤖 AI LEGAL ANALYSIS: Recommendations count: {len(result.get('recommendations', []))}")
            
            return {
                "conclusions": result.get("conclusions", []),
                "issues": result.get("issues", []),
                "recommendations": result.get("recommendations", []),
                "filing_strategy": result.get("filing_strategy", ""),
                "overall_assessment": result.get("overall_assessment", ""),
                "comprehensive_analysis": True
            }

        except json.JSONDecodeError as e:
            print(f"🚨 AI LEGAL ANALYSIS: JSON DECODE ERROR: {e}")
            print(f"🚨 AI LEGAL ANALYSIS: Failed to parse response: {raw_content if 'raw_content' in locals() else 'No raw content available'}")
            return {
                "issues": [{"description": "AI legal analysis failed - JSON parsing error", "severity": "high", "legal_basis": "Analysis Error"}],
                "recommendations": ["Legal review recommended due to analysis error"],
                "conclusions": ["Comprehensive analysis failed"],
                "comprehensive_analysis": False
            }
        except Exception as e:
            print(f"🚨 AI LEGAL ANALYSIS: GENERAL ERROR: {e}")
            print(f"🚨 AI LEGAL ANALYSIS: Error type: {type(e).__name__}")
            import traceback
            print(f"🚨 AI LEGAL ANALYSIS: Traceback: {traceback.format_exc()}")
            return {
                "issues": [{"description": f"AI legal analysis failed: {str(e)}", "severity": "high", "legal_basis": "Analysis Error"}],
                "recommendations": ["Legal review recommended due to analysis error"],
                "conclusions": ["Comprehensive analysis unavailable"],
                "comprehensive_analysis": False
            }
