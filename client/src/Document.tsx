import Editor from "./internal/Editor";
import { debounce } from "lodash";
import { useCallback } from "react";

export interface DocumentProps {
  onContentChange: (content: string) => void;
  content: string;
  onRequestSuggestions?: (content: string) => void;
}

export default function Document({ onContentChange, content, onRequestSuggestions }: DocumentProps) {
  // Debounce AI suggestion requests to avoid spamming
  const requestSuggestions = useCallback(
    debounce((content: string) => {
      if (onRequestSuggestions && content.trim().length > 50) {
        onRequestSuggestions(content);
      }
    }, 2000), // Wait 2 seconds after user stops typing
    [onRequestSuggestions]
  );

  const handleEditorChange = (content: string) => {
    onContentChange(content);

    // Automatically request AI suggestions after content changes
    requestSuggestions(content);
  };

  return (
    <div className="w-full h-full overflow-y-auto">
      <Editor handleEditorChange={handleEditorChange} content={content} />
    </div>
  );
}
