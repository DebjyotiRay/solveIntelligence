import React, { useState, useEffect } from 'react';

interface SuggestionsPanelProps {
  currentDocumentId: number;
  selectedVersionNumber: number;
  isConnected: boolean;
  isAnalyzing: boolean;
  aiSuggestions: string;
}

interface ParsedSection {
  title: string;
  content: string;
  type: 'summary' | 'issues' | 'recommendations' | 'technical' | 'legal' | 'general';
  priority?: 'high' | 'medium' | 'low';
}

const SuggestionsPanel: React.FC<SuggestionsPanelProps> = ({
  currentDocumentId,
  selectedVersionNumber,
  isConnected,
  isAnalyzing,
  aiSuggestions
}) => {
  const [error, setError] = useState<string | null>(null);

  // Handle error detection from aiSuggestions
  useEffect(() => {
    if (aiSuggestions.startsWith('Error:') || aiSuggestions.includes('Connection error')) {
      setError(aiSuggestions);
    } else {
      setError(null);
    }
  }, [aiSuggestions]);

  // Smart AI response formatting - handles ANY response format
  const formatAIResponse = (content: string) => {
    if (!content || content.length < 10) return null;

    // Split into paragraphs and clean up
    const paragraphs = content
      .split('\n\n')
      .map(p => p.trim())
      .filter(p => p.length > 0);

    // If only one paragraph, split by sentences for better readability
    if (paragraphs.length === 1) {
      const sentences = content.split(/(?<=[.!?])\s+/).filter(s => s.trim().length > 0);
      if (sentences.length > 3) {
        return sentences;
      }
    }

    return paragraphs;
  };

  // Detect if content has bullet points or lists
  const hasList = (content: string) => {
    return content.match(/^\s*[\-\*\•]\s+/m) || content.match(/^\s*\d+\.\s+/m);
  };

  // Format lists properly
  const formatList = (content: string) => {
    return content
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0);
  };

  const formattedContent = aiSuggestions && !isAnalyzing ? formatAIResponse(aiSuggestions) : null;

  return (
    <div className="h-full flex flex-col bg-white border border-gray-300">
      {/* Professional Header */}
      <div className="px-6 py-4 bg-slate-50 border-b border-gray-300">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-800">Document Analysis</h3>
            <p className="text-sm text-slate-600 mt-1">
              Patent {currentDocumentId} · Version {selectedVersionNumber}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-600' : 'bg-red-600'}`}></div>
            <span className="text-xs text-slate-600 font-medium">
              {isConnected ? 'CONNECTED' : 'OFFLINE'}
            </span>
          </div>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto">
        {/* Error State */}
        {error && (
          <div className="m-6 p-4 bg-red-50 border border-red-200 rounded">
            <div className="text-red-900 font-medium text-sm">Analysis Error</div>
            <div className="text-red-800 text-sm mt-1">{error}</div>
          </div>
        )}

        {/* Loading State */}
        {isAnalyzing && (
          <div className="m-6">
            <div className="flex items-center gap-3 p-4 bg-slate-50 border border-slate-200 rounded">
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-slate-300 border-t-slate-600"></div>
              <div>
                <div className="text-slate-800 font-medium text-sm">Processing Document</div>
                <div className="text-slate-600 text-xs">Analyzing content structure and compliance...</div>
              </div>
            </div>

            {/* Live streaming preview for professional look */}
            {aiSuggestions && (
              <div className="mt-4 p-4 bg-white border border-slate-200 rounded">
                <div className="text-xs text-slate-500 mb-2 uppercase tracking-wide">Live Analysis</div>
                <div className="text-sm text-slate-700 max-h-40 overflow-y-auto font-mono leading-relaxed">
                  {aiSuggestions}
                  <span className="animate-pulse text-slate-400">|</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Clean AI Response Display - Handles ANY Format */}
        {formattedContent && !isAnalyzing && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h4 className="text-lg font-bold text-slate-800">Analysis Results</h4>
              <span className="text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded">
                {new Date().toLocaleString()}
              </span>
            </div>

            {/* Simple, Clean Display */}
            <div className="bg-white border border-slate-200 rounded-lg shadow-sm">
              <div className="p-6 space-y-4">
                {hasList(aiSuggestions) ? (
                  /* Handle Lists */
                  <div className="space-y-2">
                    {formatList(aiSuggestions).map((item, index) => (
                      <div key={index} className="flex items-start gap-3">
                        <div className="w-2 h-2 rounded-full bg-blue-500 mt-2 flex-shrink-0"></div>
                        <div className="text-slate-700 leading-relaxed">{item}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  /* Handle Paragraphs */
                  <div className="space-y-4">
                    {formattedContent.map((paragraph, index) => (
                      <div key={index} className="text-slate-700 leading-relaxed text-base">
                        {paragraph}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* AI Insights Summary Box */}
            <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h5 className="text-blue-900 font-medium text-sm mb-2">AI Analysis Complete</h5>
              <p className="text-blue-800 text-sm">
                {formattedContent.length} key {formattedContent.length === 1 ? 'insight' : 'insights'} identified from document analysis
              </p>
            </div>
          </div>
        )}

        {/* Professional Empty State */}
        {!aiSuggestions && !isAnalyzing && !error && (
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
