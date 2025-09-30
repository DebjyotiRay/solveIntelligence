from contextlib import asynccontextmanager
import json
import os
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import insert, select, update, func
from sqlalchemy.orm import Session
from app.internal.ai import AI, get_ai
from app.internal.data import DOCUMENT_1, DOCUMENT_2
from app.internal.db import Base, SessionLocal, engine, get_db
import app.models as models
import app.schemas as schemas

# Feature Flag Configuration
# Toggle between original AI system (internal) and advanced multi-agent system (ai)
USE_MULTI_AGENT_SYSTEM = os.getenv("USE_MULTI_AGENT_SYSTEM", "false").lower() == "true"


def calculate_content_similarity(content1: str, content2: str) -> float:
    """Calculate similarity score between two document contents"""
    try:
        # Extract key features from both contents
        from bs4 import BeautifulSoup
        import re
        
        def extract_features(html_content):
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title_elem = soup.find('title') or soup.find('h1')
            title = title_elem.get_text().strip() if title_elem else ""
            
            # Extract first claim (look for "1." pattern)
            text = soup.get_text()
            first_claim_match = re.search(r'1\.\s+([^\.]+(?:\.[^\.]*){0,3})', text)
            first_claim = first_claim_match.group(1)[:200] if first_claim_match else ""
            
            # Extract key technical terms
            words = re.findall(r'\b[a-z]{4,}\b', text.lower())
            key_terms = list(set([w for w in words if len(w) > 4]))[:20]  # Top 20 terms
            
            return {
                "title": title.lower(),
                "first_claim": first_claim.lower(),
                "key_terms": set(key_terms)
            }
        
        features1 = extract_features(content1)
        features2 = extract_features(content2)
        
        # Calculate weighted similarity
        title_sim = 0.0
        if features1["title"] and features2["title"]:
            # Simple word overlap for title
            words1 = set(features1["title"].split())
            words2 = set(features2["title"].split())
            if words1 or words2:
                title_sim = len(words1 & words2) / max(len(words1 | words2), 1)
        
        claim_sim = 0.0
        if features1["first_claim"] and features2["first_claim"]:
            # Simple word overlap for first claim
            words1 = set(features1["first_claim"].split())
            words2 = set(features2["first_claim"].split())
            if words1 or words2:
                claim_sim = len(words1 & words2) / max(len(words1 | words2), 1)
        
        term_sim = 0.0
        if features1["key_terms"] or features2["key_terms"]:
            term_sim = len(features1["key_terms"] & features2["key_terms"]) / max(len(features1["key_terms"] | features2["key_terms"]), 1)
        
        # Weighted average (title: 40%, claim: 35%, terms: 25%)
        final_score = (title_sim * 0.4) + (claim_sim * 0.35) + (term_sim * 0.25)
        return final_score
        
    except Exception as e:
        print(f"⚠️ Similarity calculation error: {e}")
        return 0.0


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


fastapi_app = FastAPI(lifespan=lifespan)

# Add CORS middleware
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Document Management API Endpoints

@fastapi_app.get("/document/{document_id}", response_model=schemas.DocumentRead)
def get_document(document_id: int, db: Session = Depends(get_db)):
    """Get document metadata (stateless - no content)"""
    doc = db.scalar(select(models.Document).where(models.Document.id == document_id))
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    return doc


# Version Management API Endpoints (Clean Stateless Architecture)

@fastapi_app.get("/document/{document_id}/versions", response_model=schemas.DocumentVersionList)
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


@fastapi_app.get("/document/{document_id}/versions/{version_number}", response_model=schemas.DocumentVersionRead)
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


@fastapi_app.post("/document/{document_id}/versions", response_model=schemas.DocumentVersionRead)
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


@fastapi_app.put("/document/{document_id}/versions/{version_number}", response_model=schemas.DocumentVersionRead)
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


@fastapi_app.delete("/document/{document_id}/versions/{version_number}")
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

@fastapi_app.get("/document/{document_id}/content")
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


