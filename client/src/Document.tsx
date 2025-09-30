import Editor from "./internal/Editor";
import { debounce } from "lodash";
import { useCallback } from "react";

interface PanelSuggestion {
  issue: {
    type: string;
    severity: 'high' | 'medium' | 'low';
    paragraph?: number;
    description: string;
    suggestion: string;
  };
  position: number;
  originalText: string;
  replacementText: string;
  type: 'add' | 'replace' | 'insert';
}

export interface DocumentProps {
  onContentChange: (content: string) => void;
  content: string;
  // onRequestSuggestions removed - no auto-analysis
  // Inline suggestion props
  onInlineSuggestionRequest?: (content: string, pos: number, before: string, after: string) => void;
  pendingSuggestion?: any;
  onAcceptSuggestion?: (suggestion: any) => void;
  onRejectSuggestion?: () => void;
  // Panel suggestion props
  activePanelSuggestion?: PanelSuggestion | null;
  onAcceptPanelSuggestion?: () => void;
  onRejectPanelSuggestion?: () => void;
}

export default function Document({
  onContentChange,
  content,
  onInlineSuggestionRequest,
  pendingSuggestion,
  onAcceptSuggestion,
  onRejectSuggestion,
  activePanelSuggestion,
  onAcceptPanelSuggestion,
  onRejectPanelSuggestion
}: DocumentProps) {
  // No auto-analysis - only manual triggering

  const handleEditorChange = (content: string) => {
    onContentChange(content);
    // No auto-analysis - only inline suggestions work automatically
  };

  return (
    <div className="w-full h-full overflow-y-auto">
      <Editor
        handleEditorChange={handleEditorChange}
        content={content}
        onInlineSuggestionRequest={onInlineSuggestionRequest}
        pendingSuggestion={pendingSuggestion}
        onAcceptSuggestion={onAcceptSuggestion}
        onRejectSuggestion={onRejectSuggestion}
        activePanelSuggestion={activePanelSuggestion}
        onAcceptPanelSuggestion={onAcceptPanelSuggestion}
        onRejectPanelSuggestion={onRejectPanelSuggestion}
      />
    </div>
  );
}
