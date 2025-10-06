from contextlib import asynccontextmanager
import json
import os

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.internal.data import DOCUMENT_1, DOCUMENT_2
from app.internal.db import Base, SessionLocal, engine, get_db
import app.models as models
import app.schemas as schemas
from app.services.database_service import DatabaseService
from app.services.websocket_service import WebSocketService

USE_MULTI_AGENT_SYSTEM = os.getenv("USE_MULTI_AGENT_SYSTEM", "false").lower() == "true"


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        seed_data = [
            {"id": 1, "title": "Wireless Optogenetic Device Patent", "content": DOCUMENT_1},
            {"id": 2, "title": "Patent Application #2", "content": DOCUMENT_2}
        ]
        DatabaseService.seed_initial_data(db, seed_data)

    yield


fastapi_app = FastAPI(lifespan=lifespan)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@fastapi_app.get("/document/{document_id}", response_model=schemas.DocumentRead)
def get_document(document_id: int, db: Session = Depends(get_db)):
    doc = DatabaseService.get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    return doc


@fastapi_app.get("/document/{document_id}/versions", response_model=schemas.DocumentVersionList)
def get_document_versions(document_id: int, db: Session = Depends(get_db)):
    doc = DatabaseService.get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    versions = DatabaseService.get_document_versions(db, document_id)
    return schemas.DocumentVersionList(versions=versions)


@fastapi_app.get("/document/{document_id}/versions/{version_number}", response_model=schemas.DocumentVersionRead)
def get_document_version(document_id: int, version_number: int, db: Session = Depends(get_db)):
    version = DatabaseService.get_document_version(db, document_id, version_number)
    if not version:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version_number} not found for document {document_id}"
        )
    return version


@fastapi_app.post("/document/{document_id}/versions", response_model=schemas.DocumentVersionRead)
def create_document_version(
    document_id: int,
    version_data: schemas.DocumentVersionCreate,
    db: Session = Depends(get_db)
):
    doc = DatabaseService.get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    return DatabaseService.create_document_version(
        db, document_id, version_data.content, version_data.name
    )


@fastapi_app.put("/document/{document_id}/versions/{version_number}", response_model=schemas.DocumentVersionRead)
def update_document_version(
    document_id: int,
    version_number: int,
    version_data: schemas.DocumentVersionUpdate,
    db: Session = Depends(get_db)
):
    version = DatabaseService.get_document_version(db, document_id, version_number)
    if not version:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version_number} not found for document {document_id}"
        )

    return DatabaseService.update_document_version(
        db, document_id, version_number, version_data.content, version_data.name
    )


@fastapi_app.delete("/document/{document_id}/versions/{version_number}")
def delete_document_version(document_id: int, version_number: int, db: Session = Depends(get_db)):
    version = DatabaseService.get_document_version(db, document_id, version_number)
    if not version:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version_number} not found for document {document_id}"
        )

    DatabaseService.delete_document_version(db, document_id, version_number)
    return {"message": f"Version {version_number} deleted successfully"}


@fastapi_app.get("/document/{document_id}/content")
def get_document_content_legacy(document_id: int, db: Session = Depends(get_db)):
    latest_version = DatabaseService.get_latest_version(db, document_id)
    if not latest_version:
        raise HTTPException(status_code=404, detail=f"No versions found for document {document_id}")

    return {
        "id": document_id,
        "content": latest_version.content,
        "current_version": latest_version.version_number
    }


@fastapi_app.post("/save/{document_id}")
def save_legacy(document_id: int, document: schemas.DocumentVersionCreate, db: Session = Depends(get_db)):
    return create_document_version(document_id, document, db)


@fastapi_app.websocket("/ws")
async def websocket_ai_analysis(websocket: WebSocket):
    try:
        await WebSocketService.handle_connection(websocket, USE_MULTI_AGENT_SYSTEM)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
        error_response = {
            "status": "error",
            "error": str(e)
        }
        await websocket.send_text(json.dumps(error_response))


app = fastapi_app
