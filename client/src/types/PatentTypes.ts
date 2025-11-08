export interface PatentIssue {
  issue_type: string;
  severity: string;
  description: string;
  suggestion: string;
  location?: {
    start: number;
    end: number;
  };
  replacement?: {
    type: 'add' | 'replace' | 'insert';
    text: string; // Suggested replacement text
  };
}

export interface InlineSuggestion {
  suggested_text: string;
  reasoning?: string;
  [key: string]: unknown;
}

export interface InlineSuggestionResponse {
  status: 'inline_suggestion';
  suggestion_id: string;
  original_text: string;
  suggested_text: string;
  position: { from: number; to: number };
  confidence: number;
  reasoning: string;
  type: 'completion' | 'improvement' | 'correction';
  // 🚀 NEW: 3-tier memory grounding flags
  legal_grounded?: boolean;   // Level 1: Legal knowledge (1634 Indian laws)
  firm_grounded?: boolean;     // Level 2: Firm knowledge (successful patents, style)
  client_grounded?: boolean;   // Level 3: Client history (personalized learning)
}

export interface PanelSuggestion {
  issue: PatentIssue;
}

export interface InlineSuggestionResponse {
  original_text: string;
  suggested_text: string;
  reason: string;
}

export interface AnalysisResult {
  document_id: number;
  version_number: number;
  issues: PatentIssue[];
  summary?: string;
}

export interface StreamUpdate {
  phase?: string;
  content?: string;
  issue?: PatentIssue;
}
