#!/bin/bash

# Validation script for collaboration features

set -e

echo "🔍 Validating Collaboration Setup..."
echo ""

# Check if collaboration directory exists
echo "✅ Checking collaboration directory..."
if [ -d "collaboration" ]; then
    echo "   ✓ collaboration directory exists"
else
    echo "   ✗ collaboration directory missing"
    exit 1
fi

# Check if package.json exists in collaboration
echo "✅ Checking collaboration package.json..."
if [ -f "collaboration/package.json" ]; then
    echo "   ✓ package.json exists"
else
    echo "   ✗ package.json missing"
    exit 1
fi

# Check if Hocuspocus dependencies are installed
echo "✅ Checking Hocuspocus dependencies..."
if [ -d "collaboration/node_modules/@hocuspocus/server" ]; then
    echo "   ✓ @hocuspocus/server installed"
else
    echo "   ✗ @hocuspocus/server not installed"
    exit 1
fi

# Check if client dependencies are installed
echo "✅ Checking client collaboration dependencies..."
cd client
for pkg in "@tiptap/extension-collaboration" "@tiptap/extension-collaboration-cursor" "yjs" "y-websocket"; do
    if [ -d "node_modules/${pkg}" ]; then
        echo "   ✓ ${pkg} installed"
    else
        echo "   ✗ ${pkg} not installed"
        exit 1
    fi
done
cd ..

# Check if docker-compose includes collaboration service
echo "✅ Checking docker-compose configuration..."
if grep -q "collaboration:" docker-compose.yml; then
    echo "   ✓ collaboration service configured"
else
    echo "   ✗ collaboration service not configured"
    exit 1
fi

# Check if Editor.tsx has collaboration imports
echo "✅ Checking Editor.tsx for collaboration imports..."
if grep -q "@tiptap/extension-collaboration" client/src/internal/Editor.tsx; then
    echo "   ✓ Collaboration extension imported"
else
    echo "   ✗ Collaboration extension not imported"
    exit 1
fi

if grep -q "CollaborationCursor" client/src/internal/Editor.tsx; then
    echo "   ✓ CollaborationCursor extension imported"
else
    echo "   ✗ CollaborationCursor extension not imported"
    exit 1
fi

# Check if Yjs is imported
if grep -q "yjs" client/src/internal/Editor.tsx; then
    echo "   ✓ Yjs imported"
else
    echo "   ✗ Yjs not imported"
    exit 1
fi

# Check if WebsocketProvider is imported
if grep -q "y-websocket" client/src/internal/Editor.tsx; then
    echo "   ✓ WebsocketProvider imported"
else
    echo "   ✗ WebsocketProvider not imported"
    exit 1
fi

# Check if collaboration server can be started
echo "✅ Checking if collaboration server can start..."
cd collaboration

# Check if port is already in use (server might already be running)
if lsof -Pi :1234 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "   ✓ Collaboration server already running on port 1234"
else
    # Try to start the server
    timeout 5 node server.js > /tmp/collab-test.log 2>&1 &
    SERVER_PID=$!
    sleep 2

    if ps -p $SERVER_PID > /dev/null 2>&1; then
        echo "   ✓ Collaboration server started successfully"
        kill $SERVER_PID 2>/dev/null || true
    else
        echo "   ✗ Collaboration server failed to start"
        cat /tmp/collab-test.log
        exit 1
    fi
fi
cd ..

# Check if client builds successfully
echo "✅ Checking if client builds..."
cd client
if npm run build > /tmp/client-build.log 2>&1; then
    echo "   ✓ Client builds successfully"
else
    echo "   ✗ Client build failed"
    tail -20 /tmp/client-build.log
    exit 1
fi
cd ..

echo ""
echo "✅ All validation checks passed!"
echo ""
echo "📝 Next steps:"
echo "   1. Start all services: docker-compose up"
echo "   2. Open http://localhost:5173 in multiple browser tabs"
echo "   3. Navigate to the same document in both tabs"
echo "   4. Start typing and observe real-time synchronization"
echo ""
echo "📖 For detailed testing instructions, see COLLABORATION_TESTING.md"
