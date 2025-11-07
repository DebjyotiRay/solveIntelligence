import { useEffect, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Collaboration from "@tiptap/extension-collaboration";
import CollaborationCursor from "@tiptap/extension-collaboration-cursor";
import * as Y from "yjs";
import { HocuspocusProvider } from '@hocuspocus/provider'

export interface SimpleEditorProps {
  documentId: number;
  versionNumber: number;
}

export default function SimpleEditor({ documentId, versionNumber }: SimpleEditorProps) {
  const [ydoc] = useState(() => new Y.Doc());
  const [provider] = useState(() => {
    const roomName = `document-${documentId}-v${versionNumber}`;
    console.log('Creating Hocuspocus provider for room:', roomName);
    
    const prov = new HocuspocusProvider({
      url: 'ws://localhost:1234',
      name: roomName,
      document: ydoc,
    });

    console.log('Provider created');
    
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
    ],
    content: '<p>Test collaboration with Hocuspocus!</p>',
  });

  useEffect(() => {
    return () => {
      provider?.destroy();
    };
  }, [provider]);

  return <div className="p-4"><EditorContent editor={editor} /></div>;
}
