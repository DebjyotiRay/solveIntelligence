from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint, func, ForeignKey

from app.internal.db import Base


class Document(Base):
    __tablename__ = "document"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, default="Untitled Patent")
    current_version = Column(Integer, default=1)


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("document.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
    name = Column(String, nullable=True)  # Optional: "Claims Update", "Final Draft"

    # Ensure unique version numbers per document
    __table_args__ = (UniqueConstraint('document_id', 'version_number'),)


# Include your models here, and they will automatically be created as tables in the database on start-up
