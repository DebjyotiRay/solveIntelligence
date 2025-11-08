import { Card, SectionTitle } from './ui';
import { AnalysisResult, PatentIssue, StreamUpdate } from '../types/PatentTypes';
import { AlertCircle, CheckCircle, Info, Sparkles } from 'lucide-react';

interface SuggestionsPanelProps {
  currentDocumentId: number;
  selectedVersionNumber: number;
  isConnected: boolean;
  isAnalyzing: boolean;
  analysisResult: AnalysisResult | null;
  currentPhase: string;
  streamUpdates: StreamUpdate[];
  onShowSuggestionLocation: (issue: PatentIssue) => void;
  activeSuggestion: PatentIssue | null;
}

export default function SuggestionsPanel({
  isAnalyzing,
  analysisResult,
  currentPhase,
  onShowSuggestionLocation,
  activeSuggestion
}: SuggestionsPanelProps) {
  const getSeverityIcon = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'error':
      case 'high':
        return <AlertCircle className="w-5 h-5 text-destructive" />;
      case 'warning':
      case 'medium':
        return <AlertCircle className="w-5 h-5 text-warning" />;
      case 'info':
      case 'low':
        return <Info className="w-5 h-5 text-primary" />;
      default:
        return <CheckCircle className="w-5 h-5 text-success" />;
    }
  };

  return (
    <div className="h-full flex flex-col bg-muted/30">
      <div className="p-6 border-b border-border bg-card">
        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-semibold text-foreground">AI Analysis</h2>
        </div>
        {isAnalyzing && (
          <div className="text-sm text-muted-foreground">
            {currentPhase || 'Analyzing document...'}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {isAnalyzing ? (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary/20 border-t-primary" />
              <p className="text-sm text-muted-foreground">Running AI analysis...</p>
            </div>
          </div>
        ) : analysisResult && analysisResult.issues.length > 0 ? (
          <div className="space-y-4">
            <SectionTitle>Found {analysisResult.issues.length} Issues</SectionTitle>
            {analysisResult.issues.map((issue, index) => (
              <Card
                key={index}
                className={`cursor-pointer transition-all hover-lift ${
                  activeSuggestion === issue ? 'ring-2 ring-primary' : ''
                }`}
                onClick={() => onShowSuggestionLocation(issue)}
              >
                <div className="flex gap-4">
                  <div className="flex-shrink-0">
                    {getSeverityIcon(issue.severity)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary">
                        {issue.issue_type}
                      </span>
                      <span className="text-xs text-muted-foreground capitalize">
                        {issue.severity}
                      </span>
                    </div>
                    <p className="text-sm text-foreground font-medium mb-2">
                      {issue.description}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {issue.suggestion}
                    </p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : analysisResult ? (
          <div className="text-center py-12">
            <CheckCircle className="w-16 h-16 mx-auto text-success mb-4" />
            <p className="text-sm text-muted-foreground">
              No issues found! Your document looks great.
            </p>
          </div>
        ) : (
          <div className="text-center py-12">
            <Sparkles className="w-16 h-16 mx-auto text-muted-foreground/50 mb-4" />
            <p className="text-sm text-muted-foreground">
              Click "Run AI Analysis" to analyze your document
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
