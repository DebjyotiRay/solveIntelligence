from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List


class DocumentBase(BaseModel):
    content: str


class DocumentRead(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    current_version: int


class DocumentVersionBase(BaseModel):
    content: str


class DocumentVersionRead(DocumentVersionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    version_number: int
    created_at: datetime


class DocumentVersionCreate(BaseModel):
    pass  # Will copy from current version


class DocumentVersionList(BaseModel):
    versions: List[DocumentVersionRead]
