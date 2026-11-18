import React, { useState, useEffect, useRef, useMemo, memo } from 'react';
import { 
  Copy, Download, Check, SplitSquareVertical, Code2, GitCommit, 
  CheckCircle2, Wrench, RefreshCw, XCircle, Eye, Sparkles
} from 'lucide-react';
import { downloadCorrectedCode, downloadAuditReport } from '../services/api';

/**
 * Computes Myers/LCS diff between original and corrected text.
 * Returns aligned diff operations: 'equal', 'del', 'add'.
 */
function computeLineDiff(origText, corrText) {
  const orig = (origText || '').split('\n');
  const corr = (corrText || '').split('\n');

  const m = orig.length;
  const n = corr.length;

  if (m * n > 250000 || m > 800 || n > 800) {
    const maxLen = Math.max(m, n);
    const ops = [];
    for (let k = 0; k < maxLen; k++) {
      const o = orig[k];
      const c = corr[k];
      if (o === c) {
        ops.push({ type: 'equal', origLine: o, corrLine: c, origIdx: k + 1, corrIdx: k + 1 });
      } else {
        if (o !== undefined) ops.push({ type: 'del', origLine: o, origIdx: k + 1 });
        if (c !== undefined) ops.push({ type: 'add', corrLine: c, corrIdx: k + 1 });
      }
    }
    return ops;
  }

  const dp = Array.from({ length: m + 1 }, () => new Uint16Array(n + 1));
  for (let i = 0; i < m; i++) {
    for (let j = 0; j < n; j++) {
      if (orig[i] === corr[j]) {
        dp[i + 1][j + 1] = dp[i][j] + 1;
      } else {
        dp[i + 1][j + 1] = Math.max(dp[i + 1][j], dp[i][j + 1]);
      }
    }
  }

  let i = m, j = n;
  const rawOps = [];
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && orig[i - 1] === corr[j - 1]) {
      rawOps.push({ type: 'equal', origLine: orig[i - 1], corrLine: corr[j - 1], origIdx: i, corrIdx: j });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      rawOps.push({ type: 'add', corrLine: corr[j - 1], corrIdx: j });
      j--;
    } else if (i > 0 && (j === 0 || dp[i][j - 1] < dp[i - 1][j])) {
      rawOps.push({ type: 'del', origLine: orig[i - 1], origIdx: i });
      i--;
    }
  }

  rawOps.reverse();
  return rawOps;
}

