from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from ..workflow.patent_state import PatentAnalysisState, update_agent_progress, AgentStatus

logger = logging.getLogger(__name__)

class BasePatentAgent(ABC):
    
    def __init__(
        self, 
        agent_name: str, 
        memory=None,
        max_retries: int = 3
    ):
        self.agent_name = agent_name
        self.memory = memory
        self.max_retries = max_retries
        self.logger = logging.getLogger(f"agent.{agent_name}")

    @abstractmethod
    async def analyze(
        self, 
        state: PatentAnalysisState,
        stream_callback=None
    ) -> Dict[str, Any]:
        pass

    async def analyze_with_memory(
        self, 
        state: PatentAnalysisState,
        stream_callback=None
    ) -> Dict[str, Any]:
        
        document_id = state["document_id"]
        self.logger.info(f"Starting analysis for document {document_id}")
        
        try:
            updated_state = update_agent_progress(
                state, 
                self.agent_name, 
                AgentStatus.RUNNING,
                progress=10,
                findings_summary="Starting analysis..."
            )
            
            analysis_result = await self.analyze(updated_state, stream_callback)
            validated_result = self._validate_analysis_result(analysis_result)
            final_state = self._update_state_with_results(updated_state, validated_result)
            
            final_state = update_agent_progress(
                final_state, 
                self.agent_name, 
                AgentStatus.COMPLETE,
                progress=100,
                findings_summary=self._get_findings_summary(validated_result)
            )
            
            if "completed_agents" not in final_state:
                final_state["completed_agents"] = []
            if self.agent_name not in final_state["completed_agents"]:
                final_state["completed_agents"].append(self.agent_name)
            
            self.logger.info(f"Analysis completed successfully for {self.agent_name}")
            return final_state
            
        except Exception as e:
            self.logger.error(f"Analysis failed for {self.agent_name}: {e}")
            
            retry_count = state.get("retry_attempts", {}).get(self.agent_name, 0)
            
            if retry_count < self.max_retries:
                self.logger.info(f"Retrying analysis for {self.agent_name} (attempt {retry_count + 1})")
                
                if "retry_attempts" not in state:
                    updated_state = dict(state)
                    updated_state["retry_attempts"] = {}
                else:
                    updated_state = state
                updated_state["retry_attempts"][self.agent_name] = retry_count + 1
                
                return await self.analyze_with_memory(updated_state, stream_callback)
            else:
                error_state = self._handle_analysis_failure(state, e)
                return error_state

    def _validate_analysis_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        
        validated = {
            "agent": self.agent_name,
            "timestamp": datetime.now().isoformat(),
            "confidence": result.get("confidence", 0.5),
            "type": result.get("type", f"{self.agent_name}_analysis"),
            **result
        }
        
        validated["confidence"] = max(0.0, min(1.0, validated["confidence"]))
        
        return validated


    def _update_state_with_results(
        self, 
        state: Dict[str, Any], 
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        updated_state = dict(state)
        analysis_field = f"{self.agent_name}_analysis"
        updated_state[analysis_field] = results
        
        return updated_state

    def _get_findings_summary(self, results: Dict[str, Any]) -> str:
        
        confidence = results.get("confidence", 0.0)
        issues_count = len(results.get("issues", []))
        
        return f"Confidence: {confidence:.2f}, Issues found: {issues_count}"

    def _handle_analysis_failure(
        self, 
        state: Dict[str, Any], 
        error: Exception
    ) -> Dict[str, Any]:
        
        error_state = dict(state)
        
        error_state = update_agent_progress(
            error_state,
            self.agent_name,
            AgentStatus.ERROR,
            progress=0,
            findings_summary=f"Analysis failed: {str(error)[:50]}"
        )
        
        if "errors" not in error_state:
            error_state["errors"] = []
            
        error_state["errors"].append({
            "agent": self.agent_name,
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": datetime.now().isoformat()
        })
        
        fallback_result = {
            "agent": self.agent_name,
            "type": f"{self.agent_name}_analysis_failed",
            "error": str(error),
            "confidence": 0.0,
            "issues": [],
            "timestamp": datetime.now().isoformat()
        }
        
        analysis_field = f"{self.agent_name}_analysis"
        error_state[analysis_field] = fallback_result
        
        return error_state

    def get_agent_capabilities(self) -> Dict[str, Any]:
        
        return {
            "agent_name": self.agent_name,
            "max_retries": self.max_retries,
            "error_recovery_enabled": True
        }
