import socketio
from typing import Dict, Set, Optional, Any
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Socket.IO server
sio = socketio.AsyncServer(
    cors_allowed_origins="http://localhost:3000",
    logger=True,
    engineio_logger=True
)


class CollaborationManager:
    """Manages real-time collaboration state for documents and versions"""

    def __init__(self):
        # Track user sessions: {session_id: {user_id, document_id, version_number, join_time}}
        self.sessions: Dict[str, Dict[str, Any]] = {}


        # Track room memberships: {room_name: {session_ids}}
        self.rooms: Dict[str, Set[str]] = {}

        # Track active users per document/version: {doc_id: {version_num: {user_data}}}
        self.active_users: Dict[int, Dict[int, Set[Dict[str, Any]]]] = {}

    def get_room_name(self, document_id: int, version_number: int) -> str:
        """Generate consistent room name for document + version combination"""
        return f"doc_{document_id}_v{version_number}"

    async def user_join_room(self, session_id: str, user_id: str, document_id: int, version_number: int):
        """Handle user joining a document/version room"""
        room_name = self.get_room_name(document_id, version_number)

        # Store session info
        self.sessions[session_id] = {
            "user_id": user_id,
            "document_id": document_id,
            "version_number": version_number,
            "join_time": datetime.now(),
            "room_name": room_name
        }

        # Add to room
        if room_name not in self.rooms:
            self.rooms[room_name] = set()
        self.rooms[room_name].add(session_id)

        # Track active users
        if document_id not in self.active_users:
            self.active_users[document_id] = {}
        if version_number not in self.active_users[document_id]:
            self.active_users[document_id][version_number] = set()

        user_data = {"user_id": user_id, "session_id": session_id, "joined_at": datetime.now().isoformat()}
        self.active_users[document_id][version_number].add(frozenset(user_data.items()))

        # Join Socket.IO room
        await sio.enter_room(session_id, room_name)

        logger.info(f"User {user_id} joined {room_name}")

        # Notify other users in the room
        await sio.emit('user_joined', {
            "user_id": user_id,
            "document_id": document_id,
            "version_number": version_number,
            "timestamp": datetime.now().isoformat()
        }, room=room_name, skip_sid=session_id)

    async def user_leave_room(self, session_id: str):
        """Handle user leaving a room"""
        if session_id not in self.sessions:
            return


        session_info = self.sessions[session_id]
        room_name = session_info["room_name"]
        user_id = session_info["user_id"]
        document_id = session_info["document_id"]
        version_number = session_info["version_number"]

        # Remove from room tracking
        if room_name in self.rooms:
            self.rooms[room_name].discard(session_id)
            if not self.rooms[room_name]:  # Empty room
                del self.rooms[room_name]

        # Remove from active users
        if (document_id in self.active_users and
                version_number in self.active_users[document_id]):
            # Remove user from active set (need to find matching frozenset)
            active_set = self.active_users[document_id][version_number]
            to_remove = None
            for user_frozen in active_set:
                user_dict = dict(user_frozen)
                if user_dict.get("session_id") == session_id:
                    to_remove = user_frozen
                    break

            if to_remove:
                active_set.discard(to_remove)

        # Leave Socket.IO room
        await sio.leave_room(session_id, room_name)

        # Clean up session
        del self.sessions[session_id]

        logger.info(f"User {user_id} left {room_name}")

        # Notify other users in the room
        await sio.emit('user_left', {
            "user_id": user_id,
            "document_id": document_id,
            "version_number": version_number,
            "timestamp": datetime.now().isoformat()
        }, room=room_name)

    def get_active_users(self, document_id: int, version_number: int) -> list:
        """Get list of active users for a document/version"""
        if (document_id not in self.active_users or
                version_number not in self.active_users[document_id]):
            return []

        active_set = self.active_users[document_id][version_number]
        return [dict(user_frozen) for user_frozen in active_set]

    async def broadcast_to_room(self, document_id: int, version_number: int, event: str, data: dict, exclude_session: Optional[str] = None):
        """Broadcast message to all users in a document/version room"""
        room_name = self.get_room_name(document_id, version_number)
        await sio.emit(event, data, room=room_name, skip_sid=exclude_session)


