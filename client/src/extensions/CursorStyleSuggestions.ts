/**
 * Cursor-Style Inline Suggestions Extension for TipTap
 *
 * Features:
 * - Ghost text rendered inline (gray, italic)
 * - Multiple alternatives with arrow key cycling
 * - Tab to accept, Esc to reject
 * - Suggestion counter (1/3)
 * - Auto-expire on document changes
 */

import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';

export interface SuggestionAlternative {
  text: string;
  confidence: number;
  reasoning: string;
}

export interface CursorStyleSuggestion {
  id: string;
  position: number;  // Where to insert ghost text
  alternatives: SuggestionAlternative[];
  currentIndex: number;  // Which alternative is shown
  anchorText: string;  // Last 50 chars before position (for validation)
}

interface CursorStyleSuggestionsOptions {
  onSuggestionRequest: (content: string, pos: number, before: string, after: string) => void;
  onSuggestionAccepted: (suggestion: CursorStyleSuggestion, acceptedText: string) => void;
  onSuggestionRejected: (suggestion: CursorStyleSuggestion) => void;
  onCycleAlternative: (suggestion: CursorStyleSuggestion, newIndex: number) => void;
  debounceMs: number;
  documentKey?: string;
}

interface PluginState {
  suggestion: CursorStyleSuggestion | null;
  decorations: DecorationSet;
}

