from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import insert, select, update, func
from sqlalchemy.orm import Session

from app.internal.ai import AI, get_ai
from app.internal.data import DOCUMENT_1, DOCUMENT_2
from app.internal.db import Base, SessionLocal, engine, get_db

import app.models as models
import app.schemas as schemas


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Create the database tables
    Base.metadata.create_all(bind=engine)

    # Safe migration: Insert seed data with both old and new structure
    with SessionLocal() as db:
        # Insert documents (keep old structure temporarily for migration)
        db.execute(insert(models.Document).values(
            id=1, title="Wireless Optogenetic Device Patent",
            content=DOCUMENT_1, current_version=1
        ))
        db.execute(insert(models.Document).values(
            id=2, title="Patent Application #2",
            content=DOCUMENT_2, current_version=1
        ))

        # Create Version 1 for each document (new architecture)
        db.execute(insert(models.DocumentVersion).values(
            document_id=1, version_number=1, content=DOCUMENT_1, name="Initial Draft"
        ))
        db.execute(insert(models.DocumentVersion).values(
            document_id=2, version_number=1, content=DOCUMENT_2, name="Initial Draft"
        ))

        db.commit()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Document Management API Endpoints

@app.get("/document/{document_id}", response_model=schemas.DocumentRead)
def get_document(document_id: int, db: Session = Depends(get_db)):
    """Get document metadata (stateless - no content)"""
    doc = db.scalar(select(models.Document).where(models.Document.id == document_id))
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    return doc


# Version Management API Endpoints (Clean Stateless Architecture)

@app.get("/document/{document_id}/versions", response_model=schemas.DocumentVersionList)
def get_document_versions(document_id: int, db: Session = Depends(get_db)):
    """Get all versions of a document"""
    # Check if document exists
    doc = db.scalar(select(models.Document).where(models.Document.id == document_id))
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    versions = db.scalars(
        select(models.DocumentVersion)
        .where(models.DocumentVersion.document_id == document_id)
        .order_by(models.DocumentVersion.version_number)
    ).all()

    return schemas.DocumentVersionList(versions=versions)


@app.get("/document/{document_id}/versions/{version_number}", response_model=schemas.DocumentVersionRead)
def get_document_version(document_id: int, version_number: int, db: Session = Depends(get_db)):
    """Get a specific version of a document"""
    version = db.scalar(
        select(models.DocumentVersion)
        .where(models.DocumentVersion.document_id == document_id)
        .where(models.DocumentVersion.version_number == version_number)
    )

    if not version:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version_number} not found for document {document_id}"
        )

    return version


@app.post("/document/{document_id}/versions", response_model=schemas.DocumentVersionRead)
def create_document_version(
    document_id: int,
    version_data: schemas.DocumentVersionCreate,
    db: Session = Depends(get_db)
):
    """Create a new version with race-condition protection"""

    # Check if document exists
    doc = db.scalar(select(models.Document).where(models.Document.id == document_id))
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    # Get next version number with SELECT FOR UPDATE lock (race-condition protection)
    max_version = db.scalar(
        select(func.coalesce(func.max(models.DocumentVersion.version_number), 0))
        .where(models.DocumentVersion.document_id == document_id)
        .with_for_update()
    )

    new_version_number = max_version + 1

    # Create new version
    new_version = models.DocumentVersion(
        document_id=document_id,
        version_number=new_version_number,
        content=version_data.content,
        name=version_data.name or f"Version {new_version_number}"
    )

    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    return new_version


@app.put("/document/{document_id}/versions/{version_number}", response_model=schemas.DocumentVersionRead)
def update_document_version(
    document_id: int,
    version_number: int,
    version_data: schemas.DocumentVersionUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing version"""

    # Check if version exists
    version = db.scalar(
        select(models.DocumentVersion)
        .where(models.DocumentVersion.document_id == document_id)
        .where(models.DocumentVersion.version_number == version_number)
    )

    if not version:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version_number} not found for document {document_id}"
        )

    # Update version
    db.execute(
        update(models.DocumentVersion)
        .where(models.DocumentVersion.document_id == document_id)
        .where(models.DocumentVersion.version_number == version_number)
        .values(
            content=version_data.content,
            name=version_data.name if version_data.name is not None else version.name
        )
    )

    db.commit()
    db.refresh(version)

    return version


@app.delete("/document/{document_id}/versions/{version_number}")
def delete_document_version(document_id: int, version_number: int, db: Session = Depends(get_db)):
    """Delete a specific version (optional feature)"""

    # Check if version exists
    version = db.scalar(
        select(models.DocumentVersion)
        .where(models.DocumentVersion.document_id == document_id)
        .where(models.DocumentVersion.version_number == version_number)
    )

    if not version:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version_number} not found for document {document_id}"
        )

    # Prevent deletion of the only version
    version_count = db.scalar(
        select(func.count(models.DocumentVersion.id))
        .where(models.DocumentVersion.document_id == document_id)
    )

    if version_count <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the only version of a document"
        )

    db.delete(version)
    db.commit()

    return {"message": f"Version {version_number} deleted successfully"}


# Legacy API Endpoints (for backward compatibility during transition)

@app.get("/document/{document_id}/content")
def get_document_content_legacy(document_id: int, db: Session = Depends(get_db)):
    """Legacy endpoint: Get latest version content for backward compatibility"""
    # Get latest version
    latest_version = db.scalar(
        select(models.DocumentVersion)
        .where(models.DocumentVersion.document_id == document_id)
        .order_by(models.DocumentVersion.version_number.desc())
        .limit(1)
    )

    if not latest_version:
        raise HTTPException(status_code=404, detail=f"No versions found for document {document_id}")

    return {
        "id": document_id,
        "content": latest_version.content,
        "current_version": latest_version.version_number
    }


@app.post("/save/{document_id}")
def save_legacy(document_id: int, document: schemas.DocumentVersionCreate, db: Session = Depends(get_db)):
    """Legacy endpoint: Save as new version for backward compatibility"""
    return create_document_version(document_id, document, db)


@app.websocket("/ws")
async def websocket(websocket: WebSocket, ai: AI = Depends(get_ai)):
    await websocket.accept()
    while True:
        try:
            """
            The AI doesn't expect to receive any HTML.
            You can call ai.review_document to receive suggestions from the LLM.
            Remember, the output from the LLM will not be deterministic, so you may want to validate the output before sending it to the client.
            """
            document = await websocket.receive_text()
            print("Received data via websocket")
        except WebSocketDisconnect:
            break
        except Exception as e:
            print(f"Error occurred: {e}")
            continue
