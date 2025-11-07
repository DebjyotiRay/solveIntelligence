import { Extension } from '@tiptap/core';
import { Plugin, PluginKey, EditorState } from '@tiptap/pm/state';

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
    let lastDocContent = '';

    // Improved trigger logic with multiple conditions
    const shouldTriggerSuggestion = (before: string, content: string) => {
      console.log('🔍 shouldTriggerSuggestion called:', {
        content_length: content.trim().length,
        before_last_20_chars: before.slice(-20),
        ends_with_space: before.endsWith(' '),
        ends_with_punct_space: /[.!?]\s$/.test(before),
        ends_with_patent_keyword: /(comprising|wherein|characterized by|including)\s$/i.test(before)
      });
      
      if (content.trim().length < 10) {
        console.log('❌ Content too short:', content.trim().length);
        return false;
      }
      
      // Trigger after space
      if (before.endsWith(' ')) {
        console.log('✅ Triggering: ends with space');
        return true;
      }
      
      // Trigger after punctuation + space
      if (/[.!?]\s$/.test(before)) {
        console.log('✅ Triggering: ends with punctuation + space');
        return true;
      }
      
      // Trigger after patent keywords
      if (/(comprising|wherein|characterized by|including)\s$/i.test(before)) {
        console.log('✅ Triggering: ends with patent keyword');
        return true;
      }
      
      console.log('❌ No trigger conditions met');
      return false;
    };

    const handleContentChange = (state: EditorState) => {
      console.log('📝 InlineSuggestions: handleContentChange called');
      
      // Reset suggestions on document/version change
      const newDocKey = documentKey || '';
      if (newDocKey !== currentDocKey) {
        console.log('🔄 Document key changed:', { old: currentDocKey, new: newDocKey });
        currentDocKey = newDocKey;
        lastDocContent = '';
        if (debounceTimer) clearTimeout(debounceTimer);
        return;
      }

      const currentContent = state.doc.textContent;
      
      console.log('📄 Content check:', {
        current_length: currentContent.length,
        last_length: lastDocContent.length,
        changed: currentContent !== lastDocContent,
        current_last_50: currentContent.slice(-50)
      });
      
      // Only trigger if content actually changed
      if (currentContent === lastDocContent) {
        console.log('⏭️ Content unchanged, skipping');
        return;
      }
      lastDocContent = currentContent;

      if (debounceTimer) {
        console.log('⏱️ Clearing existing debounce timer');
        clearTimeout(debounceTimer);
      }

      console.log(`⏱️ Setting debounce timer for ${debounceMs}ms`);
      debounceTimer = setTimeout(() => {
        console.log('⏰ Debounce timer fired!');
        const pos = state.selection.from;
        const contextBefore = state.doc.textBetween(Math.max(0, pos - 100), pos);
        const contextAfter = state.doc.textBetween(pos, Math.min(state.doc.content.size, pos + 100));

        console.log('📍 Context extracted:', {
          pos,
          contextBefore_length: contextBefore.length,
          contextBefore_last_50: contextBefore.slice(-50),
          contextAfter_length: contextAfter.length,
          contextAfter_first_50: contextAfter.slice(0, 50)
        });

        if (shouldTriggerSuggestion(contextBefore, currentContent)) {
          console.log('🚀 Calling onSuggestionRequest with:', {
            content_length: currentContent.length,
            pos,
            triggerType: 'completion'
          });
          onSuggestionRequest(currentContent, pos, contextBefore, contextAfter, 'completion');
        } else {
          console.log('🚫 shouldTriggerSuggestion returned false, not calling onSuggestionRequest');
        }
      }, debounceMs);
    };

    return [
      new Plugin({
        key: new PluginKey('inlineSuggestions'),

        // Use appendTransaction instead of view().update() for better compatibility with Collaboration
        appendTransaction: (transactions, oldState, newState) => {
          // With Yjs/Collaboration, tr.docChanged might not be set, so we need to compare content directly
          const oldContent = oldState.doc.textContent;
          const newContent = newState.doc.textContent;
          const contentActuallyChanged = oldContent !== newContent;
          
          console.log('🔄 appendTransaction called:', {
            transactionCount: transactions.length,
            tr_docChanged: transactions.some(tr => tr.docChanged),
            contentActuallyChanged,
            oldContent_length: oldContent.length,
            newContent_length: newContent.length,
            oldContent_last_50: oldContent.slice(-50),
            newContent_last_50: newContent.slice(-50)
          });
          
          // Check if document content actually changed by comparing content
          if (contentActuallyChanged) {
            console.log('✅ Document content changed, triggering handleContentChange');
            handleContentChange(newState);
          } else {
            console.log('⏭️ No content changes detected');
          }
          
          // Return null to not modify the transaction
          return null;
        },

        destroy() {
          console.log('🧹 InlineSuggestions plugin destroyed');
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
