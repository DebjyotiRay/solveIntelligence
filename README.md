# Solve Intelligence Engineering Challenge

## Objective

You have received a mock-up of a patent reviewing application from a junior colleague. Unfortunately, it is incomplete and needs additional work. Your job is to take your colleague's work, improve and extend it, and add a feature of your own creation!

After completing the tasks below, add a couple of sentences to the end of this file briefly outlining what improvements you made.

## Docker

Make sure you create a .env file (see .env.example) with the OpenAI API key we have provided.

To build and run the application using Docker, execute the following command:

```
docker-compose up --build
```

## Task 1: Implement Document Versioning

Currently, the user can save a document, but there is no concept of **versioning**. Paying customers have expressed an interest in this and have requested the following:

1. The ability to create new versions
2. The ability to switch between existing versions
3. The ability to make changes to any of the existing versions and save those changes (without creating a new version)

You will need to modify the database model (`app/models.py`), add some API routes (`app/__main__.py`), and update the client-side code accordingly.

## Task 2: Real-Time AI Suggestions

Your colleague started some work on integrating real-time improvement suggestions for your users. However, they only had time to set up a WebSocket connection. It is your job to finish it.

You will find a WebSocket endpoint that needs to be completed in the `app/__main__.py` file in the `server`. This endpoint should receive the editor contents from the client and stream out AI suggestions to the UI. There are a few complications here:

- You are using a third party AI library, which exposes a fairly poor API. The code for this library is in `server/app/internal/ai.py`.
  - The API expects a **plain** text document, with no HTML mark-up or formatting
  - There are intermittent errors in the formatting of the JSON output

You will need to find some way of notifying the user of the suggestions generated. As we don't want the user's experience to be impacted, this should be a background process. You can find the existing frontend WebSocket code in `client/src/Document.tsx`.

## Task 3: Showcase your AI Skills

Implement an additional AI-based feature or product improvement that would benefit our customers as they draft their patent applications.

This last part is open-ended, and you can take it in any direction you like. We’re interested in seeing how you come up with and implement AI-based approaches without us directing you.

Some ideas:

- Generate technical drawings (e.g. flowcharts, system diagrams, device diagrams, etc.) based on the claims.
- Have the user ask the AI to make an update to the application, and have the AI stream this update directly into the editor.
- Extend task 2 by having the AI incorporate its suggestions directly into the editor.

Or anything else you like.

Enjoy!

---

## Summary of Improvements

**Task 1 - Document Versioning:** Implemented a clean stateless versioning architecture with a dedicated `DocumentVersion` table, race-condition protection using database locks, and a Google Docs-style UI with version switching, unsaved changes warnings, and dirty state tracking. Users can create new versions, switch between existing versions, and edit/save any version independently.

**Task 2 - Real-Time AI Suggestions:** Completed the WebSocket endpoint with robust HTML-to-plaintext conversion (using BeautifulSoup), multi-stage JSON error handling with fallback parsing, and streaming progress updates for better UX. The system handles the "poor API" requirements by stripping HTML before sending to the AI library and gracefully recovering from malformed JSON responses.

**Task 3 - AI Innovation:** Built a multi-agent patent analysis system with memory-enhanced agents that learn from historical analyses. The system features: (1) **Multi-Agent Orchestration** with structure and legal compliance agents running in parallel, (2) **Persistent Memory** using Mem0 for cross-session learning and pattern recognition, (3) **GitHub Copilot-style Inline Suggestions** for real-time writing assistance with context-aware completions. The system is opt-in via feature flag (`USE_MULTI_AGENT_SYSTEM`), preserving backward compatibility with the original AI implementation.

---

## Collaboration & Awareness Features

**Real-Time Collaborative Editing:** Implemented TipTap collaboration using a self-hosted Hocuspocus WebSocket server. Multiple users can now edit the same document simultaneously with real-time synchronization powered by Yjs CRDT (Conflict-free Replicated Data Types).

**Key Features:**
- **Multi-user Editing:** Changes sync instantly between all connected users
- **Cursor Awareness:** See where other users are typing with colored cursor indicators showing their name
- **Online Presence:** Visual indicator showing how many users are currently editing
- **Document Isolation:** Each document version has its own collaborative room for independent editing
- **Self-Hosted Backend:** Uses Hocuspocus server (port 1234) instead of TipTap Cloud for full control

**Architecture:**
- **Client:** TipTap extensions (`@tiptap/extension-collaboration`, `@tiptap/extension-collaboration-cursor`) with Yjs and y-websocket
- **Collaboration Server:** Standalone Hocuspocus WebSocket server in `/collaboration` directory
- **Docker Integration:** Collaboration service runs alongside existing FastAPI server and Vite frontend

**Testing Collaboration:**
Open the application in multiple browser tabs or windows, navigate to the same document/version, and start typing to see real-time synchronization in action!

