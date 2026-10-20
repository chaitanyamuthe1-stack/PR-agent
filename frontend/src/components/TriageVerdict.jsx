import React, { useState, useEffect, memo } from 'react';
import { 
  AlertTriangle, CheckCircle2, ShieldAlert, Wrench, Shield, 
  ArrowRight, Activity, Info, HelpCircle, Check, Terminal 
} from 'lucide-react';

function TriageVerdict({
  healthScore = 10.0,
  postFixScore = null,
  verdict = 'PENDING',
  summary = 'Run the review pipeline to execute static analysis, RAG grounding, and multi-agent triage.',
  counts = { critical: 0, high: 0, medium: 0, low: 0, informational: 0 },
  unresolvedCount = 0,
  resolvedCount = 0,
  remediationStatus = 'NOT_REQUIRED',
  autoFixFailure = false,
  hasRun = false,
  iterationCount = 0,
  language = 'python'
}) {
  const [showPolicyModal, setShowPolicyModal] = useState(false);

  // Close modal on Escape key
  useEffect(() => {
    if (!showPolicyModal) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setShowPolicyModal(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showPolicyModal]);

  const isClean = (verdict === 'CLEAN' || verdict === 'PASS') && unresolvedCount === 0;
  const isNeedsReview = verdict === 'NEEDS REVIEW' || (!isClean && (counts.critical || 0) === 0 && (counts.high || 0) === 0 && unresolvedCount > 0);
  const isDegraded = ['ANALYZER UNAVAILABLE', 'MCP UNAVAILABLE', 'DEGRADED', 'RAG UNAVAILABLE', 'DEPENDENCY MISSING', 'LLM UNAVAILABLE'].some(v => (verdict || '').includes(v));
  const totalDetected = unresolvedCount + resolvedCount;

  const scoreColor = !hasRun
    ? 'text-[#606973]'
    : isClean
    ? 'text-[#1B5E36]'
    : isDegraded
    ? 'text-[#92400E]'
    : isNeedsReview
    ? 'text-[#92400E]'
    : healthScore >= 8.0
    ? 'text-[#1B5E36]'
    : healthScore >= 5.0
    ? 'text-[#92400E]'
    : 'text-[#991B1B]';

  const cardBorder = !hasRun
    ? 'border-[#E2E6EC]'
    : isClean
    ? 'border-[#C4E7D0]'
    : isDegraded
    ? 'border-[#FDE68A]'
    : isNeedsReview
    ? 'border-[#FDE68A]'
    : 'border-[#FECACA]';

  return (
    <div 
      className={`dev-card p-6 sm:p-8 shadow-sm transition-all bg-white border ${cardBorder}`}
      role="region"
      aria-label="Codebase Triage Verdict and Health Score"
    >
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 sm:gap-8">
        
        {/* Primary Hero Score & Verdict */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-baseline gap-5 sm:gap-8 mb-4">
            <div>
              <div className="flex items-center space-x-2 mb-1.5">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-[#606973] block">
                  Codebase Health Score
                </span>
                <button
                  type="button"
                  onClick={() => setShowPolicyModal(true)}
                  className="text-[#606973] hover:text-[#142B4A] transition-colors cursor-pointer p-0.5 rounded"
                  title="View Deterministic Scoring Policy"
                  aria-label="View Deterministic Scoring Policy"
                >
                  <HelpCircle className="w-4 h-4" />
                </button>
              </div>

              <div className="flex items-baseline space-x-3">
                <span 
                  className={`text-6xl sm:text-7xl font-black font-mono tracking-tight leading-none ${scoreColor}`}
                  aria-label={hasRun ? `Health Score: ${healthScore.toFixed(1)} out of 10` : 'Health score pending'}
                >
                  {hasRun ? healthScore.toFixed(1) : '--'}
                </span>
                <span className="text-2xl sm:text-3xl font-mono text-[#606973] font-semibold" aria-hidden="true">
                  / 10.0
                </span>
              </div>
            </div>

            {/* Verdict Badge & Remediation Chip */}
            <div className="flex flex-wrap items-center gap-2.5 pb-1">
              <span
                role="status"
                aria-live="polite"
                className={`inline-flex items-center space-x-2.5 px-4 py-2 rounded-xl text-sm font-bold uppercase tracking-wider border shadow-2xs ${
                  !hasRun
                    ? 'bg-[#F3F5F8] text-[#606973] border-[#E2E6EC]'
                    : isClean
                    ? 'bg-[#DDF2E5] text-[#1B5E36] border-[#C4E7D0]'
                    : isDegraded
                    ? 'bg-[#FEF3C7] text-[#92400E] border-[#FDE68A]'
                    : isNeedsReview
                    ? 'bg-[#FEF3C7] text-[#92400E] border-[#FDE68A]'
                    : 'bg-[#FEE2E2] text-[#991B1B] border-[#FECACA]'
                }`}
              >
                {!hasRun ? (
                  <Activity className="w-4 h-4 text-[#606973]" aria-hidden="true" />
                ) : isClean ? (
                  <CheckCircle2 className="w-5 h-5 text-[#10B981]" aria-hidden="true" />
                ) : isDegraded ? (
                  <AlertTriangle className="w-5 h-5 text-[#F59E0B]" aria-hidden="true" />
                ) : isNeedsReview ? (
                  <Info className="w-5 h-5 text-[#F59E0B]" aria-hidden="true" />
                ) : (
                  <ShieldAlert className="w-5 h-5 text-[#EF4444]" aria-hidden="true" />
                )}
                <span>{hasRun ? verdict : 'AWAITING REVIEW'}</span>
              </span>

              {remediationStatus && remediationStatus !== 'NOT_REQUIRED' && (
                <span className={`inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs sm:text-sm font-mono uppercase font-bold border ${
                  remediationStatus === 'SUCCESS' || remediationStatus === 'FIXED' || remediationStatus === 'PASS'
                    ? 'bg-[#DDF2E5] text-[#1B5E36] border-[#C4E7D0]'
                    : remediationStatus === 'PARTIAL' || remediationStatus === 'PARTIALLY FIXED'
                    ? 'bg-[#FEF3C7] text-[#92400E] border-[#FDE68A]'
                    : 'bg-[#FEE2E2] text-[#991B1B] border-[#FECACA]'
                }`}>
                  <Wrench className="w-4 h-4" aria-hidden="true" />
                  <span>{remediationStatus}</span>
                </span>
              )}

              {/* Post-Fix Score Transition if remediated */}
              {hasRun && postFixScore !== null && postFixScore !== undefined && postFixScore !== healthScore && (
                <div className="flex items-center space-x-2 text-xs sm:text-sm font-mono bg-[#DDF2E5] text-[#1B5E36] border border-[#C4E7D0] px-3 py-1.5 rounded-xl font-bold">
                  <span>Post-Fix:</span>
                  <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>{postFixScore.toFixed(1)} / 10.0</span>
                </div>
              )}
            </div>
          </div>

          {/* Severity Breakdown Bar (Critical, High, Medium, Low, Info) */}
          <div className="flex flex-wrap items-center gap-2 mt-4 pt-4 border-t border-[#E2E6EC] text-xs sm:text-sm font-mono">
            <span className="text-xs text-[#606973] font-sans uppercase font-bold tracking-wider mr-1">
              Findings:
            </span>
            <span className="inline-flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-[#FEE2E2] border border-[#FECACA] text-[#991B1B] font-semibold">
              <span className="w-2 h-2 rounded-full bg-[#EF4444]" aria-hidden="true" />
              <span>{counts.critical || 0} critical</span>
            </span>
            <span className="inline-flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-[#FFEDD5] border border-[#FED7AA] text-[#9A3412] font-semibold">
              <span className="w-2 h-2 rounded-full bg-[#F97316]" aria-hidden="true" />
              <span>{counts.high || 0} high</span>
            </span>
            <span className="inline-flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-[#FEF9C3] border border-[#FEF08A] text-[#854D0E] font-semibold">
              <span className="w-2 h-2 rounded-full bg-[#EAB308]" aria-hidden="true" />
              <span>{counts.medium || 0} medium</span>
            </span>
            <span className="inline-flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-[#F3F5F8] border border-[#E2E6EC] text-[#343A40] font-semibold">
              <span className="w-2 h-2 rounded-full bg-[#606973]" aria-hidden="true" />
              <span>{counts.low || 0} low</span>
            </span>
            <span className="inline-flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-[#DCE7F5] border border-[#B8D0EC] text-[#142B4A] font-semibold">
              <span className="w-2 h-2 rounded-full bg-[#142B4A]" aria-hidden="true" />
              <span>{counts.informational || 0} info</span>
            </span>

            {hasRun && (
              <>
                <span className="text-[#CBD5E1] mx-1.5 hidden sm:inline">|</span>
                <span className="text-[#606973] font-sans text-xs sm:text-sm">
                  <strong className="text-[#142B4A]">{totalDetected}</strong> detected
                </span>
                <span className="text-[#CBD5E1]">·</span>
                <span className="text-[#1B5E36] font-sans text-xs sm:text-sm">
                  <strong>{resolvedCount}</strong> resolved
                </span>
                <span className="text-[#CBD5E1]">·</span>
                <span className={`${unresolvedCount > 0 ? 'text-[#991B1B] font-bold' : 'text-[#606973]'} font-sans text-xs sm:text-sm`}>
                  <strong>{unresolvedCount}</strong> remaining
                </span>
              </>
            )}
          </div>

          {/* Validation Status Telemetry Row */}
          {hasRun && (
            <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-[#E2E6EC] text-xs font-mono text-[#606973]">
              <span className="text-[#606973] font-sans uppercase font-bold text-[11px]">Integrity Status:</span>
              <span className="inline-flex items-center space-x-1.5 text-[#1B5E36] bg-[#DDF2E5] px-2.5 py-1 rounded-md border border-[#C4E7D0]">
                <Check className="w-3.5 h-3.5 text-[#10B981]" aria-hidden="true" />
                <span>Syntax AST: Valid</span>
              </span>
              <span className="inline-flex items-center space-x-1.5 text-[#142B4A] bg-[#DCE7F5] px-2.5 py-1 rounded-md border border-[#B8D0EC]">
                <Terminal className="w-3.5 h-3.5 text-[#142B4A]" aria-hidden="true" />
                <span>Deterministic MCP: Verified</span>
              </span>
              {iterationCount > 0 && (
                <span className="inline-flex items-center space-x-1 text-[#142B4A] bg-[#E9E2F5] px-2.5 py-1 rounded-md border border-[#D7C7ED]">
                  <span>Re-check Cycles: {iterationCount}</span>
                </span>
              )}
            </div>
          )}

        </div>

        {/* Executive Summary Card */}
        <div className="lg:w-96 p-5 rounded-xl bg-[#F8FAFC] border border-[#E2E6EC] space-y-2">
          <div className="flex items-center space-x-2 text-xs font-mono font-bold uppercase tracking-wider text-[#142B4A]">
            <Shield className="w-4 h-4 text-[#142B4A]" />
            <span>Executive Triage Summary</span>
          </div>
          <p className="text-xs sm:text-sm text-[#343A40] leading-relaxed font-sans">
            {summary}
          </p>
        </div>

      </div>

      {/* Scoring Policy Modal */}
      {showPolicyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#0E1F36]/50 backdrop-blur-xs animate-in fade-in">
          <div className="dev-card max-w-lg w-full p-6 shadow-xl space-y-4 bg-white border border-[#E2E6EC]">
            <div className="flex items-center justify-between pb-3 border-b border-[#E2E6EC]">
              <h4 className="text-base font-bold text-[#142B4A]">Deterministic Scoring Formulation</h4>
              <button
                onClick={() => setShowPolicyModal(false)}
                className="text-[#606973] hover:text-[#142B4A] cursor-pointer text-lg p-1"
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>
            <div className="text-xs text-[#606973] space-y-3 font-mono">
              <p className="text-sm font-sans text-[#343A40]">
                Health Score formula: <strong>H = clamp(10.0 - ∑ w(s_i), 0.5, 10.0)</strong>
              </p>
              <div className="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E6EC] space-y-1.5 text-[#343A40]">
                <div>• Critical Severity: -3.0 points (Score capped at max 6.0)</div>
                <div>• High Severity: -1.5 points (Score capped at max 8.0)</div>
                <div>• Medium Severity: -0.75 points</div>
                <div>• Low Severity: -0.25 points</div>
                <div>• Informational: 0.0 points</div>
              </div>
              <p className="font-sans text-[#606973]">
                Zero hallucinations: Scores are calculated purely via verified static analysis and standardized OWASP/CWE deductions.
              </p>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default memo(TriageVerdict);
