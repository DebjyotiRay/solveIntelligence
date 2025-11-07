import Editor from "./internal/Editor";
import { InlineSuggestionResponse, PanelSuggestion, PatentIssue } from "./types/PatentTypes";

interface CollaborationUser {
  name: string;
  color: string;
}

export interface DocumentProps {
  onContentChange: (content: string) => void;
  content: string;
  documentId: number;
  versionNumber: number;
  // Inline suggestion props
  onInlineSuggestionRequest?: (content: string, pos: number, before: string, after: string) => void;
  pendingSuggestion?: InlineSuggestionResponse | null;
  onAcceptSuggestion?: (suggestion: InlineSuggestionResponse) => void;
  onRejectSuggestion?: () => void;
  // Panel suggestion props - simplified to just show location
  activePanelSuggestion?: PanelSuggestion | null;
  onDismissPanelSuggestion?: () => void;
  // Fix application props
  issueToApply?: PatentIssue | null;
  onFixApplied?: () => void;
  // Online users callback
  onOnlineUsersChange?: (count: number, users: CollaborationUser[], selfUser?: CollaborationUser) => void;
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
  onDismissPanelSuggestion,
  issueToApply,
  onFixApplied,
  onOnlineUsersChange
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
        issueToApply={issueToApply}
        onFixApplied={onFixApplied}
        onOnlineUsersChange={onOnlineUsersChange}
      />
    </div>
  );
}
