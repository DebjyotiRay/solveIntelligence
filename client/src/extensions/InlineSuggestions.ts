import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';

interface InlineSuggestionsOptions {
  onSuggestionRequest: (content: string, pos: number, before: string, after: string, triggerType?: string) => void;
  debounceMs: number;
  documentKey?: string; // Track document+version for state reset
}

export const InlineSuggestions = Extension.create<InlineSuggestionsOptions>({
  name: 'inlineSuggestions',

  addOptions() {
    return {
      onSuggestionRequest: () => {},
      debounceMs: 1500,
    };
  },


  addProseMirrorPlugins() {
    const { onSuggestionRequest, debounceMs, documentKey } = this.options;
    let debounceTimer: ReturnType<typeof setTimeout> | null = null;
    let currentDocKey: string | null = null;

    // Improved trigger logic with multiple conditions
    const shouldTriggerSuggestion = (before: string, content: string) => {
      if (content.trim().length < 10) return false;
      
      // Trigger after space
      if (before.endsWith(' ')) return true;
      
      // Trigger after punctuation + space
      if (/[.!?]\s$/.test(before)) return true;
      
      // Trigger after patent keywords
      if (/(comprising|wherein|characterized by|including)\s$/i.test(before)) return true;
      
      return false;
    };

    return [
      new Plugin({
        key: new PluginKey('inlineSuggestions'),

        props: {
          handleTextInput(view) {
            // Reset suggestions on document/version change
            const newDocKey = documentKey || '';
            if (newDocKey !== currentDocKey) {
              currentDocKey = newDocKey;
              if (debounceTimer) clearTimeout(debounceTimer);
              return false;
            }

            if (debounceTimer) clearTimeout(debounceTimer);

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
          }
        },

        destroy() {
          if (debounceTimer) clearTimeout(debounceTimer);
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
