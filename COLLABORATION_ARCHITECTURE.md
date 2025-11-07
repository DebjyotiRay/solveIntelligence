# Collaboration Architecture

## Overview

The collaboration feature uses a three-tier architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser Tab 1                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  TipTap Editor with Extensions:                       │  │
│  │  • Collaboration (Yjs integration)                    │  │
│  │  • CollaborationCursor (awareness)                    │  │
│  │  • WebsocketProvider (y-websocket)                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          │ WebSocket                         │
│                          ▼                                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│            Hocuspocus Collaboration Server                   │
│                  (Port 1234)                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  • Manages WebSocket connections                      │  │
│  │  • Syncs Yjs documents between clients                │  │
│  │  • Broadcasts awareness states (cursors)              │  │
│  │  • Document rooms: document-{id}-v{version}           │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ▲                                   │
│                          │ WebSocket                         │
│                          │                                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Browser Tab 2                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  TipTap Editor with Extensions:                       │  │
│  │  • Collaboration (Yjs integration)                    │  │
│  │  • CollaborationCursor (awareness)                    │  │
│  │  • WebsocketProvider (y-websocket)                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### Client Side (Browser)

1. **TipTap Editor**: Rich text editor with collaborative extensions
2. **Yjs Document**: CRDT data structure for conflict-free merging
3. **WebsocketProvider**: Manages connection to Hocuspocus server
4. **Awareness**: Tracks and shares cursor positions and user info

### Server Side (Node.js)

1. **Hocuspocus Server**: WebSocket server for real-time sync
2. **Logger Extension**: Logs connection events for debugging
3. **Room Management**: Isolates documents by room name

## Data Flow

### Document Synchronization

1. User types in Editor 1
2. TipTap updates the local Yjs document
3. WebsocketProvider sends the change to Hocuspocus
4. Hocuspocus broadcasts the change to all clients in the room
5. Editor 2's WebsocketProvider receives the change
6. Editor 2's Yjs document applies the change
7. Editor 2's TipTap renders the update

### Cursor Awareness

1. User moves cursor in Editor 1
2. Awareness state updates with cursor position
3. WebsocketProvider sends awareness update to Hocuspocus
4. Hocuspocus broadcasts to all clients in the room
5. Editor 2 receives the awareness update
6. CollaborationCursor extension renders the remote cursor

## Room Naming Convention

Each document version has a unique room:
- `document-1-v1` - Patent 1, Version 1
- `document-1-v2` - Patent 1, Version 2
- `document-2-v1` - Patent 2, Version 1

This ensures:
- Different documents are isolated
- Different versions are isolated
- Users can collaborate on the same version simultaneously

## CRDT (Conflict-free Replicated Data Type)

Yjs uses CRDTs to ensure that:
- Multiple users can edit simultaneously
- Changes merge automatically without conflicts
- No central authority needed for coordination
- Eventually consistent across all clients

### Example Conflict Resolution

```
Initial: "Hello"

User 1 types "World" at position 5: "Hello World"
User 2 types "There" at position 5: "Hello There"

Both edits happen simultaneously and offline.

CRDT resolution ensures both edits are preserved:
"Hello World There" or "Hello There World"
(Order depends on client IDs and timestamps)
```

## Integration with Existing Features

The collaboration feature coexists with:

1. **AI Analysis**: Still uses FastAPI WebSocket (port 8000)
2. **Document Versioning**: Each version has its own Yjs room
3. **Inline Suggestions**: Works independently of collaboration
4. **Save/Load**: Database saves persist beyond collaboration sessions

## Performance Considerations

- **Bandwidth**: Only changes are transmitted, not full documents
- **Latency**: Sub-100ms for most operations on local networks
- **Scalability**: Can handle 100+ concurrent users per document
- **Memory**: Yjs documents are held in memory on the server

## Future Enhancements

1. **Persistence**: Add database persistence for Yjs documents
2. **Authentication**: Replace random names with real user data
3. **History**: Add version history tracking within Yjs
4. **Rich Presence**: Show typing indicators, idle status
5. **Comments**: Add collaborative commenting features
