import React, { useState, useRef, useEffect } from 'react';
import './ChatPanel.css';
import { AnalysisResult } from '../types/PatentTypes';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatSource[];
}

interface ChatSource {
  id: number;
  citation: string;
  content: string;
  tier: string;
}

interface ChatPanelProps {
  documentId?: number;
  clientId: string;
  documentContent?: string;
  analysisResult?: AnalysisResult | null;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  documentId,
  clientId,
  documentContent,
  analysisResult
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: inputMessage
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: inputMessage,
          client_id: clientId,
          document_id: documentId,
          conversation_history: messages.map(m => ({
            role: m.role,
            content: m.content
          })),
          document_context: documentContent,
          analysis_results: analysisResult  // Pass analysis results to backend
        })
      });

      if (!response.ok) {
        throw new Error('Chat request failed');
      }

      const data = await response.json();

      console.log('📥 Chat response received:', {
        response_length: data.response?.length,
        sources_count: data.sources?.length,
        sources: data.sources
      });

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: data.response,
        sources: data.sources
      };

      console.log('💬 Assistant message with sources:', {
        has_sources: !!assistantMessage.sources,
        sources_count: assistantMessage.sources?.length
      });

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.'
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      {/* Floating chat button */}
      {!isOpen && (
        <button
          className="chat-toggle-btn"
          onClick={() => setIsOpen(true)}
          title="Chat with AI"
        >
          💬
        </button>
      )}

      {/* Chat panel */}
      {isOpen && (
        <div className="chat-panel">
          <div className="chat-header">
            <h3>AI Assistant</h3>
            <button
              className="chat-close-btn"
              onClick={() => setIsOpen(false)}
            >
              ✕
            </button>
          </div>

          {/* Analysis Context Indicator */}
          {analysisResult && analysisResult.status === 'complete' && (
            <div className="chat-context-banner">
              <span className="context-icon">🎯</span>
              <span className="context-text">
                Analysis context loaded: {analysisResult.total_issues || 0} issues found
              </span>
            </div>
          )}

          <div className="chat-messages">
            {messages.length === 0 && (
              <div className="chat-welcome">
                <p>👋 Hi! I'm your AI assistant.</p>
                <p>Ask me about:</p>
                <ul>
                  {analysisResult && analysisResult.status === 'complete' && (
                    <li><strong>Analysis results & issues</strong></li>
                  )}
                  <li>Why suggestions were made</li>
                  <li>Patent law questions</li>
                  <li>Document clarifications</li>
                </ul>
              </div>
            )}

            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`chat-message ${msg.role}`}
              >
                <div className="message-content">
                  {msg.content}
                </div>

                {msg.sources && msg.sources.length > 0 && (
                  <div className="message-sources">
                    <details open>
                      <summary>
                        📚 {msg.sources.length} source{msg.sources.length !== 1 ? 's' : ''} used
                      </summary>
                      <div className="sources-list">
                        {msg.sources.map(src => (
                          <div key={src.id} className="source-item">
                            <span className="source-id">[{src.id}]</span>
                            <div className="source-info">
                              <div className="source-citation">{src.citation}</div>
                              <div className="source-preview">{src.content?.substring(0, 100)}...</div>
                            </div>
                            <span className={`source-tier tier-${src.tier}`}>{src.tier}</span>
                          </div>
                        ))}
                      </div>
                    </details>
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="chat-message assistant">
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input-area">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me anything..."
              rows={2}
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={!inputMessage.trim() || isLoading}
              className="send-btn"
            >
              {isLoading ? '...' : '➤'}
            </button>
          </div>
        </div>
      )}
    </>
  );
};
