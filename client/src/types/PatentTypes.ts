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
