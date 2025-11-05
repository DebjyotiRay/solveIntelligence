/**
 * Cursor-Style Inline Suggestions - SIMPLIFIED VERSION
 *
 * This extension triggers suggestion requests and displays them as inline decorations.
 * Key features:
 * - Auto-triggers on typing (debounced)
 * - Shows ghost text inline (not overlay)
 * - Tab to accept, Esc to reject
 * - Arrow keys to cycle alternatives
 */

import { Extension } from '@tiptap/core';
import { Plugin, PluginKey, EditorState } from '@tiptap/pm/state';
import { Decoration, DecorationSet, EditorView } from '@tiptap/pm/view';

export interface SuggestionAlternative {
  text: string;
  confidence: number;
  reasoning: string;
}

export interface CursorStyleSuggestion {
  id: string;
  position: number;
  alternatives: SuggestionAlternative[];
  currentIndex: number;
  anchorText: string;
}

interface CursorStyleSuggestionsOptions {
  onSuggestionRequest: (content: string, pos: number, before: string, after: string, triggerType?: string) => void;
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

const pluginKey = new PluginKey<PluginState>('cursorStyleSuggestions');

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
    const { onSuggestionRequest, onSuggestionAccepted, onSuggestionRejected, onCycleAlternative, debounceMs, documentKey } = this.options;
    let debounceTimer: ReturnType<typeof setTimeout> | null = null;
    let currentDocKey: string | null = null;

    const shouldTriggerSuggestion = (before: string, content: string) => {
      if (content.trim().length < 10) return false;
      if (before.endsWith(' ')) return true;
      if (/[.!?]\s$/.test(before)) return true;
      if (/(shall|hereby|pursuant to|whereas)\s$/i.test(before)) return true;
      return false;
    };