function CodeDiffViewer({
  originalCode = '',
  correctedCode = '',
  changelog = [],
  language = 'python',
  filename = 'source_code.txt',
  reviewId = null,
  unresolvedCount = 0,
  resolvedCount = 0,
  remediationStatus = 'NOT_REQUIRED',
  autoFixFailure = false,
  mcpTools = [],
  targetedLine = null,
  onApplyFix = null,
  onRecheck = null,
  onApplyToEditor = null,
  remediating = false,
  rechecking = false,
  fixStateMessage = null,
  postFixScore = null
}) {
  const [viewMode, setViewMode] = useState('side-by-side');
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);
  const [downloadingCode, setDownloadingCode] = useState(false);
  const [downloadCodeSuccess, setDownloadCodeSuccess] = useState(false);
  const [downloadError, setDownloadError] = useState(null);

  const targetedLineRef = useRef(null);

  useEffect(() => {
    if (targetedLine && targetedLineRef.current) {
      targetedLineRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [targetedLine]);

  const origClean = (originalCode || '').trim();
  const corrClean = (correctedCode || originalCode || '').trim();
  const isCodeModified = origClean !== corrClean && ((changelog && changelog.length > 0) || remediationStatus === 'SUCCESS' || remediationStatus === 'PARTIAL');

  const origLines = useMemo(() => (originalCode || '').split('\n'), [originalCode]);
  const corrLines = useMemo(() => (correctedCode || originalCode || '').split('\n'), [correctedCode, originalCode]);

  const diffOps = useMemo(() => {
    return computeLineDiff(originalCode, correctedCode || originalCode);
  }, [originalCode, correctedCode]);

  const alignedSideBySide = useMemo(() => {
    const pairs = [];
    let idx = 0;
    while (idx < diffOps.length) {
      const op = diffOps[idx];
      if (op.type === 'equal') {
        pairs.push({
          left: { line: op.origLine, num: op.origIdx, type: 'equal' },
          right: { line: op.corrLine, num: op.corrIdx, type: 'equal' }
        });
        idx++;
      } else if (op.type === 'del') {
        if (idx + 1 < diffOps.length && diffOps[idx + 1].type === 'add') {
          pairs.push({
            left: { line: op.origLine, num: op.origIdx, type: 'del' },
            right: { line: diffOps[idx + 1].corrLine, num: diffOps[idx + 1].corrIdx, type: 'add' }
          });
          idx += 2;
        } else {
          pairs.push({
            left: { line: op.origLine, num: op.origIdx, type: 'del' },
            right: { line: '', num: null, type: 'empty' }
          });
          idx++;
        }
      } else if (op.type === 'add') {
        pairs.push({
          left: { line: '', num: null, type: 'empty' },
          right: { line: op.corrLine, num: op.corrIdx, type: 'add' }
        });
        idx++;
      }
    }
    return pairs;
  }, [diffOps]);

  const analyzerName = mcpTools && mcpTools.length > 0 ? (Array.isArray(mcpTools) ? mcpTools.join(', ') : String(mcpTools)) : 'MCP Linters';

  const handleCopy = async () => {
    try {
      const codeToCopy = viewMode === 'original' ? originalCode : (correctedCode || originalCode);
      await navigator.clipboard.writeText(codeToCopy);
      setCopied(true);
      setCopyFailed(false);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      setCopyFailed(true);
      setTimeout(() => setCopyFailed(false), 2500);
    }
  };

  const handleDownloadCode = async () => {
    setDownloadingCode(true);
    setDownloadError(null);
    try {
      const extMap = { python: '.py', cpp: '.cpp', c: '.c', java: '.java', javascript: '.js', ruby: '.rb' };
      const ext = extMap[language] || '.txt';
      const baseName = filename.replace(/\.[^/.]+$/, "");
      await downloadCorrectedCode(reviewId, `${baseName}_corrected${ext}`);
      setDownloadCodeSuccess(true);
      setTimeout(() => setDownloadCodeSuccess(false), 2000);
    } catch (err) {
      setDownloadError(`Download failed: ${err.message}`);
    } finally {
      setDownloadingCode(false);
    }
  };

  return (
    <div id="code-remediation-panel" className="dev-card p-6 sm:p-7 shadow-sm space-y-6 bg-white border border-[#E2E6EC]">
      
      {/* Panel Header & Controls */}
      <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between pb-4 border-b border-[#E2E6EC] gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <span className="w-3 h-3 rounded-full bg-[#142B4A]" />
            <h3 className="text-lg sm:text-xl font-bold text-[#142B4A] tracking-tight">
              Code Correction &amp; Diff
            </h3>
          </div>
          <p className="text-xs sm:text-sm text-[#606973] mt-1">
            Grounded multi-agent auto-correction with Myers line diff and re-check verification.
          </p>
        </div>

        {/* View Mode & Action Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Mode Selector */}
          <div className="bg-[#F3F5F8] border border-[#E2E6EC] rounded-xl p-1 flex items-center">
            <button
              onClick={() => setViewMode('side-by-side')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all cursor-pointer ${
                viewMode === 'side-by-side'
                  ? 'bg-[#142B4A] text-white shadow-xs font-bold'
                  : 'text-[#606973] hover:text-[#142B4A]'
              }`}
            >
              <SplitSquareVertical className="w-3.5 h-3.5" />
              <span>Side-by-Side</span>
            </button>

            <button
              onClick={() => setViewMode('unified')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all cursor-pointer ${
                viewMode === 'unified'
                  ? 'bg-[#142B4A] text-white shadow-xs font-bold'
                  : 'text-[#606973] hover:text-[#142B4A]'
              }`}
            >
              <Code2 className="w-3.5 h-3.5" />
              <span>Unified</span>
            </button>

            <button
              onClick={() => setViewMode('corrected')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all cursor-pointer ${
                viewMode === 'corrected'
                  ? 'bg-[#142B4A] text-white shadow-xs font-bold'
                  : 'text-[#606973] hover:text-[#142B4A]'
              }`}
            >
              <Check className="w-3.5 h-3.5" />
              <span>Corrected Only</span>
            </button>

            <button
              onClick={() => setViewMode('original')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all cursor-pointer ${
                viewMode === 'original'
                  ? 'bg-[#142B4A] text-white shadow-xs font-bold'
                  : 'text-[#606973] hover:text-[#142B4A]'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Original</span>
            </button>
          </div>

          {/* Action Buttons: Apply Fix, Re-Check, Copy, Download */}
          {onApplyFix && (
            <button
              onClick={onApplyFix}
              disabled={remediating || rechecking || !originalCode.trim()}
              className="dev-btn-primary px-4 py-2 text-xs sm:text-sm font-bold uppercase tracking-wider cursor-pointer disabled:opacity-40"
              title="Execute Coder Agent remediation"
            >
              {remediating ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Applying...</span>
                </>
              ) : (
                <>
                  <Wrench className="w-4 h-4" />
                  <span>Apply Fix</span>
                </>
              )}
            </button>
          )}

          {onApplyToEditor && isCodeModified && (
            <div className="flex items-center space-x-2">
              {postFixScore !== null && postFixScore !== undefined && (
                <div className="hidden sm:inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#DDF2E5] border border-[#C4E7D0] text-[#1B5E36] font-mono text-xs font-bold shadow-2xs">
                  <Sparkles className="w-3.5 h-3.5 text-[#10B981]" />
                  <span>Corrected Score: {postFixScore.toFixed(1)}/10.0</span>
                </div>
              )}
              <button
                onClick={() => onApplyToEditor(correctedCode || originalCode)}
                disabled={remediating || rechecking}
                className="dev-btn-primary px-4 py-2 text-xs sm:text-sm font-bold uppercase tracking-wider cursor-pointer bg-[#10B981] hover:bg-[#059669] text-white border-none flex items-center space-x-1.5 shadow-xs transition-colors"
                title="Apply auto-corrected code to main editor"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Apply to Editor</span>
              </button>
            </div>
          )}

          {onRecheck && (
            <button
              onClick={onRecheck}
              disabled={rechecking || remediating || !corrClean}
              className="dev-btn-mint px-4 py-2 text-xs sm:text-sm font-bold uppercase tracking-wider cursor-pointer disabled:opacity-40"
              title="Run static analysis and review against corrected code"
            >
              {rechecking ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-[#1B5E36] border-t-transparent rounded-full animate-spin" />
                  <span>Re-checking...</span>
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4" />
                  <span>Re-Check</span>
                </>
              )}
            </button>
          )}

          <button
            onClick={handleCopy}
            className="dev-btn-secondary px-3.5 py-2 text-xs font-semibold cursor-pointer"
            title="Copy Code to Clipboard"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 text-[#10B981]" />
                <span>Copied</span>
              </>
            ) : copyFailed ? (
              <>
                <XCircle className="w-4 h-4 text-[#EF4444]" />
                <span>Failed</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 text-[#606973]" />
                <span>Copy</span>
              </>
            )}
          </button>

          <button
            onClick={handleDownloadCode}
            disabled={downloadingCode}
            className="dev-btn-soft-blue px-3.5 py-2 text-xs font-semibold cursor-pointer disabled:opacity-40"
            title="Download Corrected Source File"
          >
            {downloadingCode ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-[#142B4A] border-t-transparent rounded-full animate-spin" />
                <span>Downloading...</span>
              </>
            ) : downloadCodeSuccess ? (
              <>
                <Check className="w-4 h-4 text-[#10B981]" />
                <span>Downloaded</span>
              </>
            ) : (
              <>
                <Download className="w-4 h-4 text-[#142B4A]" />
                <span>Download</span>
              </>
            )}
          </button>
        </div>
      </div>

      {fixStateMessage && (
        <div className="p-3.5 rounded-xl bg-[#E9E2F5] border border-[#D7C7ED] text-xs sm:text-sm text-[#4A2E7A]">
          {fixStateMessage}
        </div>
      )}

      {downloadError && (
        <div className="p-3.5 rounded-xl bg-[#FEE2E2] border border-[#FECACA] text-xs text-[#991B1B] flex items-center justify-between">
          <span>{downloadError}</span>
          <button onClick={() => setDownloadError(null)} className="text-[#991B1B] hover:text-[#7F1D1D]">✕</button>
        </div>
      )}

      {/* Main Diff Viewing Area */}
      <div className="dev-subcard overflow-hidden rounded-xl border border-[#E2E6EC] bg-white">
        {viewMode === 'side-by-side' ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-[#E2E6EC]">
            
            {/* Left Column: Original Code */}
            <div className="overflow-x-auto">
              <div className="bg-[#F3F5F8] px-4 py-2.5 border-b border-[#E2E6EC] text-xs font-bold font-mono text-[#142B4A] flex items-center justify-between">
                <span>ORIGINAL SOURCE ({filename})</span>
                <span className="text-[#606973] text-xs font-normal">{origLines.length} lines</span>
              </div>
              <div className="p-3.5 space-y-1 max-h-[520px] overflow-y-auto leading-relaxed bg-white">
                {alignedSideBySide.map((pair, idx) => {
                  const item = pair.left;
                  const isTargeted = targetedLine === item.num;
                  const isDel = item.type === 'del';
                  return (
                    <div
                      key={idx}
                      ref={isTargeted ? targetedLineRef : null}
                      className={`flex items-start px-2 py-0.5 rounded transition-all duration-150 ${
                        isTargeted
                          ? 'gutter-line-target'
                          : isDel && isCodeModified
                          ? 'diff-del'
                          : item.type === 'empty'
                          ? 'opacity-20 select-none'
                          : 'hover:bg-[#F8FAFC]'
                      }`}
                    >
                      <span className={`w-10 text-right pr-3 select-none text-xs font-mono shrink-0 ${
                        isTargeted ? 'text-[#142B4A] font-bold' : isDel ? 'text-[#991B1B] font-semibold' : 'text-[#606973]'
                      }`}>
                        {item.num !== null ? item.num : ' '}
                      </span>
                      <pre className={`whitespace-pre overflow-x-auto font-mono text-sm leading-relaxed ${
                        isDel ? 'text-[#991B1B]' : 'text-[#343A40]'
                      }`}>
                        {item.line || (item.type === 'empty' ? ' ' : ' ')}
                      </pre>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right Column: Corrected Code */}
            <div className="overflow-x-auto">
              <div className={`px-4 py-2.5 border-b border-[#E2E6EC] text-xs font-bold font-mono flex items-center justify-between ${
                isCodeModified ? 'bg-[#DDF2E5]/50 text-[#1B5E36]' : 'bg-[#F3F5F8] text-[#142B4A]'
              }`}>
                <span>
                  {isCodeModified ? 'CORRECTED SOURCE (AUTO-REMEDIATED)' : 'CORRECTED SOURCE — NO CHANGE'}
                </span>
                <span className="text-[#606973] text-xs font-normal">{corrLines.length} lines</span>
              </div>
              <div className="p-3.5 space-y-1 max-h-[520px] overflow-y-auto leading-relaxed bg-white">
                {alignedSideBySide.map((pair, idx) => {
                  const item = pair.right;
                  const isTargeted = targetedLine === item.num;
                  const isAdd = item.type === 'add';
                  return (
                    <div
                      key={idx}
                      className={`flex items-start px-2 py-0.5 rounded transition-all duration-150 ${
                        isTargeted
                          ? 'gutter-line-target'
                          : isAdd && isCodeModified
                          ? 'diff-add'
                          : item.type === 'empty'
                          ? 'opacity-20 select-none'
                          : 'hover:bg-[#F8FAFC]'
                      }`}
                    >
                      <span className={`w-10 text-right pr-3 select-none text-xs font-mono shrink-0 ${
                        isTargeted ? 'text-[#142B4A] font-bold' : isAdd ? 'text-[#14532D] font-semibold' : 'text-[#606973]'
                      }`}>
                        {item.num !== null ? item.num : ' '}
                      </span>
                      <pre className={`whitespace-pre overflow-x-auto font-mono text-sm leading-relaxed ${
                        isAdd ? 'text-[#14532D]' : 'text-[#343A40]'
                      }`}>
                        {item.line || (item.type === 'empty' ? ' ' : ' ')}
                      </pre>
                    </div>
                  );
                })}
              </div>
            </div>

          </div>
        ) : viewMode === 'unified' ? (
          <div className="overflow-x-auto">
            <div className="bg-[#F3F5F8] px-4 py-2.5 border-b border-[#E2E6EC] text-xs font-bold font-mono text-[#142B4A] flex items-center justify-between">
              <span>UNIFIED DIFF ({filename})</span>
              <span className="text-[#606973] text-xs font-normal">Additions &amp; Deletions Highlighted</span>
            </div>
            <div className="p-3.5 space-y-1 max-h-[520px] overflow-y-auto leading-relaxed bg-white">
              {diffOps.map((op, idx) => {
                if (op.type === 'del') {
                  const isTargeted = targetedLine === op.origIdx;
                  return (
                    <div
                      key={idx}
                      ref={isTargeted ? targetedLineRef : null}
                      className={`flex items-start px-2 py-0.5 diff-del rounded ${isTargeted ? 'ring-2 ring-[#142B4A]' : ''}`}
                    >
                      <span className="w-6 text-right pr-2 text-[#991B1B] select-none text-xs font-mono font-bold">-</span>
                      <span className="w-8 text-right pr-2.5 text-[#606973] select-none text-xs font-mono shrink-0">{op.origIdx}</span>
                      <pre className="text-[#991B1B] whitespace-pre overflow-x-auto font-mono text-sm leading-relaxed">{op.origLine}</pre>
                    </div>
                  );
                } else if (op.type === 'add') {
                  return (
                    <div
                      key={idx}
                      className="flex items-start px-2 py-0.5 diff-add rounded"
                    >
                      <span className="w-6 text-right pr-2 text-[#14532D] select-none text-xs font-mono font-bold">+</span>
                      <span className="w-8 text-right pr-2.5 text-[#606973] select-none text-xs font-mono shrink-0">{op.corrIdx}</span>
                      <pre className="text-[#14532D] whitespace-pre overflow-x-auto font-mono text-sm leading-relaxed">{op.corrLine}</pre>
                    </div>
                  );
                } else {
                  const isTargeted = targetedLine === op.origIdx;
                  return (
                    <div
                      key={idx}
                      ref={isTargeted ? targetedLineRef : null}
                      className={`flex items-start px-2 py-0.5 rounded ${
                        isTargeted ? 'gutter-line-target' : 'hover:bg-[#F8FAFC]'
                      }`}
                    >
                      <span className="w-6 text-right pr-2 text-[#606973] select-none text-xs font-mono"> </span>
                      <span className={`w-8 text-right pr-2.5 select-none text-xs font-mono shrink-0 ${
                        isTargeted ? 'text-[#142B4A] font-bold' : 'text-[#606973]'
                      }`}>
                        {op.origIdx}
                      </span>
                      <pre className="text-[#343A35] whitespace-pre overflow-x-auto font-mono text-sm leading-relaxed">{op.origLine || ' '}</pre>
                    </div>
                  );
                }
              })}
            </div>
          </div>
        ) : viewMode === 'original' ? (
          <div className="overflow-x-auto">
            <div className="bg-[#F3F5F8] px-4 py-2.5 border-b border-[#E2E6EC] text-xs font-bold font-mono text-[#991B1B] flex items-center justify-between">
              <span>ORIGINAL SOURCE CODE ({filename}) — PRESERVED</span>
              <span className="text-[#606973] text-xs font-normal">{origLines.length} lines</span>
            </div>
            <div className="p-3.5 space-y-1 max-h-[520px] overflow-y-auto leading-relaxed bg-white">
              {origLines.map((line, idx) => {
                const lineNum = idx + 1;
                const isTargeted = targetedLine === lineNum;
                return (
                  <div
                    key={idx}
                    ref={isTargeted ? targetedLineRef : null}
                    className={`flex items-start px-2 py-0.5 rounded ${
                      isTargeted ? 'gutter-line-target' : 'hover:bg-[#F8FAFC]'
                    }`}
                  >
                    <span className={`w-10 text-right pr-3 select-none text-xs font-mono shrink-0 ${
                      isTargeted ? 'text-[#142B4A] font-bold' : 'text-[#606973]'
                    }`}>
                      {lineNum}
                    </span>
                    <pre className="text-[#343A35] whitespace-pre overflow-x-auto font-mono text-sm leading-relaxed">
                      {line || ' '}
                    </pre>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <div className="bg-[#DDF2E5]/50 px-4 py-2.5 border-b border-[#E2E6EC] text-xs font-bold font-mono text-[#1B5E36] flex items-center justify-between">
              <span>CORRECTED SOURCE CODE ({filename})</span>
              <span className="text-[#606973] text-xs font-normal">{corrLines.length} lines</span>
            </div>
            <div className="p-3.5 space-y-1 max-h-[520px] overflow-y-auto leading-relaxed bg-white">
              {corrLines.map((line, idx) => {
                const lineNum = idx + 1;
                const isTargeted = targetedLine === lineNum;
                return (
                  <div
                    key={idx}
                    ref={isTargeted ? targetedLineRef : null}
                    className={`flex items-start px-2 py-0.5 rounded ${
                      isTargeted ? 'gutter-line-target' : 'hover:bg-[#F8FAFC]'
                    }`}
                  >
                    <span className={`w-10 text-right pr-3 select-none text-xs font-mono shrink-0 ${
                      isTargeted ? 'text-[#142B4A] font-bold' : 'text-[#606973]'
                    }`}>
                      {lineNum}
                    </span>
                    <pre className="text-[#343A35] whitespace-pre overflow-x-auto font-mono text-sm leading-relaxed">
                      {line || ' '}
                    </pre>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Refactoring Changelog */}
      <div className="pt-4 border-t border-[#E2E6EC]">
        <div className="flex items-center space-x-2.5 mb-4">
          <GitCommit className="w-4 h-4 text-[#142B4A]" />
          <h4 className="text-sm font-bold uppercase tracking-wider text-[#142B4A]">
            Refactoring Changelog ({changelog.length} modifications)
          </h4>
        </div>

        {changelog.length === 0 ? (
          <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#E2E6EC] text-xs sm:text-sm text-[#606973] font-sans">
            <strong className="text-[#142B4A]">0 modifications recorded.</strong> Remediation: {unresolvedCount > 0 ? 'Not applied' : 'Not required'}.
          </div>
        ) : (
          <div className="space-y-3">
            {changelog.map((entry, idx) => (
              <div
                key={idx}
                className="dev-subcard p-4 sm:p-5 border border-[#E2E6EC] shadow-2xs rounded-xl bg-[#F8FAFC]"
              >
                <div className="flex flex-wrap items-center justify-between pb-2.5 border-b border-[#E2E6EC] gap-2">
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 rounded font-mono text-xs font-bold bg-[#E9E2F5] text-[#4A2E7A] border border-[#D7C7ED]">
                      #{String(idx + 1).padStart(3, '0')}
                    </span>
                    <span className="text-xs sm:text-sm font-semibold text-[#142B4A]">
                      {filename} · <span className="font-mono text-[#142B4A]">Line {entry.line_affected || 'N/A'}</span>
                    </span>
                    <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold uppercase bg-white text-[#606973] border border-[#E2E6EC]">
                      {entry.change_type || 'SECURITY FIX'}
                    </span>
                  </div>

                  <div className="flex items-center space-x-2">
                    <span className="inline-flex items-center space-x-1.5 text-xs font-mono text-[#1B5E36] bg-[#DDF2E5] px-2.5 py-1 rounded-md border border-[#C4E7D0]">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Verified with {analyzerName}</span>
                    </span>
                  </div>
                </div>

                <p className="text-xs sm:text-sm text-[#343A40] mt-2.5 leading-relaxed font-sans">
                  {entry.description}
                </p>

                {(entry.before || entry.after) && (
                  <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2.5 text-xs font-mono">
                    {entry.before && (
                      <div className="p-3 rounded-lg bg-[#FEE2E2] border border-[#FECACA]">
                        <span className="text-[10px] font-bold text-[#991B1B] block mb-1 uppercase tracking-wider">Before</span>
                        <pre className="text-[#991B1B] overflow-x-auto whitespace-pre-wrap text-xs">{entry.before}</pre>
                      </div>
                    )}
                    {entry.after && (
                      <div className="p-3 rounded-lg bg-[#DDF2E5] border border-[#C4E7D0]">
                        <span className="text-[10px] font-bold text-[#14532D] block mb-1 uppercase tracking-wider">After (Remediated)</span>
                        <pre className="text-[#14532D] overflow-x-auto whitespace-pre-wrap text-xs">{entry.after}</pre>
                      </div>
                    )}
                  </div>
                )}

                <div className="mt-3 flex items-center justify-between text-xs text-[#606973] pt-2 border-t border-[#E2E6EC]">
                  <span>Agent: <strong className="text-[#142B4A]">Coder Agent</strong></span>
                  <span className="font-mono text-[#142B4A]">Rule: {entry.rule_citation}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}

export default memo(CodeDiffViewer);
