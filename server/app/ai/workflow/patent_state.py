from typing import TypedDict, Optional, List, Dict, Any, Annotated
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage
from langgraph.graph.message import add_messages
import operator

class PatentAnalysisState(TypedDict):
    """
    Comprehensive state for patent analysis workflow.
    Tracks document data, agent findings, conflicts, and progress.
    """
    
    # Core document data
    document: Dict[str, Any]
    document_id: str
    
    # Historical context from Mem0
    historical_context: Optional[List[Dict]]
    similar_cases: Optional[List[Dict]]
    correction_patterns: Optional[Dict[str, List[Dict]]]  # agent_name -> patterns
    
    # Agent analysis results - each agent stores its findings here
    structure_analysis: Optional[Dict[str, Any]]
    legal_analysis: Optional[Dict[str, Any]]
    technical_analysis: Optional[Dict[str, Any]]
    prior_art_analysis: Optional[Dict[str, Any]]
    claims_analysis: Optional[Dict[str, Any]]
    
    # Cross-agent validation and conflict resolution
    conflicts: Annotated[List[Dict[str, Any]], operator.add]
    resolutions: Annotated[List[Dict[str, Any]], operator.add]
    
    # Progress tracking for real-time updates
    completed_agents: Annotated[List[str], operator.add]
    current_phase: str
    phase_progress: Dict[str, Dict[str, Any]]  # phase_name -> progress info
    
    # Final results and synthesis
    final_analysis: Optional[Dict[str, Any]]
    overall_score: Optional[float]
    recommendations: Annotated[List[str], operator.add]
    
    # Real-time streaming messages for WebSocket
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Error handling and recovery
    errors: Annotated[List[Dict[str, Any]], operator.add]
    retry_attempts: Dict[str, int]  # agent_name -> retry_count


class PhaseStatus:
    """Constants for workflow phases"""
    INITIALIZING = "initializing"
    STRUCTURE_ANALYSIS = "structure_analysis" 
    PARALLEL_ANALYSIS = "parallel_analysis"
    CROSS_VALIDATION = "cross_validation"
    SYNTHESIS = "synthesis"
    COMPLETE = "complete"
    ERROR = "error"


class AgentStatus:
    """Constants for agent statuses"""
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"
    RETRYING = "retrying"


def create_initial_state(
    document: Dict[str, Any],
    historical_context: Optional[List[Dict]] = None,
    similar_cases: Optional[List[Dict]] = None
) -> PatentAnalysisState:
    """
    Create initial state for patent analysis workflow.
    
    Args:
        document: The patent document to analyze
        historical_context: Previous analyses for context
        similar_cases: Similar patents from memory
        
    Returns:
        Initialized PatentAnalysisState
    """
    
    document_id = document.get("id", f"doc_{hash(str(document))}")
    
    return PatentAnalysisState(
        # Document data
        document=document,
        document_id=document_id,
        
        # Memory context
        historical_context=historical_context or [],
        similar_cases=similar_cases or [],
        correction_patterns={},
        
        # Agent results (all start as None)
        structure_analysis=None,
        legal_analysis=None,
        technical_analysis=None,
        prior_art_analysis=None,
        claims_analysis=None,
        
        # Validation and conflicts
        conflicts=[],
        resolutions=[],
        
        # Progress tracking
        completed_agents=[],
        current_phase=PhaseStatus.INITIALIZING,
        phase_progress={
            PhaseStatus.STRUCTURE_ANALYSIS: {"status": AgentStatus.WAITING, "progress": 0},
            PhaseStatus.PARALLEL_ANALYSIS: {
                "status": AgentStatus.WAITING,
                "progress": 0,
                "agents": {
                    "legal": {"status": AgentStatus.WAITING, "progress": 0},
                    "technical": {"status": AgentStatus.WAITING, "progress": 0},
                    "prior_art": {"status": AgentStatus.WAITING, "progress": 0},
                    "claims": {"status": AgentStatus.WAITING, "progress": 0}
                }
            },
            PhaseStatus.CROSS_VALIDATION: {"status": AgentStatus.WAITING, "progress": 0},
            PhaseStatus.SYNTHESIS: {"status": AgentStatus.WAITING, "progress": 0}
        },
        
        # Final results
        final_analysis=None,
        overall_score=None,
        recommendations=[],
        
        # Streaming and errors
        messages=[
            SystemMessage(content=f"Starting patent analysis for document {document_id}")
        ],
        errors=[],
        retry_attempts={}
    )


