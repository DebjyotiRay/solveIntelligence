import Editor from "./internal/Editor";
import { InlineSuggestion, PanelSuggestion } from "./types/PatentTypes";

export interface DocumentProps {
  onContentChange: (content: string) => void;
  content: string;
  documentId: number;
  versionNumber: number;
  // Inline suggestion props
  onInlineSuggestionRequest?: (content: string, pos: number, before: string, after: string) => void;
  pendingSuggestion?: InlineSuggestion | null;
  onAcceptSuggestion?: (suggestion: InlineSuggestion) => void;
  onRejectSuggestion?: () => void;
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
        activePanelSuggestion={activePanelSuggestion}
        onDismissPanelSuggestion={onDismissPanelSuggestion}
      />
    </div>
  );
}
