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
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';

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
      // SIMPLIFIED VERSION - Just ghost text, no fancy tooltip
      const ghostSpan = document.createElement('span');
      ghostSpan.className = 'cursor-ghost-text';
      ghostSpan.textContent = text;

      // CRITICAL: Force inline styles to override any CSS
      ghostSpan.style.cssText = `
        color: rgba(128, 128, 128, 0.6) !important;
        font-style: italic !important;
        pointer-events: none !important;
        user-select: none !important;
        background: rgba(255, 255, 0, 0.1) !important;
        padding: 2px 4px !important;
        border-radius: 3px !important;
        display: inline !important;
        font-size: inherit !important;
        font-family: inherit !important;
        line-height: inherit !important;
      `;

      // Add counter badge if multiple alternatives
      if (totalAlternatives > 1) {
        ghostSpan.setAttribute('data-alt-count', `${alternativeIndex + 1}/${totalAlternatives}`);
        ghostSpan.title = `Press → for next alternative (${alternativeIndex + 1}/${totalAlternatives}). Tab to accept, Esc to dismiss.`;
      } else {
        ghostSpan.title = 'Press Tab to accept, Esc to dismiss';
      }

      console.log('🎨 Created ghost text widget:', {
        text: text.substring(0, 30),
        visible: ghostSpan.style.display !== 'none',
        color: ghostSpan.style.color
      });

      return ghostSpan;
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
                console.log('🧹 Clearing suggestion from plugin state');
                return {
                  suggestion: null,
                  decorations: DecorationSet.empty
                };
              } else {
                // Set new suggestion
                const suggestion = meta as CursorStyleSuggestion;
                const currentAlt = suggestion.alternatives[suggestion.currentIndex];

                console.log('🎨 Creating decoration widget for:', {
                  text: currentAlt.text.substring(0, 50),
                  position: suggestion.position,
                  alternativeIndex: suggestion.currentIndex,
                  totalAlternatives: suggestion.alternatives.length
                });

                const widget = createGhostTextWidget(
                  currentAlt.text,
                  suggestion.currentIndex,
                  suggestion.alternatives.length
                );

                const decoration = Decoration.widget(suggestion.position, widget, {
                  side: 1,
                  key: 'ghost-text'
                });

                console.log('✅ Decoration created, adding to DecorationSet');

                const decorations = DecorationSet.create(tr.doc, [decoration]);
                console.log('✅ DecorationSet created with', decorations.find().length, 'decorations');

                return {
                  suggestion,
                  decorations
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
  }
});
