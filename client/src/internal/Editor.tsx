import { useEffect, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { CursorStyleSuggestions, CursorStyleSuggestion } from "../extensions/CursorStyleSuggestions";
import { InlineSuggestionResponse, PanelSuggestion } from "../types/PatentTypes";
import "../cursor-style-suggestions.css";

export interface EditorProps {
  handleEditorChange: (content: string) => void;
  content: string;
  documentId: number;
  versionNumber: number;
  // Cursor-style inline suggestion props
  onInlineSuggestionRequest?: (content: string, pos: number, before: string, after: string, triggerType?: string) => void;
  pendingSuggestion?: InlineSuggestionResponse | null;
  onAcceptSuggestion?: (suggestion: CursorStyleSuggestion, acceptedText: string) => void;
  onRejectSuggestion?: (suggestion: CursorStyleSuggestion) => void;
  onCycleAlternative?: (suggestion: CursorStyleSuggestion, newIndex: number) => void;
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
  onCycleAlternative,
  activePanelSuggestion,
  onDismissPanelSuggestion
}: EditorProps) {
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const editor = useEditor({
    content: content,
    extensions: [
      StarterKit,
      CursorStyleSuggestions.configure({
        onSuggestionRequest: onInlineSuggestionRequest || (() => {}),
        onSuggestionAccepted: (suggestion, acceptedText) => {
          console.log('✅ Suggestion accepted:', acceptedText);
          onAcceptSuggestion?.(suggestion, acceptedText);
        },
        onSuggestionRejected: (suggestion) => {
          console.log('❌ Suggestion rejected');
          onRejectSuggestion?.(suggestion);
        },
        onCycleAlternative: (suggestion, newIndex) => {
          console.log(`🔄 Cycled to alternative ${newIndex + 1}/${suggestion.alternatives.length}`);
          onCycleAlternative?.(suggestion, newIndex);
        },
        debounceMs: 1500,
        documentKey: `${documentId}-${versionNumber}`
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

  // When suggestion arrives from backend, push it to the editor plugin
  useEffect(() => {
    if (editor && pendingSuggestion && pendingSuggestion.alternatives && pendingSuggestion.alternatives.length > 0) {
      // Convert backend response to CursorStyleSuggestion format
      const cursorSuggestion: CursorStyleSuggestion = {
        id: pendingSuggestion.suggestion_id,
        position: pendingSuggestion.position,
        alternatives: pendingSuggestion.alternatives,
        currentIndex: pendingSuggestion.current_index || 0,
        anchorText: pendingSuggestion.anchor_text
      };

      // Push suggestion to editor plugin
      editor.chain().focus().setSuggestion(cursorSuggestion).run();
    } else if (editor && !pendingSuggestion) {
      // Clear suggestion if null
      editor.chain().clearSuggestion().run();
    }
  }, [editor, pendingSuggestion]);

  // Handle panel suggestion Escape key
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Dismiss panel suggestion info on Escape
      if (activePanelSuggestion && event.key === 'Escape') {
        event.preventDefault();
        onDismissPanelSuggestion?.();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [activePanelSuggestion, onDismissPanelSuggestion]);

  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      setIsLoading(true);
      editor.commands.setContent(content);
      setIsLoading(false);
    }
  }, [content, editor]);

  return (
    <div className="relative">
      {isLoading && <div>Loading...</div>}
      <EditorContent editor={editor}></EditorContent>

      {/* Ghost text is now rendered inline by CursorStyleSuggestions extension */}
      {/* No need for separate overlay - the extension handles everything */}

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
