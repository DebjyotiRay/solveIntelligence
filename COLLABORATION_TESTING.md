# Testing Collaboration Features

This document describes how to test the real-time collaboration features.

## Prerequisites

1. All services should be running (server, client, collaboration)
2. The application should be accessible at http://localhost:5173

## Test Plan

### Test 1: Basic Collaboration
**Goal:** Verify that multiple users can edit the same document simultaneously

**Steps:**
1. Open the application in Browser Tab 1
2. Navigate to Patent 1, Version 1
3. Open the application in Browser Tab 2 (new incognito/private window)
4. Navigate to Patent 1, Version 1 in Tab 2
5. In Tab 1, type some text in the editor
6. Verify that the text appears in Tab 2 in real-time
7. In Tab 2, type some different text
8. Verify that the text appears in Tab 1 in real-time

**Expected Result:**
- Changes from one tab should appear instantly in the other tab
- No conflicts or data loss
- Both editors should show identical content

### Test 2: Cursor Awareness
**Goal:** Verify that users can see each other's cursor positions

**Steps:**
1. With both tabs open on the same document (from Test 1)
2. In Tab 1, move your cursor to a specific location
3. In Tab 2, observe the colored cursor indicator
4. Verify the cursor shows the user's name and color
5. Move cursor in Tab 2 and verify it appears in Tab 1

**Expected Result:**
- Each user's cursor is visible to other users
- Cursor shows user name and color
- Cursor position updates in real-time

### Test 3: Online Presence Indicator
**Goal:** Verify the "users online" indicator works correctly

**Steps:**
1. With Tab 1 open on a document, check the top-right corner
2. It should show "0 online" (no other users)
3. Open Tab 2 on the same document
4. In Tab 1, verify the indicator now shows "1 online"
5. Verify you see the avatar/initial of the other user
6. Close Tab 2
7. In Tab 1, verify the indicator returns to "0 online"

**Expected Result:**
- User count updates correctly when users join/leave
- User avatars are displayed with their color
- Count decrements when users disconnect

### Test 4: Document Isolation
**Goal:** Verify that different documents have separate collaboration rooms

**Steps:**
1. Open Tab 1 on Patent 1, Version 1
2. Open Tab 2 on Patent 2, Version 1
3. Type in Tab 1
4. Verify changes do NOT appear in Tab 2 (different document)
5. Type in Tab 2
6. Verify changes do NOT appear in Tab 1

**Expected Result:**
- Different documents are isolated
- Changes in one document don't affect other documents

### Test 5: Version Isolation
**Goal:** Verify that different versions have separate collaboration rooms

**Steps:**
1. Open Tab 1 on Patent 1, Version 1
2. Open Tab 2 on Patent 1, Version 2 (create new version if needed)
3. Type in Tab 1
4. Verify changes do NOT appear in Tab 2 (different version)

**Expected Result:**
- Different versions are isolated
- Each version maintains its own collaborative state

### Test 6: AI Features Still Work
**Goal:** Verify collaboration doesn't break existing AI features

**Steps:**
1. With collaboration enabled, open a document
2. Click "Run AI Analysis"
3. Verify the AI analysis completes successfully
4. Test inline suggestions by typing
5. Verify inline suggestions still work

**Expected Result:**
- AI analysis works normally
- Inline suggestions work normally
- No conflicts between AI and collaboration features

### Test 7: Disconnect and Reconnect
**Goal:** Verify graceful handling of connection issues

**Steps:**
1. Open two tabs on the same document
2. In Tab 1, note the "1 online" indicator
3. Stop the collaboration server (docker-compose stop collaboration)
4. Wait a few seconds
5. Restart the collaboration server (docker-compose start collaboration)
6. Verify both tabs reconnect automatically
7. Verify synchronization resumes

**Expected Result:**
- Graceful handling of disconnection
- Automatic reconnection when server is available
- No data loss during disconnect/reconnect

## Manual Testing Checklist

- [ ] Test 1: Basic Collaboration - PASSED
- [ ] Test 2: Cursor Awareness - PASSED
- [ ] Test 3: Online Presence Indicator - PASSED
- [ ] Test 4: Document Isolation - PASSED
- [ ] Test 5: Version Isolation - PASSED
- [ ] Test 6: AI Features Still Work - PASSED
- [ ] Test 7: Disconnect and Reconnect - PASSED

## Known Limitations

1. **Initial Content Loading:** The first user to open a document will load the content from the database. Subsequent users will sync from Yjs state. If all users disconnect, the next user will reload from database.

2. **Persistence:** Yjs state is not persisted to the database in real-time. Users should still save their versions using the "Save" button to persist changes to the database.

3. **User Names:** Currently, random names (Alice, Bob, Charlie, etc.) are assigned to users. In a production environment, these should be replaced with actual user authentication.

## Troubleshooting

### Users not seeing each other's changes
- Check that the collaboration server is running (docker-compose ps)
- Check browser console for WebSocket connection errors
- Verify both users are on the same document ID and version number

### Cursor not showing
- Verify CollaborationCursor extension is loaded (check console)
- Check that awareness provider is connected
- Browser console should show "Connected to Hocuspocus server"

### Performance Issues
- With many simultaneous users, you may need to optimize the Hocuspocus server
- Consider adding persistence extensions for production use
