import { useEffect, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Collaboration from "@tiptap/extension-collaboration";
import CollaborationCursor from "@tiptap/extension-collaboration-cursor";
import { HocuspocusProvider } from '@hocuspocus/provider';
import * as Y from "yjs";
import { InlineSuggestions } from "../extensions/InlineSuggestions";
import { InlineSuggestionResponse, PanelSuggestion } from "../types/PatentTypes";
import "../inline-suggestions.css";
import "../collaboration.css";

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
  // Online users callback
  onOnlineUsersChange?: (count: number, users: CollaborationUser[], selfUser?: CollaborationUser) => void;
}

interface CollaborationUser {
  name: string;
  color: string;
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
  onDismissPanelSuggestion,
  onOnlineUsersChange
}: EditorProps) {
  const [cursorPosition, setCursorPosition] = useState<{x: number, y: number} | null>(null);
  const [ydoc] = useState(() => new Y.Doc());
  const [provider] = useState(() => {
    const roomName = `document-${documentId}-v${versionNumber}`;
    console.log('Creating Hocuspocus provider for room:', roomName);
    
    // Generate random user info for this session
    const randomColor = '#' + Math.floor(Math.random()*16777215).toString(16).padStart(6, '0');
    const randomName = 'User ' + Math.floor(Math.random() * 1000);
    
    const prov = new HocuspocusProvider({
      url: 'ws://localhost:1234',
      name: roomName,
      document: ydoc,
    });

    // Set user information for collaboration cursor
    prov.on('synced', () => {
      prov.setAwarenessField('user', {
        name: randomName,
        color: randomColor,
      });
    });

    console.log('Provider created with user:', randomName);
    
    return prov;
  });

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        history: false,
      }),
      Collaboration.configure({
        document: ydoc,
      }),
      CollaborationCursor.configure({
        provider: provider,
      }),
      InlineSuggestions.configure({
        onSuggestionRequest: onInlineSuggestionRequest || (() => {}),
        debounceMs: 1500,
        documentKey: `${documentId}-${versionNumber}`
      })
    ],
    content: content,
    onUpdate: ({ editor }) => {
      handleEditorChange(editor.getHTML());
    },
  }, []);

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

  // Initialize content from database when editor is empty
  useEffect(() => {
    if (!editor || !content) return;

    // Check if editor is empty (has only one empty paragraph)
    const isEditorEmpty = editor.isEmpty;
    
    if (isEditorEmpty) {
      console.log('Initializing editor with database content');
      editor.commands.setContent(content);
    }
  }, [editor, content]);

  // Cleanup provider on unmount
  useEffect(() => {
    return () => {
      provider?.destroy();
    };
  }, [provider]);

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
    console.log('👁️ Editor: pendingSuggestion changed:', {
      hasSuggestion: !!pendingSuggestion,
      suggested_text: pendingSuggestion?.suggested_text,
      hasEditor: !!editor
    });
    
    if (editor && pendingSuggestion && pendingSuggestion.suggested_text) {
      const { view } = editor;
      const coords = view.coordsAtPos(view.state.selection.from);
      const editorRect = view.dom.getBoundingClientRect();
      
      const newCursorPosition = {
        x: coords.left - editorRect.left,
        y: coords.top - editorRect.top
      };
      
      console.log('📍 Editor: Setting cursor position:', newCursorPosition);
      console.log('📍 Editor: Suggested text:', pendingSuggestion.suggested_text);
      setCursorPosition(newCursorPosition);
    } else {
      console.log('📍 Editor: Clearing cursor position');
      setCursorPosition(null);
    }
  }, [editor, pendingSuggestion]);

  // Track connected users
  useEffect(() => {
    if (!provider || !provider.awareness || !onOnlineUsersChange) return;

    const updateUsers = () => {
      if (!provider.awareness) return;
      
      const states = Array.from(provider.awareness.getStates().entries()) as [number, { user?: CollaborationUser }][];
      
      // Get current user
      const currentUserState = provider.awareness.getLocalState() as { user?: CollaborationUser } | null;
      const selfUser = currentUserState?.user;
      
      // Get all users including self
      const allUsers: CollaborationUser[] = states
        .map(([, state]) => state.user)
        .filter((user): user is CollaborationUser => user !== undefined && user !== null);
      
      // Get other users (excluding self)
      const otherUsers: CollaborationUser[] = states
        .filter(([clientId]) => clientId !== provider.awareness!.clientID)
        .map(([, state]) => state.user)
        .filter((user): user is CollaborationUser => user !== undefined && user !== null);
      
      // Pass total count (including self) and other users list
      onOnlineUsersChange(allUsers.length, otherUsers, selfUser);
    };

    provider.awareness.on('change', updateUsers);
    updateUsers();

    return () => {
      provider.awareness?.off('change', updateUsers);
    };
  }, [provider, onOnlineUsersChange]);


  return (
    <div className="relative">
      <EditorContent editor={editor}></EditorContent>
      
      {/* Display inline suggestion at cursor position - clean gray italics */}
      {pendingSuggestion && pendingSuggestion.suggested_text && cursorPosition && !activePanelSuggestion && (
        <div
          className="absolute z-50 pointer-events-none"
          style={{
            left: `${cursorPosition.x}px`,
            top: `${cursorPosition.y}px`,
            color: '#9ca3af',
            fontStyle: 'italic',
            opacity: 0.6,
            fontSize: 'inherit',
            fontFamily: 'inherit',
            whiteSpace: 'pre-wrap',
            maxWidth: '500px',
            lineHeight: 'inherit'
          }}
          title="Tab to accept, Esc to reject"
        >
          {pendingSuggestion.suggested_text}
        </div>
      )}

      {/* Minimal inline suggestion hint */}
      {pendingSuggestion && pendingSuggestion.suggested_text && !activePanelSuggestion && (
        <div
          className="fixed bottom-4 right-4 z-50 bg-gray-900 bg-opacity-75 rounded px-3 py-1.5 shadow-lg flex items-center gap-2 text-xs text-white"
        >
          <kbd className="px-1.5 py-0.5 bg-gray-700 rounded font-mono text-[10px]">Tab</kbd>
          <span className="text-gray-300">accept</span>
          <span className="text-gray-600">|</span>
          <kbd className="px-1.5 py-0.5 bg-gray-700 rounded font-mono text-[10px]">Esc</kbd>
          <span className="text-gray-300">dismiss</span>
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
                  <div className="font-mono text-sm text-green-900 wrap-break-word">
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
