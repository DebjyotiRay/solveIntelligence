import asyncio
import logging
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..memory.patent_memory import PatentAnalysisMemory
from ..agents.structure_agent import DocumentStructureAgent
from ..agents.legal_agent import LegalComplianceAgent
from .patent_state import (
    PatentAnalysisState, create_initial_state, 
    PhaseStatus, AgentStatus, update_phase, get_state_summary
)

logger = logging.getLogger(__name__)


class PatentAnalysisCoordinator:
    """
    Main coordinator for multi-agent patent analysis workflow.
    Implements 4-phase analysis with memory integration.
    """
    
    def __init__(self):
        # Initialize memory system
        self.memory = PatentAnalysisMemory()
        
        # Initialize agents
        self.structure_agent = DocumentStructureAgent(self.memory)
        self.legal_agent = LegalComplianceAgent(self.memory)
        
        logger.info("PatentAnalysisCoordinator initialized with memory-enhanced agents")

    async def analyze_patent(
        self, 
        document: Dict[str, Any],
        stream_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Execute complete multi-agent patent analysis.
        
        Args:
            document: Patent document to analyze
            stream_callback: Optional callback for streaming updates
            
        Returns:
            Complete analysis results
        """
        
        # Get the document ID (should now be database ID like "1", "2", etc.)
        document_id = document.get("id")
        if not document_id:
            raise ValueError("Document ID is required but not provided")
            
        print(f"\n🚀 MULTI-AGENT COORDINATOR: ===== STARTING PATENT ANALYSIS =====")
        print(f"📄 COORDINATOR: Document ID: {document_id}")
        print(f"📄 COORDINATOR: Document keys: {list(document.keys())}")
        print(f"📄 COORDINATOR: Document length: {len(document.get('content', ''))} characters")
        print(f"📄 COORDINATOR: Content preview: {document.get('content', '')[:300]}...")
        logger.info(f"Starting multi-agent analysis for document {document_id}")

        # Add debug info about memory instance
        print(f"🧠 COORDINATOR: Memory instance ID: {id(self.memory)}")
        print(f"🧠 COORDINATOR: Memory type: {type(self.memory).__name__}")
        print(f"🧠 COORDINATOR: Available agents: {[self.structure_agent.__class__.__name__, self.legal_agent.__class__.__name__]}")
        
        try:
            # Get historical context from memory
            print(f"🔍 COORDINATOR: Retrieving similar cases from global memory...")
            similar_cases = self.memory.get_similar_cases(document)
            print(f"🔍 COORDINATOR: Found {len(similar_cases)} similar cases from historical data")
            print(f"🔍 COORDINATOR: Similar cases details: {[case.get('title', 'No title')[:50] for case in similar_cases[:3]]}")

            # Get shared analysis context (existing agent findings for this document)
            print(f"🔍 COORDINATOR: Retrieving shared analysis context...")
            shared_context = self.memory.get_shared_analysis_context(document_id)
            print(f"🔍 COORDINATOR: Shared context keys: {list(shared_context.keys())}")
            print(f"🔍 COORDINATOR: Found {len(shared_context['agent_findings'])} existing agent findings")

            # Initialize workflow state with shared context
            print(f"🔧 COORDINATOR: Creating initial workflow state...")
            state = create_initial_state(
                document=document,
                similar_cases=similar_cases
            )
            print(f"🔧 COORDINATOR: Initial state keys: {list(state.keys())}")
            print(f"🔧 COORDINATOR: Initial state document_id: {state.get('document_id', 'Missing')}")

            # Add shared context to state
            state["shared_memory_context"] = shared_context
            print(f"🔧 COORDINATOR: Added shared memory context to state")

            # Store workflow start in memory
            print(f"💾 COORDINATOR: Storing workflow start in memory...")
            self.memory.store_workflow_progress(
                document_id,
                "initialization",
                {
                    "message": "Multi-agent analysis workflow started",
                    "agents_planned": ["structure", "legal"],
                    "similar_cases_count": len(similar_cases)
                }
            )
            
            # Execute 4-phase workflow
            print(f"🚀 COORDINATOR: About to start 4-phase workflow execution")
            logger.info("🚀 COORDINATOR: About to start 4-phase workflow execution")
            state = await self._execute_workflow(state, stream_callback)
            print(f"✅ COORDINATOR: 4-phase workflow execution completed")
            logger.info("✅ COORDINATOR: 4-phase workflow execution completed")
            
            # Verify final analysis in state
            final_analysis = state.get("final_analysis") if state else None
            print(f"🎯 COORDINATOR: Final analysis present in state: {final_analysis is not None}")
            if state:
                print(f"🎯 COORDINATOR: Final state keys: {list(state.keys())}")
            else:
                print(f"🎯 COORDINATOR: WARNING: State is None after workflow execution")
            
            logger.info(f"🎯 GLOBAL STORAGE: Final analysis present in state: {final_analysis is not None}")
            logger.info(f"🎯 GLOBAL STORAGE: State keys: {list(state.keys()) if state else 'None'}")

            if final_analysis:
                print(f"🎯 COORDINATOR: Final analysis summary:")
                print(f"   - Status: {final_analysis.get('status', 'Missing')}")
                print(f"   - Issues: {len(final_analysis.get('all_issues', []))}")
                print(f"   - Overall score: {final_analysis.get('overall_score', 'Missing')}")
                print(f"   - Agents used: {final_analysis.get('analysis_metadata', {}).get('agents_used', [])}")
                logger.info(f"🎯 GLOBAL STORAGE: Final analysis already stored by synthesis phase")
            else:
                print(f"🎯 COORDINATOR: WARNING: No final analysis found in state for document {document_id}")
                logger.warning(f"🎯 GLOBAL STORAGE: No final analysis found in state for document {document_id}")

            logger.info(f"Multi-agent analysis completed for document {document_id}")
            
            result = final_analysis or {
                "status": "error",
                "error": "No final analysis generated",
                "document_id": document_id,
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"🎯 COORDINATOR: Returning result with keys: {list(result.keys())}")
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed for document {document_id}: {e}")
            
            # Return error state
            return {
                "status": "error",
                "error": str(e),
                "document_id": document_id,
                "timestamp": datetime.now().isoformat()
            }

    async def _execute_workflow(
        self, 
        state: PatentAnalysisState,
        stream_callback: Optional[callable] = None
    ) -> PatentAnalysisState:
        """Execute the complete 4-phase workflow."""
        
        try:
            # Phase 1: Structure Analysis (Sequential)
            logger.info("🚀 WORKFLOW: Starting Phase 1 - Structure Analysis")
            state = await self._phase1_structure_analysis(state, stream_callback)
            logger.info("✅ WORKFLOW: Phase 1 completed")

            # Phase 2: Parallel Analysis (Legal + future agents)
            logger.info("🚀 WORKFLOW: Starting Phase 2 - Parallel Analysis")
            state = await self._phase2_parallel_analysis(state, stream_callback)
            logger.info("✅ WORKFLOW: Phase 2 completed")

            # Phase 3: Cross-Validation
            logger.info("🚀 WORKFLOW: Starting Phase 3 - Cross-Validation")
            state = await self._phase3_cross_validation(state, stream_callback)
            logger.info("✅ WORKFLOW: Phase 3 completed")

            # Phase 4: Synthesis
            logger.info("🚀 WORKFLOW: Starting Phase 4 - Synthesis")
            state = await self._phase4_synthesis(state, stream_callback)
            logger.info("✅ WORKFLOW: Phase 4 completed")

            return state
            
        except Exception as e:
            logger.error(f"❌ WORKFLOW: Execution failed at phase: {e}")
            import traceback
            logger.error(f"❌ WORKFLOW: Full traceback: {traceback.format_exc()}")
            error_state = dict(state)
            error_state["current_phase"] = PhaseStatus.ERROR
            error_state["errors"] = error_state.get("errors", []) + [{
                "phase": "workflow",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }]
            
            if stream_callback:
                await stream_callback({
                    "status": "error",
                    "phase": "workflow",
                    "error": str(e)
                })
            
            return error_state

    async def _phase1_structure_analysis(
        self, 
        state: PatentAnalysisState,
        stream_callback: Optional[callable] = None
    ) -> PatentAnalysisState:
        """Phase 1: Document structure analysis (blocking for all other agents)."""
        
        logger.info("Phase 1: Starting structure analysis")
        
        # Update phase
        state = update_phase(state, PhaseStatus.STRUCTURE_ANALYSIS, "Starting document structure analysis...")
        
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "structure_analysis",
                "agent": "structure",
                "message": "Analyzing document structure and format compliance..."
            })
        
        try:
            # Execute structure agent analysis with streaming
            state = await self.structure_agent.analyze_with_memory(state, stream_callback)
            
            logger.info("Phase 1: Structure analysis completed")
            
            if stream_callback:
                structure_result = state.get("structure_analysis", {})
                await stream_callback({
                    "status": "complete",
                    "phase": "structure_analysis", 
                    "agent": "structure",
                    "summary": f"Confidence: {structure_result.get('confidence', 0):.2f}, Issues: {len(structure_result.get('issues', []))}"
                })
            
            return state
            
        except Exception as e:
            logger.error(f"Phase 1 failed: {e}")
            raise

    async def _phase2_parallel_analysis(
        self, 
        state: PatentAnalysisState,
        stream_callback: Optional[callable] = None
    ) -> PatentAnalysisState:
        """Phase 2: Parallel analysis by specialized agents."""
        
        logger.info("Phase 2: Starting parallel analysis")
        
        # Update phase
        state = update_phase(state, PhaseStatus.PARALLEL_ANALYSIS, "Starting parallel analysis by specialized agents...")
        
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "parallel_analysis",
                "message": "Running legal compliance analysis..."
            })
        
        try:
            # For now, we only have legal agent implemented
            # In the future, we'll run multiple agents in parallel with asyncio.gather
            
            # Execute legal agent analysis with streaming
            state = await self.legal_agent.analyze_with_memory(state, stream_callback)
            
            logger.info("Phase 2: Parallel analysis completed")
            
            if stream_callback:
                legal_result = state.get("legal_analysis", {})
                await stream_callback({
                    "status": "complete",
                    "phase": "parallel_analysis",
                    "agents_completed": ["legal"],
                    "summary": f"Legal compliance score: {legal_result.get('compliance_score', 0):.2f}"
                })
            
            return state
            
        except Exception as e:
            logger.error(f"Phase 2 failed: {e}")
            raise

    async def _phase3_cross_validation(
        self, 
        state: PatentAnalysisState,
        stream_callback: Optional[callable] = None
    ) -> PatentAnalysisState:
        """Phase 3: Cross-agent validation and conflict resolution."""
        
        logger.info("Phase 3: Starting cross-validation")
        
        # Update phase
        state = update_phase(state, PhaseStatus.CROSS_VALIDATION, "Validating findings across agents...")
        
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "cross_validation",
                "message": "Checking for conflicts between agent findings..."
            })
        
        try:
            # Get shared context for cross-validation
            if not state:
                raise ValueError("State is None during cross-validation")

            document_id = state.get("document_id")
            if not document_id:
                raise ValueError("No document_id found in state")

            shared_context = self.memory.get_shared_analysis_context(document_id)
            if not shared_context:
                shared_context = {
                    "document_id": document_id,
                    "agent_findings": {},
                    "cross_agent_insights": [],
                    "historical_patterns": []
                }

            # Enhanced conflict detection using shared memory context
            conflicts = self._detect_conflicts_with_shared_context(state, shared_context)
            resolutions = self._resolve_conflicts_with_shared_context(conflicts, shared_context)

            # Generate cross-agent insights
            cross_insights = shared_context.get('cross_agent_insights', [])
            if len(shared_context['agent_findings']) >= 2:
                # Generate additional insights from current analysis
                additional_insights = self._generate_additional_cross_insights(shared_context)
                cross_insights.extend(additional_insights)

                # Store insights in memory
                for insight in additional_insights:
                    self.memory.store_cross_agent_insight(document_id, insight)

            # Update state with validation results
            updated_state = dict(state)
            updated_state["conflicts"] = conflicts
            updated_state["resolutions"] = resolutions
            updated_state["cross_agent_insights"] = cross_insights

            # Store cross-validation results in shared memory
            self.memory.store_cross_validation_result(document_id, conflicts, resolutions)

            # Store workflow progress
            self.memory.store_workflow_progress(
                document_id,
                "cross_validation",
                {
                    "message": f"Cross-validation completed: {len(conflicts)} conflicts, {len(resolutions)} resolutions",
                    "conflicts_count": len(conflicts),
                    "insights_generated": len(cross_insights)
                }
            )
            
            logger.info(f"Phase 3: Cross-validation completed - {len(conflicts)} conflicts found")
            
            if stream_callback:
                await stream_callback({
                    "status": "complete",
                    "phase": "cross_validation",
                    "conflicts_found": len(conflicts),
                    "resolutions_applied": len(resolutions)
                })
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Phase 3 failed: {e}")
            raise

    async def _phase4_synthesis(
        self, 
        state: PatentAnalysisState,
        stream_callback: Optional[callable] = None
    ) -> PatentAnalysisState:
        """Phase 4: Final synthesis and report generation."""
        
        logger.info("Phase 4: Starting synthesis")
        
        # Update phase
        state = update_phase(state, PhaseStatus.SYNTHESIS, "Synthesizing final analysis report...")
        
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "synthesis",
                "message": "Generating comprehensive analysis report..."
            })
        
        try:
            # Get complete shared context for synthesis
            if not state:
                raise ValueError("State is None during synthesis")

            document_id = state.get("document_id")
            if not document_id:
                raise ValueError("No document_id found in state")

            shared_context = self.memory.get_shared_analysis_context(document_id)
            if not shared_context:
                shared_context = {
                    "document_id": document_id,
                    "agent_findings": {},
                    "cross_agent_insights": [],
                    "historical_patterns": []
                }

            # Generate final analysis using all shared memory context
            final_analysis = self._generate_final_analysis_with_shared_context(state, shared_context)

            # Store final analysis in memory for future learning
            logger.info(f"🌍 SYNTHESIS: About to store analysis summary in global memory")
            print(f"🌍 SYNTHESIS: Storing analysis summary for {document_id} to global memory")
            success = self.memory.store_analysis_summary(document_id, final_analysis)
            print(f"🌍 SYNTHESIS: Global storage result: {'✅ Success' if success else '❌ Failed'}")

            # Store final workflow progress
            self.memory.store_workflow_progress(
                document_id,
                "synthesis_complete",
                {
                    "message": "Final synthesis completed successfully",
                    "overall_score": final_analysis.get("overall_score", 0.0),
                    "total_issues": len(final_analysis.get("all_issues", [])),
                    "agents_used": final_analysis.get("analysis_metadata", {}).get("agents_used", [])
                }
            )

            # Update state
            updated_state = dict(state)
            updated_state["final_analysis"] = final_analysis
            updated_state["current_phase"] = PhaseStatus.COMPLETE
            updated_state["overall_score"] = final_analysis.get("overall_score", 0.0)
            updated_state["shared_context_used"] = shared_context
            
            logger.info("Phase 4: Synthesis completed")
            
            if stream_callback:
                await stream_callback({
                    "status": "complete",
                    "phase": "synthesis",
                    "overall_score": final_analysis.get("overall_score", 0.0),
                    "total_issues": len(final_analysis.get("all_issues", []))
                })
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Phase 4 failed: {e}")
            raise

    def _detect_conflicts_with_shared_context(
        self,
        state: PatentAnalysisState,
        shared_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect conflicts between agent findings using shared memory context"""

        conflicts = []
        agent_findings = shared_context.get('agent_findings', {})

        # Enhanced conflict detection using all agent findings
        if 'structure' in agent_findings and 'legal' in agent_findings:
            structure = agent_findings['structure']
            legal = agent_findings['legal']

            # Confidence divergence conflict
            structure_conf = structure.get('confidence', 0.0)
            legal_conf = legal.get('confidence', 0.0)

            if abs(structure_conf - legal_conf) > 0.4:
                conflicts.append({
                    "type": "confidence_divergence",
                    "agents": ["structure", "legal"],
                    "description": f"Significant confidence gap: structure={structure_conf:.2f}, legal={legal_conf:.2f}",
                    "severity": "high"
                })

            # Issue severity conflicts
            structure_issues = len(structure.get('issues', []))
            legal_issues = len(legal.get('issues', []))

            if structure_issues < 2 and legal_issues > 5:
                conflicts.append({
                    "type": "issue_count_mismatch",
                    "agents": ["structure", "legal"],
                    "description": f"Structure found {structure_issues} issues, legal found {legal_issues}",
                    "severity": "medium"
                })

        return conflicts

    def _resolve_conflicts_with_shared_context(
        self,
        conflicts: List[Dict[str, Any]],
        shared_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Resolve conflicts using shared memory context and historical patterns"""

        resolutions = []

        for conflict in conflicts:
            if conflict["type"] == "confidence_divergence":
                # Use historical patterns to resolve confidence conflicts
                resolution = {
                    "conflict": conflict,
                    "resolution": "Average confidence levels and flag for manual review",
                    "action": "weighted_average",
                    "manual_review_required": True
                }
                resolutions.append(resolution)

            elif conflict["type"] == "issue_count_mismatch":
                # Legal analysis typically finds more compliance issues
                resolution = {
                    "conflict": conflict,
                    "resolution": "Legal agent analysis takes precedence for issue detection",
                    "action": "prefer_legal_findings",
                    "manual_review_required": False
                }
                resolutions.append(resolution)

        return resolutions

    def _detect_basic_conflicts(self, state: PatentAnalysisState) -> List[Dict[str, Any]]:
        """Detect basic conflicts between agent findings (legacy method)"""

        conflicts = []

        structure_analysis = state.get("structure_analysis", {})
        legal_analysis = state.get("legal_analysis", {})

        # Example conflict: Structure says compliant but legal says not compliant
        structure_compliant = structure_analysis.get("format_compliance", {}).get("compliant", True)
        legal_compliant = legal_analysis.get("compliance_score", 1.0) > 0.7

        if structure_compliant and not legal_compliant:
            conflicts.append({
                "type": "compliance_disagreement",
                "agents": ["structure", "legal"],
                "description": "Structure agent found format compliance but legal agent found compliance issues",
                "severity": "medium"
            })

        return conflicts

    def _resolve_basic_conflicts(self, conflicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve basic conflicts using simple precedence rules."""
        
        resolutions = []
        
        for conflict in conflicts:
            if conflict["type"] == "compliance_disagreement":
                # Legal agent takes precedence for compliance matters
                resolution = {
                    "conflict": conflict,
                    "resolution": "Legal agent analysis takes precedence for compliance matters",
                    "precedence_agent": "legal",
                    "action": "Flag for legal review"
                }
                resolutions.append(resolution)
        
        return resolutions

    def _generate_additional_cross_insights(self, shared_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate additional cross-agent insights from shared context"""
        insights = []
        agent_findings = shared_context.get('agent_findings', {})

        # Generate insights based on agent findings
        if len(agent_findings) >= 2:
            agents = list(agent_findings.keys())

            # Confidence divergence insight
            confidences = [findings.get('confidence', 0.0) for findings in agent_findings.values()]
            if max(confidences) - min(confidences) > 0.3:
                insights.append({
                    'type': 'confidence_divergence',
                    'description': f'Significant confidence difference between agents: {min(confidences):.2f} - {max(confidences):.2f}',
                    'agents': agents,
                    'confidence': 0.8
                })

            # Issue aggregation insight
            total_issues = sum(len(findings.get('issues', [])) for findings in agent_findings.values())
            if total_issues > 0:
                insights.append({
                    'type': 'issue_aggregation',
                    'description': f'Total {total_issues} issues found across {len(agents)} agents',
                    'agents': agents,
                    'confidence': 0.9
                })

        return insights

    def _generate_final_analysis_with_shared_context(
        self,
        state: PatentAnalysisState,
        shared_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive final analysis using shared memory context"""

        print(f"\n🔧 SYNTHESIS: ===== GENERATING FINAL ANALYSIS =====")
        document_id = state["document_id"]
        print(f"🔧 SYNTHESIS: Document ID: {document_id}")
        
        agent_findings = shared_context.get('agent_findings', {})
        cross_insights = shared_context.get('cross_agent_insights', [])
        conflicts = state.get("conflicts", [])
        resolutions = state.get("resolutions", [])
        
        print(f"🔧 SYNTHESIS: Agent findings keys: {list(agent_findings.keys())}")
        print(f"🔧 SYNTHESIS: Cross insights count: {len(cross_insights)}")
        print(f"🔧 SYNTHESIS: Conflicts count: {len(conflicts)}")
        print(f"🔧 SYNTHESIS: Resolutions count: {len(resolutions)}")

        # Collect all issues from shared memory
        print(f"📊 SYNTHESIS: Collecting issues from shared memory...")
        all_issues = []
        agent_scores = []
        agent_summary = {}

        for agent_name, findings in agent_findings.items():
            print(f"📊 SYNTHESIS: Processing agent '{agent_name}':")
            print(f"   - Findings keys: {list(findings.keys())}")
            
            agent_issues = findings.get('issues', [])
            agent_confidence = findings.get('confidence', 0.0)
            
            print(f"   - Issues found: {len(agent_issues)}")
            print(f"   - Confidence: {agent_confidence}")
            
            # Log individual issues
            for i, issue in enumerate(agent_issues):
                print(f"   - Issue {i+1}: {issue.get('type', 'unknown')} - {issue.get('severity', 'unknown')} - {issue.get('description', 'no description')[:100]}...")

            all_issues.extend(agent_issues)
            agent_scores.append(agent_confidence)
            agent_summary[agent_name] = {
                "confidence": agent_confidence,
                "issues_found": len(agent_issues),
                "analysis_type": findings.get('type', 'unknown')
            }

        print(f"📊 SYNTHESIS: Total issues collected from shared memory: {len(all_issues)}")
        
        # Also check current state for direct agent results
        print(f"📊 SYNTHESIS: Checking current state for direct agent results...")
        state_structure_analysis = state.get("structure_analysis", {})
        state_legal_analysis = state.get("legal_analysis", {})
        
        print(f"📊 SYNTHESIS: State structure analysis keys: {list(state_structure_analysis.keys())}")
        print(f"📊 SYNTHESIS: State legal analysis keys: {list(state_legal_analysis.keys())}")
        
        # Add issues from current state if they're not in shared memory
        state_structure_issues = state_structure_analysis.get('issues', [])
        state_legal_issues = state_legal_analysis.get('issues', [])
        
        print(f"📊 SYNTHESIS: State structure issues: {len(state_structure_issues)}")
        print(f"📊 SYNTHESIS: State legal issues: {len(state_legal_issues)}")
        
        # Add issues from state if shared memory is empty
        if len(all_issues) == 0 and (state_structure_issues or state_legal_issues):
            print(f"📊 SYNTHESIS: Shared memory empty - using issues from current state")
            all_issues.extend(state_structure_issues)
            all_issues.extend(state_legal_issues)
            print(f"📊 SYNTHESIS: Total issues after adding from state: {len(all_issues)}")

        # Calculate overall score using shared context
        print(f"🎯 SYNTHESIS: Calculating overall score...")
        overall_score = sum(agent_scores) / len(agent_scores) if agent_scores else 0.0
        print(f"🎯 SYNTHESIS: Agent scores: {agent_scores}")
        print(f"🎯 SYNTHESIS: Overall score: {overall_score}")

        # Enhanced recommendations using cross-agent insights
        print(f"💡 SYNTHESIS: Collecting recommendations...")
        recommendations = []
        for agent_name, findings in agent_findings.items():
            agent_recommendations = findings.get('recommendations', [])
            print(f"💡 SYNTHESIS: Agent {agent_name} recommendations: {len(agent_recommendations)}")
            recommendations.extend(agent_recommendations)

        # Add recommendations from current state if shared memory is empty
        if len(recommendations) == 0:
            state_structure_recs = state_structure_analysis.get('recommendations', [])
            state_legal_recs = state_legal_analysis.get('recommendations', [])
            print(f"💡 SYNTHESIS: Adding recommendations from state - Structure: {len(state_structure_recs)}, Legal: {len(state_legal_recs)}")
            recommendations.extend(state_structure_recs)
            recommendations.extend(state_legal_recs)

        # Add recommendations from cross-agent insights
        for insight in cross_insights:
            if insight.get('type') == 'confidence_divergence':
                recommendations.append("Manual review recommended due to agent confidence divergence")
            elif insight.get('type') == 'issue_aggregation':
                recommendations.append(f"Total {insight.get('description', '')} across multiple analysis domains")

        print(f"💡 SYNTHESIS: Total recommendations collected: {len(recommendations)}")

        # Determine analysis status
        status = "complete"
        if len(all_issues) > 0:
            high_severity_issues = [issue for issue in all_issues if issue.get('severity') == 'high']
            if len(high_severity_issues) > 0:
                status = "issues_found"
        
        print(f"📋 SYNTHESIS: Analysis status determined: {status}")

        final_analysis = {
            "status": status,
            "document_id": document_id,
            "analysis_timestamp": datetime.now().isoformat(),
            "overall_score": round(overall_score, 2),
            "phase_summary": agent_summary,
            "all_issues": all_issues,
            "cross_agent_insights": cross_insights,
            "conflicts_and_resolutions": {
                "conflicts_detected": conflicts,
                "resolutions_applied": resolutions
            },
            "recommendations": list(set(recommendations)),  # Remove duplicates
            "analysis_metadata": {
                "agents_used": list(agent_findings.keys()) if agent_findings else ["structure", "legal"],
                "memory_enhanced": True,
                "shared_context_used": True,
                "workflow_version": "3.0",
                "cross_insights_count": len(cross_insights)
            }
        }

        print(f"🎯 SYNTHESIS: Final analysis generated with keys: {list(final_analysis.keys())}")
        print(f"🎯 SYNTHESIS: Final analysis summary:")
        print(f"   - Status: {final_analysis.get('status')}")
        print(f"   - Issues: {len(final_analysis.get('all_issues', []))}")
        print(f"   - Recommendations: {len(final_analysis.get('recommendations', []))}")
        print(f"   - Overall Score: {final_analysis.get('overall_score')}")
        print(f"   - Agents Used: {final_analysis.get('analysis_metadata', {}).get('agents_used', [])}")

        return final_analysis

    def _generate_final_analysis(self, state: PatentAnalysisState) -> Dict[str, Any]:
        """Generate comprehensive final analysis report (legacy method)"""

        structure_analysis = state.get("structure_analysis", {})
        legal_analysis = state.get("legal_analysis", {})
        conflicts = state.get("conflicts", [])
        resolutions = state.get("resolutions", [])

        # Collect all issues
        all_issues = []
        all_issues.extend(structure_analysis.get("issues", []))
        all_issues.extend(legal_analysis.get("issues", []))

        # Calculate overall score
        scores = []
        if structure_analysis.get("confidence"):
            scores.append(structure_analysis["confidence"])
        if legal_analysis.get("compliance_score"):
            scores.append(legal_analysis["compliance_score"])

        overall_score = sum(scores) / len(scores) if scores else 0.0

        # Generate recommendations
        recommendations = []
        recommendations.extend(structure_analysis.get("recommendations", []))
        recommendations.extend(legal_analysis.get("recommendations", []))

        final_analysis = {
            "document_id": state["document_id"],
            "analysis_timestamp": datetime.now().isoformat(),
            "overall_score": round(overall_score, 2),
            "phase_summary": {
                "structure": {
                    "confidence": structure_analysis.get("confidence", 0.0),
                    "issues_found": len(structure_analysis.get("issues", []))
                },
                "legal": {
                    "compliance_score": legal_analysis.get("compliance_score", 0.0),
                    "issues_found": len(legal_analysis.get("issues", []))
                }
            },
            "all_issues": all_issues,
            "conflicts_and_resolutions": {
                "conflicts_detected": conflicts,
                "resolutions_applied": resolutions
            },
            "recommendations": list(set(recommendations)),  # Remove duplicates
            "analysis_metadata": {
                "agents_used": ["structure", "legal"],
                "memory_enhanced": True,
                "workflow_version": "2.0"
            }
        }

        return final_analysis

    def get_coordinator_status(self) -> Dict[str, Any]:
        """Get current status of the coordinator."""
        
        memory_stats = self.memory.get_memory_stats()
        
        return {
            "coordinator_version": "2.0",
            "available_agents": ["structure", "legal"],
            "memory_system": memory_stats,
            "workflow_phases": [
                PhaseStatus.STRUCTURE_ANALYSIS,
                PhaseStatus.PARALLEL_ANALYSIS,
                PhaseStatus.CROSS_VALIDATION,
                PhaseStatus.SYNTHESIS
            ]
        }
