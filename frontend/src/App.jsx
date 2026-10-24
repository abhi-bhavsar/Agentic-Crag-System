import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import StatusBanner from './components/StatusBanner';
import DocumentManager from './components/DocumentManager';
import ChatInterface from './components/ChatInterface';
import PipelineVisualizer from './components/PipelineVisualizer';
import ConfigPanel from './components/ConfigPanel';
import { fetchHealth, fetchConfig, fetchDocuments, streamChatMessage, sendChatMessage } from './services/api';

export default function App() {
  const [health, setHealth] = useState(null);
  const [systemConfig, setSystemConfig] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [messages, setMessages] = useState([]);
  const [activeTraces, setActiveTraces] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isConfigOpen, setIsConfigOpen] = useState(false);

  // User configuration overrides
  const [config, setConfig] = useState({
    model: 'llama-3.3-70b-versatile',
    temperature: 0.2,
    mode: 'adaptive_crag_self_rag'
  });

  // Initial load
  const loadSystemState = async () => {
    try {
      const [hData, cData, dData] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchConfig().catch(() => null),
        fetchDocuments().catch(() => [])
      ]);
      if (hData) setHealth(hData);
      if (cData) setSystemConfig(cData);
      if (dData) setDocuments(dData);
    } catch (err) {
      console.warn('System state sync notice:', err);
    }
  };

  useEffect(() => {
    loadSystemState();
    const interval = setInterval(loadSystemState, 15000);
    return () => clearInterval(interval);
  }, []);

  // Handle Query Submission
  const handleSendMessage = async (text) => {
    const userMessage = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMessage]);
    setIsProcessing(true);
    setActiveTraces([]);

    const payload = {
      message: text,
      model: config.model,
      temperature: config.temperature,
      mode: config.mode
    };

    // Attempt real-time SSE streaming
    let streamSucceeded = false;
    try {
      await streamChatMessage(payload, {
        onNodeUpdate: (data) => {
          streamSucceeded = true;
          if (data.trace) {
            setActiveTraces((prev) => {
              const existingIndex = prev.findIndex((t) => t.node === data.trace.node);
              if (existingIndex >= 0) {
                const updated = [...prev];
                updated[existingIndex] = data.trace;
                return updated;
              }
              return [...prev, data.trace];
            });
          }
        },
        onCompleted: (data) => {
          streamSucceeded = true;
          const assistantMessage = {
            role: 'assistant',
            content: data.answer,
            route_decision: data.route,
            sources: data.sources || [],
            web_results: data.web_results || [],
            faithfulness_verdict: data.hallucination_detected ? 'hallucinated' : 'grounded',
            groundedness_score: data.groundedness_score,
            retries: data.retries
          };
          setMessages((prev) => [...prev, assistantMessage]);
          if (data.traces) setActiveTraces(data.traces);
          setIsProcessing(false);
        },
        onError: (err) => {
          console.warn('SSE stream error, trying fallback:', err);
          if (!streamSucceeded) {
            fallbackChat(payload);
          } else {
            setIsProcessing(false);
          }
        }
      });
    } catch (e) {
      if (!streamSucceeded) {
        fallbackChat(payload);
      }
    }
  };

  const fallbackChat = async (payload) => {
    try {
      const data = await sendChatMessage(payload);
      const assistantMessage = {
        role: 'assistant',
        content: data.answer,
        route_decision: data.route_decision,
        sources: data.sources || [],
        web_results: data.web_results || [],
        faithfulness_verdict: data.faithfulness_verdict,
        groundedness_score: data.groundedness_score,
        retries: data.retries
      };
      setMessages((prev) => [...prev, assistantMessage]);
      if (data.traces) setActiveTraces(data.traces);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ Request failed: ${err.message}`
        }
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="app-container">
      <Navbar
        health={health}
        onOpenConfig={() => setIsConfigOpen(true)}
      />

      <StatusBanner
        health={health}
        onOpenConfig={() => setIsConfigOpen(true)}
      />

      <main className="workspace-grid">
        {/* Left Column: Document Ingestion */}
        <DocumentManager
          documents={documents}
          onDocumentsChanged={loadSystemState}
          stats={health}
        />

        {/* Center Column: Adaptive Chat Studio */}
        <ChatInterface
          messages={messages}
          onSendMessage={handleSendMessage}
          isProcessing={isProcessing}
          config={config}
        />

        {/* Right Column: Execution Graph Visualizer */}
        <PipelineVisualizer
          traces={activeTraces}
          isStreaming={isProcessing}
        />
      </main>

      {/* Settings Modal */}
      <ConfigPanel
        isOpen={isConfigOpen}
        onClose={() => setIsConfigOpen(false)}
        config={config}
        setConfig={setConfig}
        systemConfig={systemConfig}
        health={health}
      />
    </div>
  );
}
