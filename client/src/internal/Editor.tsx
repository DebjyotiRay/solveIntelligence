import { useEffect, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { InlineSuggestions } from "../extensions/InlineSuggestions";
import { InlineSuggestion, PanelSuggestion } from "../types/PatentTypes";
import "../inline-suggestions.css";

export interface EditorProps {
  handleEditorChange: (content: string) => void;
  content: string;
  // Inline suggestion props
  onInlineSuggestionRequest?: (content: string, pos: number, before: string, after: string, triggerType?: string) => void;
  pendingSuggestion?: InlineSuggestion | null;
  onAcceptSuggestion?: (suggestion: InlineSuggestion) => void;
  onRejectSuggestion?: () => void;
  // Panel suggestion props - simplified to just show location
  activePanelSuggestion?: PanelSuggestion | null;
  onDismissPanelSuggestion?: () => void;
}

export default function Editor({
  handleEditorChange,
  content,
  onInlineSuggestionRequest,
  pendingSuggestion,
  onAcceptSuggestion,
  onRejectSuggestion,
  activePanelSuggestion,
  onDismissPanelSuggestion
}: EditorProps) {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [cursorPosition, setCursorPosition] = useState<{x: number, y: number} | null>(null);

  const editor = useEditor({
    content: content,
    extensions: [
      StarterKit,
      InlineSuggestions.configure({
        onSuggestionRequest: onInlineSuggestionRequest || (() => {}),
        debounceMs: 1500
      })
    ],
    onUpdate: ({ editor }) => {
      handleEditorChange(editor.getHTML());
    },
  });

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
    if (editor && content !== editor.getHTML()) {
      setIsLoading(true);
      editor.commands.setContent(content);
      setIsLoading(false);
    }
  }, [content, editor]);

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


  return (
    <div className="relative">
      {isLoading && <div>Loading...</div>}
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
