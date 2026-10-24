import React from 'react';
import { X, Server, Key, Database, Sliders, Check } from 'lucide-react';

export default function ConfigPanel({
  isOpen,
  onClose,
  config,
  setConfig,
  systemConfig,
  health
}) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Sliders size={20} color="#6366f1" />
            <span>Agentic RAG Settings</span>
          </div>
          <button className="btn-icon" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Model Selection */}
        <div className="form-group">
          <label className="form-label">Groq LLM Model</label>
          <select
            className="form-control"
            value={config.model}
            onChange={(e) => setConfig({ ...config, model: e.target.value })}
          >
            <option value="llama-3.3-70b-versatile">LLaMA 3.3 70B Versatile (Recommended)</option>
            <option value="llama-3.1-8b-instant">LLaMA 3.1 8B Instant (Ultra-fast)</option>
            <option value="mixtral-8x7b-32768">Mixtral 8x7B (32k Context)</option>
          </select>
        </div>

        {/* Pipeline Execution Mode */}
        <div className="form-group">
          <label className="form-label">Pipeline Mode</label>
          <select
            className="form-control"
            value={config.mode}
            onChange={(e) => setConfig({ ...config, mode: e.target.value })}
          >
            <option value="adaptive_crag_self_rag">
              Adaptive CRAG + Self-RAG (Production Agentic)
            </option>
            <option value="naive_rag">
              Naive RAG (Blind vector fetch, no grading)
            </option>
            <option value="web_search_only">
              Web Search Only (Direct DuckDuckGo)
            </option>
          </select>
        </div>

        {/* Temperature */}
        <div className="form-group">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
            <label className="form-label" style={{ margin: 0 }}>Temperature</label>
            <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: '#38bdf8' }}>
              {config.temperature}
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={config.temperature}
            onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) })}
            style={{ width: '100%', accentColor: 'var(--accent-primary)' }}
          />
        </div>

        {/* PostgreSQL & pgAdmin Credentials Guide Marker */}
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.8)',
            border: '1px solid rgba(99, 102, 241, 0.25)',
            borderRadius: 'var(--radius-md)',
            padding: '1rem',
            marginTop: '1.25rem',
            fontSize: '0.78rem'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', fontWeight: 600, color: '#a5b4fc', marginBottom: '0.4rem' }}>
            <Database size={15} />
            <span>PostgreSQL & pgAdmin Credentials Marker</span>
          </div>
          <p style={{ color: '#94a3b8', lineHeight: 1.45, marginBottom: '0.5rem' }}>
            Active Vector Backend: <strong style={{ color: '#6ee7b7' }}>{health?.vector_db_backend?.toUpperCase()}</strong>
          </p>
          <p style={{ color: '#64748b', fontSize: '0.73rem', lineHeight: 1.4 }}>
            To configure your PostgreSQL / pgAdmin credentials, open <code>.env</code> in the project root:
          </p>
          <pre
            style={{
              background: '#090d16',
              padding: '0.5rem',
              borderRadius: 'var(--radius-sm)',
              marginTop: '0.4rem',
              color: '#38bdf8',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.7rem'
            }}
          >
{`# In .env:
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=rag_db`}
          </pre>
        </div>

        <div style={{ marginTop: '1.25rem', display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn-primary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