@fastapi_app.post("/save/{document_id}")
def save_legacy(document_id: int, document: schemas.DocumentVersionCreate, db: Session = Depends(get_db)):
    """Legacy endpoint: Save as new version for backward compatibility"""
    return create_document_version(document_id, document, db)


@fastapi_app.websocket("/ws")
async def websocket_ai_analysis(websocket: WebSocket):
    await websocket.accept()

    if USE_MULTI_AGENT_SYSTEM:
        print("WebSocket connected - MULTI-AGENT SYSTEM ENABLED")
        await _websocket_multi_agent_analysis(websocket)
    else:
        print("WebSocket connected - Original AI system")
        await _websocket_original_ai_analysis(websocket)


async def _handle_inline_suggestion(websocket: WebSocket, request: dict, coordinator):
    """Handle inline AI suggestion requests"""
    try:
        content = request.get("content", "")
        cursor_pos = request.get("cursor_position", 0)
        context_before = request.get("context_before", "")
        context_after = request.get("context_after", "")
        suggestion_type = request.get("suggestion_type", "completion")

        print(f"💡 Inline suggestion request: type={suggestion_type}, cursor_pos={cursor_pos}")

        # Use dedicated inline suggestions service
        from app.ai.services.inline_suggestions import InlineSuggestionsService

        suggestions_service = InlineSuggestionsService()
        result = await suggestions_service.generate_suggestion(
            content=content,
            cursor_pos=cursor_pos,
            context_before=context_before,
            context_after=context_after,
            suggestion_type=suggestion_type
        )

        suggested_text = result["suggested_text"]
        reasoning = result["reasoning"]

        # Send inline suggestion response
        response = {
            "status": "inline_suggestion",
            "suggestion_id": f"suggestion_{hash(content + str(cursor_pos))}",
            "original_text": context_before,
            "suggested_text": suggested_text,
            "position": {"from": cursor_pos, "to": cursor_pos},
            "confidence": 0.8,
            "reasoning": reasoning,
            "type": suggestion_type
        }

        await websocket.send_text(json.dumps(response))
        print(f"✅ Sent inline suggestion: '{suggested_text}'")

    except Exception as e:
        print(f"❌ Error generating inline suggestion: {e}")
        await websocket.send_text(json.dumps({
            "status": "error",
            "error": f"Failed to generate inline suggestion: {str(e)}"
        }))


