import { useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import {
  AnalysisResult,
  StreamUpdate,
  InlineSuggestionResponse
} from '../types/PatentTypes';
import type { CursorStyleSuggestion } from '../extensions/CursorStyleSuggestions';

type WebSocketResponse = AnalysisResult | InlineSuggestionResponse;

interface UseWebSocketReturn {
  isConnected: boolean;
  requestAISuggestions: (content: string) => void;
  analysisResult: AnalysisResult | null;
  isAnalyzing: boolean;
  currentPhase?: string;
  streamUpdates: StreamUpdate[];
  requestInlineSuggestion: (content: string, cursorPos: number, contextBefore: string, contextAfter: string, triggerType?: string, type?: 'completion' | 'improvement' | 'correction') => void;
  pendingSuggestion: InlineSuggestionResponse | null;
  acceptInlineSuggestion: (suggestion: CursorStyleSuggestion, acceptedText: string) => void;
  rejectInlineSuggestion: (suggestion: CursorStyleSuggestion) => void;
  cycleInlineSuggestion: (suggestion: CursorStyleSuggestion, newIndex: number) => void;
  clearPendingSuggestion: () => void;
}

export const useSocket = (): UseWebSocketReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<string | undefined>(undefined);
  const [streamUpdates, setStreamUpdates] = useState<StreamUpdate[]>([]);
  const [pendingSuggestion, setPendingSuggestion] = useState<InlineSuggestionResponse | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let reconnectTimeout: number | null = null;
    
    const connectWebSocket = () => {
      console.log('🔌 Attempting WebSocket connection...');
      const ws = new WebSocket('ws://localhost:8000/ws');
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('✅ WebSocket connected for AI suggestions');
        setIsConnected(true);
        // Clear any pending reconnection attempts
        if (reconnectTimeout) {
          clearTimeout(reconnectTimeout);
          reconnectTimeout = null;
        }
      };

      ws.onclose = (event) => {
        console.log('❌ WebSocket disconnected', event.code, event.reason);
        setIsConnected(false);
        setIsAnalyzing(false);
        
        // Auto-reconnect after 1 second if not manually closed
        if (event.code !== 1000 && !reconnectTimeout) {
          console.log('🔄 Scheduling WebSocket reconnection...');
          reconnectTimeout = setTimeout(() => {
            reconnectTimeout = null;
            connectWebSocket();
          }, 1000);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        setIsConnected(false);
        setIsAnalyzing(false);
      };

    ws.onmessage = (event) => {
      console.log('📨 Raw WebSocket message received:', event.data);
      try {
        const response: WebSocketResponse = JSON.parse(event.data);
        console.log('🔍 Parsed message:', {
          status: response.status,
          phase: 'phase' in response ? response.phase : undefined,
          agent: 'agent' in response ? response.agent : undefined,
          system_type: 'system_type' in response ? response.system_type : undefined,
          issues_count: 'analysis' in response ? response.analysis?.issues?.length : undefined,
          suggested_text: 'suggested_text' in response ? response.suggested_text : undefined,
          message: 'message' in response ? response.message?.substring(0, 100) : undefined
        });
        
        if (response.status === 'analyzing') {
          console.log('🔄 Processing analyzing message - Phase:', response.phase, 'Agent:', response.agent);
          
          // Use flushSync for immediate UI updates to prevent React batching delays
          flushSync(() => {
            // Handle streaming updates
            setIsAnalyzing(true);
            
            // Update current phase if provided
            if (response.phase) {
              console.log('📍 Setting current phase:', response.phase);
              setCurrentPhase(response.phase);
            }
            
            // Add to stream updates for progress display - ALWAYS add if message exists
            if (response.message) {
              const streamUpdate: StreamUpdate = {
                status: 'analyzing',
                phase: response.phase,
                agent: response.agent,
                message: response.message || '',
                system_type: response.system_type,
                workflow: response.workflow,
                agents: response.agents,
                memory_enabled: response.memory_enabled,
                orchestrator: response.orchestrator
              };
              
              console.log('📋 Adding stream update:', streamUpdate);
              setStreamUpdates(prev => {
                const newUpdates = [...prev, streamUpdate];
                console.log('📋 Total stream updates now:', newUpdates.length);
                return newUpdates;
              });
            } else {
              console.log('⚠️ Analyzing message has no message content - skipping stream update');
            }
            
            // Keep the latest analyzing message as the current result
            setAnalysisResult(response);
            console.log('📊 Updated analysis result with analyzing status');
          });
          
        } else if (response.status === 'complete') {
          // Handle final results
          console.log('✅ Processing complete message - Issues:', response.total_issues);
          setIsAnalyzing(false);
          setAnalysisResult(response);
          console.log('✅ Multi-agent analysis complete:', {
            total_issues: response.total_issues,
            overall_score: response.overall_score,
            agents_used: response.agents_used
          });

        } else if (response.status === 'inline_suggestion') {
          // Handle inline suggestions
          const suggestion = response as InlineSuggestionResponse;
          setPendingSuggestion(suggestion);

        } else if (response.status === 'error') {
          // Handle errors
          console.log('❌ Processing error message:', response.error);
          setIsAnalyzing(false);
          setAnalysisResult(response);
          console.error('❌ Multi-agent analysis error:', response.error);
        } else if (response.status === 'streaming') {
          // Handle legacy streaming messages
          const streamingResponse = response as AnalysisResult & { message: string }; // Type assertion for legacy messages
          console.log('🔄 Processing legacy streaming message:', streamingResponse.message);
          const streamUpdate: StreamUpdate = {
            status: 'analyzing',
            message: streamingResponse.message || 'Processing...'
          };
          setStreamUpdates(prev => [...prev, streamUpdate]);
        } else {
          console.log('⚠️ Unknown message status:', response.status);
        }
        
      } catch (error) {
        // Handle legacy text messages or malformed JSON
        console.warn('❌ Failed to parse WebSocket message as JSON:', error);
        console.warn('❌ Raw message was:', event.data?.substring(0, 200));
        setIsAnalyzing(false);
        setAnalysisResult({
          status: 'error',
          error: 'Received malformed response from server',
          raw_content: event.data
        });
      }
    };

      return ws;
    };

    // Initialize connection
    connectWebSocket();

    // Cleanup on unmount
    return () => {
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting'); // Normal closure
      }
    };
  }, []);

  const requestAISuggestions = (content: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected');
      setAnalysisResult({
        status: 'error',
        error: 'Connection error. Please refresh the page.'
      });
      return;
    }

    console.log('Requesting AI suggestions via WebSocket');
    setIsAnalyzing(true);
    setAnalysisResult(null); // Clear previous results
    setStreamUpdates([]); // Clear previous stream updates
    setCurrentPhase(undefined); // Clear previous phase
    
    // Send HTML content to WebSocket for AI processing
    wsRef.current.send(content);
  };

  const requestInlineSuggestion = (
    content: string,
    cursorPos: number,
    contextBefore: string,
    contextAfter: string,
    triggerType?: string,
    type: 'completion' | 'improvement' | 'correction' = 'completion'
  ) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected for inline suggestions');
      return;
    }

    console.log('💡 Requesting inline AI suggestion...');

    wsRef.current.send(JSON.stringify({
      type: 'inline_suggestion',
      content: content,
      cursor_position: cursorPos,
      context_before: contextBefore,
      context_after: contextAfter,
      suggestion_type: type,
      trigger_type: triggerType
    }));
  };

  const acceptInlineSuggestion = (suggestion: CursorStyleSuggestion, acceptedText: string) => {
    console.log('✅ Accepting inline suggestion:', acceptedText);
    setPendingSuggestion(null);

    // TODO: Send feedback to backend for memory/learning
    // wsRef.current?.send(JSON.stringify({
    //   type: 'suggestion_feedback',
    //   suggestion_id: suggestion.id,
    //   action: 'accepted',
    //   accepted_text: acceptedText
    // }));
  };

  const rejectInlineSuggestion = (suggestion: CursorStyleSuggestion) => {
    console.log('❌ Rejecting inline suggestion:', suggestion.id);
    setPendingSuggestion(null);

    // TODO: Send feedback to backend for memory/learning
    // wsRef.current?.send(JSON.stringify({
    //   type: 'suggestion_feedback',
    //   suggestion_id: suggestion.id,
    //   action: 'rejected'
    // }));
  };

  const cycleInlineSuggestion = (suggestion: CursorStyleSuggestion, newIndex: number) => {
    console.log(`🔄 Cycled to alternative ${newIndex + 1}/${suggestion.alternatives.length}`);
    // Cycling is handled in the editor extension, no need to update state here
    // Just log for analytics/debugging
  };

  const clearPendingSuggestion = () => {
    console.log('🧹 Clearing pending inline suggestion');
    setPendingSuggestion(null);
  };

  return {
    isConnected,
    requestAISuggestions,
    analysisResult,
    isAnalyzing,
    currentPhase,
    streamUpdates,
    requestInlineSuggestion,
    pendingSuggestion,
    acceptInlineSuggestion,
    rejectInlineSuggestion,
    cycleInlineSuggestion,
    clearPendingSuggestion
  };
};
