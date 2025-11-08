"""
Shared Memory Context Service
Provides unified memory context that ALL agents can access.

Key insight: Instead of each agent querying memory independently,
they share a single "context bundle" with both legal + client knowledge.

This ensures:
1. Consistency across agents
2. Efficient memory usage (query once, use many times)
3. Cross-agent learning (what one agent learns, all agents benefit)
"""

from typing import Dict, Any, List, Optional
from app.services.memory_service import get_memory_service
from app.services.memory_types import (
    LegalMemoryResult,
    FirmMemoryResult,
    CaseMemoryResult,
    MemoryResult,
    AgentLearning,
    SharedContext
)
import logging

logger = logging.getLogger(__name__)


class SharedMemoryContext:
    """
    Unified memory context shared across all agents in a workflow.

    Think of this as a "shared workspace" where agents can:
    - Read the same legal references
    - Access the same client history
    - Contribute learnings that other agents see
    """

    def __init__(
        self,
        client_id: str,
        document_content: str,
        task_type: str = "analysis"  # or "drafting"
    ):
        self.client_id = client_id
        self.document_content = document_content
        self.task_type = task_type
        self.memory = get_memory_service()

        # Shared context (all agents read from this)
        self.legal_context: List[LegalMemoryResult] = []    # Level 1
        self.firm_context: List[FirmMemoryResult] = []      # Level 2
        self.client_context: List[CaseMemoryResult] = []    # Level 3
        self.firm_preferences: List[MemoryResult] = []      # Preferences

        # Agent contributions (agents write to this)
        self.shared_learnings: List[AgentLearning] = []

        # Build initial context
        self._build_initial_context()

    def _build_initial_context(self):
        """Build shared context that all agents will use."""
        try:
            # Level 1: Get legal knowledge relevant to the document
            self.legal_context = self.memory.query_legal_knowledge(
                query=self.document_content[:1000],  # First 1000 chars
                limit=5  # Top 5 legal references
            )

            # Level 2: Get firm knowledge (successful patents, templates)
            self.firm_context = self.memory.query_firm_knowledge(
                query=self.document_content[:1000],
                limit=3  # Top 3 firm documents
            )

            # Level 3: Get case-specific documents (via Mem0)
            self.client_context = self.memory.query_client_memory(
                client_id=self.client_id,
                query=self.document_content[:500],
                memory_type="document",  # Case-specific docs
                limit=3
            )

            # Get firm's writing preferences (from case memory)
            self.firm_preferences = self.memory.query_client_memory(
                client_id=self.client_id,
                query="writing preferences terminology style",
                memory_type="preference",
                limit=5
            )

            logger.info(
                f"✓ 3-tier context built: "
                f"L1={len(self.legal_context)} legal, "
                f"L2={len(self.firm_context)} firm, "
                f"L3={len(self.client_context)} case docs, "
                f"{len(self.firm_preferences)} preferences"
            )

        except Exception as e:
            logger.error(f"Failed to build shared context: {e}")

    def get_context_for_agent(
        self,
        agent_name: str,
        query: Optional[str] = None
    ) -> SharedContext:
        """
        Get tailored context for a specific agent.

        Different agents need different context:
        - Structure agent: Mostly client preferences (formatting)
        - Legal agent: Mostly legal knowledge + past legal issues
        - Prior art agent: Past similar patents
        """

        if agent_name == "structure":
            # Structure cares about firm formatting preferences
            return {
                "legal_references": self.legal_context[:2],  # Minimal legal
                "firm_documents": self.firm_context[:2],     # Firm style examples
                "case_documents": self.client_context[:1],   # 1 case example
                "firm_preferences": self.firm_preferences,   # All preferences
                "shared_learnings": self.shared_learnings
            }

        elif agent_name == "legal":
            # Legal agent needs heavy legal context
            return {
                "legal_references": self.legal_context,      # All legal refs
                "firm_documents": self.firm_context,         # Firm examples
                "case_documents": self.client_context,       # All case docs
                "firm_preferences": self.firm_preferences[:2],  # Some preferences
                "shared_learnings": self.shared_learnings
            }

        else:
            # Default: balanced context
            return {
                "legal_references": self.legal_context[:3],
                "firm_documents": self.firm_context[:2],
                "case_documents": self.client_context[:2],
                "firm_preferences": self.firm_preferences[:3],
                "shared_learnings": self.shared_learnings
            }

    def add_agent_learning(
        self,
        agent_name: str,
        learning: AgentLearning
    ) -> None:
        """
        Agent contributes a learning to the shared context.

        Example: Structure agent finds "user prefers 'comprising' over 'including'"
        → Adds to shared learnings
        → Legal agent can now use this preference too!
        """
        learning["source_agent"] = agent_name
        self.shared_learnings.append(learning)

        logger.info(f"📚 {agent_name} contributed learning: {learning.get('description', 'N/A')}")

    def persist_learnings(self):
        """
        Persist shared learnings to long-term memory.

        Called AFTER workflow completes to save what agents learned.
        """
        try:
            for learning in self.shared_learnings:
                if learning.get('type') == 'preference':
                    self.memory.store_client_preference(
                        client_id=self.client_id,
                        preference=learning['description'],
                        metadata={
                            'source_agent': learning['source_agent'],
                            'confidence': learning.get('confidence', 0.7),
                            'pattern_type': learning.get('pattern_type', 'general')
                        }
                    )

            logger.info(f"✓ Persisted {len(self.shared_learnings)} shared learnings to memory")

        except Exception as e:
            logger.error(f"Failed to persist learnings: {e}")

    def get_formatted_context_for_llm(
        self,
        agent_name: str,
        max_chars: int = 3000
    ) -> str:
        """
        Get formatted context string to inject into LLM prompts.

        Returns a formatted string that agents can append to their prompts.
        """
        context = self.get_context_for_agent(agent_name)

        # Build formatted string
        parts = []

        # Level 1: Legal references
        if context['legal_references']:
            parts.append("=== LEVEL 1: LEGAL KNOWLEDGE ===")
            for ref in context['legal_references'][:3]:  # Top 3
                section = ref.get('metadata', {}).get('section', 'N/A')
                text = ref.get('memory', '')[:200]  # First 200 chars
                parts.append(f"• {section}: {text}")

        # Level 2: Firm documents
        if context['firm_documents']:
            parts.append("\n=== LEVEL 2: YOUR FIRM'S SUCCESSFUL EXAMPLES ===")
            for doc in context['firm_documents'][:2]:  # Top 2
                title = doc.get('metadata', {}).get('title', 'Untitled')
                text = doc.get('memory', '')[:150]
                parts.append(f"• {title}: {text}")

        # Firm preferences
        if context['firm_preferences']:
            parts.append("\n=== YOUR FIRM'S WRITING STYLE ===")
            for pref in context['firm_preferences'][:3]:
                parts.append(f"• {pref.get('memory', '')}")

        # Level 3: Case documents
        if context['case_documents']:
            parts.append("\n=== LEVEL 3: THIS CASE'S REFERENCE DOCUMENTS ===")
            for ex in context['case_documents'][:1]:  # Just 1 example
                doc_type = ex.get('metadata', {}).get('document_type', 'document')
                text = ex.get('memory', '')[:100]
                parts.append(f"• {doc_type}: {text}")

        formatted = "\n".join(parts)

        # Truncate if too long
        if len(formatted) > max_chars:
            formatted = formatted[:max_chars] + "..."

        return formatted


def create_shared_context(
    client_id: str,
    document_content: str,
    task_type: str = "analysis"
) -> SharedMemoryContext:
    """Factory function to create shared context."""
    return SharedMemoryContext(client_id, document_content, task_type)
