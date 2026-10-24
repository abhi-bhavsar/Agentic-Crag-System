import React from 'react';
import { Cpu, Database, Settings as SettingsIcon, ShieldCheck, Sparkles } from 'lucide-react';

export default function Navbar({ health, onOpenConfig }) {
  const isPostgres = health?.vector_db_backend === 'postgres_pgvector';
  const isGroqReady = health?.groq_configured;

  return (
    <header className="navbar">
      <div className="brand">
        <div className="brand-icon-wrapper">
          <Cpu size={22} />
        </div>
        <div className="brand-text">
          <h1>Agentic RAG Studio</h1>
        </div>
        <span className="brand-badge">CRAG + Self-RAG</span>
      </div>

      <div className="nav-actions">
        {/* Database Status Badge */}
        <div className={`nav-pill ${isPostgres ? 'active-postgres' : 'active-chroma'}`} title="Active Vector Store">
          <Database size={14} />
          <span className={`pulse-dot ${isPostgres ? 'online' : 'warning'}`}></span>
          <span>{isPostgres ? 'PostgreSQL (pgvector)' : 'Local ChromaDB'}</span>
        </div>

        {/* Groq API Status Badge */}
        <div className={`nav-pill ${isGroqReady ? 'active-groq' : 'warning-groq'}`} title="Groq Inference Engine">
          <Sparkles size={14} />
          <span className={`pulse-dot ${isGroqReady ? 'online' : 'warning'}`}></span>
          <span>{isGroqReady ? (health?.groq_model || 'Groq Active') : 'Groq Key Needed'}</span>
        </div>

        {/* Free HuggingFace Embeddings Badge */}
        <div className="nav-pill" title="Free Local Hugging Face Embeddings">
          <ShieldCheck size={14} color="#38bdf8" />
          <span>MiniLM-L6-v2 (384d)</span>
        </div>

        {/* Settings Toggle */}
        <button className="btn-icon" onClick={onOpenConfig} title="Agent & Database Settings">
          <SettingsIcon size={18} />
        </button>
      </div>
    </header>
  );
}
