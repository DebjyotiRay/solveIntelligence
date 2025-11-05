import Editor from "./internal/Editor";
import { InlineSuggestionResponse, PanelSuggestion } from "./types/PatentTypes";
import { CursorStyleSuggestion } from "./extensions/CursorStyleSuggestions";

export interface DocumentProps {
  onContentChange: (content: string) => void;
  content: string;
  documentId: number;
  versionNumber: number;
  // Cursor-style inline suggestion props
  onInlineSuggestionRequest?: (content: string, pos: number, before: string, after: string) => void;
  pendingSuggestion?: InlineSuggestionResponse | null;
  onAcceptSuggestion?: (suggestion: CursorStyleSuggestion, acceptedText: string) => void;
  onRejectSuggestion?: (suggestion: CursorStyleSuggestion) => void;
  onCycleAlternative?: (suggestion: CursorStyleSuggestion, newIndex: number) => void;
  // Panel suggestion props - simplified to just show location
  activePanelSuggestion?: PanelSuggestion | null;
  onDismissPanelSuggestion?: () => void;
}

export default function Document({
  onContentChange,
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
}: DocumentProps) {
  const handleEditorChange = (content: string) => {
    onContentChange(content);
  };

  return (
    <div className="w-full h-full overflow-y-auto">
      <Editor
        handleEditorChange={handleEditorChange}
        content={content}
        documentId={documentId}
        versionNumber={versionNumber}
        onInlineSuggestionRequest={onInlineSuggestionRequest}
        pendingSuggestion={pendingSuggestion}
        onAcceptSuggestion={onAcceptSuggestion}
        onRejectSuggestion={onRejectSuggestion}
        onCycleAlternative={onCycleAlternative}
        activePanelSuggestion={activePanelSuggestion}
        onDismissPanelSuggestion={onDismissPanelSuggestion}
      />
    </div>
  );
}
