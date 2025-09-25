import { useEffect, useRef, useState } from 'react';

interface UseWebSocketReturn {
  isConnected: boolean;
  requestAISuggestions: (content: string) => void;
  aiSuggestions: string;
  isAnalyzing: boolean;
}

export const useSocket = (): UseWebSocketReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState<string>('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Initialize WebSocket connection
    const ws = new WebSocket('ws://localhost:8000/ws');
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected for AI suggestions');
      setIsConnected(true);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      setIsAnalyzing(false);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
      setIsAnalyzing(false);
    };

    ws.onmessage = (event) => {
      const chunk = event.data;
      console.log('Received AI chunk:', chunk.substring(0, 100) + '...');
      
      // Handle error messages
      if (chunk.startsWith('Error:')) {
        console.error('AI Error:', chunk);
        setIsAnalyzing(false);
        setAiSuggestions('Error processing request: ' + chunk);
        return;
      }

      // Handle empty content response
      if (chunk === 'No content to analyze') {
        setIsAnalyzing(false);
        setAiSuggestions('No content available for analysis.');
        return;
      }
      
      // Append chunk to suggestions for streaming effect
      setAiSuggestions(prev => prev + chunk);
    };

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const requestAISuggestions = (content: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected');
      setAiSuggestions('Connection error. Please refresh the page.');
      return;
    }

    console.log('Requesting AI suggestions via WebSocket');
    setIsAnalyzing(true);
    setAiSuggestions(''); // Clear previous suggestions
    
    // Send HTML content to WebSocket for AI processing
    wsRef.current.send(content);
  };

  return {
    isConnected,
    requestAISuggestions,
    aiSuggestions,
    isAnalyzing
  };
};