def update_agent_progress(
    state: PatentAnalysisState,
    agent_name: str,
    status: str,
    progress: int = 0,
    findings_summary: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update progress for a specific agent.
    
    Args:
        state: Current workflow state
        agent_name: Name of the agent
        status: New status for the agent
        progress: Progress percentage (0-100)
        findings_summary: Optional summary of findings
        
    Returns:
        Updated state dictionary
    """
    
    # Create a copy of the state to modify
    updated_state = dict(state)
    
    # Update phase progress
    if state["current_phase"] == PhaseStatus.PARALLEL_ANALYSIS:
        if "phase_progress" not in updated_state:
            updated_state["phase_progress"] = state["phase_progress"].copy()
            
        if "agents" not in updated_state["phase_progress"][PhaseStatus.PARALLEL_ANALYSIS]:
            updated_state["phase_progress"][PhaseStatus.PARALLEL_ANALYSIS]["agents"] = {}
            
        updated_state["phase_progress"][PhaseStatus.PARALLEL_ANALYSIS]["agents"][agent_name] = {
            "status": status,
            "progress": progress,
            "findings_summary": findings_summary
        }
        
        # Update overall parallel phase progress
        agent_progresses = [
            agent_info.get("progress", 0) 
            for agent_info in updated_state["phase_progress"][PhaseStatus.PARALLEL_ANALYSIS]["agents"].values()
        ]
        updated_state["phase_progress"][PhaseStatus.PARALLEL_ANALYSIS]["progress"] = sum(agent_progresses) // len(agent_progresses) if agent_progresses else 0
    
    # Add progress message for streaming
    progress_message = AIMessage(
        content=f"Agent {agent_name}: {status}"
        + (f" - {findings_summary}" if findings_summary else "")
        + (f" ({progress}%)" if progress > 0 else "")
    )
    
    if "messages" not in updated_state:
        updated_state["messages"] = []
    updated_state["messages"].append(progress_message)
    
    return updated_state


def update_phase(
    state: PatentAnalysisState,
    new_phase: str,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update the current phase of the workflow.
    
    Args:
        state: Current workflow state
        new_phase: New phase to transition to
        message: Optional message about the phase transition
        
    Returns:
        Updated state dictionary
    """
    
    updated_state = dict(state)
    updated_state["current_phase"] = new_phase
    
    # Update phase status
    if "phase_progress" not in updated_state:
        updated_state["phase_progress"] = state["phase_progress"].copy()
        
    if new_phase in updated_state["phase_progress"]:
        updated_state["phase_progress"][new_phase]["status"] = AgentStatus.RUNNING
    
    # Add phase transition message
    phase_message = SystemMessage(
        content=message or f"Transitioning to phase: {new_phase}"
    )
    
    if "messages" not in updated_state:
        updated_state["messages"] = []
    updated_state["messages"].append(phase_message)
    
    return updated_state


def add_error(
    state: PatentAnalysisState,
    agent_name: str,
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Add an error to the state for tracking and recovery.
    
    Args:
        state: Current workflow state
        agent_name: Name of the agent that encountered the error
        error: The exception that occurred
        context: Additional context about the error
        
    Returns:
        Updated state dictionary
    """
    
    updated_state = dict(state)
    
    error_entry = {
        "agent": agent_name,
        "error": str(error),
        "error_type": type(error).__name__,
        "timestamp": str(pd.Timestamp.now()) if 'pd' in globals() else "now",
        "context": context or {}
    }
    
    if "errors" not in updated_state:
        updated_state["errors"] = []
    updated_state["errors"].append(error_entry)
    
    # Update retry attempts
    if "retry_attempts" not in updated_state:
        updated_state["retry_attempts"] = {}
    updated_state["retry_attempts"][agent_name] = updated_state["retry_attempts"].get(agent_name, 0) + 1
    
    # Add error message for streaming
    error_message = AIMessage(
        content=f"Error in {agent_name}: {str(error)[:100]}..."
    )
    
    if "messages" not in updated_state:
        updated_state["messages"] = []
    updated_state["messages"].append(error_message)
    
    return updated_state


def get_state_summary(state: PatentAnalysisState) -> Dict[str, Any]:
    """
    Get a summary of the current state for debugging/monitoring.
    
    Args:
        state: Current workflow state
        
    Returns:
        Summary dictionary
    """
    
    completed_count = len(state.get("completed_agents", []))
    total_errors = len(state.get("errors", []))
    current_phase = state.get("current_phase", "unknown")
    
    return {
        "document_id": state.get("document_id"),
        "current_phase": current_phase,
        "completed_agents": completed_count,
        "total_errors": total_errors,
        "has_conflicts": len(state.get("conflicts", [])) > 0,
        "overall_score": state.get("overall_score"),
        "is_complete": current_phase == PhaseStatus.COMPLETE,
        "message_count": len(state.get("messages", [])),
        "phase_progress": state.get("phase_progress", {})
    }