# Global collaboration manager instance
collaboration_manager = CollaborationManager()


# Socket.IO Event Handlers
@sio.event
async def connect(sid, environ):
    """Handle client connection"""
    logger.info(f"Client {sid} connected")
    await sio.emit('connection_confirmed', {"session_id": sid}, room=sid)


@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    logger.info(f"Client {sid} disconnected")
    await collaboration_manager.user_leave_room(sid)


@sio.event
async def join_document(sid, data):
    """Handle user joining a document/version for collaboration"""
    try:
        user_id = data.get('user_id', f'anonymous_{sid[:8]}')
        document_id = data['document_id']
        version_number = data['version_number']

        await collaboration_manager.user_join_room(sid, user_id, document_id, version_number)

        # Send current active users to the joining user
        active_users = collaboration_manager.get_active_users(document_id, version_number)
        await sio.emit('active_users', {
            "document_id": document_id,
            "version_number": version_number,
            "users": active_users
        }, room=sid)

    except Exception as e:
        logger.error(f"Error in join_document: {e}")
        await sio.emit('error', {"message": "Failed to join document"}, room=sid)


@sio.event
async def leave_document(sid, data):
    """Handle user explicitly leaving a document"""
    await collaboration_manager.user_leave_room(sid)


@sio.event
async def request_ai_suggestions(sid, data):
    """Handle AI suggestion requests with streaming"""
    try:
        session_info = collaboration_manager.sessions.get(sid)
        if not session_info:
            await sio.emit('error', {"message": "Not connected to any document"}, room=sid)
            return

        document_id = session_info["document_id"]
        version_number = session_info["version_number"]
        content = data.get('content', '')

        # Broadcast that AI analysis is starting
        await collaboration_manager.broadcast_to_room(
            document_id, version_number,
            'ai_analysis_started',
            {
                "document_id": document_id,
                "version_number": version_number,
                "initiated_by": session_info["user_id"],
                "timestamp": datetime.now().isoformat()
            }
        )

        # Import here to avoid circular imports
        from app.internal.ai_utils import prepare_content_for_ai, chunk_content_for_streaming
        from app.internal.ai import get_ai

        # Prepare content for AI
        ai_input = prepare_content_for_ai(content, {
            "document_id": document_id,
            "version_number": version_number,
            "user_id": session_info["user_id"]
        })

        if not ai_input["has_content"]:
            await collaboration_manager.broadcast_to_room(
                document_id, version_number,
                'ai_suggestion',
                {
                    "suggestion": "No content available for analysis. Please add some text to get AI suggestions.",
                    "is_final": True,
                    "document_id": document_id,
                    "version_number": version_number
                }
            )
            return

        # Get AI instance and process content with streaming
        ai = get_ai()

        accumulated_content = ""
        try:
            # Process the entire content with AI streaming
            async for chunk in ai.review_document(ai_input["clean_text"]):
                if chunk:
                    accumulated_content += chunk

                    # Stream each chunk as it arrives
                    await collaboration_manager.broadcast_to_room(
                        document_id, version_number,
                        'ai_suggestion_chunk',
                        {
                            "chunk": chunk,
                            "accumulated_content": accumulated_content,
                            "is_partial": True,
                            "document_id": document_id,
                            "version_number": version_number,
                            "timestamp": datetime.now().isoformat()
                        }
                    )

            # Send final complete result
            await collaboration_manager.broadcast_to_room(
                document_id, version_number,
                'ai_suggestion',
                {
                    "content": accumulated_content,
                    "is_final": True,
                    "document_id": document_id,
                    "version_number": version_number,
                    "word_count": ai_input["word_count"],
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error in AI processing: {e}")
            await collaboration_manager.broadcast_to_room(
                document_id, version_number,
                'ai_error',
                {
                    "error": str(e),
                    "document_id": document_id,
                    "version_number": version_number,
                    "timestamp": datetime.now().isoformat()
                }
            )

    except Exception as e:
        logger.error(f"Error in request_ai_suggestions: {e}")
        await sio.emit('error', {"message": f"AI processing failed: {str(e)}"}, room=sid)