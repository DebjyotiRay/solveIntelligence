from contextlib import asynccontextmanager
import json
import os

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.internal.data import DOCUMENT_1, DOCUMENT_2
from app.internal.db import Base, SessionLocal, engine, get_db
import app.models as models
import app.schemas as schemas
from app.services.database_service import DatabaseService
from app.services.websocket_service import WebSocketService
<<<<<<< HEAD
from app.services.chat_service import get_chat_service
from app.services.learning_service import get_learning_service
from app.api_onboarding import router as onboarding_router
=======
from app.auth import (
    get_current_user,
    get_password_hash,
    verify_password,
    create_access_token,
)
>>>>>>> eb7489f (Made auth page and dashboard)

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

        # Seed a default master user and project
        # Only if not present (in-memory DB each boot)
        if not db.scalar(models.User.__table__.select().limit(1)):
            master = models.User(
                email="master@example.com",
                full_name="Master User",
                hashed_password=get_password_hash("password123"),
                is_active=True,
            )
            db.add(master)
            db.commit()
            db.refresh(master)

            # Create a default project for document 1
            project = models.Project(
                name="Default Project",
                owner_id=master.id,
                document_id=1,
            )
            db.add(project)
            db.commit()
            db.refresh(project)

            # Owner membership
            owner_member = models.ProjectMember(
                project_id=project.id,
                user_id=master.id,
                role="owner",
                status="approved",
            )
            db.add(owner_member)
            db.commit()

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


# -------------------------
# Auth Routes
# -------------------------

