import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, Trash2, Layers, CheckCircle2, AlertTriangle, FileCode } from 'lucide-react';
import { uploadDocuments, deleteDocument } from '../services/api';

export default function DocumentManager({ documents, onDocumentsChanged, stats }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState(null);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      await processFiles(e.dataTransfer.files);
    }
  };

  const handleFileInput = async (e) => {
    if (e.target.files && e.target.files.length > 0) {
      await processFiles(e.target.files);
    }
  };

  const processFiles = async (fileList) => {
    setUploading(true);
    setUploadMsg({ type: 'info', text: `Parsing and embedding ${fileList.length} file(s)...` });
    try {
      const res = await uploadDocuments(fileList);
      const totalIndexed = res.reduce((acc, curr) => acc + (curr.chunk_count || 0), 0);
      setUploadMsg({
        type: 'success',
        text: `Indexed ${res.length} file(s) into ${totalIndexed} vector chunks!`
      });
      onDocumentsChanged();
      setTimeout(() => setUploadMsg(null), 4500);
    } catch (err) {
      setUploadMsg({ type: 'error', text: `Upload failed: ${err.message}` });
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (docId, filename) => {
    if (!window.confirm(`Delete document "${filename}" and its vector chunks?`)) return;
    try {
      await deleteDocument(docId);
      onDocumentsChanged();
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>
          <Layers size={18} color="#06b6d4" />
          <span>Knowledge Base</span>
        </h2>
        <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
          {documents.length} docs &bull; {stats?.total_chunks || 0} chunks
        </span>
      </div>

      <div className="panel-body">
        {/* Drag and Drop Zone */}
        <div
          className={`dropzone ${isDragging ? 'active' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileInput}
            multiple
            accept=".pdf,.docx,.doc,.txt,.md,.markdown,.csv,.json"
            style={{ display: 'none' }}
          />
          <div className="dropzone-icon">
            <UploadCloud size={24} />
          </div>
          <div className="dropzone-title">
            {uploading ? 'Processing & Embedding...' : 'Drop files here or click to browse'}
          </div>
          <div className="dropzone-desc">
            Supports PDF, DOCX, TXT, MD &bull; Free HuggingFace MiniLM Embeddings
          </div>
        </div>

        {/* Upload Alert */}
        {uploadMsg && (
          <div
            style={{
              marginTop: '0.75rem',
              padding: '0.6rem 0.85rem',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.78rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              background: uploadMsg.type === 'error' ? 'rgba(244, 63, 94, 0.15)' : 'rgba(16, 185, 129, 0.15)',
              color: uploadMsg.type === 'error' ? '#fca5a5' : '#6ee7b7',
              border: `1px solid ${uploadMsg.type === 'error' ? 'rgba(244, 63, 94, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`
            }}
          >
            {uploadMsg.type === 'error' ? <AlertTriangle size={15} /> : <CheckCircle2 size={15} />}
            <span>{uploadMsg.text}</span>
          </div>
        )}

        {/* Ingested Documents List */}
        <div className="doc-list">
          {documents.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#64748b', fontSize: '0.8rem', padding: '2rem 1rem' }}>
              No documents indexed yet. Upload a PDF, DOCX, or text file to initialize your vector store!
            </div>
          ) : (
            documents.map((doc) => (
              <div key={doc.id} className="doc-card">
                <div className="doc-info">
                  <div className="doc-icon">
                    {doc.file_type === 'PDF' ? <FileText size={18} color="#f43f5e" /> : <FileCode size={18} color="#38bdf8" />}
                  </div>
                  <div className="doc-details">
                    <span className="doc-name" title={doc.filename}>{doc.filename}</span>
                    <span className="doc-meta">
                      {doc.chunk_count} chunks &bull; {formatFileSize(doc.file_size)}
                    </span>
                  </div>
                </div>

                <button
                  className="doc-delete"
                  onClick={() => handleDelete(doc.id, doc.filename)}
                  title="Delete document and vector chunks"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
