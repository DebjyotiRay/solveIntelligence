// Consolidated type definitions for patent analysis

export interface PatentIssue {
  type: string;
  severity: 'high' | 'medium' | 'low';
  paragraph?: number;
  description: string;
  suggestion: string;
  target?: {
    text?: string; // Text to find and highlight
  };
  replacement?: {
    type: 'add' | 'replace' | 'insert';
    text: string; // Suggested replacement text
  };
}

// Cursor-style suggestion alternative
export interface SuggestionAlternative {
  text: string;
  confidence: number;
  reasoning: string;
}

// Single inline suggestion (old format, for backward compatibility)
export interface InlineSuggestion {
  suggested_text: string;
  reasoning?: string;
  [key: string]: unknown;
}

// Cursor-style suggestion response with multiple alternatives
export interface InlineSuggestionResponse {
  status: 'inline_suggestion';
  suggestion_id: string;
  position: number;  // Cursor position
  anchor_text: string;  // Last 50 chars before cursor (for validation)
  alternatives: SuggestionAlternative[];  // Array of alternatives to cycle through
  current_index: number;  // Which alternative is currently shown (0-indexed)
  type: 'completion' | 'improvement' | 'correction';
  reasoning: string;  // Overall reasoning for the suggestion

  // Legacy fields (for backward compatibility)
  original_text?: string;
  suggested_text?: string;
  confidence?: number;
}

export interface PanelSuggestion {
  issue: PatentIssue;
}

export interface AnalysisResult {
  status: 'analyzing' | 'complete' | 'error' | 'streaming';
  message?: string;
  analysis?: {
    issues: PatentIssue[];
  };
  total_issues?: number;
  overall_score?: number;
  agents_used?: string[];
  timestamp?: string;
  error?: string;
  raw_content?: string;
  parse_error?: string;
  // Multi-agent specific fields
  system_type?: string;
  workflow?: string;
  agents?: string[];
  memory_enabled?: boolean;
  orchestrator?: string;
  phase?: string;
  agent?: string;
}

export interface StreamUpdate {
  status: 'analyzing';
  phase?: string;
  agent?: string;
  message: string;
  system_type?: string;
  workflow?: string;
  agents?: string[];
  memory_enabled?: boolean;
  orchestrator?: string;
}