async def _websocket_multi_agent_analysis(websocket: WebSocket):
    """Advanced multi-agent patent analysis (Task 3 innovation)"""

    # Initialize multi-agent coordinator
    from app.ai.workflow.patent_coordinator import PatentAnalysisCoordinator
    coordinator = PatentAnalysisCoordinator()

    while True:
        try:
            # Receive message from client
            message = await websocket.receive_text()
            print(f"Received message: {len(message)} chars")

            # Try to parse as JSON first (new inline suggestion format)
            try:
                parsed_message = json.loads(message)
                message_type = parsed_message.get("type")

                if message_type == "inline_suggestion":
                    # Handle inline suggestion request
                    await _handle_inline_suggestion(websocket, parsed_message, coordinator)
                    continue
                elif message_type == "analyze_patent":
                    # Handle full patent analysis request
                    document_html = parsed_message.get("content", "")
                else:
                    # Fallback for unknown JSON message types
                    await websocket.send_text(json.dumps({
                        "status": "error",
                        "error": f"Unknown message type: {message_type}"
                    }))
                    continue

            except json.JSONDecodeError:
                # Legacy format - treat as raw document content for analysis
                document_html = message
                print("Received legacy format - treating as document content")

            # Process content for analysis
            from app.ai.utils import prepare_content_for_ai
            ai_input = prepare_content_for_ai(document_html)

            if not ai_input["has_content"]:
                await websocket.send_text(json.dumps({"error": "No content to analyze"}))
                continue

            # Try to find matching document using simple content similarity
            document_id = None
            document_title = None
            
            with SessionLocal() as db:
                documents = db.scalars(select(models.Document)).all()
                print(f"🔍 SIMILARITY CHECK: Found {len(documents)} documents in database")
                
                best_match = None
                highest_score = 0.0
                
                for doc in documents:
                    if doc.content:
                        # Simple similarity scoring
                        similarity_score = calculate_content_similarity(document_html, doc.content)
                        print(f"🔍 SIMILARITY: Doc ID={doc.id}, Title='{doc.title}', Score={similarity_score:.3f}")
                        
                        if similarity_score > highest_score and similarity_score > 0.7:  # 70% threshold
                            highest_score = similarity_score
                            best_match = doc
                
                if best_match:
                    # Found existing document - use its ID
                    document_id = str(best_match.id)
                    document_title = best_match.title
                    print(f"✅ MATCHED: Found similar document ID={document_id}, Title='{document_title}', Score={highest_score:.3f}")
                else:
                    # No match found - create new document entry
                    # Extract title from HTML content
                    from bs4 import BeautifulSoup
                    try:
                        soup = BeautifulSoup(document_html, 'html.parser')
                        title_element = soup.find('title') or soup.find('h1')
                        extracted_title = title_element.get_text().strip()[:100] if title_element else "New Patent Document"
                    except:
                        extracted_title = "New Patent Document"
                    
                    # Create new document in database
                    new_doc = models.Document(
                        title=extracted_title,
                        content=document_html,
                        current_version=1
                    )
                    db.add(new_doc)
                    db.commit()
                    db.refresh(new_doc)
                    
                    document_id = str(new_doc.id)
                    document_title = new_doc.title
                    print(f"🆕 NEW DOCUMENT: Created ID={document_id}, Title='{document_title}'")
            
            # Prepare document for multi-agent analysis using database ID for consistent memory
            document = {
                "id": document_id,  # Use database ID for memory consistency (e.g., "1", "2")
                "title": document_title,
                "content": document_html,
                "clean_text": ai_input["clean_text"],
                "timestamp": datetime.now().isoformat(),
                "db_id": document_id  # Keep DB ID for reference
            }

            # Send initial analysis started message with clear multi-agent identification
            await websocket.send_text(json.dumps({
                "status": "analyzing",
                "message": "🤖 MULTI-AGENT SYSTEM ACTIVATED - Starting intelligent patent analysis...",
                "system_type": "multi_agent_v2.0",
                "workflow": "4-phase analysis (Structure → Legal → Cross-validation → Synthesis)",
                "agents": ["structure", "legal"],
                "memory_enabled": True,
                "orchestrator": "PatentAnalysisCoordinator"
            }))

            # Define streaming callback for real-time updates with error handling
            async def stream_callback(update):
                try:
                    print(f"🔄 STREAM_CALLBACK: Sending update - {update.get('status', 'unknown')} - {update.get('message', 'no message')[:80]}...")
                    
                    # Check websocket state more robustly
                    if not hasattr(websocket, 'client_state') or websocket.client_state is None:
                        print(f"⚠️ STREAM_CALLBACK: WebSocket client_state is None")
                        return
                        
                    if websocket.client_state.value != 1:  # Not CONNECTED
                        print(f"⚠️ STREAM_CALLBACK: WebSocket not connected (state: {websocket.client_state.value})")
                        return
                    
                    # Ensure JSON serializable
                    json_data = json.dumps(update)
                    print(f"🔄 STREAM_CALLBACK: JSON serialized successfully ({len(json_data)} chars)")
                    
                    await websocket.send_text(json_data)
                    print(f"✅ STREAM_CALLBACK: Successfully sent update")
                    
                except (WebSocketDisconnect, RuntimeError) as e:
                    print(f"⚠️ STREAM_CALLBACK: WebSocket disconnected during streaming: {e}")
                    # Silently continue - client disconnected
                    return
                except json.JSONEncodeError as e:
                    print(f"❌ STREAM_CALLBACK: JSON encoding error: {e}")
                    print(f"❌ STREAM_CALLBACK: Update data: {update}")
                    return
                except Exception as e:
                    print(f"❌ STREAM_CALLBACK: Unexpected error: {e}")
                    print(f"❌ STREAM_CALLBACK: Update data: {update}")
                    import traceback
                    print(f"❌ STREAM_CALLBACK: Traceback: {traceback.format_exc()}")
                    return

            # Execute multi-agent analysis with streaming
            final_analysis = await coordinator.analyze_patent(document, stream_callback)

            # Send final results in the format expected by frontend
            if final_analysis.get("status") == "error":
                await websocket.send_text(json.dumps(final_analysis))
            else:
                # Transform multi-agent results to match frontend expectations
                structured_response = {
                    "status": "complete",
                    "analysis": {
                        "issues": final_analysis.get("all_issues", [])
                    },
                    "total_issues": len(final_analysis.get("all_issues", [])),
                    "overall_score": final_analysis.get("overall_score", 0.0),
                    "agents_used": final_analysis.get("analysis_metadata", {}).get("agents_used", []),
                    "timestamp": final_analysis.get("analysis_timestamp")
                }
                await websocket.send_text(json.dumps(structured_response))

        except WebSocketDisconnect:
            break
        except Exception as e:
            print(f"Multi-agent analysis error: {e}")
            error_response = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_text(json.dumps(error_response))


