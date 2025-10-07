import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..agents.structure_agent import DocumentStructureAgent
from ..agents.legal_agent import LegalComplianceAgent
from .patent_state import (
    PatentAnalysisState, create_initial_state, 
    PhaseStatus, AgentStatus, update_phase
)

logger = logging.getLogger(__name__)


class PatentAnalysisCoordinator:
    """
    Main coordinator for multi-agent patent analysis workflow.
    Implements 3-phase analysis: Structure → Parallel Analysis → Synthesis.
    """
    
    def __init__(self):
        # Initialize agents
        self.structure_agent = DocumentStructureAgent()
        self.legal_agent = LegalComplianceAgent()
        
        logger.info("PatentAnalysisCoordinator initialized")

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
            
        logger.info(f"Starting multi-agent analysis for document {document_id}")
        
        try:
            # Initialize workflow state
            state = create_initial_state(document=document)
            
            # Execute 3-phase workflow
            state = await self._execute_workflow(state, stream_callback)
            
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
        """Phase 3: Final synthesis and report generation."""
        
        logger.info("Phase 3 (Synthesis): Starting synthesis")
        
        # Update phase
        state = update_phase(state, PhaseStatus.SYNTHESIS, "Synthesizing final analysis report...")
        
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "synthesis",
                "message": "Generating comprehensive analysis report..."
            })
        
        try:
            if not state:
                raise ValueError("State is None during synthesis")

            document_id = state.get("document_id")
            if not document_id:
                raise ValueError("No document_id found in state")

            # Generate final analysis from current state
            final_analysis = self._generate_final_analysis(state)

            # Update state
            updated_state = dict(state)
            updated_state["final_analysis"] = final_analysis
            updated_state["current_phase"] = PhaseStatus.COMPLETE
            
            logger.info("Phase 3 (Synthesis): Synthesis completed")
            
            if stream_callback:
                await stream_callback({
                    "status": "complete",
                    "phase": "synthesis",
                    "overall_score": final_analysis.get("overall_score", 0.0),
                    "total_issues": len(final_analysis.get("all_issues", []))
                })
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Phase 3 (Synthesis) failed: {e}")
            raise

    def _generate_final_analysis(self, state: PatentAnalysisState) -> Dict[str, Any]:
        """Generate final analysis from current state."""
        
        document_id = state["document_id"]
        
        # Get agent results from state
        structure_analysis = state.get("structure_analysis", {})
        legal_analysis = state.get("legal_analysis", {})
        
        # Collect all issues
        all_issues = []
        all_issues.extend(structure_analysis.get('issues', []))
        all_issues.extend(legal_analysis.get('issues', []))
        
        # Collect recommendations
        recommendations = []
        recommendations.extend(structure_analysis.get('recommendations', []))
        recommendations.extend(legal_analysis.get('recommendations', []))
        
        # Calculate overall score
        structure_confidence = structure_analysis.get('confidence', 0.0)
        legal_confidence = legal_analysis.get('confidence', 0.0)
        overall_score = (structure_confidence + legal_confidence) / 2.0
        
        # Determine status
        status = "complete"
        if len(all_issues) > 0:
            high_severity_issues = [issue for issue in all_issues if issue.get('severity') == 'high']
            if len(high_severity_issues) > 0:
                status = "issues_found"
        
        return {
            "status": status,
            "document_id": document_id,
            "analysis_timestamp": datetime.now().isoformat(),
            "overall_score": round(overall_score, 2),
            "all_issues": all_issues,
            "recommendations": list(set(recommendations)),
            "analysis_metadata": {
                "agents_used": ["structure", "legal"],
                "workflow_version": "3.0"
            }
        }
