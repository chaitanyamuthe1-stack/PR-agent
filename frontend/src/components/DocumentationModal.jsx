import React from 'react';
import { X, BookOpen, ShieldCheck, Terminal, Database, Server, GitBranch, RefreshCw, FileText } from 'lucide-react';

export default function DocumentationModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#142B4A]/50 backdrop-blur-sm animate-in fade-in">
      <div className="dev-card max-w-3xl w-full shadow-2xl overflow-hidden max-h-[85vh] flex flex-col bg-white border border-[#E2E6EC] rounded-xl">
        
        {/* Header - Navy Blue #142B4A */}
        <div className="flex items-center justify-between p-5 bg-[#142B4A] text-white">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-white/10 text-[#DCE7F5] border border-white/20">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">
                AG-12 Protocol Specification &amp; Engineering Guide
              </h3>
              <p className="text-xs text-[#DCE7F5]/80">
                Multilingual AI Code Review &amp; Autonomous Remediation Protocol
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-white/70 hover:text-white p-1 rounded-md hover:bg-white/10 transition-colors cursor-pointer"
            title="Close Documentation (Esc)"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-sm bg-white">
          
          {/* Section: Operational Pipeline */}
          <div>
            <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-[#142B4A] mb-2">
              1. Deterministic Multi-Agent Review Pipeline
            </h4>
            <div className="space-y-2 text-xs text-[#343A40] leading-relaxed bg-[#F3F5F8] p-4 rounded-xl border border-[#E2E6EC] font-sans">
              <p>
                <strong className="text-[#142B4A]">Layer 1 — Source Ingestion:</strong> Normalizes source code across 6 languages (Python, C++, C, Java, JavaScript, Ruby) and parses syntax tokens.
              </p>
              <p>
                <strong className="text-[#142B4A]">Layer 2 — MCP Static Linters:</strong> Dispatches native linters (pylint, bandit, cppcheck, checkstyle, eslint, rubocop) via Model Context Protocol to extract deterministic baseline findings.
              </p>
              <p>
                <strong className="text-[#142B4A]">Layer 3 — RAG Knowledge Retrieval:</strong> Semantic search in vector store matching detected patterns against OWASP Top 10 (2021) and CWE Top 25 weaknesses.
              </p>
              <p>
                <strong className="text-[#142B4A]">Layer 4 — LLM Gateway &amp; Failover:</strong> Dynamic routing to Gemini, Groq, or local Ollama (Qwen2.5-Coder:7B) with automatic failover.
              </p>
              <p>
                <strong className="text-[#142B4A]">Layer 5 — Parallel Review Agents:</strong> Security Agent identifies vulnerabilities and CWE mappings; Bug Agent identifies logic regressions and leaks.
              </p>
              <p>
                <strong className="text-[#142B4A]">Layer 6 — Summary Synthesis:</strong> Weighted severity scoring (Critical: -3.0, High: -1.5, Medium: -0.75, Low: -0.25) to compute Health Score out of 10.
              </p>
              <p>
                <strong className="text-[#142B4A]">Layer 7 — Coder Agent &amp; Re-Check:</strong> Applies grounded auto-remediations and re-executes static linters to verify defect eradication.
              </p>
            </div>
          </div>

          {/* Section: Critical Verdict Invariant */}
          <div>
            <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-[#142B4A] mb-2">
              2. Strict Verdict Invariant
            </h4>
            <div className="p-4 rounded-xl bg-[#F3F5F8] border border-[#E2E6EC] text-xs font-mono space-y-1">
              <div className="text-[#991B1B] font-bold">if (unresolvedFindings.length &gt; 0) =&gt; Final Verdict = "FIX REQUIRED"</div>
              <div className="text-[#1B5E36] font-bold">if (unresolvedFindings.length === 0) =&gt; Final Verdict = "CLEAN"</div>
              <p className="text-[#718096] text-xs font-sans mt-2 pt-2 border-t border-[#E2E6EC]">
                No manual override to "CLEAN" is permitted. Every verdict update must be backed by empirical analysis or confirmed engineer ignores.
              </p>
            </div>
          </div>

          {/* Section: API Endpoints */}
          <div>
            <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-[#142B4A] mb-2">
              3. Backend API Reference
            </h4>
            <div className="border border-[#E2E6EC] rounded-xl overflow-hidden font-mono text-xs">
              <table className="w-full text-left">
                <thead className="bg-[#F3F5F8] text-[#142B4A] border-b border-[#E2E6EC]">
                  <tr>
                    <th className="p-2.5 font-bold">Endpoint</th>
                    <th className="p-2.5 font-bold">Method</th>
                    <th className="p-2.5 font-bold">Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E2E6EC] bg-white">
                  <tr>
                    <td className="p-2.5 text-[#142B4A] font-bold">/api/upload</td>
                    <td className="p-2.5 text-[#718096]">POST</td>
                    <td className="p-2.5 text-[#343A40] font-sans">Accepts source code file, infers language and line count</td>
                  </tr>
                  <tr>
                    <td className="p-2.5 text-[#142B4A] font-bold">/api/review</td>
                    <td className="p-2.5 text-[#718096]">POST</td>
                    <td className="p-2.5 text-[#343A40] font-sans">Full LangGraph multi-agent review pipeline execution</td>
                  </tr>
                  <tr>
                    <td className="p-2.5 text-[#142B4A] font-bold">/api/remediate</td>
                    <td className="p-2.5 text-[#718096]">POST</td>
                    <td className="p-2.5 text-[#343A40] font-sans">Coder Agent auto-correction grounded in RAG</td>
                  </tr>
                  <tr>
                    <td className="p-2.5 text-[#142B4A] font-bold">/api/recheck</td>
                    <td className="p-2.5 text-[#718096]">POST</td>
                    <td className="p-2.5 text-[#343A40] font-sans">Verifies corrected code with static linters</td>
                  </tr>
                  <tr>
                    <td className="p-2.5 text-[#142B4A] font-bold">/api/download</td>
                    <td className="p-2.5 text-[#718096]">GET</td>
                    <td className="p-2.5 text-[#343A40] font-sans">Exports remediated source code file</td>
                  </tr>
                  <tr>
                    <td className="p-2.5 text-[#142B4A] font-bold">/api/audit-report</td>
                    <td className="p-2.5 text-[#718096]">GET</td>
                    <td className="p-2.5 text-[#343A40] font-sans">Generates certified Markdown audit report</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[#E2E6EC] bg-[#F3F5F8] flex justify-end">
          <button
            onClick={onClose}
            className="dev-btn-secondary px-4 py-2 text-xs font-semibold cursor-pointer"
          >
            Close Documentation
          </button>
        </div>

      </div>
    </div>
  );
}
