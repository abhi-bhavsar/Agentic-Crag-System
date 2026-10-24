import React, { useState } from 'react';
import { 
  GitCommit, 
  Search, 
  Filter, 
  Globe, 
  Cpu, 
  ShieldCheck, 
  ChevronDown, 
  ChevronUp, 
  CheckCircle, 
  AlertTriangle,
  ArrowDown
} from 'lucide-react';

export default function PipelineVisualizer({ traces = [], isStreaming = false }) {
  const [expandedNode, setExpandedNode] = useState(null);

  const nodeIcons = {
    query_transform: <GitCommit size={16} color="#818cf8" />,
    retrieve: <Search size={16} color="#38bdf8" />,
    grade_documents: <Filter size={16} color="#06b6d4" />,
    web_search: <Globe size={16} color="#f59e0b" />,
    generate: <Cpu size={16} color="#a855f7" />,
    verify_hallucination: <ShieldCheck size={16} color="#10b981" />,
  };

  const toggleExpand = (index) => {
    setExpandedNode(expandedNode === index ? null : index);
  };

  return (
    <div className="panel visualizer-column">
      <div className="panel-header">
        <h2>
          <ShieldCheck size={18} color="#10b981" />
          <span>Execution Graph</span>
        </h2>
        <span style={{ fontSize: '0.72rem', color: isStreaming ? '#38bdf8' : '#94a3b8' }}>
          {isStreaming ? 'Agent Active...' : `${traces.length} steps`}
        </span>
      </div>

      <div className="panel-body">
        {traces.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#64748b', fontSize: '0.8rem', padding: '3rem 1rem' }}>
            <GitCommit size={32} style={{ margin: '0 auto 0.75rem', opacity: 0.4 }} />
            <p>CRAG + Self-RAG Graph is idle.</p>
            <p style={{ fontSize: '0.72rem', marginTop: '0.4rem' }}>
              Send a query to observe real-time query transformations, retrieval grading, and hallucination checks.
            </p>
          </div>
        ) : (
          traces.map((trace, idx) => {
            const isLast = idx === traces.length - 1;
            const isWarning = trace.status === 'warning' || trace.details?.web_search_fallback_triggered;
            const isExpanded = expandedNode === idx;

            return (
              <React.Fragment key={idx}>
                <div
                  className={`graph-step ${trace.status} ${isWarning ? 'warning' : 'completed'} ${isLast && isStreaming ? 'active' : ''}`}
                  onClick={() => toggleExpand(idx)}
                >
                  <div className="step-header">
                    <span className="step-title">
                      {nodeIcons[trace.node] || <GitCommit size={16} />}
                      <span>{trace.title}</span>
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <span className="step-duration">{trace.duration_ms} ms</span>
                      {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </span>
                  </div>

                  {/* Summary Snippet */}
                  <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                    {trace.node === 'query_transform' && (
                      <span>
                        Route: <strong>{trace.details?.route_decision}</strong>
                        {trace.details?.sub_queries?.length > 0 && ` (${trace.details.sub_queries.length} sub-queries)`}
                      </span>
                    )}
                    {trace.node === 'retrieve' && (
                      <span>
                        Found <strong>{trace.details?.chunks_found}</strong> vector chunks &bull; top sim {trace.details?.top_similarity}
                      </span>
                    )}
                    {trace.node === 'grade_documents' && (
                      <span>
                        CRAG: Kept <strong>{trace.details?.relevant_kept}</strong> relevant, filtered {trace.details?.irrelevant_filtered} noisy chunks
                      </span>
                    )}
                    {trace.node === 'web_search' && (
                      <span>
                        DuckDuckGo Fallback: Added <strong>{trace.details?.results_count}</strong> web sources
                      </span>
                    )}
                    {trace.node === 'generate' && (
                      <span>
                        Synthesized using <strong>{trace.details?.model}</strong> ({trace.details?.context_chunks_used} chunks)
                      </span>
                    )}
                    {trace.node === 'verify_hallucination' && (
                      <span>
                        Verdict: <strong style={{ color: trace.details?.verdict === 'grounded' ? '#6ee7b7' : '#fca5a5' }}>
                          {trace.details?.verdict?.toUpperCase()}
                        </strong> &bull; Score: {trace.details?.groundedness_score}
                      </span>
                    )}
                  </div>

                  {/* Expanded JSON Inspector */}
                  {isExpanded && (
                    <pre className="step-details">
                      {JSON.stringify(trace.details, null, 2)}
                    </pre>
                  )}
                </div>

                {!isLast && (
                  <div className="flow-arrow">
                    <ArrowDown size={14} />
                  </div>
                )}
              </React.Fragment>
            );
          })
        )}
      </div>
    </div>
  );
}