@fastapi_app.post("/auth/signup", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.scalar(models.User.__table__.select().where(models.User.email == user.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    db_user = models.User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=get_password_hash(user.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


from fastapi import Body


@fastapi_app.post("/auth/login_simple", response_model=schemas.Token)
def login_simple(email: str = Body(...), password: str = Body(...), db: Session = Depends(get_db)):
    user_obj = db.execute(select(models.User).where(models.User.email == email)).scalar_one_or_none()
    if not user_obj or not verify_password(password, user_obj.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    token = create_access_token({"sub": str(user_obj.id), "email": user_obj.email})
    return {"access_token": token, "token_type": "bearer"}


@fastapi_app.get("/me", response_model=schemas.UserRead)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


# -------------------------
# Project Access Routes
# -------------------------

@fastapi_app.post("/projects", response_model=schemas.ProjectRead)
def create_project(
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_project = models.Project(
        name=project.name,
        owner_id=current_user.id,
        document_id=project.document_id,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    # Add owner membership
    membership = models.ProjectMember(
        project_id=db_project.id,
        user_id=current_user.id,
        role="owner",
        status="approved",
    )
    db.add(membership)
    db.commit()
    return db_project


@fastapi_app.post("/projects/create_with_document", response_model=schemas.ProjectRead)
def create_project_with_document(
    req: schemas.ProjectWithDocumentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Create document first
    doc = models.Document(title=req.document_title or req.name, current_version=1)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Create initial version
    DatabaseService.create_document_version(
        db=db,
        document_id=doc.id,
        content=req.content,
        name=req.version_name or "Initial Version",
    )

    # Create project owned by current user
    project = models.Project(
        name=req.name,
        owner_id=current_user.id,
        document_id=doc.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Ensure owner membership
    owner_member = models.ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        role="owner",
        status="approved",
    )
    db.add(owner_member)
    db.commit()

    return project


@fastapi_app.get("/projects", response_model=list[schemas.ProjectRead])
def list_my_projects(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # List owned or approved membership projects
    # First, get memberships
    member_rows = db.execute(models.ProjectMember.__table__.select().where(
        (models.ProjectMember.user_id == current_user.id) & (models.ProjectMember.status == "approved")
    )).fetchall()
    project_ids = {row.project_id for row in member_rows}
    # Also include owned projects
    owned = db.execute(models.Project.__table__.select().where(models.Project.owner_id == current_user.id)).fetchall()
    project_ids |= {row.id for row in owned}
    if not project_ids:
        return []
    projects = db.scalars(models.Project.__table__.select().where(models.Project.id.in_(list(project_ids)))).all()
    # Convert to ORM instances
    return [db.get(models.Project, p.id) for p in projects]


@fastapi_app.post("/projects/{project_id}/request-access")
def request_access(project_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    project = db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # If already member, return
    existing = db.scalar(models.ProjectMember.__table__.select().where(
        (models.ProjectMember.project_id == project_id) & (models.ProjectMember.user_id == current_user.id)
    ))
    if existing:
        return {"message": "Already requested or a member"}

    member = models.ProjectMember(project_id=project_id, user_id=current_user.id, role="viewer", status="pending")
    db.add(member)
    db.commit()
    return {"message": "Access requested"}


@fastapi_app.post("/projects/{project_id}/approve/{user_id}")
def approve_member(project_id: int, user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    project = db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can approve")

    # Update membership
    member_row = db.scalar(models.ProjectMember.__table__.select().where(
        (models.ProjectMember.project_id == project_id) & (models.ProjectMember.user_id == user_id)
    ))
    if not member_row:
        # create approved membership
        member = models.ProjectMember(project_id=project_id, user_id=user_id, role="editor", status="approved")
        db.add(member)
        db.commit()
        return {"message": "Approved"}
    else:
        # set approved
        db.execute(models.ProjectMember.__table__.update().where(
            (models.ProjectMember.project_id == project_id) & (models.ProjectMember.user_id == user_id)
        ).values(status="approved", role="editor"))
        db.commit()
        return {"message": "Approved"}


@fastapi_app.get("/projects/{project_id}/access-requests", response_model=list[schemas.ProjectMemberRead])
def list_access_requests(project_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    project = db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can view access requests")

    pending = db.execute(
        models.ProjectMember.__table__.select().where(
            (models.ProjectMember.project_id == project_id) & (models.ProjectMember.status == "pending")
        )
    ).fetchall()
    # Return as ORM-like objects
    return [schemas.ProjectMemberRead.model_validate({
        "id": row.id,
        "project_id": row.project_id,
        "user_id": row.user_id,
        "role": row.role,
        "status": row.status,
    }) for row in pending]


@fastapi_app.post("/projects/{project_id}/versions", response_model=schemas.DocumentVersionRead)
def create_project_document_version(
    project_id: int,
    version_data: schemas.DocumentVersionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.document_id:
        raise HTTPException(status_code=400, detail="Project has no document attached")

    # Only owner or approved members can edit
    if not _user_can_edit_document(db, current_user.id, project.document_id):
        raise HTTPException(status_code=403, detail="Not allowed to edit this project's document")

    return DatabaseService.create_document_version(
        db,
        project.document_id,
        version_data.content,
        version_data.name,
    )


@fastapi_app.post("/projects/{project_id}/reject/{user_id}")
def reject_member(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can reject")

    member_row = db.scalar(models.ProjectMember.__table__.select().where(
        (models.ProjectMember.project_id == project_id) & (models.ProjectMember.user_id == user_id)
    ))
    if not member_row:
        return {"message": "No request found"}

    # Mark as rejected (keep history); alternatively, delete the row
    db.execute(models.ProjectMember.__table__.update().where(
        (models.ProjectMember.project_id == project_id) & (models.ProjectMember.user_id == user_id)
    ).values(status="rejected", role="viewer"))
    db.commit()
    return {"message": "Rejected"}

@fastapi_app.get("/dashboard/documents", response_model=list[schemas.DashboardDocument])
def list_accessible_documents(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # list documents for approved memberships or owned projects
    # Get project ids
    member_rows = db.execute(models.ProjectMember.__table__.select().where(
        (models.ProjectMember.user_id == current_user.id) & (models.ProjectMember.status == "approved")
    )).fetchall()
    project_ids = {row.project_id for row in member_rows}
    owned = db.execute(models.Project.__table__.select().where(models.Project.owner_id == current_user.id)).fetchall()
    project_ids |= {row.id for row in owned}
    if not project_ids:
        return []

    # Fetch projects with document_id
    projects = db.execute(models.Project.__table__.select().where(models.Project.id.in_(list(project_ids)))).fetchall()
    result: list[schemas.DashboardDocument] = []
    for p in projects:
        if p.document_id:
            doc = db.get(models.Document, p.document_id)
            if doc:
                result.append(schemas.DashboardDocument(project_id=p.id, document_id=doc.id, document_title=doc.title))
    return result

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


# -------------------------
# Secure Document Editing (with access control)
# -------------------------

def _user_can_edit_document(db: Session, user_id: int, document_id: int) -> bool:
    # Find projects with this document id
    projects = db.execute(models.Project.__table__.select().where(models.Project.document_id == document_id)).fetchall()
    if not projects:
        return False
    project_ids = [p.id for p in projects]
    # Owner check
    owners = db.execute(models.Project.__table__.select().where(
        (models.Project.id.in_(project_ids)) & (models.Project.owner_id == user_id)
    )).fetchall()
    if owners:
        return True
    # Membership check
    member = db.execute(models.ProjectMember.__table__.select().where(
        (models.ProjectMember.project_id.in_(project_ids)) &
        (models.ProjectMember.user_id == user_id) &
        (models.ProjectMember.status == "approved")
    )).fetchone()
    return member is not None


@fastapi_app.post("/secure/document/{document_id}/versions", response_model=schemas.DocumentVersionRead)
def secure_create_document_version(
    document_id: int,
    version_data: schemas.DocumentVersionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not _user_can_edit_document(db, current_user.id, document_id):
        raise HTTPException(status_code=403, detail="Not allowed to edit this document")
    doc = DatabaseService.get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    return DatabaseService.create_document_version(db, document_id, version_data.content, version_data.name)


@fastapi_app.put("/secure/document/{document_id}/versions/{version_number}", response_model=schemas.DocumentVersionRead)
def secure_update_document_version(
    document_id: int,
    version_number: int,
    version_data: schemas.DocumentVersionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not _user_can_edit_document(db, current_user.id, document_id):
        raise HTTPException(status_code=403, detail="Not allowed to edit this document")
    return DatabaseService.update_document_version(db, document_id, version_number, version_data.content, version_data.name)
