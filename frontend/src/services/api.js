/**
 * API Service for PR Agent
 * Enhanced in Phase 16:
 * - In-flight request deduplication (prevents duplicate simultaneous calls)
 * - TTL caching for static endpoints (languages, samples, catalog)
 * - Understandable, user-friendly error translations
 * - Request cancellation via AbortSignal
 */

const API_BASE = '/api';

// In-flight request pool for deduplicating identical simultaneous network calls
const inFlightRequests = new Map();

// In-memory cache for static/semi-static responses with TTL
const responseCache = new Map();

/**
 * Normalizes error messages into plain-language, understandable guidance.
 */
export function normalizeErrorMessage(err, fallback = 'Operation failed') {
  if (!err) return fallback;
  if (err.name === 'AbortError' || err.message?.includes('aborted')) {
    return 'Operation safely cancelled by user.';
  }
  const msg = typeof err === 'string' ? err : (err.message || String(err));
  
  if (msg.includes('Failed to fetch') || msg.includes('NetworkError') || msg.includes('Load failed')) {
    return 'Unable to reach the PR Agent backend service (http://127.0.0.1:8000). Please ensure the backend server is running.';
  }
  if (msg.includes('413') || msg.includes('too large') || msg.includes('Payload too large')) {
    return 'Source code file exceeds maximum size limit (5MB / 250,000 characters). Please reduce the file size and try again.';
  }
  if (msg.includes('Unsupported language')) {
    return msg; // Already clear
  }
  if (msg.includes('500') || msg.includes('Internal server error')) {
    return 'The review engine encountered an unexpected error during pipeline execution. Please verify your code syntax and try again.';
  }
  return msg || fallback;
}

/**
 * Deduplicated fetch wrapper that reuses existing in-flight promises and supports TTL caching.
 */
async function deduplicatedFetch(url, options = {}, cacheTtlMs = 0) {
  const method = (options.method || 'GET').toUpperCase();
  const cacheKey = `${method}:${url}:${options.body || ''}`;

  // Check TTL cache for GET requests
  if (method === 'GET' && cacheTtlMs > 0) {
    const cached = responseCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < cacheTtlMs) {
      return cached.data;
    }
  }

  // Check in-flight pool to avoid duplicate network requests
  if (inFlightRequests.has(cacheKey)) {
    return inFlightRequests.get(cacheKey);
  }

  const fetchPromise = (async () => {
    try {
      const res = await fetch(url, options);
      if (!res.ok) {
        let errorDetail = res.statusText;
        try {
          const errJson = await res.json();
          errorDetail = errJson.detail || res.statusText;
        } catch {
          try {
            errorDetail = await res.text();
          } catch {
            // Keep statusText
          }
        }
        throw new Error(normalizeErrorMessage(errorDetail, `Request failed with HTTP ${res.status}`));
      }

      const contentType = res.headers.get('content-type') || '';
      const data = contentType.includes('application/json') ? await res.json() : await res.text();

      // Store in TTL cache if applicable
      if (method === 'GET' && cacheTtlMs > 0) {
        responseCache.set(cacheKey, { timestamp: Date.now(), data });
      }

      return data;
    } catch (err) {
      throw new Error(normalizeErrorMessage(err));
    } finally {
      inFlightRequests.delete(cacheKey);
    }
  })();

  inFlightRequests.set(cacheKey, fetchPromise);
  return fetchPromise;
}

export async function fetchStatus() {
  // Deduplicate and cache status for 3 seconds to avoid spamming the backend
  return deduplicatedFetch(`${API_BASE}/status`, {}, 3000);
}

export async function fetchLanguages() {
  // Languages and tool bindings are static: cache for 10 minutes
  return deduplicatedFetch(`${API_BASE}/languages`, {}, 600000);
}

export async function fetchSamples() {
  // Buggy code samples are static: cache for 10 minutes
  return deduplicatedFetch(`${API_BASE}/samples`, {}, 600000);
}

export async function uploadSourceFile(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(normalizeErrorMessage(err.detail || `Upload failed: ${res.statusText}`));
  }
  return res.json();
}

export async function runReview(payload, signal = null) {
  // Bound payload size before transmission
  if (payload.code && payload.code.length > 500000) {
    payload = { ...payload, code: payload.code.slice(0, 500000) };
  }
  const options = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  };
  if (signal) options.signal = signal;

  // In-flight deduplication for identical concurrent review clicks
  const sigKey = `POST:${API_BASE}/review:${payload.language}:${payload.filename}:${payload.code.length}:${payload.code.slice(0, 100)}`;
  if (inFlightRequests.has(sigKey)) {
    return inFlightRequests.get(sigKey);
  }

  const reviewPromise = (async () => {
    try {
      const res = await fetch(`${API_BASE}/review`, options);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(normalizeErrorMessage(err.detail || `Review request failed: ${res.statusText}`));
      }
      return await res.json();
    } catch (err) {
      throw new Error(normalizeErrorMessage(err));
    } finally {
      inFlightRequests.delete(sigKey);
    }
  })();

  inFlightRequests.set(sigKey, reviewPromise);
  return reviewPromise;
}

export async function configureGateway(config) {
  const res = await fetch(`${API_BASE}/gateway/configure`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(normalizeErrorMessage(err.detail || `Gateway config failed: ${res.statusText}`));
  }
  // Clear status cache so changes reflect immediately
  responseCache.delete(`GET:${API_BASE}/status:`);
  return res.json();
}

