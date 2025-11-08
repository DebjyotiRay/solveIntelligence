from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint, func, ForeignKey, Boolean

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


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class Project(Base):
    __tablename__ = "project"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    # Associate a single document to this project for simplicity
    document_id = Column(Integer, ForeignKey("document.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=func.now())


class ProjectMember(Base):
    __tablename__ = "project_member"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    # roles: owner/editor/viewer; status: pending/approved
    role = Column(String, default="viewer")
    status = Column(String, default="pending")
    __table_args__ = (UniqueConstraint('project_id', 'user_id'),)


# Include your models here, and they will automatically be created as tables in the database on start-up
