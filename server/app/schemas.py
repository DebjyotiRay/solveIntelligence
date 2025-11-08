from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime
from typing import List, Optional


class DocumentBase(BaseModel):
    title: str = "Untitled Patent"


class DocumentRead(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    # Removed: content field (eliminate duplication)
    # Removed: current_version field (eliminate global state)


class DocumentVersionBase(BaseModel):
    content: str
    name: Optional[str] = None


class DocumentVersionRead(DocumentVersionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    version_number: int
    created_at: datetime


class DocumentVersionCreate(BaseModel):
    content: str
    name: Optional[str] = None


class DocumentVersionUpdate(BaseModel):
    content: str
    name: Optional[str] = None


class DocumentVersionList(BaseModel):
    versions: List[DocumentVersionRead]


# Chat schemas
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    client_id: str
    document_id: Optional[int] = None
    conversation_history: Optional[List[ChatMessage]] = None
    document_context: Optional[str] = None
    analysis_results: Optional[dict] = None  # AI analysis results (issues, scores, etc.)


class ChatSource(BaseModel):
    id: int
    citation: str
    content: str
    tier: str


class ChatResponse(BaseModel):
    response: str
    sources: List[ChatSource]
    metadata: dict


# Learning & Feedback schemas
class SuggestionFeedbackRequest(BaseModel):
    client_id: str
    suggestion_id: str
    action: str  # "accepted", "rejected", "modified"
    suggested_text: str
    actual_text: Optional[str] = None
    context_before: Optional[str] = None
    context_after: Optional[str] = None


class LearnSessionRequest(BaseModel):
    client_id: str
    document_text: str
    document_id: Optional[str] = None