export const CursorStyleSuggestions = Extension.create<CursorStyleSuggestionsOptions>({
  name: 'cursorStyleSuggestions',

  addOptions() {
    return {
      onSuggestionRequest: () => {},
      onSuggestionAccepted: () => {},
      onSuggestionRejected: () => {},
      onCycleAlternative: () => {},
      debounceMs: 1500,
    };
  },

  addProseMirrorPlugins() {
    const {
      onSuggestionRequest,
      onSuggestionAccepted,
      onSuggestionRejected,
      onCycleAlternative,
      debounceMs,
      documentKey
    } = this.options;

    let debounceTimer: ReturnType<typeof setTimeout> | null = null;
    let currentDocKey: string | null = null;

    const pluginKey = new PluginKey<PluginState>('cursorStyleSuggestions');

    // Helper: Should trigger suggestion?
    const shouldTriggerSuggestion = (before: string, content: string) => {
      if (content.trim().length < 10) return false;

      // Trigger after space
      if (before.endsWith(' ')) return true;

      // Trigger after punctuation + space
      if (/[.!?]\s$/.test(before)) return true;

      // Trigger after legal keywords
      if (/(shall|hereby|pursuant to|notwithstanding|whereas)\s$/i.test(before)) return true;

      return false;
    };

    // Helper: Create ghost text decoration
    const createGhostTextDecoration = (
      suggestion: CursorStyleSuggestion,
      position: number
    ): Decoration => {
      const currentAlt = suggestion.alternatives[suggestion.currentIndex];
      const ghostText = currentAlt.text;

      // Create DOM node for ghost text
      const ghostSpan = document.createElement('span');
      ghostSpan.className = 'cursor-ghost-text';
      ghostSpan.textContent = ghostText;
      ghostSpan.setAttribute('data-suggestion-id', suggestion.id);

      // Inline styles for ghost text
      ghostSpan.style.color = 'rgba(128, 128, 128, 0.5)';
      ghostSpan.style.fontStyle = 'italic';
      ghostSpan.style.pointerEvents = 'none';
      ghostSpan.style.userSelect = 'none';

      return Decoration.widget(position, ghostSpan, {
        side: 1,  // Place after cursor
        key: 'ghost-text'
      });
    };

    // Helper: Create suggestion hint decoration (keyboard shortcuts)
    const createHintDecoration = (
      suggestion: CursorStyleSuggestion,
      position: number
    ): Decoration => {
      const hint = document.createElement('span');
      hint.className = 'cursor-suggestion-hint';

      const hasMultiple = suggestion.alternatives.length > 1;
      const counter = `${suggestion.currentIndex + 1}/${suggestion.alternatives.length}`;

      hint.innerHTML = `
        <span class="hint-key">⇥ Tab</span> to accept
        ${hasMultiple ? `<span class="hint-key">→</span> Next (${counter})` : ''}
        <span class="hint-key">Esc</span> to dismiss
      `;

      // Positioning and styling
      hint.style.position = 'absolute';
      hint.style.bottom = '100%';
      hint.style.left = '0';
      hint.style.marginBottom = '4px';
      hint.style.padding = '4px 8px';
      hint.style.background = 'rgba(0, 0, 0, 0.8)';
      hint.style.color = 'white';
      hint.style.fontSize = '11px';
      hint.style.borderRadius = '4px';
      hint.style.whiteSpace = 'nowrap';
      hint.style.zIndex = '1000';
      hint.style.pointerEvents = 'none';

      return Decoration.widget(position, hint, {
        side: 1,
        key: 'suggestion-hint'
      });
    };

    return [
      new Plugin<PluginState>({
        key: pluginKey,

        state: {
          init(): PluginState {
            return {
              suggestion: null,
              decorations: DecorationSet.empty
            };
          },

          apply(tr, state, oldState, newState): PluginState {
            // Check if suggestion should be expired due to document changes
            if (state.suggestion) {
              const docChanged = !oldState.doc.eq(newState.doc);
              const suggestionPos = state.suggestion.position;

              // If document changed around suggestion position, expire it
              if (docChanged) {
                const textBefore = newState.doc.textBetween(
                  Math.max(0, suggestionPos - 50),
                  suggestionPos
                );

                // If anchor text doesn't match, suggestion is stale
                if (textBefore !== state.suggestion.anchorText) {
                  return {
                    suggestion: null,
                    decorations: DecorationSet.empty
                  };
                }
              }
            }

            // Get suggestion from transaction metadata
            const newSuggestion = tr.getMeta(pluginKey);

            if (newSuggestion === null) {
              // Clear suggestion
              return {
                suggestion: null,
                decorations: DecorationSet.empty
              };
            }

            if (newSuggestion) {
              // Update suggestion
              const decorations = DecorationSet.create(newState.doc, [
                createGhostTextDecoration(newSuggestion, newSuggestion.position),
                createHintDecoration(newSuggestion, newSuggestion.position)
              ]);

              return {
                suggestion: newSuggestion,
                decorations
              };
            }

            // Map existing decorations through changes
            if (state.suggestion) {
              const decorations = state.decorations.map(tr.mapping, tr.doc);
              return {
                ...state,
                decorations
              };
            }

            return state;
          }
        },

        props: {
          decorations(state) {
            return pluginKey.getState(state)?.decorations;
          },

          handleTextInput(view) {
            // Reset on document change
            const newDocKey = documentKey || '';
            if (newDocKey !== currentDocKey) {
              currentDocKey = newDocKey;
              if (debounceTimer) clearTimeout(debounceTimer);

              // Clear existing suggestion
              view.dispatch(
                view.state.tr.setMeta(pluginKey, null)
              );

              return false;
            }

            // Clear existing timer
            if (debounceTimer) clearTimeout(debounceTimer);

            // Set new timer for suggestion request
            debounceTimer = setTimeout(() => {
              const { state } = view;
              const pos = state.selection.from;
              const contextBefore = state.doc.textBetween(Math.max(0, pos - 100), pos);
              const contextAfter = state.doc.textBetween(pos, Math.min(state.doc.content.size, pos + 100));

              if (shouldTriggerSuggestion(contextBefore, state.doc.textContent)) {
                onSuggestionRequest(state.doc.textContent, pos, contextBefore, contextAfter);
              }
            }, debounceMs);

            return false;
          },

          handleKeyDown(view, event) {
            const state = pluginKey.getState(view.state);

            if (!state?.suggestion) return false;

            const suggestion = state.suggestion;

            // Tab: Accept suggestion
            if (event.key === 'Tab' && !event.shiftKey) {
              event.preventDefault();

              const acceptedText = suggestion.alternatives[suggestion.currentIndex].text;

              // Insert text at position
              const tr = view.state.tr.insertText(acceptedText, suggestion.position);

              // Clear suggestion
              tr.setMeta(pluginKey, null);

              view.dispatch(tr);

              // Notify parent
              onSuggestionAccepted(suggestion, acceptedText);

              return true;
            }

            // Escape: Reject suggestion
            if (event.key === 'Escape') {
              event.preventDefault();

              // Clear suggestion
              view.dispatch(
                view.state.tr.setMeta(pluginKey, null)
              );

              // Notify parent
              onSuggestionRejected(suggestion);

              return true;
            }

            // Arrow Right: Cycle to next alternative
            if (event.key === 'ArrowRight' && suggestion.alternatives.length > 1) {
              event.preventDefault();

              const newIndex = (suggestion.currentIndex + 1) % suggestion.alternatives.length;
              const updatedSuggestion: CursorStyleSuggestion = {
                ...suggestion,
                currentIndex: newIndex
              };

              // Update decoration
              view.dispatch(
                view.state.tr.setMeta(pluginKey, updatedSuggestion)
              );

              // Notify parent
              onCycleAlternative(updatedSuggestion, newIndex);

              return true;
            }

            // Arrow Left: Cycle to previous alternative
            if (event.key === 'ArrowLeft' && suggestion.alternatives.length > 1) {
              event.preventDefault();

              const newIndex = suggestion.currentIndex === 0
                ? suggestion.alternatives.length - 1
                : suggestion.currentIndex - 1;

              const updatedSuggestion: CursorStyleSuggestion = {
                ...suggestion,
                currentIndex: newIndex
              };

              // Update decoration
              view.dispatch(
                view.state.tr.setMeta(pluginKey, updatedSuggestion)
              );

              // Notify parent
              onCycleAlternative(updatedSuggestion, newIndex);

              return true;
            }

            return false;
          }
        },

        view() {
          return {
            destroy() {
              if (debounceTimer) clearTimeout(debounceTimer);
            }
          };
        }
      })
    ];
  },

  // Manual trigger via Cmd+Space
  addKeyboardShortcuts() {
    return {
      'Mod-Space': () => {
        const { editor } = this;
        if (editor) {
          const pos = editor.state.selection.from;
          const contextBefore = editor.state.doc.textBetween(Math.max(0, pos - 100), pos);
          const contextAfter = editor.state.doc.textBetween(pos, Math.min(editor.state.doc.content.size, pos + 100));
          this.options.onSuggestionRequest(editor.state.doc.textContent, pos, contextBefore, contextAfter);
        }
        return true;
      }
    };
  },

  // Public methods to control suggestion from outside
  addCommands() {
    return {
      setSuggestion: (suggestion: CursorStyleSuggestion | null) => ({ tr, dispatch }) => {
        if (dispatch) {
          const pluginKey = new PluginKey<PluginState>('cursorStyleSuggestions');
          tr.setMeta(pluginKey, suggestion);
        }
        return true;
      },

      clearSuggestion: () => ({ tr, dispatch }) => {
        if (dispatch) {
          const pluginKey = new PluginKey<PluginState>('cursorStyleSuggestions');
          tr.setMeta(pluginKey, null);
        }
        return true;
      }
    };
  }
});
