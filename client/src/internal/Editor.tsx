import { useEffect, useState, useRef } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import "../inline-suggestions.css";

interface InlineSuggestion {
  suggested_text: string;
  reasoning?: string;
  [key: string]: unknown;
}

interface PatentIssue {
  type: string;
  severity: 'high' | 'medium' | 'low';
  paragraph?: number;
  description: string;
  suggestion: string;
  target?: {
    text?: string;           
    position?: number;       
    pattern?: string;        
    context?: string;        
  };
  replacement?: {
    type: 'add' | 'replace' | 'insert';
    text: string;           
    position?: 'before' | 'after' | 'replace';
  };
}

interface PanelSuggestion {
  issue: PatentIssue;
  position: number;
  originalText: string;
  replacementText: string;
  type: 'add' | 'replace' | 'insert';
}

export interface EditorProps {
  handleEditorChange: (content: string) => void;
  content: string;
  // Inline suggestion props
  onInlineSuggestionRequest?: (content: string, pos: number, before: string, after: string, triggerType?: string) => void;
  pendingSuggestion?: InlineSuggestion | null;
  onAcceptSuggestion?: (suggestion: InlineSuggestion) => void;
  onRejectSuggestion?: () => void;
  // Panel suggestion props
  activePanelSuggestion?: PanelSuggestion | null;
  onAcceptPanelSuggestion?: () => void;
  onRejectPanelSuggestion?: () => void;
}

