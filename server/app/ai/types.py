"""
Type definitions for AI agent analysis results.
Provides strong typing with Pydantic validation.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# Shared Types for both agents
class TargetLocation(BaseModel):
    """Location information for text replacement"""
    text: Optional[str] = None
    section: Optional[str] = None
    position: Optional[Literal["before", "after", "replace"]] = None


class ReplacementText(BaseModel):
    """Replacement text specification"""
    type: Literal["add", "replace", "insert"]
    text: str


# Structure Agent Types
class DocumentSection(BaseModel):
    """A section within a patent document"""
    title: str
    content: str
    start_pos: int
    end_pos: int


class ClaimItem(BaseModel):
    """A patent claim"""
    number: int
    type: Literal["independent", "dependent"]
    text: str
    dependencies: List[int] = []


class StructuralIssue(BaseModel):
    """An issue found in document structure"""
    type: Literal["missing_section", "format_error", "clarity_issue", "claim_issue"]
    severity: Literal["high", "medium", "low"]
    description: str
    location: Optional[str] = None
    suggestion: str
    paragraph: Optional[int] = None
    target: Optional[TargetLocation] = None
    replacement: Optional[ReplacementText] = None


class StructureAnalysisResult(BaseModel):
    """Result from structure agent analysis"""
    status: Literal["complete", "error"]
    sections: List[DocumentSection] = []
    claims: List[ClaimItem] = []
    issues: List[StructuralIssue] = []
    suggestions: List[str] = []
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


# Legal Agent Types


class LegalIssue(BaseModel):
    """A legal or compliance issue"""
    type: str
    severity: Literal["high", "medium", "low"]
    description: str
    suggestion: str
    legal_basis: Optional[str] = None
    paragraph: Optional[int] = None
    target: Optional[TargetLocation] = None
    replacement: Optional[ReplacementText] = None


class PriorArtReference(BaseModel):
    """Reference to prior art"""
    title: str
    similarity_score: float = Field(ge=0.0, le=1.0, default=0.0)
    url: Optional[str] = None
    relevant_claims: List[int] = []


class LegalAnalysisResult(BaseModel):
    """Result from legal agent analysis"""
    type: str = "legal_analysis"
    comprehensive_analysis: bool = True
    conclusions: List[str] = []
    issues: List[LegalIssue] = []
    recommendations: List[str] = []
    filing_strategy: Optional[str] = None
    overall_assessment: Optional[str] = None
    legal_conclusions: List[str] = []
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


# Agent State
class AgentAnalysisState(BaseModel):
    """State passed to agents for analysis"""
    document_content: str
    document_id: Optional[int] = None
    version_number: Optional[int] = None
    previous_analyses: dict = {}