async def _websocket_original_ai_analysis(websocket: WebSocket):
    """Original AI analysis system with streaming support"""
    
    ai = get_ai()
    
    while True:
        try:
            # Receive document content from client
            document_html = await websocket.receive_text()
            print(f"Received document: {len(document_html)} chars")

            # Send initial analysis started message
            await websocket.send_text(json.dumps({
                "status": "analyzing",
                "message": "🧠 ORIGINAL AI SYSTEM - Starting streaming analysis...",
                "system_type": "original_ai",
                "workflow": "Single-agent streaming analysis"
            }))

            # Process content for analysis using original AI
            from app.ai.utils import prepare_content_for_ai
            ai_input = prepare_content_for_ai(document_html)

            if not ai_input["has_content"]:
                await websocket.send_text(json.dumps({"error": "No content to analyze"}))
                continue

            # Stream AI analysis with proper JSON parsing
            accumulated_content = ""
            chunk_count = 0
            
            async for chunk in ai.review_document(ai_input["clean_text"]):
                if chunk:
                    accumulated_content += chunk
                    chunk_count += 1
                    
                    # Send progress update every few chunks
                    if chunk_count % 5 == 0:
                        await websocket.send_text(json.dumps({
                            "status": "streaming",
                            "message": f"Processing... received {chunk_count} chunks",
                            "progress": min(chunk_count * 2, 90)  # Rough progress estimate
                        }))
            
            # Parse the accumulated JSON response (handle formatting errors)
            try:
                # First attempt: direct JSON parse
                analysis_result = json.loads(accumulated_content)
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                try:
                    # Second attempt: clean up common formatting issues
                    cleaned_content = accumulated_content.strip()
                    # Remove potential trailing commas and fix common issues
                    cleaned_content = cleaned_content.replace(',}', '}').replace(',]', ']')
                    analysis_result = json.loads(cleaned_content)
                except json.JSONDecodeError:
                    print(f"Failed to parse AI response: {accumulated_content[:200]}...")
                    # Fallback: create a basic error response
                    analysis_result = {
                        "issues": [{
                            "type": "parsing_error",
                            "severity": "high",
                            "paragraph": 1,
                            "description": "AI response could not be parsed",
                            "suggestion": "Please try again or check the document format"
                        }]
                    }
            
            # Extract issues from the parsed result
            issues = analysis_result.get("issues", [])
            
            # Send final results in the format expected by frontend
            response = {
                "status": "complete",
                "analysis": {
                    "issues": issues
                },
                "total_issues": len(issues),
                "system_type": "original_ai",
                "chunks_processed": chunk_count,
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_text(json.dumps(response))

        except WebSocketDisconnect:
            break
        except Exception as e:
            print(f"Original AI analysis error: {e}")
            error_response = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_text(json.dumps(error_response))

# Export the FastAPI app directly (Socket.IO removed)
app = fastapi_app
