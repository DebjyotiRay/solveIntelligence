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
        """Execute complete multi-agent patent analysis."""
        
        document_id = document.get("id")
        if not document_id:
            raise ValueError("Document ID is required")
            
        logger.info(f"Starting analysis for document {document_id}")
        
        try:
            state = create_initial_state(document=document)
            state = await self._execute_workflow(state, stream_callback)
            
            final_analysis = state.get("final_analysis")
            if not final_analysis:
                raise ValueError("No final analysis generated")
            
            logger.info(f"Analysis completed - {len(final_analysis.get('all_issues', []))} issues found")
            return final_analysis
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
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
        """Execute 3-phase workflow: Structure → Parallel → Synthesis."""
        
        try:
            state = await self._phase1_structure_analysis(state, stream_callback)
            state = await self._phase2_parallel_analysis(state, stream_callback)
            state = await self._phase4_synthesis(state, stream_callback)
            return state
            
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
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
        """Phase 1: Structure analysis."""
        
        state = update_phase(state, PhaseStatus.STRUCTURE_ANALYSIS, "Analyzing document structure...")
        
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "structure_analysis",
                "agent": "structure",
                "message": "Analyzing document structure..."
            })
        
        state = await self.structure_agent.analyze_with_memory(state, stream_callback)
        
        if stream_callback:
            result = state.get("structure_analysis", {})
            await stream_callback({
                "status": "complete",
                "phase": "structure_analysis", 
                "agent": "structure",
                "summary": f"Found {len(result.get('issues', []))} issues"
            })
        
        return state

    async def _phase2_parallel_analysis(
        self,
        state: PatentAnalysisState,
        stream_callback: Optional[callable] = None
    ) -> PatentAnalysisState:
        """Phase 2: Parallel analysis (legal + future agents)."""

        state = update_phase(state, PhaseStatus.PARALLEL_ANALYSIS, "Running parallel analysis...")

        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "parallel_analysis",
                "message": "Running legal compliance analysis..."
            })

        # Run agents in parallel (currently just legal)
        # To add more: results = await asyncio.gather(legal_task, prior_art_task, quality_task)
        results = await asyncio.gather(
            self.legal_agent.analyze_with_memory(state, stream_callback),
            return_exceptions=True
        )

        # Check for exceptions
        if isinstance(results[0], Exception):
            raise results[0]

        state = results[0]

        if stream_callback:
            await stream_callback({
                "status": "complete",
                "phase": "parallel_analysis",
                "summary": f"Found {len(state.get('legal_analysis', {}).get('issues', []))} issues"
            })

        return state

    async def _phase4_synthesis(
        self, 
        state: PatentAnalysisState,
        stream_callback: Optional[callable] = None
    ) -> PatentAnalysisState:
        """Phase 3: Final synthesis."""
        
        state = update_phase(state, PhaseStatus.SYNTHESIS, "Generating final report...")
        
        if stream_callback:
            await stream_callback({
                "status": "analyzing",
                "phase": "synthesis",
                "message": "Generating final report..."
            })
        
        final_analysis = self._generate_final_analysis(state)
        
        updated_state = dict(state)
        updated_state["final_analysis"] = final_analysis
        updated_state["current_phase"] = PhaseStatus.COMPLETE
        
        if stream_callback:
            await stream_callback({
                "status": "complete",
                "phase": "synthesis",
                "overall_score": final_analysis.get("overall_score", 0.0),
                "total_issues": len(final_analysis.get("all_issues", []))
            })
        
        return updated_state

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
