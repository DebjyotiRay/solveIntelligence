# Collaboration Server

This is a Hocuspocus WebSocket server that enables real-time collaboration features for the TipTap editor.

## What it does

- Provides real-time collaborative editing using Yjs CRDT
- Shows cursor positions and selections of other users
- Syncs document changes instantly between multiple users
- Each document version has its own collaborative room

## How it works

- Runs on port 1234 by default
- Connects to clients via WebSocket
- Uses Yjs for conflict-free replicated data types (CRDT)
- Documents are identified by room names: `document-{documentId}-v{versionNumber}`

## Running

The server is automatically started with docker-compose:

```bash
docker-compose up
```

Or run it standalone:

```bash
npm install
npm start
```

## Testing Collaboration

1. Open the application in two different browser tabs or windows
2. Navigate to the same document and version
3. Start typing in one tab and see the changes appear in the other
4. Move your cursor and see your user indicator in the other tab
