"""
Type definitions for 3-tier hierarchical memory system.

Provides strong typing for memory results across all levels.
"""

from typing import TypedDict, Literal, Optional


class MemoryMetadata(TypedDict, total=False):
    """Base metadata for all memory types."""
    source: str
    section: Optional[str]
    document_type: str
    category: str
    title: Optional[str]
    firm_id: Optional[str]
    client_id: Optional[str]
    memory_type: Optional[str]


class MemoryResult(TypedDict):
    """Standard memory query result format."""
    id: str
    memory: str  # The actual text content
    metadata: MemoryMetadata
    score: Optional[float]  # Similarity score (0-1)


class LegalMemoryMetadata(TypedDict):
    """Metadata specific to legal knowledge (Level 1)."""
    source: str  # e.g., "Indian Patent Act, 1970"
    section: str  # e.g., "3(k)"
    document_type: Literal["statute", "criminal_law", "evidence_law", "constitutional_law"]
    category: str  # e.g., "patent_law", "fundamental_rights"
    topic: str  # e.g., "section_3k"


class LegalMemoryResult(TypedDict):
    """Level 1: Legal knowledge result."""
    id: str
    memory: str
    metadata: LegalMemoryMetadata
    score: Optional[float]


class FirmMemoryMetadata(TypedDict):
    """Metadata specific to firm knowledge (Level 2)."""
    source: str  # e.g., "successful_patent_2024.pdf"
    section: str  # e.g., "chunk_1"
    document_type: Literal["firm_document"]
    firm_id: str  # e.g., "default_firm"
    category: Literal["firm_knowledge"]
    title: str  # e.g., "successful_patent_2024.pdf - Part 1"


class FirmMemoryResult(TypedDict):
    """Level 2: Firm knowledge result."""
    id: str
    memory: str
    metadata: FirmMemoryMetadata
    score: Optional[float]


class CaseMemoryMetadata(TypedDict, total=False):
    """Metadata specific to case documents (Level 3)."""
    document_id: str
    document_type: str  # e.g., "invention_disclosure", "prior_art"
    title: str
    client_id: str
    memory_type: Literal["document", "analysis", "preference"]
    timestamp: str


class CaseMemoryResult(TypedDict):
    """Level 3: Case-specific knowledge result."""
    id: str
    memory: str
    metadata: CaseMemoryMetadata
    score: Optional[float]


class SharedContext(TypedDict):
    """Complete shared context passed to agents."""
    legal_references: list[LegalMemoryResult]
    firm_documents: list[FirmMemoryResult]
    case_documents: list[CaseMemoryResult]
    firm_preferences: list[MemoryResult]
    shared_learnings: list[dict]  # Learnings contributed by agents


class AgentLearning(TypedDict):
    """Learning contributed by an agent to shared context."""
    type: Literal["preference", "pattern", "insight"]
    description: str
    source_agent: str
    confidence: float
    pattern_type: Optional[str]
    examples: Optional[list[str]]
