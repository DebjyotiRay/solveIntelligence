# Quick Start Guide - Collaboration Features

This guide will help you quickly test the new collaboration features.

## Prerequisites

- Docker and Docker Compose installed
- OpenAI API key (see server/.env.example)

## Setup (30 seconds)

1. **Clone and enter the repository**
   ```bash
   cd solveIntelligence
   ```

2. **Create environment file**
   ```bash
   cp server/.env.example server/.env
   # Edit server/.env and add your OpenAI API key
   ```

3. **Start all services**
   ```bash
   docker-compose up
   ```

   This will start three services:
   - Frontend (Vite): http://localhost:5173
   - Backend (FastAPI): http://localhost:8000
   - Collaboration (Hocuspocus): ws://localhost:1234

## Test Collaboration (2 minutes)

### Step 1: Open First Tab
1. Open http://localhost:5173 in your browser
2. Click on "Patent 1" to load the first document
3. You should see the TipTap editor with the document content

### Step 2: Open Second Tab  
1. Open a new browser tab (or incognito window)
2. Go to http://localhost:5173
3. Click on "Patent 1" again

### Step 3: Observe Real-Time Collaboration
1. In Tab 1, start typing in the editor
2. Watch Tab 2 - you should see your typing appear instantly!
3. In Tab 2, type something different
4. Watch Tab 1 - the changes appear instantly there too!

### Step 4: Check User Awareness
1. Look at the top-right corner of the editor
2. You should see an indicator showing "1 online"
3. It displays the other user's avatar with their color and name
4. Move your cursor in Tab 1 and watch Tab 2 - you'll see a colored cursor with your name!

## What You Should See

✅ **Instant Synchronization**: Changes appear immediately in all tabs
✅ **Cursor Awareness**: See colored cursors showing where others are typing
✅ **Online Presence**: Counter showing how many users are editing
✅ **User Avatars**: Colored circles with user initials in the top-right

## Testing Different Documents

1. Open "Patent 2" in both tabs instead
2. Changes in Patent 2 won't appear in Patent 1 (document isolation)
3. Each document has its own collaboration room

## Testing Version Isolation

1. In Tab 1, click "New Version" to create Version 2
2. In Tab 2, stay on Version 1
3. Type in both tabs
4. Changes won't sync between different versions (version isolation)

## Troubleshooting

### Changes Not Syncing?
- Check that both tabs are on the same document AND version
- Check browser console for WebSocket connection errors
- Verify collaboration service is running: `docker-compose ps`

### Can't See Other Users' Cursors?
- Refresh both tabs
- Check that you're on the same document and version
- Look in the browser console for any errors

### Server Won't Start?
- Port 1234 might be in use: `lsof -i :1234`
- Port 5173 might be in use: `lsof -i :5173`
- Port 8000 might be in use: `lsof -i :8000`

## Validate Installation

Run the validation script to check everything is set up correctly:

```bash
./validate-collaboration.sh
```

This will verify:
- All dependencies are installed
- Docker configuration is correct
- Server can start successfully
- Client builds without errors

## Next Steps

- Read COLLABORATION_TESTING.md for comprehensive test scenarios
- Read COLLABORATION_ARCHITECTURE.md to understand how it works
- Read SECURITY_SUMMARY.md for security considerations

## Key Points

🔑 **Document Rooms**: `document-{id}-v{version}`
🔑 **Port 1234**: Hocuspocus WebSocket server
🔑 **Self-Hosted**: No external services required
🔑 **CRDT**: Conflict-free replicated data types ensure consistency

Enjoy collaborative editing! 🎉
