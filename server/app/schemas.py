from pydantic import BaseModel, ConfigDict
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