export async function queryRag(query, language = null, top_k = 4, min_similarity = 0.12, category = null) {
  // Bound top_k safely
  const safeTopK = Math.max(1, Math.min(top_k || 4, 10));
  const res = await fetch(`${API_BASE}/rag/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: (query || '').slice(0, 2000), language, top_k: safeTopK, min_similarity, category }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(normalizeErrorMessage(err.detail || `RAG query failed: ${res.statusText}`));
  }
  return res.json();
}

export async function fetchRagStats() {
  return deduplicatedFetch(`${API_BASE}/rag/stats`, {}, 5000);
}

export async function ingestRagContext(payload) {
  // Bound content size to 100,000 chars
  if (payload.content && payload.content.length > 100000) {
    payload = { ...payload, content: payload.content.slice(0, 100000) };
  }
  const res = await fetch(`${API_BASE}/rag/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(normalizeErrorMessage(err.detail || `Ingestion failed: ${res.statusText}`));
  }
  responseCache.delete(`GET:${API_BASE}/rag/stats:`);
  return res.json();
}

export async function uploadRagContextFile(file, language = null) {
  const formData = new FormData();
  formData.append('file', file);
  if (language) formData.append('language', language);
  const res = await fetch(`${API_BASE}/rag/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(normalizeErrorMessage(err.detail || `Context upload failed: ${res.statusText}`));
  }
  responseCache.delete(`GET:${API_BASE}/rag/stats:`);
  return res.json();
}

// Phase 13: Benchmark API Service Methods
export async function fetchBenchmarkCatalog() {
  return deduplicatedFetch(`${API_BASE}/benchmark/catalog`, {}, 300000);
}

export async function runPipelineBenchmark(params = {}, signal = null) {
  const options = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  };
  if (signal) options.signal = signal;
  const res = await fetch(`${API_BASE}/benchmark/pipeline/run`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(normalizeErrorMessage(err.detail || `Pipeline benchmark run failed: ${res.statusText}`));
  }
  return res.json();
}

export async function runRagBenchmark() {
  const res = await fetch(`${API_BASE}/benchmark/rag/run`, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(normalizeErrorMessage(err.detail || `RAG benchmark run failed: ${res.statusText}`));
  }
  return res.json();
}

export async function fetchBenchmarkStatus() {
  return deduplicatedFetch(`${API_BASE}/benchmark/status`, {}, 5000);
}

export function getDownloadUrl(reviewId = null) {
  return reviewId ? `${API_BASE}/download?review_id=${encodeURIComponent(reviewId)}` : `${API_BASE}/download`;
}

export function getAuditReportUrl(reviewId = null) {
  return reviewId ? `${API_BASE}/audit-report?review_id=${encodeURIComponent(reviewId)}` : `${API_BASE}/audit-report`;
}

export async function remediateCode(payload, signal = null) {
  if (payload.code && payload.code.length > 500000) {
    payload = { ...payload, code: payload.code.slice(0, 500000) };
  }
  const options = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  };
  if (signal) options.signal = signal;
  const res = await fetch(`${API_BASE}/remediate`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(normalizeErrorMessage(err.detail || `Remediation failed: ${res.statusText}`));
  }
  return res.json();
}

export async function recheckCode(payload, signal = null) {
  if (payload.corrected_code && payload.corrected_code.length > 500000) {
    payload = { ...payload, corrected_code: payload.corrected_code.slice(0, 500000) };
  }
  const options = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  };
  if (signal) options.signal = signal;
  const res = await fetch(`${API_BASE}/recheck`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(normalizeErrorMessage(err.detail || `Re-check failed: ${res.statusText}`));
  }
  return res.json();
}

export async function downloadAuditReport(reviewId = null, fallbackFilename = 'PR_Agent_Audit_Report.md') {
  const url = getAuditReportUrl(reviewId);
  const res = await fetch(url);
  if (!res.ok) throw new Error(normalizeErrorMessage(`Report generation failed: ${res.statusText}`));
  const blob = await res.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  
  let filename = fallbackFilename;
  const disp = res.headers.get('Content-Disposition');
  if (disp && disp.includes('filename=')) {
    const match = disp.match(/filename=["']?([^"';]+)["']?/);
    if (match && match[1]) filename = match[1];
  }
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(downloadUrl);
  return filename;
}

export async function downloadCorrectedCode(reviewId = null, fallbackFilename = 'corrected_code.txt') {
  const url = getDownloadUrl(reviewId);
  const res = await fetch(url);
  if (!res.ok) throw new Error(normalizeErrorMessage(`Code export failed: ${res.statusText}`));
  const blob = await res.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;

  let filename = fallbackFilename;
  const disp = res.headers.get('Content-Disposition');
  if (disp && disp.includes('filename=')) {
    const match = disp.match(/filename=["']?([^"';]+)["']?/);
    if (match && match[1]) filename = match[1];
  }
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(downloadUrl);
  return filename;
}

export async function fetchAuditReportText(reviewId = null) {
  const url = getAuditReportUrl(reviewId);
  const res = await fetch(url);
  if (!res.ok) throw new Error(normalizeErrorMessage(`Report retrieval failed: ${res.statusText}`));
  return res.text();
}

