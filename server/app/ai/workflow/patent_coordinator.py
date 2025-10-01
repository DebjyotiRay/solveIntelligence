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
            
        logger.info(f"\n🚀 MULTI-AGENT COORDINATOR: ===== STARTING PATENT ANALYSIS =====")
        logger.info(f"📄 COORDINATOR: Document ID: {document_id}")
        logger.info(f"📄 COORDINATOR: Document keys: {list(document.keys())}")
        logger.info(f"📄 COORDINATOR: Document length: {len(document.get('content', ''))} characters")
        logger.info(f"📄 COORDINATOR: Content preview: {document.get('content', '')[:300]}...")
        logger.info(f"Starting multi-agent analysis for document {document_id}")

        # Add debug info about memory instance
        logger.info(f"🧠 COORDINATOR: Memory instance ID: {id(self.memory)}")
        logger.info(f"🧠 COORDINATOR: Memory type: {type(self.memory).__name__}")
        logger.info(f"🧠 COORDINATOR: Available agents: {[self.structure_agent.__class__.__name__, self.legal_agent.__class__.__name__]}")
        
        try:
            # Get historical context from memory
            logger.info(f"🔍 COORDINATOR: Retrieving similar cases from global memory...")
            similar_cases = self.memory.get_similar_cases(document)
            logger.info(f"🔍 COORDINATOR: Found {len(similar_cases)} similar cases from historical data")
            logger.info(f"🔍 COORDINATOR: Similar cases details: {[case.get('title', 'No title')[:50] for case in similar_cases[:3]]}")

            # Get shared analysis context (existing agent findings for this document)
            logger.info(f"🔍 COORDINATOR: Retrieving shared analysis context...")
            shared_context = self.memory.get_shared_analysis_context(document_id)
            logger.info(f"🔍 COORDINATOR: Shared context keys: {list(shared_context.keys())}")
            logger.info(f"🔍 COORDINATOR: Found {len(shared_context['agent_findings'])} existing agent findings")

            # Initialize workflow state with shared context
            logger.info(f"🔧 COORDINATOR: Creating initial workflow state...")
            state = create_initial_state(
                document=document,
                similar_cases=similar_cases
            )
            logger.info(f"🔧 COORDINATOR: Initial state keys: {list(state.keys())}")
            logger.info(f"🔧 COORDINATOR: Initial state document_id: {state.get('document_id', 'Missing')}")

            # Add shared context to state
            state["shared_memory_context"] = shared_context
            logger.info(f"🔧 COORDINATOR: Added shared memory context to state")

            # Store workflow start in memory
            logger.info(f"💾 COORDINATOR: Storing workflow start in memory...")
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
            logger.info(f"🚀 COORDINATOR: About to start 4-phase workflow execution")
            logger.info("🚀 COORDINATOR: About to start 4-phase workflow execution")
            state = await self._execute_workflow(state, stream_callback)
            logger.info(f"✅ COORDINATOR: 4-phase workflow execution completed")
            logger.info("✅ COORDINATOR: 4-phase workflow execution completed")
            
            # Verify final analysis in state
            final_analysis = state.get("final_analysis") if state else None
            logger.info(f"🎯 COORDINATOR: Final analysis present in state: {final_analysis is not None}")
            if state:
                logger.info(f"🎯 COORDINATOR: Final state keys: {list(state.keys())}")
            else:
                logger.warning(f"🎯 COORDINATOR: WARNING: State is None after workflow execution")
            
            logger.info(f"🎯 GLOBAL STORAGE: Final analysis present in state: {final_analysis is not None}")
            logger.info(f"🎯 GLOBAL STORAGE: State keys: {list(state.keys()) if state else 'None'}")

            if final_analysis:
                logger.info(f"🎯 COORDINATOR: Final analysis summary:")
                logger.info(f"   - Status: {final_analysis.get('status', 'Missing')}")
                logger.info(f"   - Issues: {len(final_analysis.get('all_issues', []))}")
                logger.info(f"   - Overall score: {final_analysis.get('overall_score', 'Missing')}")
                logger.info(f"   - Agents used: {final_analysis.get('analysis_metadata', {}).get('agents_used', [])}")
                logger.info(f"🎯 GLOBAL STORAGE: Final analysis already stored by synthesis phase")
            else:
                logger.warning(f"🎯 COORDINATOR: WARNING: No final analysis found in state for document {document_id}")
                logger.warning(f"🎯 GLOBAL STORAGE: No final analysis found in state for document {document_id}")

            logger.info(f"Multi-agent analysis completed for document {document_id}")
            
            result = final_analysis or {
                "status": "error",
                "error": "No final analysis generated",
                "document_id": document_id,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"🎯 COORDINATOR: Returning result with keys: {list(result.keys())}")
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

            # Phase 3: Cross-Validation - DELETED
            # Reason: Orthogonal agents don't have overlapping analysis areas,
            # so conflict detection is meaningless. Skipping to synthesis.

            # Phase 3: Synthesis (renamed from Phase 4)
            logger.info("🚀 WORKFLOW: Starting Phase 3 - Synthesis")
            state = await self._phase4_synthesis(state, stream_callback)
            logger.info("✅ WORKFLOW: Phase 3 completed")

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
        """Phase 2: TRUE parallel analysis by specialized agents using asyncio.gather."""

        logger.info("Phase 2: Starting REAL parallel analysis with asyncio.gather")

        # Update phase
        state = update_phase(state, PhaseStatus.PARALLEL_ANALYSIS, "Starting parallel analysis by specialized agents...")

        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "parallel_analysis",
                "message": "⚡ Running agents in parallel (legal + future agents)..."
            })

        try:
            import asyncio
            import time

            # Record start time to prove parallelism
            start_time = time.time()
            logger.info(f"⚡ COORDINATOR: Phase 2 starting parallel execution at {start_time}")

            # NEW: Run agents in TRUE PARALLEL with asyncio.gather
            # Currently: 1 agent (legal)
            # To add more agents:
            #   prior_art_task = self.prior_art_agent.analyze_with_memory(state, stream_callback)
            #   quality_task = self.quality_agent.analyze_with_memory(state, stream_callback)
            # Then: results = await asyncio.gather(legal_task, prior_art_task, quality_task)

            legal_task = self.legal_agent.analyze_with_memory(state, stream_callback)

            # TODO: Add more agents here for true parallelism:
            # prior_art_task = self.prior_art_agent.analyze_with_memory(state, stream_callback)

            # Run all agents in parallel
            agents_count = 1  # Will be 3+ when we add prior art and quality agents
            logger.info(f"⚡ COORDINATOR: Launching {agents_count} agent(s) in parallel with asyncio.gather")
            results = await asyncio.gather(
                legal_task,
                # prior_art_task,  # Uncomment when agent exists
                return_exceptions=True  # Don't fail entire analysis if one agent fails
            )

            end_time = time.time()
            duration = end_time - start_time
            logger.info(f"⚡ COORDINATOR: Phase 2 parallel execution completed in {duration:.2f}s")

            # Process results
            legal_result = results[0]

            # Check for exceptions
            if isinstance(legal_result, Exception):
                logger.error(f"Legal agent failed: {legal_result}")
                raise legal_result

            # Legal agent result is a full state dict (from analyze_with_memory)
            state = legal_result

            logger.info(f"Phase 2: Parallel analysis completed in {duration:.2f}s")

            if stream_callback:
                legal_analysis = state.get("legal_analysis", {})
                await stream_callback({
                    "status": "complete",
                    "phase": "parallel_analysis",
                    "agents_completed": ["legal"],
                    "execution_time": f"{duration:.2f}s",
                    "parallelism": "TRUE (asyncio.gather)",
                    "summary": f"Parallel execution: {duration:.2f}s"
                })

            return state

        except Exception as e:
            logger.error(f"Phase 2 failed: {e}")
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
            logger.info(f"🌍 SYNTHESIS: Storing analysis summary for {document_id} to global memory")
            success = self.memory.store_analysis_summary(document_id, final_analysis)
            logger.info(f"🌍 SYNTHESIS: Global storage result: {'✅ Success' if success else '❌ Failed'}")

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
            # Removed write-only variables: overall_score, shared_context_used (never read)
            
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

    def _generate_final_analysis_with_shared_context(
        self,
        state: PatentAnalysisState,
        shared_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive final analysis using shared memory context"""

        logger.info(f"\n🔧 SYNTHESIS: ===== GENERATING FINAL ANALYSIS =====")
        document_id = state["document_id"]
        logger.info(f"🔧 SYNTHESIS: Document ID: {document_id}")
        
        agent_findings = shared_context.get('agent_findings', {})
        cross_insights = shared_context.get('cross_agent_insights', [])

        logger.info(f"🔧 SYNTHESIS: Agent findings keys: {list(agent_findings.keys())}")
        logger.info(f"🔧 SYNTHESIS: Cross insights count: {len(cross_insights)}")

        # Collect all issues from shared memory
        logger.info(f"📊 SYNTHESIS: Collecting issues from shared memory...")
        all_issues = []
        agent_scores = []
        agent_summary = {}

        for agent_name, findings in agent_findings.items():
            logger.info(f"📊 SYNTHESIS: Processing agent '{agent_name}':")
            logger.info(f"   - Findings keys: {list(findings.keys())}")

            agent_issues = findings.get('issues', [])
            agent_confidence = findings.get('confidence', 0.0)

            logger.info(f"   - Issues found: {len(agent_issues)}")
            logger.info(f"   - Confidence: {agent_confidence}")

            # Log individual issues
            for i, issue in enumerate(agent_issues):
                logger.info(f"   - Issue {i+1}: {issue.get('type', 'unknown')} - {issue.get('severity', 'unknown')} - {issue.get('description', 'no description')[:100]}...")

            all_issues.extend(agent_issues)
            agent_scores.append(agent_confidence)
            # FIXED: Store complete findings so agents can learn from historical patterns
            agent_summary[agent_name] = {
                "confidence": agent_confidence,
                "issues": agent_issues,  # Added for memory learning
                "recommendations": findings.get('recommendations', []),  # Added for memory learning
                "analysis_type": findings.get('type', 'unknown')
            }

        logger.info(f"📊 SYNTHESIS: Total issues collected from shared memory: {len(all_issues)}")
        
        # Also check current state for direct agent results
        logger.info(f"📊 SYNTHESIS: Checking current state for direct agent results...")
        state_structure_analysis = state.get("structure_analysis", {})
        state_legal_analysis = state.get("legal_analysis", {})
        
        logger.info(f"📊 SYNTHESIS: State structure analysis keys: {list(state_structure_analysis.keys())}")
        logger.info(f"📊 SYNTHESIS: State legal analysis keys: {list(state_legal_analysis.keys())}")
        
        # Add issues from current state if they're not in shared memory
        state_structure_issues = state_structure_analysis.get('issues', [])
        state_legal_issues = state_legal_analysis.get('issues', [])
        
        logger.info(f"📊 SYNTHESIS: State structure issues: {len(state_structure_issues)}")
        logger.info(f"📊 SYNTHESIS: State legal issues: {len(state_legal_issues)}")
        
        # Add issues from state if shared memory is empty
        if len(all_issues) == 0 and (state_structure_issues or state_legal_issues):
            logger.info(f"📊 SYNTHESIS: Shared memory empty - using issues from current state")
            all_issues.extend(state_structure_issues)
            all_issues.extend(state_legal_issues)
            logger.info(f"📊 SYNTHESIS: Total issues after adding from state: {len(all_issues)}")

        # Calculate overall score using shared context
        logger.info(f"🎯 SYNTHESIS: Calculating overall score...")
        overall_score = sum(agent_scores) / len(agent_scores) if agent_scores else 0.0
        logger.info(f"🎯 SYNTHESIS: Agent scores: {agent_scores}")
        logger.info(f"🎯 SYNTHESIS: Overall score: {overall_score}")

        # Enhanced recommendations using cross-agent insights
        logger.info(f"💡 SYNTHESIS: Collecting recommendations...")
        recommendations = []
        for agent_name, findings in agent_findings.items():
            agent_recommendations = findings.get('recommendations', [])
            logger.info(f"💡 SYNTHESIS: Agent {agent_name} recommendations: {len(agent_recommendations)}")
            recommendations.extend(agent_recommendations)

        # Add recommendations from current state if shared memory is empty
        if len(recommendations) == 0:
            state_structure_recs = state_structure_analysis.get('recommendations', [])
            state_legal_recs = state_legal_analysis.get('recommendations', [])
            logger.info(f"💡 SYNTHESIS: Adding recommendations from state - Structure: {len(state_structure_recs)}, Legal: {len(state_legal_recs)}")
            recommendations.extend(state_structure_recs)
            recommendations.extend(state_legal_recs)

        # Add recommendations from cross-agent insights
        for insight in cross_insights:
            if insight.get('type') == 'confidence_divergence':
                recommendations.append("Manual review recommended due to agent confidence divergence")
            elif insight.get('type') == 'issue_aggregation':
                recommendations.append(f"Total {insight.get('description', '')} across multiple analysis domains")

        logger.info(f"💡 SYNTHESIS: Total recommendations collected: {len(recommendations)}")

        # Determine analysis status
        status = "complete"
        if len(all_issues) > 0:
            high_severity_issues = [issue for issue in all_issues if issue.get('severity') == 'high']
            if len(high_severity_issues) > 0:
                status = "issues_found"
        
        logger.info(f"📋 SYNTHESIS: Analysis status determined: {status}")

        final_analysis = {
            "status": status,
            "document_id": document_id,
            "analysis_timestamp": datetime.now().isoformat(),
            "overall_score": round(overall_score, 2),
            "agent_findings": agent_summary,  # FIXED: Renamed from phase_summary to match agent expectations
            "all_issues": all_issues,
            "cross_agent_insights": cross_insights,
            "recommendations": list(set(recommendations)),  # Remove duplicates
            "analysis_metadata": {
                "agents_used": list(agent_findings.keys()) if agent_findings else ["structure", "legal"],
                "memory_enhanced": True,
                "shared_context_used": True,
                "workflow_version": "3.0",
                "cross_insights_count": len(cross_insights),
                "conflict_detection": "disabled (orthogonal agents)"
            }
        }

        logger.info(f"🎯 SYNTHESIS: Final analysis generated with keys: {list(final_analysis.keys())}")
        logger.info(f"🎯 SYNTHESIS: Final analysis summary:")
        logger.info(f"   - Status: {final_analysis.get('status')}")
        logger.info(f"   - Issues: {len(final_analysis.get('all_issues', []))}")
        logger.info(f"   - Recommendations: {len(final_analysis.get('recommendations', []))}")
        logger.info(f"   - Overall Score: {final_analysis.get('overall_score')}")
        logger.info(f"   - Agents Used: {final_analysis.get('analysis_metadata', {}).get('agents_used', [])}")

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
