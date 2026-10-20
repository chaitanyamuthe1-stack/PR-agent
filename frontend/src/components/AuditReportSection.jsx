import React, { useState, memo } from 'react';
import { FileText, Download, Copy, Check, ShieldCheck, Terminal, Cpu, CheckCircle2, AlertTriangle, ShieldAlert, XCircle } from 'lucide-react';
import { downloadAuditReport, fetchAuditReportText, downloadCorrectedCode } from '../services/api';

function AuditReportSection({ reviewResult = null, gatewayStatus = null }) {
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);
  const [downloadingCode, setDownloadingCode] = useState(false);
  const [downloadCodeSuccess, setDownloadCodeSuccess] = useState(false);
  const [downloadError, setDownloadError] = useState(null);

  if (!reviewResult) {
    return (
      <div className="dev-card p-8 sm:p-10 shadow-sm text-center bg-white border border-[#E2E6EC]">
        <FileText className="w-10 h-10 text-[#606973] mx-auto mb-3 opacity-60" />
        <h4 className="text-base font-bold text-[#142B4A]">Compliance &amp; Audit Report</h4>
        <p className="text-sm text-[#606973] mt-1 max-w-md mx-auto">
          Execute code review in Code Studio to generate the certified technical audit report.
        </p>
      </div>
    );
  }

  const {
    filename = 'source_code.txt',
    language = 'python',
    review_id = 'N/A',
    health_score = 10.0,
    post_fix_score = null,
    verdict = 'PENDING',
    counts = { critical: 0, high: 0, medium: 0, low: 0 },
    unresolved_count = 0,
    resolved_count = 0,
    remediation_status = 'NOT_REQUIRED',
    summary = '',
    issues = [],
    telemetry = [],
    mcp_tools = [],
    tools_execution = [],
    coverage = null,
    coverage_explanation = null
  } = reviewResult;

  const remediationStatus = remediation_status;
  const provider = (gatewayStatus?.provider || 'OLLAMA').toUpperCase();
  const model = gatewayStatus?.model || 'qwen2.5-coder:7b';
  const analyzerText = mcp_tools && mcp_tools.length > 0 ? (Array.isArray(mcp_tools) ? mcp_tools.join(', ') : String(mcp_tools)) : 'Standard Linters';

  const isClean = (verdict === 'CLEAN' || verdict === 'PASS') && unresolved_count === 0;
  const isDegraded = ['ANALYZER UNAVAILABLE', 'MCP UNAVAILABLE', 'DEGRADED', 'RAG UNAVAILABLE', 'DEPENDENCY MISSING', 'LLM UNAVAILABLE'].some(v => (verdict || '').includes(v));

  const handleCopyReport = async () => {
    try {
      let reportText = '';
      try {
        reportText = await fetchAuditReportText(review_id);
      } catch (err) {
        reportText = `# PR AGENT AUDIT REPORT
Generated: ${new Date().toISOString()}
Target Artifact: ${filename} (${language.toUpperCase()})
MCP Static Linters: ${analyzerText}
Health Score: ${health_score.toFixed(1)} / 10.0
Final Verdict: ${verdict}
Unresolved Findings: ${unresolved_count}
Resolved Findings: ${resolved_count}

Executive Summary:
${summary}

Findings:
${issues.map((iss, i) => `#${i+1} [Line ${iss.line || 1}] [${(iss.severity||'MEDIUM').toUpperCase()}] ${iss.title}: ${iss.description}`).join('\n')}
`;
      }

      await navigator.clipboard.writeText(reportText);
      setCopied(true);
      setCopyFailed(false);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      setCopyFailed(true);
      setTimeout(() => setCopyFailed(false), 2500);
    }
  };

  const handleDownloadReport = async () => {
    setDownloading(true);
    setDownloadError(null);
    try {
      const baseName = filename.replace(/\.[^/.]+$/, "");
      await downloadAuditReport(review_id, `${baseName}_PR_Agent_Audit_Report.md`);
      setDownloadSuccess(true);
      setTimeout(() => setDownloadSuccess(false), 2000);
    } catch (err) {
      setDownloadError(`Download failed: ${err.message}`);
    } finally {
      setDownloading(false);
    }
  };

  const handleDownloadCorrectedSource = async () => {
    setDownloadingCode(true);
    setDownloadError(null);
    try {
      const extMap = { python: '.py', cpp: '.cpp', c: '.c', java: '.java', javascript: '.js', ruby: '.rb' };
      const ext = extMap[language] || '.txt';
      const baseName = filename.replace(/\.[^/.]+$/, "");
      await downloadCorrectedCode(review_id, `${baseName}_corrected${ext}`);
      setDownloadCodeSuccess(true);
      setTimeout(() => setDownloadCodeSuccess(false), 2000);
    } catch (err) {
      setDownloadError(`Download failed: ${err.message}`);
    } finally {
      setDownloadingCode(false);
    }
  };

  return (
    <div className="dev-card p-6 sm:p-8 shadow-sm space-y-6 bg-white border border-[#E2E6EC]">
      
      {/* Report Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between pb-4 border-b border-[#E2E6EC] gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <span className="w-3 h-3 rounded-full bg-[#142B4A]" />
            <h3 className="text-lg sm:text-xl font-bold text-[#142B4A] tracking-tight">
              Audit Report &amp; Downloads
            </h3>
          </div>
          <p className="text-xs sm:text-sm text-[#606973] mt-1">
            Certified technical audit documenting deterministic findings, semantic RAG grounding, and remediation telemetry.
          </p>
        </div>

        {/* Report Actions: Download Code, Copy Report, Download Report */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleDownloadCorrectedSource}
            disabled={downloadingCode}
            className="dev-btn-soft-blue px-4 py-2 text-xs sm:text-sm font-semibold cursor-pointer disabled:opacity-40"
            title="Download corrected source code file"
          >
            {downloadingCode ? (
              <span>Downloading Code...</span>
            ) : downloadCodeSuccess ? (
              <>
                <Check className="w-4 h-4 text-[#10B981]" />
                <span>Code Downloaded</span>
              </>
            ) : (
              <>
                <Download className="w-4 h-4 text-[#142B4A]" />
                <span>Download Code</span>
              </>
            )}
          </button>

          <button
            onClick={handleCopyReport}
            className="dev-btn-secondary px-4 py-2 text-xs sm:text-sm font-semibold cursor-pointer"
            title="Copy formatted Markdown report to clipboard"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 text-[#10B981]" />
                <span>Report Copied</span>
              </>
            ) : copyFailed ? (
              <>
                <XCircle className="w-4 h-4 text-[#EF4444]" />
                <span>Failed</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 text-[#606973]" />
                <span>Copy Report</span>
              </>
            )}
          </button>

          <button
            onClick={handleDownloadReport}
            disabled={downloading}
            className="dev-btn-primary px-4 py-2 text-xs sm:text-sm font-bold uppercase tracking-wider cursor-pointer disabled:opacity-40"
            title="Download complete Markdown report"
          >
            {downloading ? (
              <span>Generating Report...</span>
            ) : downloadSuccess ? (
              <>
                <Check className="w-4 h-4 text-white" />
                <span>Downloaded</span>
              </>
            ) : (
              <>
                <Download className="w-4 h-4 text-white" />
                <span>Download Report</span>
              </>
            )}
          </button>
        </div>
      </div>

      {downloadError && (
        <div className="p-3.5 rounded-xl bg-[#FEE2E2] border border-[#FECACA] text-xs text-[#991B1B] flex items-center justify-between">
          <span>{downloadError}</span>
          <button onClick={() => setDownloadError(null)} className="text-[#991B1B] hover:text-[#7F1D1D]">✕</button>
        </div>
      )}

      {/* Structured Report Canvas */}
      <div className="bg-[#F8FAFC] border border-[#E2E6EC] rounded-xl p-6 space-y-6 text-xs sm:text-sm">
        
        {/* Section 1: Executive Summary */}
        <div>
          <h4 className="font-mono font-bold uppercase tracking-wider text-[#142B4A] pb-2 border-b border-[#E2E6EC] mb-3">
            1. Executive Compliance Summary
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-3.5 rounded-xl bg-white border border-[#E2E6EC]">
              <span className="text-[#606973] uppercase block text-[11px] mb-1 font-semibold">Final Verdict</span>
              <span className={`text-base font-bold uppercase ${
                isClean ? 'text-[#1B5E36]' : isDegraded ? 'text-[#92400E]' : 'text-[#991B1B]'
              }`}>
                {verdict}
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-white border border-[#E2E6EC]">
              <span className="text-[#606973] uppercase block text-[11px] mb-1 font-semibold">Health Score</span>
              <span className="text-base font-mono font-bold text-[#142B4A]">
                {health_score.toFixed(1)} / 10.0
                {post_fix_score && post_fix_score !== health_score && (
                  <span className="text-xs text-[#1B5E36] font-normal ml-2">
                    (Post-Fix: {post_fix_score.toFixed(1)})
                  </span>
                )}
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-white border border-[#E2E6EC]">
              <span className="text-[#606973] uppercase block text-[11px] mb-1 font-semibold">Remediation Status</span>
              <span className="text-base font-mono font-bold text-[#4A2E7A] uppercase">
                {remediationStatus}
              </span>
            </div>
          </div>
          <p className="mt-3 text-[#343A40] leading-relaxed font-sans">
            {summary}
          </p>
        </div>

        {/* Section 2: Severity Distribution */}
        <div>
          <h4 className="font-mono font-bold uppercase tracking-wider text-[#142B4A] pb-2 border-b border-[#E2E6EC] mb-3">
            2. Defect Severity Breakdown
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div className="p-3 rounded-xl bg-[#FEE2E2] border border-[#FECACA]">
              <span className="font-mono uppercase text-[#991B1B] block text-[11px] font-semibold">Critical</span>
              <span className="text-xl font-mono font-bold text-[#991B1B]">{counts.critical || 0}</span>
            </div>
            <div className="p-3 rounded-xl bg-[#FFEDD5] border border-[#FED7AA]">
              <span className="font-mono uppercase text-[#9A3412] block text-[11px] font-semibold">High</span>
              <span className="text-xl font-mono font-bold text-[#9A3412]">{counts.high || 0}</span>
            </div>
            <div className="p-3 rounded-xl bg-[#FEF9C3] border border-[#FEF08A]">
              <span className="font-mono uppercase text-[#854D0E] block text-[11px] font-semibold">Medium</span>
              <span className="text-xl font-mono font-bold text-[#854D0E]">{counts.medium || 0}</span>
            </div>
            <div className="p-3 rounded-xl bg-[#F3F5F8] border border-[#E2E6EC]">
              <span className="font-mono uppercase text-[#343A40] block text-[11px] font-semibold">Low</span>
              <span className="text-xl font-mono font-bold text-[#343A40]">{counts.low || 0}</span>
            </div>
          </div>
          <div className="mt-3 flex items-center space-x-3 text-xs font-mono text-[#606973]">
            <span>Total: <strong className="text-[#142B4A]">{unresolved_count + resolved_count}</strong></span>
            <span>·</span>
            <span>Remediated: <strong className="text-[#1B5E36]">{resolved_count}</strong></span>
            <span>·</span>
            <span>Remaining: <strong className={unresolved_count > 0 ? 'text-[#991B1B]' : 'text-[#142B4A]'}>{unresolved_count}</strong></span>
          </div>
        </div>

        {/* Section 3: Static Analysis & Tools */}
        <div>
          <div className="flex items-center justify-between pb-2 border-b border-[#E2E6EC] mb-3">
            <h4 className="font-mono font-bold uppercase tracking-wider text-[#142B4A]">
              3. Tool &amp; Verification Environment
            </h4>
            {coverage && (
              <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-bold uppercase tracking-wider bg-[#DDF2E5] text-[#1B5E36] border border-[#C4E7D0]">
                {coverage === 'full' ? 'Full Native Coverage' : 'Partial Coverage'}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
            <div className="p-3 rounded-xl bg-white border border-[#E2E6EC]">
              <span className="text-[#606973] block text-[11px] mb-1 font-semibold">Linters for {language.toUpperCase()}:</span>
              <span className="text-[#142B4A] font-bold">{analyzerText}</span>
            </div>
            <div className="p-3 rounded-xl bg-white border border-[#E2E6EC]">
              <span className="text-[#606973] block text-[11px] mb-1 font-semibold">Pipeline Stages Executed:</span>
              <span className="text-[#4A2E7A] font-bold">{telemetry.length} Stages</span>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}

export default memo(AuditReportSection);