export default function Editor({
  handleEditorChange,
  content,
  onInlineSuggestionRequest,
  pendingSuggestion,
  onAcceptSuggestion,
  onRejectSuggestion,
  activePanelSuggestion,
  onAcceptPanelSuggestion,
  onRejectPanelSuggestion
}: EditorProps) {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [cursorPosition, setCursorPosition] = useState<{x: number, y: number} | null>(null);

  const editor = useEditor({
    content: content,
    extensions: [StarterKit],
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      handleEditorChange(html);

      console.log('📝 Editor onUpdate fired! hasInlineSuggestionHandler:', !!onInlineSuggestionRequest);

      // Handle inline suggestions on editor update
      if (onInlineSuggestionRequest) {
        // Clear existing debounce timer
        if (debounceTimerRef.current) {
          clearTimeout(debounceTimerRef.current);
        }

        // Set new debounced suggestion request
        debounceTimerRef.current = setTimeout(() => {
          const { state } = editor;
          const doc = state.doc;
          const pos = state.selection.from;

          // Get context around cursor
          const contextLength = 100;
          const contextStart = Math.max(0, pos - contextLength);
          const contextEnd = Math.min(doc.content.size, pos + contextLength);

          const contextBefore = doc.textBetween(contextStart, pos);
          const contextAfter = doc.textBetween(pos, contextEnd);
          const fullContent = doc.textContent;

          // Simple trigger logic like GitHub Copilot
          const shouldTrigger = (before: string, after: string, content: string) => {
            // Trigger on space (most common)
            if (before.endsWith(' ') && content.trim().length > 5) {
              return { trigger: true, type: 'completion' };
            }
            
            // Trigger on colon
            if (before.endsWith(':') || before.endsWith(': ')) {
              return { trigger: true, type: 'completion' };
            }
            
            // Trigger on period
            if (before.endsWith('.') || before.endsWith('. ')) {
              return { trigger: true, type: 'completion' };
            }
            
            return { trigger: false, type: undefined };
          };

          const triggerResult = shouldTrigger(contextBefore, contextAfter, fullContent);
          
          console.log('🔍 Checking trigger:', {
            contextBefore: contextBefore.slice(-10),
            triggerResult,
            contentLength: fullContent.length
          });
          
          if (triggerResult.trigger) {
            console.log('🎯 Triggering inline suggestion request...', {
              pos,
              triggerType: triggerResult.type,
              contextBefore: contextBefore.slice(-20),
              contextAfter: contextAfter.slice(0, 20)
            });
            onInlineSuggestionRequest(fullContent, pos, contextBefore, contextAfter, triggerResult.type);
          }
        }, 1500);
      }
    },
  });

  // Handle keyboard events for suggestion acceptance/rejection
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Handle panel suggestions first (higher priority)
      if (activePanelSuggestion) {
        if (event.key === 'Tab') {
          event.preventDefault();
          console.log('✅ Accepting panel suggestion via Tab:', activePanelSuggestion.issue.type);
          
          if (editor) {
            const { position, type, replacementText, originalText } = activePanelSuggestion;
            
            if (type === 'add') {
              // Insert text at position
              editor.chain().focus().insertContentAt(position, replacementText).run();
            } else if (type === 'replace') {
              // Replace text from position to position + length
              const endPos = position + originalText.length;
              editor.chain().focus()
                .setTextSelection({ from: position, to: endPos })
                .insertContent(replacementText)
                .run();
            }
          }
          
          onAcceptPanelSuggestion?.();
        } else if (event.key === 'Escape') {
          event.preventDefault();
          console.log('❌ Rejecting panel suggestion via Esc');
          onRejectPanelSuggestion?.();
        }
        return; // Don't process inline suggestions if panel suggestion is active
      }
      
      // Handle inline suggestions (existing logic)
      if (pendingSuggestion) {
        if (event.key === 'Tab') {
          event.preventDefault();
          console.log('✅ Accepting suggestion via Tab:', pendingSuggestion.suggested_text);
          if (editor && pendingSuggestion.suggested_text) {
            const { state } = editor;
            const { selection } = state;
            const currentPos = selection.from;
            // Insert the suggested text
            editor.chain().focus().insertContentAt(currentPos, pendingSuggestion.suggested_text).run();
          }
          onAcceptSuggestion?.(pendingSuggestion);
        } else if (event.key === 'Escape') {
          event.preventDefault();
          console.log('❌ Rejecting suggestion via Esc');
          onRejectSuggestion?.();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [editor, pendingSuggestion, onAcceptSuggestion, onRejectSuggestion, activePanelSuggestion, onAcceptPanelSuggestion, onRejectPanelSuggestion]);

  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      setIsLoading(true);
      editor.commands.setContent(content);
      setIsLoading(false);
    }
  }, [content, editor]);

  // Update cursor position when editor selection changes
  useEffect(() => {
    if (editor && pendingSuggestion) {
      const updateCursorPosition = () => {
        const { view } = editor;
        const { state } = view;
        const { from } = state.selection;
        
        // Get DOM position of cursor
        const coords = view.coordsAtPos(from);
        const editorElement = view.dom;
        const editorRect = editorElement.getBoundingClientRect();
        
        setCursorPosition({
          x: coords.left - editorRect.left,
          y: coords.top - editorRect.top - 2 
        });
      };
      
      updateCursorPosition();
    } else {
      setCursorPosition(null);
    }
  }, [editor, pendingSuggestion]);

  // Debug: Log when pendingSuggestion changes
  useEffect(() => {
    console.log('🎭 React state pendingSuggestion changed:', !!pendingSuggestion, pendingSuggestion?.suggested_text);
  }, [pendingSuggestion]);

  // Function to get DOM coordinates for a text position
  const getTextPosition = (position: number): { x: number; y: number } | null => {
    if (!editor) return null;
    
    try {
      const { view } = editor;
      const coords = view.coordsAtPos(position);
      const editorElement = view.dom;
      const editorRect = editorElement.getBoundingClientRect();
      
      return {
        x: coords.left - editorRect.left,
        y: coords.top - editorRect.top
      };
    } catch (error) {
      console.error('Error getting text position:', error);
      return null;
    }
  };

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

      {/* Panel Suggestion Preview Overlay */}
      {activePanelSuggestion && (() => {
        const textPos = getTextPosition(activePanelSuggestion.position);
        return textPos ? (
          <div
            className="absolute z-50 bg-yellow-50 border-2 border-yellow-300 rounded-lg p-4 shadow-lg max-w-sm"
            style={{
              left: Math.min(textPos.x, window.innerWidth - 400), // Keep within viewport
              top: textPos.y - 120, // Position above the text
              minWidth: '350px'
            }}
          >
            {/* Preview Header */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
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
              <button
                onClick={onRejectPanelSuggestion}
                className="text-gray-400 hover:text-gray-600 text-sm"
                title="Close preview"
              >
                ✕
              </button>
            </div>

            {/* Suggestion Description */}
            <div className="mb-3">
              <h6 className="text-sm font-medium text-gray-800 mb-1">Suggestion:</h6>
              <p className="text-sm text-gray-700">{activePanelSuggestion.issue.suggestion}</p>
            </div>

            {/* Before/After Preview */}
            <div className="bg-white border rounded p-3 mb-3">
              <div className="text-xs font-medium text-gray-600 mb-2">Preview Changes:</div>
              
              {activePanelSuggestion.type === 'add' ? (
                <div className="space-y-1">
                  <div className="text-xs text-gray-500">Will add:</div>
                  <div className="font-mono text-sm">
                    <span className="bg-green-100 text-green-800 px-1 rounded">
                      {activePanelSuggestion.replacementText}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="space-y-1">
                  <div className="text-xs text-gray-500">Current:</div>
                  <div className="font-mono text-sm">
                    <span className="bg-red-100 text-red-800 px-1 rounded line-through">
                      {activePanelSuggestion.originalText || '[End of text]'}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 mt-2">Will become:</div>
                  <div className="font-mono text-sm">
                    <span className="bg-green-100 text-green-800 px-1 rounded">
                      {activePanelSuggestion.replacementText}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3 text-xs">
              <div className="flex items-center gap-1">
                <kbd className="px-2 py-1 bg-blue-100 text-blue-800 rounded font-mono">Tab</kbd>
                <span className="text-gray-600">to accept</span>
              </div>
              <div className="flex items-center gap-1">
                <kbd className="px-2 py-1 bg-gray-200 text-gray-700 rounded font-mono">Esc</kbd>
                <span className="text-gray-600">to cancel</span>
              </div>
            </div>
          </div>
        ) : null;
      })()}
    </div>
  );
}
