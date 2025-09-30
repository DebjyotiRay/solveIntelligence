import React, { useState, useEffect } from 'react';
import { generateSuggestionId } from '../utils/suggestionUtils';

interface PatentIssue {
  type: string;
  severity: 'high' | 'medium' | 'low';
  paragraph?: number;
  description: string;
  suggestion: string;
  // Enhanced for apply functionality
  target?: {
    text?: string;           // Specific text to find
    position?: number;       // Exact character position if known
    pattern?: string;        // Regex pattern to match
    context?: string;        // Surrounding context
  };
  replacement?: {
    type: 'add' | 'replace' | 'insert';
    text: string;           // What to add/replace with
    position?: 'before' | 'after' | 'replace';
  };
}

interface AnalysisResult {
  status: 'analyzing' | 'complete' | 'error';
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

interface StreamUpdate {
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

interface SuggestionsPanelProps {
  currentDocumentId: number;
  selectedVersionNumber: number;
  isConnected: boolean;
  isAnalyzing: boolean;
  analysisResult: AnalysisResult | null;
  currentPhase?: string;
  streamUpdates: StreamUpdate[];
  onApplySuggestion?: (issue: PatentIssue, index: number) => void;
  activeSuggestionId?: string;
  appliedSuggestionIds?: Set<string>;
  acceptedSuggestionIds?: Set<string>;
}

const SuggestionsPanel: React.FC<SuggestionsPanelProps> = ({
  currentDocumentId,
  selectedVersionNumber,
  isConnected,
  isAnalyzing,
  analysisResult,
  currentPhase,
  streamUpdates,
  onApplySuggestion,
  activeSuggestionId,
  appliedSuggestionIds = new Set(),
  acceptedSuggestionIds = new Set()
}) => {
  const [error, setError] = useState<string | null>(null);

  // Handle error detection from analysisResult
  useEffect(() => {
    if (analysisResult?.status === 'error') {
      setError(analysisResult.error || 'Unknown error occurred');
    } else {
      setError(null);
    }
  }, [analysisResult]);

  // Get severity color for badges
  const getSeverityColor = (severity: 'high' | 'medium' | 'low') => {
    switch (severity) {
      case 'high': return 'bg-red-100 text-red-800 border-red-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  // Group issues by severity
  const groupIssuesBySeverity = (issues: PatentIssue[]) => {
    return issues.reduce((acc, issue) => {
      if (!acc[issue.severity]) acc[issue.severity] = [];
      acc[issue.severity].push(issue);
      return acc;
    }, {} as Record<string, PatentIssue[]>);
  };

  // Filter out accepted suggestions from display, but keep original indices
  const allIssues = analysisResult?.analysis?.issues || [];
  const issuesWithOriginalIndex = allIssues
    .map((issue, originalIndex) => ({ issue, originalIndex }))
    .filter(({ issue, originalIndex }) => {
      const suggestionId = generateSuggestionId(issue, originalIndex);
      return !acceptedSuggestionIds.has(suggestionId);
    });
  
  const issues = issuesWithOriginalIndex.map(item => item.issue);
  const groupedIssues = groupIssuesBySeverity(issues);

  return (
    <div className="h-full flex flex-col bg-white border border-gray-300">
      {/* Professional Header */}
      <div className="flex-shrink-0 px-6 py-4 bg-slate-50 border-b border-gray-300">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-800">Document Analysis</h3>
            <p className="text-sm text-slate-600 mt-1">
              Patent {currentDocumentId} · Version {selectedVersionNumber}
            </p>
          </div>
          {/* Connection Status */}
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-600' : 'bg-red-600'}`}></div>
            <span className="text-xs text-slate-600 font-medium">
              {isConnected ? 'CONNECTED' : 'OFFLINE'}
            </span>
          </div>
        </div>

      </div>


      {/* Content Area - Now with proper height constraint and scrolling */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {/* Error State */}
        {error && (
          <div className="m-6 p-4 bg-red-50 border border-red-200 rounded">
            <div className="text-red-900 font-medium text-sm">Analysis Error</div>
            <div className="text-red-800 text-sm mt-1">{error}</div>
          </div>
        )}

        {/* Multi-Agent Progress Display */}
        {isAnalyzing && (
          <div className="m-6 space-y-4">
            {/* Multi-Agent System Header */}
            {analysisResult?.system_type && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center gap-3 mb-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-300 border-t-blue-600"></div>
                  <div className="text-blue-900 font-semibold text-sm">
                    🤖 {analysisResult.system_type.toUpperCase().replace('_', ' ')} ACTIVE
                  </div>
                </div>
                {analysisResult.workflow && (
                  <div className="text-blue-800 text-xs mb-2">
                    Workflow: {analysisResult.workflow}
                  </div>
                )}
                {analysisResult.orchestrator && (
                  <div className="text-blue-700 text-xs">
                    Orchestrator: {analysisResult.orchestrator}
                  </div>
                )}
              </div>
            )}

            {/* Current Phase Indicator */}
            {currentPhase && (
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                <div className="flex items-center gap-3">
                  <div className="animate-pulse w-2 h-2 rounded-full bg-orange-500"></div>
                  <div>
                    <div className="text-slate-800 font-medium text-sm">
                      Current Phase: {currentPhase.replace('_', ' ').toUpperCase()}
                    </div>
                    <div className="text-slate-600 text-xs">
                      {analysisResult?.message || 'Processing...'}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Stream Updates Log */}
            {streamUpdates.length > 0 && (
              <div className="bg-white border border-slate-200 rounded-lg">
                <div className="px-4 py-3 border-b border-slate-200">
                  <h5 className="text-slate-800 font-medium text-sm">Analysis Progress</h5>
                </div>
                <div className="max-h-48 overflow-y-auto">
                  {streamUpdates.slice(-10).map((update, index) => (
                    <div key={index} className="px-4 py-2 border-b border-slate-100 last:border-b-0">
                      <div className="flex items-center gap-2 mb-1">
                        {update.agent && (
                          <span className="px-2 py-1 text-xs font-medium bg-purple-100 text-purple-800 rounded">
                            {update.agent.toUpperCase()}
                          </span>
                        )}
                        {update.phase && (
                          <span className="text-xs text-slate-600">
                            {update.phase.replace('_', ' ')}
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-slate-700">
                        {update.message}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Fallback Basic Loading */}
            {!currentPhase && streamUpdates.length === 0 && (
              <div className="flex items-center gap-3 p-4 bg-slate-50 border border-slate-200 rounded">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-slate-300 border-t-slate-600"></div>
                <div>
                  <div className="text-slate-800 font-medium text-sm">Processing Document</div>
                  <div className="text-slate-600 text-xs">Analyzing content structure and compliance...</div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Structured Issues Display */}
        {analysisResult?.status === 'complete' && issues.length > 0 && (
          <div className="p-6">
            {/* Multi-Agent Results Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h4 className="text-lg font-bold text-slate-800">Multi-Agent Analysis Results</h4>
                {analysisResult.agents_used && (
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-slate-600">Analyzed by:</span>
                    {analysisResult.agents_used.map((agent, index) => (
                      <span key={index} className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded">
                        {agent.toUpperCase()}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className="text-right">
                <span className="text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded block mb-2">
                  {issues.length} {issues.length === 1 ? 'issue' : 'issues'} found
                </span>
                {analysisResult.overall_score !== undefined && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-600">Overall Score:</span>
                    <span className={`px-2 py-1 text-xs font-semibold rounded ${
                      analysisResult.overall_score >= 0.8 ? 'bg-green-100 text-green-800' :
                      analysisResult.overall_score >= 0.6 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {(analysisResult.overall_score * 100).toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Issues List */}
            <div className="space-y-4">
              {issuesWithOriginalIndex.map(({ issue, originalIndex }) => {
                const suggestionId = generateSuggestionId(issue, originalIndex);
                const isApplied = appliedSuggestionIds.has(suggestionId);
                const isActive = activeSuggestionId === suggestionId;
                
                return (
                  <div key={originalIndex} className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
                    {/* Issue Header */}
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-1 text-xs font-medium rounded border ${getSeverityColor(issue.severity)}`}>
                          {issue.severity.toUpperCase()}
                        </span>
                        <span className="text-sm text-slate-600 capitalize">
                          {issue.type}
                        </span>
                        {issue.paragraph && issue.paragraph > 0 && (
                          <span className="text-xs text-slate-500">
                            Paragraph {issue.paragraph}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Issue Description */}
                    <div className="mb-3">
                      <h5 className="text-sm font-medium text-slate-800 mb-2">Issue:</h5>
                      <p className="text-sm text-slate-700 leading-relaxed">{issue.description}</p>
                    </div>

                    {/* Suggestion */}
                    <div className="bg-blue-50 border border-blue-100 rounded p-3">
                      <div className="flex items-start justify-between mb-2">
                        <h5 className="text-sm font-medium text-blue-900">Suggestion:</h5>
                        
                        {onApplySuggestion && (
                          <div className="flex flex-col items-end gap-1">
                            {/* Apply Button States */}
                            {!isApplied && !isActive && (
                              <button
                                onClick={() => onApplySuggestion(issue, originalIndex)}
                                className="px-3 py-1 text-xs rounded transition-all font-medium bg-blue-600 text-white hover:bg-blue-700 border border-blue-600 hover:border-blue-700"
                                title="Apply this suggestion to the document"
                              >
                                Apply
                              </button>
                            )}
                            
                            {/* Applied State - Show instructions */}
                            {(isApplied || isActive) && (
                              <div className="text-right">
                                <div className="px-3 py-1 text-xs rounded bg-orange-100 text-orange-800 border border-orange-200 font-medium mb-1">
                                  Preview Active
                                </div>
                                <div className="text-xs text-slate-600">
                                  <kbd className="px-1 py-0.5 bg-slate-200 rounded text-xs">Tab</kbd> to accept • <kbd className="px-1 py-0.5 bg-slate-200 rounded text-xs">Esc</kbd> to cancel
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                      <p className="text-sm text-blue-800 leading-relaxed">{issue.suggestion}</p>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Summary */}
            <div className="mt-6 bg-slate-50 border border-slate-200 rounded-lg p-4">
              <h5 className="text-slate-800 font-medium text-sm mb-2">Analysis Summary</h5>
              <div className="flex gap-4 text-sm">
                {groupedIssues.high && (
                  <span className="text-red-700">
                    {groupedIssues.high.length} High Priority
                  </span>
                )}
                {groupedIssues.medium && (
                  <span className="text-yellow-700">
                    {groupedIssues.medium.length} Medium Priority
                  </span>
                )}
                {groupedIssues.low && (
                  <span className="text-green-700">
                    {groupedIssues.low.length} Low Priority
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* No Issues Found */}
        {analysisResult?.status === 'complete' && issues.length === 0 && (
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-100 flex items-center justify-center">
                <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-sm font-medium text-slate-800 mb-2">Analysis Complete</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                No issues found. The document appears to meet patent compliance standards.
              </p>
            </div>
          </div>
        )}

        {/* Professional Empty State */}
        {!analysisResult && !isAnalyzing && !error && (
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-100 flex items-center justify-center">
                <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} 
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-sm font-medium text-slate-800 mb-2">Ready for Analysis</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Click "AI Document Analysis" to begin comprehensive review of this patent document.
              </p>
            </div>
          </div>
        )}
      </div>

    </div>
  );
};

export default SuggestionsPanel;
