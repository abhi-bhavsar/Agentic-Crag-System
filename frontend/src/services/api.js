/**
 * API Service for communicating with FastAPI Backend.
 */

const BASE_URL = '/api';

export async function fetchHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function fetchConfig() {
  const res = await fetch(`${BASE_URL}/system/config`);
  if (!res.ok) throw new Error('Config fetch failed');
  return res.json();
}

export async function fetchDocuments() {
  const res = await fetch(`${BASE_URL}/documents`);
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export async function uploadDocuments(files) {
  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i]);
  }

  const res = await fetch(`${BASE_URL}/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) throw new Error('Document upload failed');
  return res.json();
}

export async function deleteDocument(docId) {
  const res = await fetch(`${BASE_URL}/documents/${docId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Document deletion failed');
  return res.json();
}

export async function sendChatMessage(payload) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Chat query failed');
  }
  return res.json();
}

/**
 * Streams chat responses using Server-Sent Events (SSE).
 */
export async function streamChatMessage(payload, { onNodeUpdate, onCompleted, onError }) {
  try {
    const res = await fetch(`${BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error(`Server returned HTTP ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep last unfinished line

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data:')) {
          const jsonStr = trimmed.slice(5).trim();
          if (jsonStr) {
            try {
              const data = JSON.parse(jsonStr);
              if (data.event === 'node_update' && onNodeUpdate) {
                onNodeUpdate(data);
              } else if (data.event === 'completed' && onCompleted) {
                onCompleted(data);
              } else if (data.event === 'error' && onError) {
                onError(new Error(data.error));
              }
            } catch (err) {
              console.warn('JSON parse error on SSE chunk', err);
            }
          }
        }
      }
    }
  } catch (err) {
    if (onError) onError(err);
  }
}
