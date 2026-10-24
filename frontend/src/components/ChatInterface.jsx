import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, Globe, ShieldCheck, AlertCircle, RefreshCw } from 'lucide-react';
import CitationCard from './CitationCard';

export default function ChatInterface({
  messages,
  onSendMessage,
  isProcessing,
  config
}) {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef(null);

  const samplePrompts = [
    "What is the difference between Naive RAG and Corrective RAG (CRAG)?",
    "How does the Self-RAG post-generation guardrail prevent hallucinations?",
    "Summarize the key findings from the uploaded document.",
    "What are the latest AI breakthroughs in 2026? (Triggers web fallback)"
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isProcessing]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!inputText.trim() || isProcessing) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="panel" style={{ flex: 1 }}>
      <div className="panel-header">
        <h2>
          <Bot size={18} color="#6366f1" />
          <span>Adaptive Agent Studio</span>
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.74rem', color: '#94a3b8' }}>
          <span>Mode:</span>
          <span style={{ color: '#38bdf8', fontWeight: 600 }}>
            {config.mode === 'adaptive_crag_self_rag' ? 'CRAG + Self-RAG' : config.mode}
          </span>
        </div>
      </div>

      {/* Message Thread */}
      <div className="chat-thread">
        {messages.length === 0 ? (
          <div style={{ margin: 'auto', textAlign: 'center', maxWidth: '520px', padding: '2rem 1rem' }}>
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: 'var(--radius-lg)',
                background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(6, 182, 212, 0.2))',
                border: '1px solid rgba(99, 102, 241, 0.35)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 1rem',
                color: '#38bdf8'
              }}
            >
              <Sparkles size={28} />
            </div>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', marginBottom: '0.5rem' }}>
              Self-Corrective & Adaptive Agentic RAG
            </h3>
            <p style={{ color: '#94a3b8', fontSize: '0.85rem', lineHeight: 1.5, marginBottom: '1.5rem' }}>
              Ask questions about your uploaded documents or query general knowledge. The pipeline adapts
              using query transformation, CRAG retrieval relevance grading with web search fallback, and Self-RAG hallucination guardrails.
            </p>

            {/* Quick Prompt Pills */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', textAlign: 'left' }}>
              {samplePrompts.map((p, idx) => (
                <button
                  key={idx}
                  className="sugg-pill"
                  onClick={() => onSendMessage(p)}
                  style={{ textAlign: 'left', padding: '0.55rem 0.85rem' }}
                >
                  &rarr; {p}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`message-wrapper ${msg.role}`}>
              <div className={`avatar ${msg.role === 'user' ? 'user-avatar' : 'ai-avatar'}`}>
                {msg.role === 'user' ? <User size={18} /> : <Bot size={18} />}
              </div>

              <div className="message-bubble">
                {/* AI Metadata Pills */}
                {msg.role === 'assistant' && (
                  <div className="meta-pills">
                    {msg.route_decision && (
                      <span className={`meta-pill ${msg.route_decision === 'web_search' ? 'route-web' : 'route-vector'}`}>
                        {msg.route_decision === 'web_search' ? <Globe size={11} /> : <Sparkles size={11} />}
                        Route: {msg.route_decision}
                      </span>
                    )}

                    {msg.faithfulness_verdict && (
                      <span className={`meta-pill ${msg.faithfulness_verdict === 'grounded' ? 'grounded' : 'hallucinated'}`}>
                        <ShieldCheck size={11} />
                        Self-RAG: {msg.faithfulness_verdict} ({Math.round((msg.groundedness_score || 1) * 100)}%)
                      </span>
                    )}

                    {msg.retries > 0 && (
                      <span className="meta-pill" style={{ color: '#f59e0b', borderColor: 'rgba(245, 158, 11, 0.3)' }}>
                        <RefreshCw size={11} />
                        Self-Corrected ({msg.retries}x)
                      </span>
                    )}
                  </div>
                )}

                {/* Text Content */}
                <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {msg.content}
                </div>

                {/* Citations Box */}
                {msg.role === 'assistant' && (
                  <CitationCard sources={msg.sources || []} webResults={msg.web_results || []} />
                )}
              </div>
            </div>
          ))
        )}

        {/* Processing Indicator */}
        {isProcessing && (
          <div className="message-wrapper assistant">
            <div className="avatar ai-avatar">
              <Bot size={18} />
            </div>
            <div className="message-bubble" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <div className="pulse-dot online"></div>
              <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
                Orchestrating agent graph (Routing &bull; CRAG Grading &bull; Guardrails)...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="chat-input-container">
        <form onSubmit={handleSubmit}>
          <div className="input-box">
            <textarea
              className="input-textarea"
              rows={1}
              placeholder="Ask a question or compare concepts from your knowledge base..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isProcessing}
            />
            <button
              type="submit"
              className="btn-send"
              disabled={!inputText.trim() || isProcessing}
              title="Send message"
            >
              <Send size={16} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
