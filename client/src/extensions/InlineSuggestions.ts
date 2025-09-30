import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';

interface InlineSuggestion {
  suggested_text: string;
  reasoning?: string;
  [key: string]: unknown;
}

interface InlineSuggestionsOptions {
  onSuggestionRequest: (content: string, pos: number, before: string, after: string, triggerType?: string) => void;
  pendingSuggestion: InlineSuggestion | null;
  onAcceptSuggestion: (suggestion: InlineSuggestion) => void;
  onRejectSuggestion: () => void;
  debounceMs: number;
}

export const InlineSuggestions = Extension.create<InlineSuggestionsOptions>({
  name: 'inlineSuggestions',

  addOptions() {
    return {
      onSuggestionRequest: () => {},
      pendingSuggestion: null,
      onAcceptSuggestion: () => {},
      onRejectSuggestion: () => {},
      debounceMs: 1500,
    };
  },


  addProseMirrorPlugins() {
    const { onSuggestionRequest, pendingSuggestion, onAcceptSuggestion, onRejectSuggestion, debounceMs } = this.options;
    let debounceTimer: ReturnType<typeof setTimeout> | null = null;

    // Define trigger logic within plugin scope
    const shouldTriggerSuggestion = (before: string, after: string, content: string) => {
      // Natural completion points
      if (before.endsWith('. ') || before.endsWith(': ')) {
        return { trigger: true, type: 'sentence-start' };
      }
      if (before.endsWith(' the ') || before.endsWith(' a ') || before.endsWith(' an ')) {
        return { trigger: true, type: 'noun-phrase' };
      }
      if (before.endsWith(' and ') || before.endsWith(' or ') || before.endsWith(' but ') || before.endsWith(' while ')) {
        return { trigger: true, type: 'parallel-structure' };
      }
      
      // Patent-specific triggers
      if (before.endsWith('comprising ')) {
        return { trigger: true, type: 'claim-elements' };
      }
      if (before.endsWith('wherein ')) {
        return { trigger: true, type: 'claim-limitation' };
      }
      if (before.endsWith('embodiment ')) {
        return { trigger: true, type: 'description-detail' };
      }
      
      // General word completion after space
      if (before.endsWith(' ') && content.trim().length > 10 && before.trim().length > 5) {
        return { trigger: true, type: 'word-completion' };
      }
      
        return { trigger: false, type: undefined };
    };

    return [
      new Plugin({
        key: new PluginKey('inlineSuggestions'),

        state: {
          init() {
            return {
              decorations: DecorationSet.empty,
              lastTrigger: 0,
              lastCursorPos: 0,
              lastPendingSuggestion: null as InlineSuggestion | null
            };
          },

          apply(tr, oldState) {
            let { decorations } = oldState;
            const { selection } = tr;
            const currentPos = selection.from;

            // Clear existing decorations
            decorations = DecorationSet.empty;

            // Get current pendingSuggestion from extension options (updated via useEffect)
            const currentSuggestion = pendingSuggestion;
            
            // Check if this is a forced update from React
            const isForceUpdate = tr.getMeta('updateSuggestions');
            
            console.log('🎨 TipTap apply() called - pendingSuggestion:', !!currentSuggestion, currentSuggestion?.suggested_text, 'forceUpdate:', isForceUpdate);

            // Add suggestion decoration if there's a pending suggestion
            if (currentSuggestion && currentSuggestion.suggested_text) {
              try {
                console.log('✨ Creating decoration for suggestion:', currentSuggestion.suggested_text, 'at position:', currentPos);
                
                const suggestionEl = document.createElement('span');
                suggestionEl.className = 'inline-suggestion';
                suggestionEl.style.cssText = `
                  color: #888;
                  font-style: italic;
                  opacity: 0.6;
                  pointer-events: none;
                `;
                suggestionEl.textContent = currentSuggestion.suggested_text;
                suggestionEl.title = `Tab to accept, Esc to reject`;

                const decoration = Decoration.widget(currentPos, suggestionEl, {
                  side: 1,
                  key: 'inline-suggestion'
                });

                decorations = DecorationSet.create(tr.doc, [decoration]);
                console.log('✅ Decoration created successfully');
              } catch (error) {
                console.error('❌ Error creating suggestion decoration:', error);
              }
            }

            return {
              ...oldState,
              decorations,
              lastCursorPos: currentPos,
              lastPendingSuggestion: currentSuggestion
            };
          }
        },

        props: {
          decorations(state) {
            return this.getState(state)?.decorations;
          },

          handleTextInput(view) {
            // Clear any existing debounce timer
            if (debounceTimer) {
              clearTimeout(debounceTimer);
            }

            // Set new debounced suggestion request
            debounceTimer = setTimeout(() => {
              const { state } = view;
              const doc = state.doc;
              const pos = state.selection.from;

              // Get context around cursor
              const contextLength = 100;
              const contextStart = Math.max(0, pos - contextLength);
              const contextEnd = Math.min(doc.content.size, pos + contextLength);

              const contextBefore = doc.textBetween(contextStart, pos);
              const contextAfter = doc.textBetween(pos, contextEnd);
              const fullContent = doc.textContent;

              // Enhanced semantic triggering
              const shouldTrigger = shouldTriggerSuggestion(contextBefore, contextAfter, fullContent);
              if (shouldTrigger.trigger) {
                console.log('🎯 Triggering inline suggestion request...', {
                  pos,
                  triggerType: shouldTrigger.type,
                  contextBefore: contextBefore.slice(-20),
                  contextAfter: contextAfter.slice(0, 20)
                });
                onSuggestionRequest(fullContent, pos, contextBefore, contextAfter, shouldTrigger.type);
              }
            }, debounceMs);

            return false; // Don't prevent the input
          },

          handleKeyDown(view, event) {
            // Handle suggestion acceptance/rejection
            if (pendingSuggestion) {
              if (event.key === 'Tab') {
                event.preventDefault();
                onAcceptSuggestion(pendingSuggestion);
                return true;
              } else if (event.key === 'Escape') {
                event.preventDefault();
                onRejectSuggestion();
                return true;
              }
            }
            return false;
          }
        },

        // Cleanup timer on destroy
        destroy() {
          if (debounceTimer) {
            clearTimeout(debounceTimer);
          }
        }
      })
    ];
  },

  addKeyboardShortcuts() {
    return {
      'Tab': () => {
        if (this.options.pendingSuggestion) {
          this.options.onAcceptSuggestion(this.options.pendingSuggestion);
          return true;
        }
        return false;
      },
      'Escape': () => {
        if (this.options.pendingSuggestion) {
          this.options.onRejectSuggestion();
          return true;
        }
        return false;
      },
      // Manual trigger with Ctrl/Cmd + Space
      'Mod-Space': () => {
        const { editor } = this;
        if (editor) {
          const { state } = editor;
          const pos = state.selection.from;
          const doc = state.doc;

          const contextBefore = doc.textBetween(Math.max(0, pos - 100), pos);
          const contextAfter = doc.textBetween(pos, Math.min(doc.content.size, pos + 100));

          console.log('🎯 Manual inline suggestion triggered');
          this.options.onSuggestionRequest(doc.textContent, pos, contextBefore, contextAfter);
        }
        return true;
      }
    };
  }
});
