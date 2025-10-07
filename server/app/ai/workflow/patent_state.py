from typing import TypedDict, Optional, Dict, Any, List


class PatentAnalysisState(TypedDict, total=False):
    """State for patent analysis workflow."""
    
    # Core data
    document: Dict[str, Any]
    document_id: str
    
    # Agent results
    structure_analysis: Optional[Dict[str, Any]]
    legal_analysis: Optional[Dict[str, Any]]
    
    # Progress
    current_phase: str
    completed_agents: List[str]
    
    # Results
    final_analysis: Optional[Dict[str, Any]]
    
    # Errors
    errors: List[Dict[str, Any]]
    retry_attempts: Dict[str, int]


class PhaseStatus:
    """Workflow phases."""
    STRUCTURE_ANALYSIS = "structure_analysis" 
    PARALLEL_ANALYSIS = "parallel_analysis"
    SYNTHESIS = "synthesis"
    COMPLETE = "complete"
    ERROR = "error"


class AgentStatus:
    """Agent statuses."""
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


def create_initial_state(document: Dict[str, Any]) -> PatentAnalysisState:
    """Create initial workflow state."""
    
    return PatentAnalysisState(
        document=document,
        document_id=str(document.get("id", "")),
        structure_analysis=None,
        legal_analysis=None,
        current_phase=PhaseStatus.STRUCTURE_ANALYSIS,
        completed_agents=[],
        final_analysis=None,
        errors=[],
        retry_attempts={}
    )


def update_phase(state: PatentAnalysisState, new_phase: str, message: str = "") -> Dict[str, Any]:
    """Update current phase."""
    updated_state = dict(state)
    updated_state["current_phase"] = new_phase
    return updated_state


def update_agent_progress(
    state: PatentAnalysisState,
    agent_name: str,
    status: str,
    progress: int = 0,
    findings_summary: str = ""
) -> Dict[str, Any]:
    """Update agent progress (minimal implementation)."""
    return dict(state)
