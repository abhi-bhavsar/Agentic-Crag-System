import React, { useState } from 'react';
import { AlertCircle, X, CheckCircle2 } from 'lucide-react';

export default function StatusBanner({ health, onOpenConfig }) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  const isGroqConfigured = health?.groq_configured;
  const isPostgresReachable = health?.postgres_status?.reachable;

  if (isGroqConfigured && isPostgresReachable) {
    return null; // All production systems green
  }

  return (
    <div className="status-banner">
      <div className="banner-info">
        <AlertCircle size={16} color="#f59e0b" />
        <span>
          {!isGroqConfigured ? (
            <>
              <strong>Groq API key not detected:</strong> Pipeline is executing in local preview mode. Add your free key in <code>.env</code> or Settings.
            </>
          ) : !isPostgresReachable ? (
            <>
              <strong>PostgreSQL pgvector offline:</strong> Automatically utilizing persistent local ChromaDB. You can start Postgres anytime with <code>docker compose up db</code>.
            </>
          ) : null}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <button
          onClick={onOpenConfig}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#38bdf8',
            fontSize: '0.78rem',
            cursor: 'pointer',
            textDecoration: 'underline'
          }}
        >
          Configure Settings
        </button>
        <button
          onClick={() => setDismissed(true)}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center'
          }}
        >
          <X size={15} />
        </button>
      </div>
    </div>
  );
}
