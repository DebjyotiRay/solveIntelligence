from datetime import datetime
from typing import Optional

from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup

from app.models import Document, DocumentVersion


class DatabaseService:
    
    @staticmethod
    def get_document(db: Session, document_id: int) -> Optional[Document]:
        return db.scalar(
            select(Document).where(Document.id == document_id)
        )

    @staticmethod
    def get_document_versions(db: Session, document_id: int) -> list[DocumentVersion]:
        return db.scalars(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number)
        ).all()

    @staticmethod
    def get_document_version(
        db: Session, document_id: int, version_number: int
    ) -> Optional[DocumentVersion]:
        return db.scalar(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .where(DocumentVersion.version_number == version_number)
        )

    @staticmethod
    def create_document_version(
        db: Session,
        document_id: int,
        content: str,
        name: Optional[str] = None
    ) -> DocumentVersion:
        max_version = db.scalar(
            select(func.coalesce(func.max(DocumentVersion.version_number), 0))
            .where(DocumentVersion.document_id == document_id)
            .with_for_update()
        )

        new_version_number = max_version + 1

        new_version = DocumentVersion(
            document_id=document_id,
            version_number=new_version_number,
            content=content,
            name=name or f"Version {new_version_number}"
        )

        db.add(new_version)
        db.commit()
        db.refresh(new_version)

        return new_version

    @staticmethod
    def update_document_version(
        db: Session,
        document_id: int,
        version_number: int,
        content: str,
        name: Optional[str] = None
    ) -> DocumentVersion:
        version = DatabaseService.get_document_version(
            db, document_id, version_number
        )

        if not version:
            raise ValueError(
                f"Version {version_number} not found for document {document_id}"
            )

        db.execute(
            update(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .where(DocumentVersion.version_number == version_number)
            .values(
                content=content,
                name=name if name is not None else version.name
            )
        )

        db.commit()
        db.refresh(version)

        return version

    @staticmethod
    def delete_document_version(
        db: Session, document_id: int, version_number: int
    ) -> None:
        version = DatabaseService.get_document_version(
            db, document_id, version_number
        )

        if not version:
            raise ValueError(
                f"Version {version_number} not found for document {document_id}"
            )

        version_count = db.scalar(
            select(func.count(DocumentVersion.id))
            .where(DocumentVersion.document_id == document_id)
        )

        if version_count <= 1:
            raise ValueError("Cannot delete the only version of a document")

        db.delete(version)
        db.commit()

    @staticmethod
    def get_latest_version(db: Session, document_id: int) -> Optional[DocumentVersion]:
        return db.scalar(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())
            .limit(1)
        )

    @staticmethod
    def get_or_create_document(
        db: Session,
        document_id: Optional[int],
        html_content: str
    ) -> tuple[int, str]:
        if document_id:
            doc = db.get(Document, document_id)
            if doc:
                return doc.id, doc.title

        soup = BeautifulSoup(html_content, 'html.parser')
        title_element = soup.find('title') or soup.find('h1')
        extracted_title = (
            title_element.get_text().strip()[:100]
            if title_element else "New Patent Document"
        )

        new_doc = Document(
            title=extracted_title,
            current_version=1
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        return new_doc.id, new_doc.title

    @staticmethod
    def seed_initial_data(db: Session, documents_data: list[dict]) -> None:
        for doc_data in documents_data:
            db.execute(
                insert(Document).values(
                    id=doc_data["id"],
                    title=doc_data["title"],
                    current_version=1
                )
            )

            db.execute(
                insert(DocumentVersion).values(
                    document_id=doc_data["id"],
                    version_number=1,
                    content=doc_data["content"],
                    name="Initial Draft"
                )
            )

        db.commit()
