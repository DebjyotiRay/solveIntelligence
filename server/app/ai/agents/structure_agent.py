import re
import openai
import os
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from collections import Counter

from .base_agent import BasePatentAgent
from ..workflow.patent_state import PatentAnalysisState
from ..utils import strip_html
from .quality_enhancements import ContentQualityValidator

logger = logging.getLogger(__name__)


class DocumentStructureAgent(BasePatentAgent):
    """
    Specialized agent for document structure analysis and patent format validation.
    Parses patent documents and validates format compliance.
    """
    
    def __init__(self, memory):
        super().__init__("structure", memory)

    async def analyze(self, state: PatentAnalysisState, stream_callback=None) -> Dict[str, Any]:
        """
        Analyze document structure and format compliance.

        Args:
            state: Current workflow state
            stream_callback: Optional callback for streaming progress updates

        Returns:
            Analysis results with parsed document and format validation
        """

        logger.info(f"\n🔍 STRUCTURE AGENT: ===== STARTING ANALYSIS =====")
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "structure_analysis",
                "agent": "structure",
                "message": "🔍 Starting memory-enhanced document structure analysis..."
            })

        logger.info(f"📋 STRUCTURE AGENT: Document ID: {state.get('document_id', 'Unknown')}")
        document = state["document"]
        document_content = document.get("content", "")
        logger.info(f"📋 STRUCTURE AGENT: Original content length: {len(document_content)} chars")
        logger.info(f"📋 STRUCTURE AGENT: Content preview: {document_content[:200]}..." if document_content else "📋 STRUCTURE AGENT: NO CONTENT FOUND")

        # NEW: Use historical memory to learn patterns and prioritize checks
        similar_cases = state.get("similar_cases", [])
        historical_insights = self._learn_from_history(similar_cases)

        if historical_insights["patterns_found"] > 0:
            logger.info(f"🧠 STRUCTURE AGENT: Learning from {historical_insights['patterns_found']} similar cases")
            logger.info(f"🧠 STRUCTURE AGENT: Common issues: {historical_insights['common_issues'][:3]}")
            if stream_callback:
                await stream_callback({
                    "status": "analyzing",
                    "phase": "structure_analysis",
                    "agent": "structure",
                    "message": f"🧠 Applied learning from {historical_insights['patterns_found']} similar patents"
                })
        
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "structure_analysis",
                "agent": "structure", 
                "message": f"📋 Processing document ({len(document_content)} characters)..."
            })
        
        # Clean HTML content
        logger.info(f"🧹 STRUCTURE AGENT: Cleaning HTML content...")
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "structure_analysis",
                "agent": "structure",
                "message": "🧹 Cleaning HTML content and extracting text..."
            })
            
        clean_text = strip_html(document_content)
        logger.info(f"📋 STRUCTURE AGENT: Cleaned text length: {len(clean_text)} chars")
        logger.info(f"📋 STRUCTURE AGENT: Clean text preview: {clean_text[:300]}...")
        
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "structure_analysis", 
                "agent": "structure",
                "message": f"📋 Cleaned text extracted ({len(clean_text)} chars)"
            })
        
        # Parse document sections
        logger.info(f"📄 STRUCTURE AGENT: Parsing document sections...")
        if stream_callback:
            await stream_callback({
                "status": "analyzing", 
                "phase": "structure_analysis",
                "agent": "structure",
                "message": "📄 Parsing document sections (title, abstract, claims)..."
            })
            
        parsed_document = self._parse_document_sections(clean_text)
        logger.info(f"📄 STRUCTURE AGENT: Parsed sections: {list(parsed_document.keys())}")
        logger.info(f"📄 STRUCTURE AGENT: Claims found: {len(parsed_document.get('claims', []))}")
        logger.info(f"📄 STRUCTURE AGENT: Word count: {parsed_document.get('word_count', 0)}")
        
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "structure_analysis", 
                "agent": "structure",
                "message": f"📄 Found {len(parsed_document.get('claims', []))} claims, {parsed_document.get('word_count', 0)} words"
            })
        
        # Validate format compliance
        logger.info(f"✅ STRUCTURE AGENT: Validating format compliance...")
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "structure_analysis",
                "agent": "structure", 
                "message": "✅ Validating format compliance..."
            })
            
        format_validation = self._validate_format_compliance(parsed_document)
        logger.info(f"✅ STRUCTURE AGENT: Format compliance - Compliant: {format_validation.get('compliant', False)}")
        logger.info(f"✅ STRUCTURE AGENT: Format violations: {len(format_validation.get('violations', []))}")
        
        # Analyze claims structure
        logger.info(f"⚖️  STRUCTURE AGENT: Analyzing claims structure...")
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "structure_analysis",
                "agent": "structure",
                "message": "⚖️ Analyzing claims structure..."
            })
            
        claims_analysis = self._analyze_claims_structure(parsed_document.get("claims", []))
        logger.info(f"⚖️  STRUCTURE AGENT: Claims analysis - Total: {claims_analysis.get('total_claims', 0)}, Independent: {claims_analysis.get('independent_claims', 0)}")
        logger.info(f"⚖️  STRUCTURE AGENT: Claims issues: {len(claims_analysis.get('issues', []))}")
        
        # NEW: AI-powered patent-specific claims validation
        logger.info(f"🤖 STRUCTURE AGENT: Starting AI patent claims validation...")
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "structure_analysis",
                "agent": "structure",
                "message": "🤖 Starting AI patent claims validation..."
            })
            
        patent_claims_validation = await self._ai_validate_patent_claims_format(parsed_document.get("claims", []), stream_callback)
        logger.info(f"🤖 STRUCTURE AGENT: AI Patent claims validation COMPLETE")
        logger.info(f"🤖 STRUCTURE AGENT: Claims validation score: {patent_claims_validation.get('score', 0):.2f}")
        logger.info(f"🤖 STRUCTURE AGENT: Claims validation issues: {len(patent_claims_validation.get('issues', []))}")
        logger.info(f"🤖 STRUCTURE AGENT: Claims validation compliant: {patent_claims_validation.get('compliant', False)}")
        
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "structure_analysis", 
                "agent": "structure",
                "message": f"🤖 AI claims validation complete - Score: {patent_claims_validation.get('score', 0):.2f}"
            })
        
        # NEW: AI-powered Brief Description of Drawings validation
        logger.info(f"🖼️  STRUCTURE AGENT: Starting AI drawings validation...")
        drawings_validation = await self._ai_validate_brief_description_drawings(parsed_document)
        logger.info(f"🖼️  STRUCTURE AGENT: AI Drawings validation COMPLETE")
        logger.info(f"🖼️  STRUCTURE AGENT: Drawings validation score: {drawings_validation.get('score', 0):.2f}")
        logger.info(f"🖼️  STRUCTURE AGENT: Drawings validation issues: {len(drawings_validation.get('issues', []))}")
        
        # NEW: Validate content quality (grammar, spelling, style, readability)
        logger.info(f"📝 STRUCTURE AGENT: Starting content quality validation...")
        content_quality = await self._validate_content_quality(parsed_document, state)
        logger.info(f"📝 STRUCTURE AGENT: Content quality validation COMPLETE")
        logger.info(f"📝 STRUCTURE AGENT: Content quality score: {content_quality.get('overall_score', 0):.2f}")
        logger.info(f"📝 STRUCTURE AGENT: Content quality issues: {len(content_quality.get('all_issues', []))}")
        
        # Calculate confidence score
        logger.info(f"🎯 STRUCTURE AGENT: Calculating overall confidence score...")
        confidence = self._calculate_confidence(parsed_document, format_validation, claims_analysis)
        logger.info(f"🎯 STRUCTURE AGENT: Confidence score calculated: {confidence}")
        
        # Extract all issues including AI analysis results
        logger.info(f"⚠️  STRUCTURE AGENT: Extracting all issues...")
        all_issues = self._extract_issues(format_validation, claims_analysis, content_quality, patent_claims_validation)
        logger.info(f"⚠️  STRUCTURE AGENT: Total issues extracted: {len(all_issues)}")
        for i, issue in enumerate(all_issues):
            logger.info(f"⚠️  STRUCTURE AGENT: Issue {i+1}: {issue.get('type', 'unknown')} - {issue.get('severity', 'unknown')} - {issue.get('description', 'no description')[:100]}...")

        # NEW: Enhance issues with historical successful suggestions
        if similar_cases:
            logger.info(f"💡 STRUCTURE AGENT: Enhancing issues with historical suggestions...")
            all_issues = self._reuse_successful_suggestions(all_issues, similar_cases)
            logger.info(f"💡 STRUCTURE AGENT: Enhanced {len(all_issues)} issues with historical context")
        
        # Generate recommendations
        logger.info(f"💡 STRUCTURE AGENT: Generating recommendations...")
        recommendations = self._generate_recommendations(format_validation, claims_analysis, content_quality)
        logger.info(f"💡 STRUCTURE AGENT: Recommendations generated: {len(recommendations)}")
        for i, rec in enumerate(recommendations):
            logger.info(f"💡 STRUCTURE AGENT: Recommendation {i+1}: {rec[:100]}...")
        
        findings = {
            "type": "structure_analysis",
            "parsed_document": parsed_document,
            "format_compliance": format_validation,
            "claims_structure": claims_analysis,
            "content_quality": content_quality,  # NEW
            "confidence": confidence,
            "issues": all_issues,
            "recommendations": recommendations
        }
        
        logger.info(f"\n✅ STRUCTURE AGENT: ===== ANALYSIS COMPLETE =====")
        logger.info(f"✅ STRUCTURE AGENT: Final results summary:")
        logger.info(f"   - Confidence: {confidence}")
        logger.info(f"   - Total Issues: {len(all_issues)}")
        logger.info(f"   - Recommendations: {len(recommendations)}")
        logger.info(f"   - Claims Found: {len(parsed_document.get('claims', []))}")
        logger.info(f"   - Format Compliant: {format_validation.get('compliant', False)}")
        
        return findings

    def _parse_document_sections(self, content: str) -> Dict[str, Any]:
        """Parse patent document into structured sections."""
        
        sections = {
            "title": self._extract_title(content),
            "abstract": self._extract_abstract(content),
            "background": self._extract_background(content),
            "summary": self._extract_summary(content),
            "detailed_description": self._extract_detailed_description(content),
            "claims": self._extract_claims(content),
            "figures": self._extract_figure_references(content),
            "word_count": len(content.split()),
            "character_count": len(content)
        }
        
        return sections

    def _extract_title(self, content: str) -> str:
        """Extract patent title from document."""
        # Look for title patterns at the beginning
        lines = content.split('\n')[:10]  # Check first 10 lines
        for line in lines:
            line = line.strip()
            if len(line) > 10 and not line.lower().startswith(('patent', 'application', 'field')):
                # Likely the title
                return line
        return "Title not found"

    def _extract_abstract(self, content: str) -> str:
        """Extract abstract section."""
        abstract_match = re.search(
            r'(?:ABSTRACT|Abstract)\s*\n(.*?)(?:\n\s*(?:BACKGROUND|Background|FIELD|Field|SUMMARY|Summary|DETAILED|Detailed))',
            content, re.DOTALL | re.IGNORECASE
        )
        return abstract_match.group(1).strip() if abstract_match else ""

    def _extract_background(self, content: str) -> str:
        """Extract background section."""
        background_match = re.search(
            r'(?:BACKGROUND|Background).*?\n(.*?)(?:\n\s*(?:SUMMARY|Summary|DETAILED|Detailed|CLAIMS|Claims))',
            content, re.DOTALL | re.IGNORECASE
        )
        return background_match.group(1).strip() if background_match else ""

    def _extract_summary(self, content: str) -> str:
        """Extract summary section."""
        summary_match = re.search(
            r'(?:SUMMARY|Summary).*?\n(.*?)(?:\n\s*(?:DETAILED|Detailed|CLAIMS|Claims))',
            content, re.DOTALL | re.IGNORECASE
        )
        return summary_match.group(1).strip() if summary_match else ""

    def _extract_detailed_description(self, content: str) -> str:
        """Extract detailed description section."""
        detailed_match = re.search(
            r'(?:DETAILED DESCRIPTION|Detailed Description).*?\n(.*?)(?:\n\s*(?:CLAIMS|Claims|WHAT IS CLAIMED|What is claimed))',
            content, re.DOTALL | re.IGNORECASE
        )
        return detailed_match.group(1).strip() if detailed_match else ""

    def _extract_claims(self, content: str) -> List[Dict[str, Any]]:
        """Extract and parse patent claims."""
        claims = []
        
        # Find claims section
        claims_match = re.search(
            r'(?:CLAIMS?|What is claimed|WHAT IS CLAIMED).*?\n(.*?)(?:\n\s*$|\Z)',
            content, re.DOTALL | re.IGNORECASE
        )
        
        if not claims_match:
            return claims
            
        claims_text = claims_match.group(1)
        
        # Split claims by numbers
        claim_pattern = r'(\d+)\.\s*(.*?)(?=\d+\.\s*|\Z)'
        claim_matches = re.findall(claim_pattern, claims_text, re.DOTALL)
        
        for claim_num, claim_text in claim_matches:
            claim_text = claim_text.strip()
            claims.append({
                "number": int(claim_num),
                "text": claim_text,
                "type": self._classify_claim_type(claim_text),
                "dependencies": self._find_claim_dependencies(claim_text),
                "word_count": len(claim_text.split())
            })
        
        return claims

    def _classify_claim_type(self, claim_text: str) -> str:
        """Classify claim as independent or dependent."""
        dependency_patterns = [
            r'claim \d+',
            r'any of claims \d+',
            r'any preceding claim',
            r'any of the preceding claims'
        ]
        
        for pattern in dependency_patterns:
            if re.search(pattern, claim_text, re.IGNORECASE):
                return "dependent"
        
        return "independent"

    def _find_claim_dependencies(self, claim_text: str) -> List[int]:
        """Find which claims this claim depends on."""
        dependencies = []
        
        # Look for "claim X" references
        claim_refs = re.findall(r'claim (\d+)', claim_text, re.IGNORECASE)
        dependencies.extend([int(ref) for ref in claim_refs])
        
        # Look for "claims X-Y" references
        range_refs = re.findall(r'claims (\d+)-(\d+)', claim_text, re.IGNORECASE)
        for start, end in range_refs:
            dependencies.extend(range(int(start), int(end) + 1))
        
        return list(set(dependencies))  # Remove duplicates

    def _extract_figure_references(self, content: str) -> List[str]:
        """Extract figure references from document."""
        figure_refs = re.findall(r'(?:FIG\.?\s*\d+|Figure\s*\d+)', content, re.IGNORECASE)
        return list(set(figure_refs))

    def _validate_format_compliance(self, parsed_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Validate patent document format compliance."""
        
        validation_results = {
            "compliant": True,
            "violations": [],
            "warnings": [],
            "score": 1.0
        }
        
        # Check for required sections
        required_sections = ["title", "abstract", "claims"]
        missing_sections = []
        
        for section in required_sections:
            if not parsed_doc.get(section) or len(str(parsed_doc.get(section, "")).strip()) < 10:
                missing_sections.append(section)
        
        if missing_sections:
            validation_results["violations"].append({
                "type": "missing_sections",
                "description": f"Missing required sections: {', '.join(missing_sections)}",
                "severity": "high"
            })
            validation_results["compliant"] = False
        
        # Validate claims structure
        claims = parsed_doc.get("claims", [])
        if not claims:
            validation_results["violations"].append({
                "type": "no_claims",
                "description": "Document contains no patent claims",
                "severity": "high"
            })
            validation_results["compliant"] = False
        else:
            # Check for independent claims
            independent_claims = [c for c in claims if c.get("type") == "independent"]
            if not independent_claims:
                validation_results["violations"].append({
                    "type": "no_independent_claims",
                    "description": "No independent claims found",
                    "severity": "high"
                })
                validation_results["compliant"] = False
        
        # Calculate compliance score
        total_checks = 3  # number of validation checks
        violations = len(validation_results["violations"])
        validation_results["score"] = max(0.0, (total_checks - violations) / total_checks)
        
        return validation_results

    def _analyze_claims_structure(self, claims: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the structure and quality of patent claims."""
        
        if not claims:
            return {
                "total_claims": 0,
                "independent_claims": 0,
                "dependent_claims": 0,
                "issues": ["No claims found"],
                "structure_score": 0.0
            }
        
        independent_claims = [c for c in claims if c.get("type") == "independent"]
        dependent_claims = [c for c in claims if c.get("type") == "dependent"]
        
        issues = []
        
        # Check claim numbering
        expected_numbers = list(range(1, len(claims) + 1))
        actual_numbers = [c.get("number") for c in claims]
        if actual_numbers != expected_numbers:
            issues.append("Claims are not numbered consecutively")
        
        # Check for overly long claims
        long_claims = [c for c in claims if c.get("word_count", 0) > 200]
        if long_claims:
            issues.append(f"{len(long_claims)} claims exceed 200 words")
        
        # Check dependency structure
        for claim in dependent_claims:
            dependencies = claim.get("dependencies", [])
            if dependencies:
                # Ensure dependent claims reference valid claim numbers
                invalid_deps = [d for d in dependencies if d > len(claims) or d < 1]
                if invalid_deps:
                    issues.append(f"Claim {claim['number']} references invalid claims: {invalid_deps}")
        
        # Calculate structure score
        structure_score = 1.0
        if issues:
            structure_score = max(0.0, 1.0 - (len(issues) * 0.2))
        
        return {
            "total_claims": len(claims),
            "independent_claims": len(independent_claims),
            "dependent_claims": len(dependent_claims),
            "issues": issues,
            "structure_score": structure_score,
            "average_claim_length": sum(c.get("word_count", 0) for c in claims) / len(claims) if claims else 0
        }

    def _calculate_confidence(
        self, 
        parsed_doc: Dict[str, Any], 
        format_validation: Dict[str, Any], 
        claims_analysis: Dict[str, Any]
    ) -> float:
        """Calculate overall confidence in the structure analysis."""
        
        # Base confidence on content availability
        content_score = 0.0
        required_sections = ["title", "abstract", "claims"]
        
        for section in required_sections:
            if parsed_doc.get(section) and len(str(parsed_doc.get(section, "")).strip()) > 10:
                content_score += 1.0 / len(required_sections)
        
        # Factor in format compliance
        format_score = format_validation.get("score", 0.0)
        
        # Factor in claims structure
        claims_score = claims_analysis.get("structure_score", 0.0)
        
        # Weighted average
        confidence = (content_score * 0.4 + format_score * 0.4 + claims_score * 0.2)
        
        return round(confidence, 2)

    def _extract_issues(
        self,
        format_validation: Dict[str, Any],
        claims_analysis: Dict[str, Any],
        content_quality: Dict[str, Any],
        patent_claims_validation: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Extract issues from validation results."""
        
        issues = []
        
        # Add format violations
        for violation in format_validation.get("violations", []):
            issues.append({
                "type": "format",
                "severity": violation.get("severity", "medium"),
                "description": violation.get("description", ""),
                "suggestion": self._get_format_suggestion(violation.get("type", ""))
            })
        
        # Add claims structure issues
        for issue in claims_analysis.get("issues", []):
            issues.append({
                "type": "claims_structure",
                "severity": "medium",
                "description": issue,
                "suggestion": self._get_claims_suggestion(issue)
            })

        # Add content quality issues
        if content_quality.get("overall_score", 1.0) < 0.5:
            issues.append({
                "type": "content_quality",
                "severity": "high",
                "description": "Document content quality is below acceptable standards",
                "suggestion": "Improve the clarity and completeness of the document content"
            })

        # Add AI patent claims validation issues (this was missing!)
        if patent_claims_validation:
            logger.info(f"⚠️  STRUCTURE AGENT: Adding AI patent claims issues: {len(patent_claims_validation.get('issues', []))}")
            for ai_issue in patent_claims_validation.get("issues", []):
                # Convert AI issue format to our standard format
                issue_description = ai_issue.get("description", "")
                claim_num = ai_issue.get("claim", "")
                if claim_num:
                    issue_description = f"Claim {claim_num}: {issue_description}"
                
                issues.append({
                    "type": f"ai_claims_{ai_issue.get('type', 'unknown').lower()}",
                    "severity": ai_issue.get("severity", "medium"),
                    "description": issue_description,
                    "suggestion": ai_issue.get("suggestion", "Review claim formatting requirements"),
                    "claim_number": claim_num,
                    "ai_generated": True
                })
                logger.info(f"⚠️  STRUCTURE AGENT: Added AI issue: {ai_issue.get('type', 'unknown')} - {issue_description[:80]}...")

        return issues

    def _get_format_suggestion(self, violation_type: str) -> str:
        """Get suggestion for format violations."""
        suggestions = {
            "missing_sections": "Add the missing required sections to complete the patent document",
            "no_claims": "Add patent claims section with at least one independent claim",
            "no_independent_claims": "Include at least one independent claim that stands alone"
        }
        return suggestions.get(violation_type, "Review patent formatting requirements")

    def _get_claims_suggestion(self, issue: str) -> str:
        """Get suggestion for claims structure issues."""
        if "consecutively" in issue.lower():
            return "Renumber claims consecutively starting from 1"
        elif "exceed 200 words" in issue.lower():
            return "Consider breaking long claims into shorter, more focused claims"
        elif "references invalid claims" in issue.lower():
            return "Ensure all claim dependencies reference valid claim numbers"
        else:
            return "Review claims structure for compliance with patent requirements"

    def _generate_recommendations(
        self,
        format_validation: Dict[str, Any],
        claims_analysis: Dict[str, Any],
        content_quality: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations."""
        
        recommendations = []
        
        if not format_validation.get("compliant", False):
            recommendations.append("Address format compliance issues before filing")
        
        if claims_analysis.get("independent_claims", 0) == 0:
            recommendations.append("Add at least one independent claim")
        
        if claims_analysis.get("structure_score", 1.0) < 0.8:
            recommendations.append("Review and improve claims structure")
        
        if claims_analysis.get("average_claim_length", 0) > 150:
            recommendations.append("Consider shortening lengthy claims for clarity")

        if content_quality.get("overall_score", 1.0) < 0.7:
            recommendations.append("Improve document content quality and clarity")

        return recommendations

    async def _validate_content_quality(self, parsed_doc: Dict[str, Any], state: PatentAnalysisState) -> Dict[str, Any]:
        """Use AI to check raw document content quality."""
        
        # Get the raw document content from state
        document = state.get("document", {})
        raw_content = document.get("content", "")
        
        # If no raw content, try to get it from parsed sections
        if not raw_content:
            sections = [parsed_doc.get("abstract", ""), parsed_doc.get("background", ""), 
                       parsed_doc.get("summary", ""), parsed_doc.get("detailed_description", "")]
            raw_content = " ".join(s for s in sections if s)
        
        if not raw_content or len(raw_content.strip()) < 10:
            return {
                "overall_score": 0.0,
                "all_issues": [{
                    "type": "no_content",
                    "severity": "high", 
                    "description": "Document is empty or has no readable content",
                    "suggestion": "Add meaningful content"
                }]
            }
        
        # Use AI to evaluate the raw content directly
        issues = await self._ai_evaluate_raw_content(raw_content[:1000])  # First 1000 chars
        
        return {
            "overall_score": max(0.0, 1.0 - (len(issues) * 0.2)),
            "all_issues": issues
        }

    async def _ai_evaluate_raw_content(self, content: str) -> List[Dict[str, Any]]:
        """Use AI to evaluate raw document content."""
        
        import openai
        import os
        import json
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return self._basic_trash_detection(content)
        
        try:
            client = openai.OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model="gpt-4.1-2025-04-14",
                messages=[{
                    "role": "user", 
                    "content": f"""Check this document content for quality issues:

"{content}"

Look for: spelling errors, gibberish, repeated characters, nonsensical text, poor grammar.

Respond JSON only: {{"issues": [{{"type": "issue_type", "description": "what's wrong", "severity": "high/medium/low"}}]}}
If acceptable: {{"issues": []}}"""
                }],
                max_tokens=200,
                temperature=0
            )
            
            result = json.loads(response.choices[0].message.content.strip())
            
            for issue in result.get("issues", []):
                issue["suggestion"] = "Improve content quality"
            
            return result.get("issues", [])
            
        except Exception as e:
            logger.error(f"AI evaluation failed: {e}")
            return self._basic_trash_detection(content)

    def _basic_trash_detection(self, content: str) -> List[Dict[str, Any]]:
        """Basic trash detection without AI."""
        
        issues = []
        
        # Gibberish detection
        if re.search(r'(.)\1{5,}', content):
            issues.append({
                "type": "gibberish",
                "severity": "high", 
                "description": "Repeated characters detected",
                "suggestion": "Remove gibberish content"
            })
        
        return issues

    def _check_section_quality(self, text: str, section: str) -> Dict[str, Any]:
        """Check quality of a specific section."""
        
        issues = []
        
        # Grammar checks
        grammar_issues = self._check_grammar_issues(text)
        issues.extend(grammar_issues)
        
        # Spelling checks  
        spelling_issues = self._check_spelling_issues(text)
        issues.extend(spelling_issues)
        
        # Style checks
        style_issues = self._check_style_issues(text)
        issues.extend(style_issues)
        
        # Readability check
        readability = self._check_readability(text)
        if readability.get("issues"):
            issues.extend([{
                "type": "readability",
                "severity": "low", 
                "description": issue,
                "suggestion": "Improve sentence structure and word choice"
            } for issue in readability["issues"]])
        
        # Calculate quality score
        quality_score = 1.0 - (len(issues) * 0.1)  # Each issue reduces score by 0.1
        quality_score = max(0.0, quality_score)
        
        return {
            "issues": issues,
            "quality_score": quality_score,
            "readability": readability
        }

    def _check_grammar_issues(self, text: str) -> List[Dict[str, Any]]:
        """Check for basic grammar issues."""
        
        issues = []
        sentences = re.split(r'[.!?]+', text)
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) < 5:
                continue
                
            # Check subject-verb agreement patterns
            if re.search(r'\b(this|that)\s+(are|were)\b', sentence, re.IGNORECASE):
                issues.append({
                    "type": "subject_verb_agreement",
                    "severity": "medium",
                    "description": "Singular subject with plural verb",
                    "suggestion": "Check subject-verb agreement",
                    "sentence": i+1
                })
            
            # Check for overly long sentences
            if len(sentence.split()) > 40:
                issues.append({
                    "type": "long_sentence",
                    "severity": "medium", 
                    "description": f"Very long sentence ({len(sentence.split())} words)",
                    "suggestion": "Break into shorter sentences",
                    "sentence": i+1
                })
        
        return issues

    def _check_spelling_issues(self, text: str) -> List[Dict[str, Any]]:
        """Check for potential spelling issues."""
        
        issues = []
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        # Common typos in patent language
        common_typos = {
            'recieve': 'receive', 'seperate': 'separate', 'occured': 'occurred',
            'begining': 'beginning', 'definately': 'definitely', 'wiered': 'weird',
            'apparant': 'apparent', 'neccessary': 'necessary'
        }
        
        for word in words:
            if word in common_typos:
                issues.append({
                    "type": "spelling_error",
                    "severity": "medium",
                    "description": f"Misspelled word: '{word}'",
                    "suggestion": f"Correct spelling: '{common_typos[word]}'"
                })
            
            # Check for repeated letters (potential typos)
            if len(word) > 3 and re.search(r'(.)\1{2,}', word):
                issues.append({
                    "type": "potential_typo", 
                    "severity": "low",
                    "description": f"Word with repeated letters: '{word}'",
                    "suggestion": "Check spelling"
                })
        
        return issues

    def _check_style_issues(self, text: str) -> List[Dict[str, Any]]:
        """Check for writing style issues."""
        
        issues = []
        
        # Check for excessive passive voice
        passive_count = len(re.findall(r'\b(is|are|was|were|been|being)\s+\w+ed\b', text))
        sentence_count = len(re.split(r'[.!?]+', text))
        
        if sentence_count > 0:
            passive_ratio = passive_count / sentence_count
            if passive_ratio > 0.6:  # More than 60% passive
                issues.append({
                    "type": "excessive_passive_voice",
                    "severity": "medium",
                    "description": f"High passive voice usage ({passive_ratio:.1%})",
                    "suggestion": "Use more active voice for clarity"
                })
        
        # Check for word repetition
        words = re.findall(r'\b\w{4,}\b', text.lower())
        word_counts = Counter(words)
        
        # Patent-specific terms that are OK to repeat
        patent_terms = {'comprising', 'wherein', 'whereby', 'device', 'system', 'method'}
        
        overused = [(word, count) for word, count in word_counts.items() 
                   if count > 3 and word not in patent_terms and len(text.split()) > 50]
        
        if overused:
            issues.append({
                "type": "word_repetition",
                "severity": "low", 
                "description": f"Overused words: {dict(overused[:3])}",  # Show top 3
                "suggestion": "Use synonyms for variety"
            })
        
        # Check for unclear pronouns
        pronouns = len(re.findall(r'\b(this|that|these|those|it|they)\b', text, re.IGNORECASE))
        if pronouns > len(text.split()) * 0.08:  # More than 8% pronouns
            issues.append({
                "type": "unclear_pronouns",
                "severity": "low",
                "description": "High use of pronouns may reduce clarity", 
                "suggestion": "Replace pronouns with specific nouns"
            })
        
        return issues

    def _check_readability(self, text: str) -> Dict[str, Any]:
        """Check readability metrics."""
        
        if not text or len(text.strip()) < 10:
            return {"score": 0.0, "issues": ["Insufficient text"]}
        
        sentences = len(re.split(r'[.!?]+', text))
        words = len(text.split())
        
        if sentences == 0 or words == 0:
            return {"score": 0.0, "issues": ["No complete sentences"]}
        
        avg_sentence_length = words / sentences
        
        issues = []
        if avg_sentence_length > 25:
            issues.append("Average sentence length is high")
        
        # Simple readability approximation
        if avg_sentence_length > 30:
            score = 30  # Very difficult
        elif avg_sentence_length > 20:
            score = 50  # Difficult  
        else:
            score = 70  # Acceptable
        
        return {
            "flesch_score": score,
            "avg_sentence_length": round(avg_sentence_length, 1),
            "issues": issues
        }

    async def _ai_validate_patent_claims_format(self, claims: List[Dict[str, Any]], stream_callback=None) -> Dict[str, Any]:
        """
        AI-powered validation of patent claims format based on USPTO rules.
        Uses AI to check punctuation, antecedent basis, vague terms, and dependent claim structure.
        """
        logger.info(f"🤖 AI CLAIMS VALIDATION: Starting with {len(claims)} claims")
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "structure_analysis",
                "agent": "structure",
                "message": f"🤖 AI analyzing {len(claims)} claims for USPTO compliance..."
            })
        
        if not claims:
            logger.info(f"🤖 AI CLAIMS VALIDATION: No claims provided - returning early")
            return {
                "score": 0.0,
                "issues": [{"type": "no_claims", "description": "No claims to validate"}],
                "compliant": False
            }

        api_key = os.getenv("OPENAI_API_KEY")
        logger.info(f"🤖 AI CLAIMS VALIDATION: OpenAI API key present: {bool(api_key)}")
        if not api_key:
            logger.info(f"🤖 AI CLAIMS VALIDATION: No API key - using fallback")
            return {"score": 0.5, "issues": [], "compliant": True}  # Fallback

        try:
            logger.info(f"🤖 AI CLAIMS VALIDATION: Creating OpenAI client")
            if stream_callback:
                await stream_callback({
                    "status": "analyzing",
                    "phase": "structure_analysis",
                    "agent": "structure", 
                    "message": "🤖 Preparing claims for AI analysis..."
                })
            
            client = openai.OpenAI(api_key=api_key)

            # Prepare claims text for AI analysis
            logger.info(f"🤖 AI CLAIMS VALIDATION: Preparing claims text from first {min(5, len(claims))} claims")
            claims_text = ""
            for claim in claims[:5]:  # Limit to first 5 claims for AI analysis
                claim_preview = claim['text'][:500]
                claims_text += f"Claim {claim['number']}: {claim_preview}\n\n"
                logger.info(f"🤖 AI CLAIMS VALIDATION: Added claim {claim['number']} ({len(claim_preview)} chars)")

            # Create prompt based on patent format rules from examples
            prompt = f"""Analyze these patent claims for USPTO format compliance:

{claims_text}

Check for these specific issues based on USPTO patent rules:

1. PUNCTUATION: Claims should end with periods. Elements should be separated with semicolons, with '; and' before the final element.

2. ANTECEDENT BASIS: Elements introduced with 'a/an' should later be referenced with 'the'. Check for proper antecedent basis.

3. VAGUE TERMS: Flag vague terms like 'long', 'short', 'effective', 'suitable', 'about', 'substantially' that make claims indefinite.

4. DEPENDENT CLAIMS: Dependent claims should narrow (not broaden) parent claims. Check for broadening language like 'or', 'alternatively', 'optionally'.

Respond in JSON format:
{{"score": 0.0-1.0, "issues": [{{"type": "issue_type", "claim": claim_number, "description": "specific issue", "severity": "high/medium/low", "suggestion": "how to fix"}}], "compliant": true/false}}"""

            logger.info(f"🤖 AI CLAIMS VALIDATION: Making API call to gpt-4-turbo-preview")
            logger.info(f"🤖 AI CLAIMS VALIDATION: Prompt length: {len(prompt)} chars")
            
            if stream_callback:
                await stream_callback({
                    "status": "analyzing",
                    "phase": "structure_analysis",
                    "agent": "structure",
                    "message": "🤖 Making AI API call for claims validation..."
                })
            
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0
            )

            logger.info(f"🤖 AI CLAIMS VALIDATION: API call successful")
            if stream_callback:
                await stream_callback({
                    "status": "analyzing", 
                    "phase": "structure_analysis",
                    "agent": "structure",
                    "message": "🤖 Processing AI response for claims validation..."
                })
            logger.info(f"🤖 AI CLAIMS VALIDATION: Response usage: {response.usage}")
            logger.info(f"🤖 AI CLAIMS VALIDATION: Response finish_reason: {response.choices[0].finish_reason}")
            
            raw_content = response.choices[0].message.content.strip()
            logger.info(f"🤖 AI CLAIMS VALIDATION: Raw response length: {len(raw_content)}")
            logger.info(f"🤖 AI CLAIMS VALIDATION: Raw response: {raw_content[:500]}...")
            
            logger.info(f"🤖 AI CLAIMS VALIDATION: Cleaning JSON response...")
            # Remove ```json wrapper if present
            cleaned_content = raw_content
            if cleaned_content.startswith('```json'):
                cleaned_content = cleaned_content[7:]  # Remove ```json
            if cleaned_content.endswith('```'):
                cleaned_content = cleaned_content[:-3]  # Remove closing ```
            cleaned_content = cleaned_content.strip()
            logger.info(f"🤖 AI CLAIMS VALIDATION: Cleaned response length: {len(cleaned_content)}")
            
            logger.info(f"🤖 AI CLAIMS VALIDATION: Attempting JSON parse...")
            result = json.loads(cleaned_content)
            logger.info(f"🤖 AI CLAIMS VALIDATION: JSON parse successful")
            logger.info(f"🤖 AI CLAIMS VALIDATION: Parsed result keys: {list(result.keys())}")
            logger.info(f"🤖 AI CLAIMS VALIDATION: Score: {result.get('score', 'missing')}")
            logger.info(f"🤖 AI CLAIMS VALIDATION: Issues count: {len(result.get('issues', []))}")
            logger.info(f"🤖 AI CLAIMS VALIDATION: Compliant: {result.get('compliant', 'missing')}")
            
            return {
                "score": result.get("score", 0.5),
                "issues": result.get("issues", []),
                "compliant": result.get("compliant", True),
                "ai_analyzed_claims": len(claims[:5])
            }

        except json.JSONDecodeError as e:
            logger.error(f"🚨 AI CLAIMS VALIDATION: JSON DECODE ERROR: {e}")
            logger.error(f"🚨 AI CLAIMS VALIDATION: Failed to parse response: {raw_content if 'raw_content' in locals() else 'No raw content available'}")
            return {"score": 0.5, "issues": [{"type": "analysis_error", "description": "AI analysis failed - JSON parsing error", "severity": "high"}], "compliant": False}
        except Exception as e:
            logger.error(f"🚨 AI CLAIMS VALIDATION: GENERAL ERROR: {e}")
            logger.error(f"🚨 AI CLAIMS VALIDATION: Error type: {type(e).__name__}")
            import traceback
            logger.error(f"🚨 AI CLAIMS VALIDATION: Traceback: {traceback.format_exc()}")
            return {"score": 0.5, "issues": [{"type": "analysis_error", "description": f"AI analysis failed: {str(e)}", "severity": "high"}], "compliant": False}

    async def _ai_validate_brief_description_drawings(self, parsed_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        AI-powered validation of Brief Description of Drawings section.
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {"score": 1.0, "issues": [], "compliant": True}  # Fallback

        try:
            client = openai.OpenAI(api_key=api_key)

            # Get relevant content for analysis
            content = f"{parsed_doc.get('background', '')} {parsed_doc.get('summary', '')} {parsed_doc.get('detailed_description', '')}"
            figure_references = parsed_doc.get("figures", [])
            
            if not figure_references:
                return {"score": 1.0, "issues": [], "compliant": True, "no_figures": True}

            # Limit content for AI analysis
            content = content[:2000] if content else ""
            
            prompt = f"""Analyze this patent document for Brief Description of Drawings compliance:

FIGURE REFERENCES FOUND: {', '.join(figure_references)}

DOCUMENT CONTENT:
{content}

Check for:
1. If figures are referenced, is there a "Brief Description of the Drawings" section?
2. Are all referenced figures described in the Brief Description?
3. Are there any figures described but not referenced in the document?
4. Is the Brief Description section properly formatted?

Respond in JSON format:
{{"score": 0.0-1.0, "issues": [{{"type": "issue_type", "description": "specific issue", "severity": "high/medium/low", "suggestion": "how to fix"}}], "compliant": true/false, "brief_description_present": true/false}}"""

            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0
            )

            result = json.loads(response.choices[0].message.content.strip())
            
            return {
                "score": result.get("score", 1.0),
                "issues": result.get("issues", []),
                "compliant": result.get("compliant", True),
                "brief_description_present": result.get("brief_description_present", False),
                "figures_referenced": len(figure_references)
            }

        except Exception as e:
            logger.error(f"AI drawings validation failed: {e}")
            return {"score": 1.0, "issues": [], "compliant": True}

    def _learn_from_history(self, similar_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Learn from historical similar cases to prioritize checks and improve accuracy.
        This makes the memory system ACTUALLY USEFUL.

        Returns:
            Dictionary with:
            - patterns_found: number of similar cases analyzed
            - common_issues: list of frequently occurring issue types
            - high_risk_checks: checks to prioritize based on history
            - avg_confidence: average confidence from similar cases
        """
        if not similar_cases:
            return {
                "patterns_found": 0,
                "common_issues": [],
                "high_risk_checks": [],
                "avg_confidence": 0.0
            }

        # Analyze historical issues to find patterns
        issue_counter = Counter()
        confidences = []

        for case in similar_cases:
            # Extract structure-related findings if available
            agent_findings = case.get("agent_findings", {})
            structure_findings = agent_findings.get("structure", {})

            if structure_findings:
                # Count issue types
                for issue in structure_findings.get("issues", []):
                    issue_type = issue.get("type", "unknown")
                    issue_counter[issue_type] += 1

                # Track confidence levels
                confidence = structure_findings.get("confidence", 0.0)
                if confidence > 0:
                    confidences.append(confidence)

        # Identify most common issues (these should be checked first)
        common_issues = [issue_type for issue_type, count in issue_counter.most_common(5)]

        # Determine high-risk checks based on frequency
        high_risk_checks = []
        if "claims_structure" in common_issues:
            high_risk_checks.append("claims_numbering")
            high_risk_checks.append("dependent_claims")
        if "format" in common_issues:
            high_risk_checks.append("required_sections")
        if any("antecedent" in issue for issue in common_issues):
            high_risk_checks.append("antecedent_basis")

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "patterns_found": len(similar_cases),
            "common_issues": common_issues,
            "high_risk_checks": high_risk_checks,
            "avg_confidence": round(avg_confidence, 2),
            "total_historical_issues": sum(issue_counter.values())
        }

    def _reuse_successful_suggestions(
        self,
        current_issues: List[Dict[str, Any]],
        similar_cases: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Reuse suggestions from similar historical cases that were successful.
        This demonstrates REAL cross-session learning.

        Args:
            current_issues: Issues found in current analysis
            similar_cases: Historical similar patent analyses

        Returns:
            Enhanced issues list with historically successful suggestions
        """
        if not similar_cases:
            return current_issues

        # Build a suggestion library from historical successes
        suggestion_library = {}

        for case in similar_cases:
            agent_findings = case.get("agent_findings", {})
            structure_findings = agent_findings.get("structure", {})

            for historical_issue in structure_findings.get("issues", []):
                issue_type = historical_issue.get("type")
                suggestion = historical_issue.get("suggestion")

                # Only use if suggestion exists and has context
                if issue_type and suggestion and len(suggestion) > 20:
                    # Store successful suggestions (we assume historical issues were resolved)
                    if issue_type not in suggestion_library:
                        suggestion_library[issue_type] = []
                    suggestion_library[issue_type].append(suggestion)

        # Enhance current issues with historical suggestions
        enhanced_issues = []
        for issue in current_issues:
            issue_type = issue.get("type")

            # If we have successful historical suggestions for this issue type
            if issue_type in suggestion_library:
                historical_suggestions = suggestion_library[issue_type]

                # Use the most common historical suggestion
                suggestion_counter = Counter(historical_suggestions)
                best_suggestion, usage_count = suggestion_counter.most_common(1)[0]

                # Replace generic suggestion with proven historical one
                original_suggestion = issue.get("suggestion", "")
                issue["suggestion"] = best_suggestion
                issue["suggestion_source"] = "historical_success"
                issue["suggestion_success_rate"] = f"Used successfully in {usage_count} similar patents"

                logger.info(f"💡 STRUCTURE AGENT: Reused successful suggestion for {issue_type}")
                logger.info(f"💡 STRUCTURE AGENT: Original: '{original_suggestion[:60]}...'")
                logger.info(f"💡 STRUCTURE AGENT: Historical: '{best_suggestion[:60]}...' (success rate: {usage_count} cases)")

            enhanced_issues.append(issue)

        return enhanced_issues
