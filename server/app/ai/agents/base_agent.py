from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from ..memory.patent_memory import PatentAnalysisMemory
from ..workflow.patent_state import PatentAnalysisState, update_agent_progress, AgentStatus

logger = logging.getLogger(__name__)

class BasePatentAgent(ABC):
    """
    Base class for all patent analysis agents.
    Provides memory integration, error handling, and standardized analysis flow.
    """
    
    def __init__(
        self, 
        agent_name: str, 
        memory: PatentAnalysisMemory,
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
        """
        Perform agent-specific analysis.
        
        Args:
            state: Current workflow state containing document and context
            stream_callback: Optional callback for streaming progress updates
            
        Returns:
            Updated state dictionary with agent's findings
        """
        pass

    async def analyze_with_memory(
        self, 
        state: PatentAnalysisState,
        stream_callback=None
    ) -> Dict[str, Any]:
        """
        Main analysis entry point with memory integration and error handling.
        
        Args:
            state: Current workflow state
            stream_callback: Optional callback for streaming progress updates
            
        Returns:
            Updated state with analysis results
        """
        
        document_id = state["document_id"]
        print(f"\n🔍 AGENT [{self.agent_name.upper()}]: Starting analysis for document {document_id}")
        print(f"📊 AGENT [{self.agent_name.upper()}]: Memory system: {type(self.memory).__name__}")
        print(f"⚙️  AGENT [{self.agent_name.upper()}]: Max retries: {self.max_retries}")
        self.logger.info(f"Starting analysis for document {document_id}")
        
        try:
            # Update progress to running
            updated_state = update_agent_progress(
                state, 
                self.agent_name, 
                AgentStatus.RUNNING,
                progress=10,
                findings_summary="Loading historical context..."
            )
            
            # Get shared memory context (includes previous agent findings)
            shared_context = self.memory.get_shared_analysis_context(document_id)
            historical_context = self._get_historical_context(document_id)
            correction_patterns = self._get_correction_patterns()

            # Add all memory context to state
            updated_state["shared_memory_context"] = shared_context
            updated_state["historical_context"] = historical_context
            if "correction_patterns" not in updated_state:
                updated_state["correction_patterns"] = {}
            updated_state["correction_patterns"][self.agent_name] = correction_patterns

            # Extract previous agent findings for this agent to use
            previous_agent_findings = shared_context.get('agent_findings', {})
            if previous_agent_findings:
                print(f"🔗 AGENT [{self.agent_name.upper()}]: Found {len(previous_agent_findings)} previous agent findings")
                for agent_name, findings in previous_agent_findings.items():
                    print(f"🔗 AGENT [{self.agent_name.upper()}]: {agent_name} analysis - confidence: {findings.get('confidence', 'N/A')}, issues: {len(findings.get('issues', []))}")
                updated_state["previous_agent_findings"] = previous_agent_findings
            
            # Update progress
            updated_state = update_agent_progress(
                updated_state, 
                self.agent_name, 
                AgentStatus.RUNNING,
                progress=30,
                findings_summary="Analyzing document..."
            )
            
            # Perform the actual analysis with streaming support
            analysis_result = await self.analyze(updated_state, stream_callback)
            
            # Validate analysis result
            validated_result = self._validate_analysis_result(analysis_result)
            
            # Apply correction patterns if available
            corrected_result = self._apply_correction_patterns(
                validated_result, 
                correction_patterns
            )
            
            # Store findings in memory
            self._store_findings(document_id, corrected_result)
            
            # Update state with completed analysis
            final_state = self._update_state_with_results(updated_state, corrected_result)
            
            # Update progress to complete
            final_state = update_agent_progress(
                final_state, 
                self.agent_name, 
                AgentStatus.COMPLETE,
                progress=100,
                findings_summary=self._get_findings_summary(corrected_result)
            )
            
            # Add agent to completed list
            if "completed_agents" not in final_state:
                final_state["completed_agents"] = []
            if self.agent_name not in final_state["completed_agents"]:
                final_state["completed_agents"].append(self.agent_name)
            
            self.logger.info(f"Analysis completed successfully for {self.agent_name}")
            return final_state
            
        except Exception as e:
            self.logger.error(f"Analysis failed for {self.agent_name}: {e}")
            
            # Handle retry logic
            retry_count = state.get("retry_attempts", {}).get(self.agent_name, 0)
            
            if retry_count < self.max_retries:
                self.logger.info(f"Retrying analysis for {self.agent_name} (attempt {retry_count + 1})")
                
                # Update retry count
                if "retry_attempts" not in state:
                    updated_state = dict(state)
                    updated_state["retry_attempts"] = {}
                else:
                    updated_state = state
                updated_state["retry_attempts"][self.agent_name] = retry_count + 1
                
                # Retry the analysis
                return await self.analyze_with_memory(updated_state)
            else:
                # Max retries reached, return error state
                error_state = self._handle_analysis_failure(state, e)
                return error_state

    def _get_historical_context(self, document_id: str) -> List[Dict]:
        """Get historical context for this agent from memory."""
        print(f"🧠 MEMORY [{self.agent_name.upper()}]: Retrieving historical context for document {document_id}")
        try:
            # Use the new shared context method for better historical data
            shared_context = self.memory.get_shared_analysis_context(document_id)

            # Extract historical patterns specific to this agent
            agent_findings = shared_context.get('agent_findings', {})
            historical_patterns = shared_context.get('historical_patterns', [])

            # Combine agent-specific and cross-agent historical context
            context = []
            if self.agent_name in agent_findings:
                context.append({
                    "type": "previous_analysis",
                    "agent": self.agent_name,
                    "findings": agent_findings[self.agent_name]
                })

            # Add cross-agent historical patterns
            context.extend(historical_patterns)

            print(f"🧠 MEMORY [{self.agent_name.upper()}]: Retrieved {len(context)} historical context items")
            if context:
                print(f"🧠 MEMORY [{self.agent_name.upper()}]: Context preview: {context[0].get('type', 'unknown')} context available")
            else:
                print(f"🧠 MEMORY [{self.agent_name.upper()}]: No historical context found - this might be first analysis")
            return context
        except Exception as e:
            print(f"🧠 MEMORY [{self.agent_name.upper()}]: FAILED to get historical context: {e}")
            self.logger.warning(f"Failed to get historical context: {e}")
            return []

    def _get_correction_patterns(self) -> List[Dict]:
        """Get correction patterns for this agent from memory."""
        print(f"🔧 PATTERNS [{self.agent_name.upper()}]: Retrieving correction patterns for agent")
        try:
            patterns = self.memory.get_agent_correction_patterns(self.agent_name)
            print(f"🔧 PATTERNS [{self.agent_name.upper()}]: Retrieved {len(patterns)} correction patterns")
            if patterns:
                print(f"🔧 PATTERNS [{self.agent_name.upper()}]: Pattern preview: {patterns[0] if patterns else 'None'}")
            else:
                print(f"🔧 PATTERNS [{self.agent_name.upper()}]: No correction patterns found - agent learning from scratch")
            return patterns
        except Exception as e:
            print(f"🔧 PATTERNS [{self.agent_name.upper()}]: FAILED to get correction patterns: {e}")
            self.logger.warning(f"Failed to get correction patterns: {e}")
            return []

    def _validate_analysis_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize analysis results.
        
        Args:
            result: Raw analysis result
            
        Returns:
            Validated and normalized result
        """
        
        # Ensure required fields exist
        validated = {
            "agent": self.agent_name,
            "timestamp": datetime.now().isoformat(),
            "confidence": result.get("confidence", 0.5),
            "type": result.get("type", f"{self.agent_name}_analysis"),
            **result
        }
        
        # Ensure confidence is in valid range
        validated["confidence"] = max(0.0, min(1.0, validated["confidence"]))
        
        return validated

    def _apply_correction_patterns(
        self, 
        result: Dict[str, Any], 
        patterns: List[Dict]
    ) -> Dict[str, Any]:
        """
        Apply learned correction patterns to improve results.
        
        Args:
            result: Analysis result to correct
            patterns: Historical correction patterns
            
        Returns:
            Corrected result
        """
        
        corrected_result = result.copy()
        corrections_applied = []
        
        for pattern in patterns:
            try:
                # Apply pattern-based corrections
                pattern_type = pattern.get("pattern_type")
                effectiveness = pattern.get("effectiveness", 1.0)
                
                # Only apply high-effectiveness patterns
                if effectiveness > 0.7:
                    # Pattern-specific correction logic would go here
                    # For now, we'll log the pattern availability
                    corrections_applied.append(pattern_type)
                    
            except Exception as e:
                self.logger.warning(f"Failed to apply correction pattern: {e}")
                continue
        
        if corrections_applied:
            corrected_result["corrections_applied"] = corrections_applied
            self.logger.info(f"Applied {len(corrections_applied)} correction patterns")
        
        return corrected_result

    def _store_findings(self, document_id: str, findings: Dict[str, Any]) -> bool:
        """Store analysis findings in memory for future learning."""
        print(f"💾 STORE [{self.agent_name.upper()}]: Attempting to store findings for document {document_id}")
        print(f"💾 STORE [{self.agent_name.upper()}]: Findings summary - confidence: {findings.get('confidence', 'N/A')}, issues: {len(findings.get('issues', []))}")
        try:
            success = self.memory.store_agent_findings(
                document_id,
                self.agent_name,
                findings,
                metadata={
                    "analysis_version": "2.0",
                    "memory_enhanced": True
                }
            )
            
            if success:
                print(f"💾 STORE [{self.agent_name.upper()}]: ✅ Successfully stored findings in memory")
            else:
                print(f"💾 STORE [{self.agent_name.upper()}]: ❌ Failed to store findings in memory")
            
            return success
        except Exception as e:
            print(f"💾 STORE [{self.agent_name.upper()}]: ❌ Exception during storage: {e}")
            self.logger.error(f"Failed to store findings: {e}")
            return False

    def _update_state_with_results(
        self, 
        state: Dict[str, Any], 
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update the workflow state with this agent's results.
        
        Args:
            state: Current workflow state
            results: Analysis results to add
            
        Returns:
            Updated state
        """
        
        updated_state = dict(state)
        
        # Store results in the appropriate state field
        analysis_field = f"{self.agent_name}_analysis"
        updated_state[analysis_field] = results
        
        return updated_state

    def _get_findings_summary(self, results: Dict[str, Any]) -> str:
        """
        Generate a brief summary of findings for progress updates.
        
        Args:
            results: Analysis results
            
        Returns:
            Brief summary string
        """
        
        confidence = results.get("confidence", 0.0)
        issues_count = len(results.get("issues", []))
        
        return f"Confidence: {confidence:.2f}, Issues found: {issues_count}"

    def _handle_analysis_failure(
        self, 
        state: Dict[str, Any], 
        error: Exception
    ) -> Dict[str, Any]:
        """
        Handle analysis failure and create appropriate error state.
        
        Args:
            state: Current state
            error: Exception that occurred
            
        Returns:
            Error state
        """
        
        error_state = dict(state)
        
        # Update progress to error
        error_state = update_agent_progress(
            error_state,
            self.agent_name,
            AgentStatus.ERROR,
            progress=0,
            findings_summary=f"Analysis failed: {str(error)[:50]}"
        )
        
        # Add error to state
        if "errors" not in error_state:
            error_state["errors"] = []
            
        error_state["errors"].append({
            "agent": self.agent_name,
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": datetime.now().isoformat()
        })
        
        # Create fallback analysis result
        fallback_result = {
            "agent": self.agent_name,
            "type": f"{self.agent_name}_analysis_failed",
            "error": str(error),
            "confidence": 0.0,
            "issues": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Store fallback result
        analysis_field = f"{self.agent_name}_analysis"
        error_state[analysis_field] = fallback_result
        
        return error_state

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """
        Return information about this agent's capabilities.
        
        Returns:
            Capabilities dictionary
        """
        
        return {
            "agent_name": self.agent_name,
            "max_retries": self.max_retries,
            "memory_enabled": True,
            "correction_patterns_enabled": True,
            "error_recovery_enabled": True
        }
