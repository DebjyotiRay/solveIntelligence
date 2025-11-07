import { useEffect, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Collaboration from "@tiptap/extension-collaboration";
import CollaborationCursor from "@tiptap/extension-collaboration-cursor";
import { WebsocketProvider } from "y-websocket";
import * as Y from "yjs";
import { InlineSuggestions } from "../extensions/InlineSuggestions";
import { InlineSuggestionResponse, PanelSuggestion } from "../types/PatentTypes";
import "../inline-suggestions.css";

export interface EditorProps {
  handleEditorChange: (content: string) => void;
  content: string;
  documentId: number;
  versionNumber: number;
  // Inline suggestion props
  onInlineSuggestionRequest?: (content: string, pos: number, before: string, after: string, triggerType?: string) => void;
  pendingSuggestion?: InlineSuggestionResponse | null;
  onAcceptSuggestion?: (suggestion: InlineSuggestionResponse) => void;
  onRejectSuggestion?: () => void;
  // Panel suggestion props - simplified to just show location
  activePanelSuggestion?: PanelSuggestion | null;
  onDismissPanelSuggestion?: () => void;
}

export default function Editor({
  handleEditorChange,
  content,
  documentId,
  versionNumber,
  onInlineSuggestionRequest,
  pendingSuggestion,
  onAcceptSuggestion,
  onRejectSuggestion,
  activePanelSuggestion,
  onDismissPanelSuggestion
}: EditorProps) {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [cursorPosition, setCursorPosition] = useState<{x: number, y: number} | null>(null);
  const [provider, setProvider] = useState<WebsocketProvider | null>(null);
  const [ydoc] = useState(() => new Y.Doc());

  // Initialize collaboration provider
  useEffect(() => {
    // Generate a random color for this user
    const getRandomColor = () => {
      const colors = ['#958DF1', '#F98181', '#FBBC88', '#FAF594', '#70CFF8', '#94FADB', '#B9F18D'];
      return colors[Math.floor(Math.random() * colors.length)];
    };

    // Generate a random name for this user
    const getRandomName = () => {
      const names = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Henry'];
      return names[Math.floor(Math.random() * names.length)];
    };

    const roomName = `document-${documentId}-v${versionNumber}`;
    
    // Connect to Hocuspocus server
    const websocketProvider = new WebsocketProvider(
      'ws://localhost:1234',
      roomName,
      ydoc,
      {
        connect: true,
      }
    );

    websocketProvider.awareness.setLocalStateField('user', {
      name: getRandomName(),
      color: getRandomColor(),
    });

    setProvider(websocketProvider);

    return () => {
      websocketProvider.destroy();
    };
  }, [documentId, versionNumber, ydoc]);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        // Disable history extension as Collaboration handles it
        history: false,
      }),
      Collaboration.configure({
        document: ydoc,
      }),
      CollaborationCursor.configure({
        provider: provider as any,
        user: {
          name: 'Anonymous',
          color: '#958DF1',
        },
      }),
      InlineSuggestions.configure({
        onSuggestionRequest: onInlineSuggestionRequest || (() => {}),
        debounceMs: 1500,
        documentKey: `${documentId}-${versionNumber}`
      })
    ],
    onUpdate: ({ editor }) => {
      handleEditorChange(editor.getHTML());
    },
  }, [provider, ydoc]);

  // Highlight and scroll to the issue location when panel suggestion is active
  useEffect(() => {
    if (editor && activePanelSuggestion) {
      const editorTextContent = editor.state.doc.textContent;
      const targetText = activePanelSuggestion.issue.target?.text;
      
      if (targetText) {
        // Simple text search
        const pos = editorTextContent.indexOf(targetText);
        
        if (pos !== -1) {
          // Select/highlight the text
          editor.chain()
            .focus()
            .setTextSelection({ 
              from: pos, 
              to: pos + targetText.length 
            })
            .run();
        }
      }
    }
  }, [editor, activePanelSuggestion]);

  // Load initial content only when document is empty (first user)
  useEffect(() => {
    if (editor && provider && content && !isLoading) {
      // Only set content if the Yjs document is empty
      const yXmlFragment = ydoc.getXmlFragment('default');
      if (yXmlFragment.length === 0) {
        setIsLoading(true);
        editor.commands.setContent(content);
        setIsLoading(false);
      }
    }
  }, [editor, provider, content, ydoc, isLoading]);

  // Handle keyboard shortcuts for inline suggestions only
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Only handle inline suggestions, not panel suggestions
      if (pendingSuggestion && !activePanelSuggestion) {
        if (event.key === 'Tab') {
          event.preventDefault();
          if (editor && pendingSuggestion.suggested_text) {
            editor.chain().focus().insertContentAt(editor.state.selection.from, pendingSuggestion.suggested_text).run();
          }
          onAcceptSuggestion?.(pendingSuggestion);
        } else if (event.key === 'Escape') {
          event.preventDefault();
          onRejectSuggestion?.();
        }
      }
      
      // Dismiss panel suggestion info on Escape
      if (activePanelSuggestion && event.key === 'Escape') {
        event.preventDefault();
        onDismissPanelSuggestion?.();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [editor, pendingSuggestion, onAcceptSuggestion, onRejectSuggestion, activePanelSuggestion, onDismissPanelSuggestion]);

  useEffect(() => {
    if (editor && pendingSuggestion) {
      const { view } = editor;
      const coords = view.coordsAtPos(view.state.selection.from);
      const editorRect = view.dom.getBoundingClientRect();
      
      setCursorPosition({
        x: coords.left - editorRect.left,
        y: coords.top - editorRect.top - 2
      });
    } else {
      setCursorPosition(null);
    }
  }, [editor, pendingSuggestion]);

  // Track connected users
  const [connectedUsers, setConnectedUsers] = useState<any[]>([]);
  
  useEffect(() => {
    if (!provider) return;

    const updateUsers = () => {
      const states = Array.from(provider.awareness.getStates().entries());
      const users = states
        .filter(([clientId]) => clientId !== provider.awareness.clientID)
        .map(([, state]) => state.user)
        .filter(user => user);
      setConnectedUsers(users);
    };

    provider.awareness.on('change', updateUsers);
    updateUsers();

    return () => {
      provider.awareness.off('change', updateUsers);
    };
  }, [provider]);


  return (
    <div className="relative">
      {isLoading && <div>Loading...</div>}
      
      {/* Connected Users Indicator */}
      {connectedUsers.length > 0 && (
        <div className="absolute top-2 right-2 z-50 flex items-center gap-2 bg-white rounded-full px-3 py-1 shadow-md border border-gray-200">
          <div className="flex -space-x-2">
            {connectedUsers.map((user, index) => (
              <div
                key={index}
                className="w-8 h-8 rounded-full border-2 border-white flex items-center justify-center text-white text-xs font-bold"
                style={{ backgroundColor: user.color }}
                title={user.name}
              >
                {user.name?.charAt(0).toUpperCase()}
              </div>
            ))}
          </div>
          <span className="text-xs text-gray-600 font-medium">
            {connectedUsers.length} online
          </span>
        </div>
      )}
      
      <EditorContent editor={editor}></EditorContent>
      
      {/* Display inline suggestion at cursor position */}
      {pendingSuggestion && cursorPosition && !activePanelSuggestion && (
        <div
          className="absolute pointer-events-none z-10"
          style={{
            left: cursorPosition.x,
            top: cursorPosition.y,
            color: '#888',
            fontStyle: 'italic',
            opacity: 0.6,
            fontSize: 'inherit',
            fontFamily: 'inherit',
            whiteSpace: 'nowrap'
          }}
          title="Tab to accept, Esc to reject"
        >
          {pendingSuggestion.suggested_text}
        </div>
      )}

      {/* Panel Suggestion Info Overlay - Shows what to fix manually */}
      {activePanelSuggestion && (
        <div
          className="fixed bottom-4 right-4 z-50 bg-blue-50 border-2 border-blue-300 rounded-lg p-4 shadow-lg max-w-md"
          style={{ minWidth: '350px' }}
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="text-blue-600 text-xl">📍</span>
              <span className="font-medium text-blue-900">Location Highlighted</span>
            </div>
            <button
              onClick={onDismissPanelSuggestion}
              className="text-gray-400 hover:text-gray-600"
              title="Close"
            >
              ✕
            </button>
          </div>

          {/* Issue Details */}
          <div className="mb-3">
            <div className="flex items-center gap-2 mb-2">
              <span className={`px-2 py-1 text-xs font-medium rounded ${
                activePanelSuggestion.issue.severity === 'high' ? 'bg-red-100 text-red-800' :
                activePanelSuggestion.issue.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                'bg-green-100 text-green-800'
              }`}>
                {activePanelSuggestion.issue.severity.toUpperCase()}
              </span>
              <span className="text-xs text-gray-600 capitalize">
                {activePanelSuggestion.issue.type}
              </span>
            </div>
            <p className="text-sm text-gray-700 mb-2">{activePanelSuggestion.issue.description}</p>
          </div>

          {/* What to Change */}
          <div className="bg-white border rounded p-3 mb-3">
            <div className="text-xs font-medium text-gray-700 mb-2">How to Fix:</div>
            <p className="text-sm text-gray-800 mb-3">{activePanelSuggestion.issue.suggestion}</p>
            
            {activePanelSuggestion.issue.replacement?.text && (
              <div className="mt-3">
                <div className="text-xs text-gray-500 mb-1">Suggested Text:</div>
                <div className="bg-green-50 border border-green-200 rounded p-2">
                  <div className="font-mono text-sm text-green-900 break-words">
                    {activePanelSuggestion.issue.replacement.text}
                  </div>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(activePanelSuggestion.issue.replacement!.text);
                    }}
                    className="mt-2 text-xs text-green-700 hover:text-green-900 underline"
                  >
                    📋 Copy to Clipboard
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Instructions */}
          <div className="text-xs text-gray-600">
            
            <div className="mt-2">
              <kbd className="px-2 py-1 bg-gray-200 text-gray-700 rounded font-mono">Esc</kbd>
              <span className="ml-1">to close</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
