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
from app.services.chat_service import get_chat_service
from app.services.learning_service import get_learning_service
from app.api_onboarding import router as onboarding_router

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

# Include onboarding routes
fastapi_app.include_router(onboarding_router)


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
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        # Only try to send error if connection is still open
        try:
            error_response = {
                "status": "error",
                "error": str(e)
            }
            await websocket.send_text(json.dumps(error_response))
        except:
            print("Could not send error message - WebSocket already closed")


@fastapi_app.post("/chat", response_model=schemas.ChatResponse)
async def chat_endpoint(request: schemas.ChatRequest):
    """
    Grounded chatbot endpoint for discussing analysis results.

    User can ask questions about analysis, request clarifications,
    or discuss disagreements with AI suggestions.
    """
    chat_service = get_chat_service()

    # Convert Pydantic models to dicts for service
    conversation_history = None
    if request.conversation_history:
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]

    result = await chat_service.chat(
        user_message=request.message,
        client_id=request.client_id,
        document_id=request.document_id,
        conversation_history=conversation_history,
        document_context=request.document_context,
        analysis_results=request.analysis_results
    )

    return schemas.ChatResponse(
        response=result["response"],
        sources=[schemas.ChatSource(**src) for src in result["sources"]],
        metadata=result["metadata"]
    )


# ==================== LEARNING & FEEDBACK ENDPOINTS ====================

@fastapi_app.post("/suggestions/feedback")
async def track_suggestion_feedback(request: schemas.SuggestionFeedbackRequest):
    """
    Track user feedback on inline suggestions (accepted/rejected/modified).
    
    This completes the learning loop by capturing what users do with suggestions.
    """
    learning_service = get_learning_service()
    
    result = await learning_service.track_suggestion_feedback(
        client_id=request.client_id,
        suggestion_id=request.suggestion_id,
        action=request.action,
        suggested_text=request.suggested_text,
        actual_text=request.actual_text,
        context_before=request.context_before or "",
        context_after=request.context_after or ""
    )
    
    return result


@fastapi_app.post("/learning/session")
async def learn_from_session(request: schemas.LearnSessionRequest):
    """
    Analyze a writing session to extract patterns and learn preferences.
    
    Should be called when user pauses, saves, or finishes a document.
    """
    learning_service = get_learning_service()
    
    result = await learning_service.learn_from_session(
        client_id=request.client_id,
        document_text=request.document_text,
        document_id=request.document_id
    )
    
    return result


@fastapi_app.get("/learning/progress/{client_id}")
async def get_learning_progress(client_id: str):
    """
    Get comprehensive learning progress for a client.
    
    Shows:
    - Documents processed
    - Suggestion acceptance rate
    - Patterns learned
    - Learning stage
    """
    learning_service = get_learning_service()
    
    progress = await learning_service.get_learning_progress(client_id)
    
    return progress


@fastapi_app.get("/learning/patterns/{client_id}")
async def get_client_patterns(client_id: str, pattern_type: str = None):
    """
    Get learned patterns for a client.
    
    Optional pattern_type filter: phrases, terminology, structure
    """
    learning_service = get_learning_service()
    
    patterns = await learning_service.get_client_patterns(
        client_id=client_id,
        pattern_type=pattern_type
    )
    
    return {"patterns": patterns}


@fastapi_app.get("/learning/acceptance-rate/{client_id}")
async def get_acceptance_rate(client_id: str, recent_count: int = 50):
    """
    Get suggestion acceptance rate statistics for a client.
    """
    learning_service = get_learning_service()
    
    stats = await learning_service.get_suggestion_acceptance_rate(
        client_id=client_id,
        recent_count=recent_count
    )
    
    return stats


app = fastapi_app