    const createGhostTextWidget = (text: string, alternativeIndex: number, totalAlternatives: number) => {
      const wrapper = document.createElement('span');
      wrapper.className = 'cursor-ghost-text-wrapper';
      wrapper.style.position = 'relative';
      wrapper.style.display = 'inline';

      const ghostSpan = document.createElement('span');
      ghostSpan.className = 'cursor-ghost-text';
      ghostSpan.textContent = text;
      ghostSpan.style.color = 'rgba(128, 128, 128, 0.5)';
      ghostSpan.style.fontStyle = 'italic';
      ghostSpan.style.pointerEvents = 'none';
      ghostSpan.style.userSelect = 'none';

      const hint = document.createElement('span');
      hint.className = 'cursor-suggestion-hint';
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

      if (totalAlternatives > 1) {
        hint.innerHTML = `<kbd style="background: rgba(255,255,255,0.2); padding: 2px 6px; border-radius: 3px; margin: 0 2px;">Tab</kbd> accept <kbd style="background: rgba(255,255,255,0.2); padding: 2px 6px; border-radius: 3px; margin: 0 2px;">→</kbd> next (${alternativeIndex + 1}/${totalAlternatives}) <kbd style="background: rgba(255,255,255,0.2); padding: 2px 6px; border-radius: 3px; margin: 0 2px;">Esc</kbd> dismiss`;
      } else {
        hint.innerHTML = `<kbd style="background: rgba(255,255,255,0.2); padding: 2px 6px; border-radius: 3px; margin: 0 2px;">Tab</kbd> accept <kbd style="background: rgba(255,255,255,0.2); padding: 2px 6px; border-radius: 3px; margin: 0 2px;">Esc</kbd> dismiss`;
      }

      wrapper.appendChild(ghostSpan);
      wrapper.appendChild(hint);

      return wrapper;
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

          apply(tr, state): PluginState {
            // Check for meta updates (setting/clearing suggestion)
            const meta = tr.getMeta(pluginKey);
            if (meta !== undefined) {
              if (meta === null) {
                // Clear suggestion
                return {
                  suggestion: null,
                  decorations: DecorationSet.empty
                };
              } else {
                // Set new suggestion
                const suggestion = meta as CursorStyleSuggestion;
                const currentAlt = suggestion.alternatives[suggestion.currentIndex];
                const widget = createGhostTextWidget(
                  currentAlt.text,
                  suggestion.currentIndex,
                  suggestion.alternatives.length
                );

                const decoration = Decoration.widget(suggestion.position, widget, {
                  side: 1,
                  key: 'ghost-text'
                });

                return {
                  suggestion,
                  decorations: DecorationSet.create(tr.doc, [decoration])
                };
              }
            }

            // Map decorations through document changes
            if (state.suggestion) {
              return {
                ...state,
                decorations: state.decorations.map(tr.mapping, tr.doc)
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
              view.dispatch(view.state.tr.setMeta(pluginKey, null));
              return false;
            }

            // Clear existing timer
            if (debounceTimer) clearTimeout(debounceTimer);

            // Clear any existing suggestion when typing
            const currentState = pluginKey.getState(view.state);
            if (currentState?.suggestion) {
              view.dispatch(view.state.tr.setMeta(pluginKey, null));
            }

            // Set new timer
            debounceTimer = setTimeout(() => {
              const { state } = view;
              const pos = state.selection.from;
              const contextBefore = state.doc.textBetween(Math.max(0, pos - 100), pos);
              const contextAfter = state.doc.textBetween(pos, Math.min(state.doc.content.size, pos + 100));

              if (shouldTriggerSuggestion(contextBefore, state.doc.textContent)) {
                onSuggestionRequest(state.doc.textContent, pos, contextBefore, contextAfter, 'completion');
              }
            }, debounceMs);

            return false;
          },

          handleKeyDown(view, event) {
            const state = pluginKey.getState(view.state);
            if (!state?.suggestion) return false;

            const suggestion = state.suggestion;

            // Tab: Accept
            if (event.key === 'Tab' && !event.shiftKey) {
              event.preventDefault();
              const acceptedText = suggestion.alternatives[suggestion.currentIndex].text;
              const tr = view.state.tr.insertText(acceptedText, suggestion.position);
              tr.setMeta(pluginKey, null);
              view.dispatch(tr);
              onSuggestionAccepted(suggestion, acceptedText);
              return true;
            }

            // Escape: Reject
            if (event.key === 'Escape') {
              event.preventDefault();
              view.dispatch(view.state.tr.setMeta(pluginKey, null));
              onSuggestionRejected(suggestion);
              return true;
            }

            // Arrow Right: Next alternative
            if (event.key === 'ArrowRight' && suggestion.alternatives.length > 1) {
              event.preventDefault();
              const newIndex = (suggestion.currentIndex + 1) % suggestion.alternatives.length;
              const updatedSuggestion = { ...suggestion, currentIndex: newIndex };
              view.dispatch(view.state.tr.setMeta(pluginKey, updatedSuggestion));
              onCycleAlternative(updatedSuggestion, newIndex);
              return true;
            }

            // Arrow Left: Previous alternative
            if (event.key === 'ArrowLeft' && suggestion.alternatives.length > 1) {
              event.preventDefault();
              const newIndex = suggestion.currentIndex === 0
                ? suggestion.alternatives.length - 1
                : suggestion.currentIndex - 1;
              const updatedSuggestion = { ...suggestion, currentIndex: newIndex };
              view.dispatch(view.state.tr.setMeta(pluginKey, updatedSuggestion));
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

  addCommands() {
    return {
      setSuggestion: (suggestion: CursorStyleSuggestion | null) => ({ tr, dispatch }) => {
        if (dispatch) {
          tr.setMeta(pluginKey, suggestion);
        }
        return true;
      },

      clearSuggestion: () => ({ tr, dispatch }) => {
        if (dispatch) {
          tr.setMeta(pluginKey, null);
        }
        return true;
      }
    };
  }
});
