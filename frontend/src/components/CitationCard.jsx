import React, { useState } from 'react';
import { BookOpen, ExternalLink, ChevronDown, ChevronUp, FileText, Globe } from 'lucide-react';

export default function CitationCard({ sources = [], webResults = [] }) {
  const [open, setOpen] = useState(false);

  const totalSources = sources.length + webResults.length;
  if (totalSources === 0) return null;

  return (
    <div className="citation-box">
      <button className="citation-toggle" onClick={() => setOpen(!open)}>
        <BookOpen size={14} />
        <span>Grounded in {totalSources} verified source(s)</span>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {open && (
        <div className="citation-cards">
          {/* Vector Document Sources */}
          {sources.map((src, idx) => (
            <div key={`doc-${idx}`} className="citation-card">
              <div className="citation-head">
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <FileText size={13} />
                  <span>{src.source} (Page {src.page || 1})</span>
                </span>
                <span className="citation-score">
                  {src.grade && `[${src.grade.toUpperCase()}] `}
                  {src.relevance_score ? `score: ${src.relevance_score}` : ''}
                </span>
              </div>
              <div className="citation-body">
                {src.content?.slice(0, 220)}...
              </div>
            </div>
          ))}

          {/* Web Fallback Sources */}
          {webResults.map((wr, idx) => (
            <div key={`web-${idx}`} className="citation-card" style={{ borderColor: 'rgba(245, 158, 11, 0.3)' }}>
              <div className="citation-head">
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#fcd34d' }}>
                  <Globe size={13} />
                  <a
                    href={wr.link}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: 'inherit', textDecoration: 'none' }}
                  >
                    {wr.title || 'Web Search Source'}
                  </a>
                </span>
                <a
                  href={wr.link}
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: '#94a3b8', display: 'flex', alignItems: 'center' }}
                >
                  <ExternalLink size={12} />
                </a>
              </div>
              <div className="citation-body">
                {wr.snippet?.slice(0, 220)}...
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
