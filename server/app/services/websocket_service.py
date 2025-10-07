import json
from datetime import datetime
from typing import Callable

from fastapi import WebSocket, WebSocketDisconnect

from app.ai.utils import prepare_content_for_ai
from app.ai.services.inline_suggestions import InlineSuggestionsService
from app.ai.workflow.patent_coordinator import PatentAnalysisCoordinator
from app.internal.ai import get_ai
from app.internal.db import SessionLocal
from app.models import Document
from app.services.database_service import DatabaseService


class WebSocketService:
    
    @staticmethod
    async def handle_connection(websocket: WebSocket, use_multi_agent: bool):
        await websocket.accept()

        if use_multi_agent:
            print("WebSocket connected - MULTI-AGENT SYSTEM ENABLED")
            await WebSocketService._handle_multi_agent_analysis(websocket)
        else:
            print("WebSocket connected - Original AI system")
            await WebSocketService._handle_original_ai_analysis(websocket)

    @staticmethod
    async def _handle_inline_suggestion(websocket: WebSocket, request: dict):
        content = request.get("content", "")
        cursor_pos = request.get("cursor_position", 0)
        context_before = request.get("context_before", "")
        context_after = request.get("context_after", "")
        suggestion_type = request.get("suggestion_type", "completion")

        print(f"💡 Inline suggestion request: type={suggestion_type}, cursor_pos={cursor_pos}")

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

    @staticmethod
    async def _handle_multi_agent_analysis(websocket: WebSocket):
        coordinator = PatentAnalysisCoordinator()

        while True:
            message = await websocket.receive_text()
            print(f"Received message: {len(message)} chars")

            try:
                parsed_message = json.loads(message)
                message_type = parsed_message.get("type")

                if message_type == "inline_suggestion":
                    await WebSocketService._handle_inline_suggestion(websocket, parsed_message)
                    continue
                elif message_type == "analyze_patent":
                    document_html = parsed_message.get("content", "")
                    document_id = parsed_message.get("document_id")
                else:
                    await websocket.send_text(json.dumps({
                        "status": "error",
                        "error": f"Unknown message type: {message_type}"
                    }))
                    continue
            except json.JSONDecodeError:
                document_html = message
                document_id = "1"
                print("Received non-JSON format - treating as document content with default document_id=1")

            ai_input = prepare_content_for_ai(document_html)

            if not ai_input["has_content"]:
                await websocket.send_text(json.dumps({"error": "No content to analyze"}))
                continue

            document_title = None
            print(f"📄 WEBSOCKET: Using document_id: {document_id}")

            with SessionLocal() as db:
                doc_id, doc_title = DatabaseService.get_or_create_document(
                    db, int(document_id), document_html
                )
                document_id = str(doc_id)
                document_title = doc_title
                print(f"🆕 Document ID={document_id}, Title='{document_title}'")
            
            document = {
                "id": document_id,
                "title": document_title,
                "content": document_html,
                "clean_text": ai_input["clean_text"],
                "timestamp": datetime.now().isoformat(),
                "db_id": document_id
            }

            await websocket.send_text(json.dumps({
                "status": "analyzing",
                "message": "🤖 MULTI-AGENT SYSTEM ACTIVATED - Starting intelligent patent analysis...",
                "system_type": "multi_agent_v2.0",
                "workflow": "4-phase analysis (Structure → Legal → Cross-validation → Synthesis)",
                "agents": ["structure", "legal"],
                "memory_enabled": True,
                "orchestrator": "PatentAnalysisCoordinator"
            }))

            async def stream_callback(update):
                try:
                    if not hasattr(websocket, 'client_state') or websocket.client_state is None:
                        print(f"⚠️ STREAM_CALLBACK: WebSocket client_state is None - client disconnected")
                        return
                        
                    if websocket.client_state.value != 1:
                        print(f"⚠️ STREAM_CALLBACK: WebSocket not connected (state: {websocket.client_state.value})")
                        return
                    
                    json_data = json.dumps(update)
                    await websocket.send_text(json_data)
                except RuntimeError as e:
                    if "close message has been sent" in str(e):
                        print(f"⚠️ STREAM_CALLBACK: Client disconnected during analysis")
                        return
                    raise
                except Exception as e:
                    print(f"⚠️ STREAM_CALLBACK: Error sending update: {e}")
                    return

            try:
                final_analysis = await coordinator.analyze_patent(document, stream_callback)

                # Check if websocket is still connected before sending final result
                try:
                    if hasattr(websocket, 'client_state') and websocket.client_state and websocket.client_state.value == 1:
                        if final_analysis.get("status") == "error":
                            await websocket.send_text(json.dumps(final_analysis))
                        else:
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
                    else:
                        print("⚠️ Client disconnected before final results could be sent")
                except RuntimeError as e:
                    if "close message has been sent" in str(e):
                        print("⚠️ Client disconnected - cannot send final results")
                    else:
                        raise
            except json.JSONDecodeError as json_err:
                print(f"❌ JSON parsing error in analysis pipeline: {json_err}")
                try:
                    if hasattr(websocket, 'client_state') and websocket.client_state and websocket.client_state.value == 1:
                        await websocket.send_text(json.dumps({
                            "status": "error",
                            "error": f"AI response parsing failed: {str(json_err)}",
                            "error_type": "json_decode_error",
                            "suggestion": "The AI may have returned invalid JSON. Please try again."
                        }))
                except RuntimeError:
                    print("⚠️ Cannot send error - client already disconnected")
            except WebSocketDisconnect:
                print("⚠️ Client disconnected during analysis")
                break
            except Exception as analysis_err:
                print(f"❌ Analysis error: {analysis_err}")
                import traceback
                print(f"❌ Traceback: {traceback.format_exc()}")
                try:
                    if hasattr(websocket, 'client_state') and websocket.client_state and websocket.client_state.value == 1:
                        await websocket.send_text(json.dumps({
                            "status": "error",
                            "error": f"Analysis failed: {str(analysis_err)}",
                            "error_type": "analysis_error"
                        }))
                except RuntimeError:
                    print("⚠️ Cannot send error - client already disconnected")

    @staticmethod
    async def _handle_original_ai_analysis(websocket: WebSocket):
        ai = get_ai()
        
        while True:
            document_html = await websocket.receive_text()
            print(f"Received document: {len(document_html)} chars")

            await websocket.send_text(json.dumps({
                "status": "analyzing",
                "message": "🧠 ORIGINAL AI SYSTEM - Starting streaming analysis...",
                "system_type": "original_ai",
                "workflow": "Single-agent streaming analysis"
            }))

            ai_input = prepare_content_for_ai(document_html)

            if not ai_input["has_content"]:
                await websocket.send_text(json.dumps({"error": "No content to analyze"}))
                continue

            accumulated_content = ""
            chunk_count = 0
            
            async for chunk in ai.review_document(ai_input["clean_text"]):
                if chunk:
                    accumulated_content += chunk
                    chunk_count += 1
                    
                    if chunk_count % 5 == 0:
                        await websocket.send_text(json.dumps({
                            "status": "streaming",
                            "message": f"Processing... received {chunk_count} chunks",
                            "progress": min(chunk_count * 2, 90)
                        }))
            
            analysis_result = json.loads(accumulated_content)
            issues = analysis_result.get("issues", [])
            
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
