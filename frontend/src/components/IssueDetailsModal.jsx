import React, { useState } from 'react';
import { X, ShieldAlert, AlertTriangle, CheckCircle2, Bookmark, FileCode, Copy, Check, Terminal, ExternalLink, Activity, Bot, Shield } from 'lucide-react';

export default function IssueDetailsModal({ isOpen, onClose, issue, filename = 'source_code.txt' }) {
  if (!isOpen || !issue) return null;

  const [copiedRec, setCopiedRec] = useState(false);

  const issueId = issue.id || issue.finding_id || `${(issue.category || 'ISSUE').toUpperCase()}-${String(issue.line || 1).padStart(3, '0')}`;
  const severity = (issue.severity || 'medium').toUpperCase();
  const category = (issue.category || 'bug').toUpperCase();
  const ruleCitation = issue.rule_citation || issue.rule_id || 'Standard Security Rule';
  const cwe = issue.cwe ? (issue.cwe.startsWith('CWE-') ? issue.cwe : `CWE-${issue.cwe}`) : 'OWASP Top 10';
  const owasp = issue.owasp || (category === 'SECURITY' ? 'OWASP Top 10' : 'N/A');
  const line = issue.line || 1;
  const description = issue.description || 'No detailed description provided.';
  const recommendation = issue.recommendation || 'Follow grounded defensive coding guidelines.';
  const rawOutput = issue.evidence || issue.raw_linter_output || null;
  const detectionSource = issue.detection_source || issue.tool || (category === 'SECURITY' ? 'security_agent' : 'bug_agent');
  const isVerifiedStatic = issue.verification_status === 'verified_static' || issue.verified;
  const verificationStatus = issue.verification_status || (isVerifiedStatic ? 'verified_static' : 'unverified_llm_observation');
  
  const isIgnored = issue.ignored || false;
  const isResolved = issue.resolved || false;
  const currentStatus = isIgnored ? 'IGNORED' : isResolved ? 'RESOLVED' : 'UNRESOLVED (ACTIONABLE)';
  const resolutionStatus = isIgnored
    ? 'Finding marked as ignored by review engineer. Omitted from actionable defect triage count.'
    : isResolved
    ? 'Defect successfully eradicated by Coder Agent auto-remediation and verified by re-check analyzer.'
    : 'Active actionable defect. Must be remediated or verified before PR approval.';

  const handleCopyRecommendation = () => {
    navigator.clipboard.writeText(recommendation);
    setCopiedRec(true);
    setTimeout(() => setCopiedRec(false), 2000);
  };

  const getSeverityBadge = () => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-[#FEE2E2] text-[#991B1B] border-[#FECACA]';
      case 'HIGH':
        return 'bg-[#FFEDD5] text-[#9A3412] border-[#FED7AA]';
      case 'MEDIUM':
        return 'bg-[#FEF9C3] text-[#854D0E] border-[#FEF08A]';
      case 'LOW':
        return 'bg-[#EAEFEA] text-[#425044] border-[#D5DFD5]';
      case 'INFORMATIONAL':
        return 'bg-[#E6F4F1] text-[#1B5E50] border-[#CCEBE5]';
      default:
        return 'bg-[#F8F6F0] text-[#747A73] border-[#E6E4DC]';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-in fade-in">
      <div className="dev-card max-w-2xl w-full shadow-2xl overflow-hidden max-h-[90vh] flex flex-col bg-white border border-[#E6E4DC]">
        
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-[#E6E4DC] bg-[#E7EDE2]">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs font-bold px-2.5 py-1 rounded-md bg-white text-[#343A35] border border-[#E6E4DC]">
              #{issueId}
            </span>
            <span className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold uppercase tracking-wider border ${getSeverityBadge()}`}>
              {severity}
            </span>
            <span className="px-2.5 py-0.5 rounded text-xs font-mono font-semibold uppercase tracking-wider bg-white text-[#555C56] border border-[#E6E4DC]">
              {category}
            </span>
            <span className={`px-2.5 py-0.5 rounded text-[11px] font-mono font-semibold uppercase border ${
              isVerifiedStatic
                ? 'bg-[#D8E9E5] text-[#14532D] border-[#BDE0D7]'
                : 'bg-[#E8DFF2] text-[#573B72] border-[#D4C4E3]'
            }`}>
              {isVerifiedStatic ? '✓ Verified Static' : 'AI Observation'}
            </span>
          </div>

          <button
            onClick={onClose}
            className="text-[#747A73] hover:text-[#343A35] p-1 rounded-md hover:bg-[#DCE8D8] transition-colors cursor-pointer"
            title="Close details (Esc)"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-sm bg-white">
          
          {/* Issue Title & Status Grid */}
          <div>
            <h3 className="text-base sm:text-lg font-bold text-[#343A35] tracking-tight">
              {issue.title || 'Code Finding'}
            </h3>

            <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs font-mono">
              <div className="p-2.5 rounded-lg bg-[#F8F6F0] border border-[#E6E4DC]">
                <span className="text-[#747A73] block mb-0.5 text-[10px] uppercase">FILE & LINE</span>
                <span className="text-[#343A35] font-semibold flex items-center space-x-1 truncate" title={filename}>
                  <FileCode className="w-3.5 h-3.5 text-[#4A6B56] shrink-0" />
                  <span className="truncate">{filename}:{line}</span>
                </span>
              </div>

              <div className="p-2.5 rounded-lg bg-[#F8F6F0] border border-[#E6E4DC]">
                <span className="text-[#747A73] block mb-0.5 text-[10px] uppercase">CWE / OWASP</span>
                <span className="text-[#573B72] font-semibold truncate" title={`${cwe} | ${owasp}`}>{cwe}</span>
              </div>

              <div className="p-2.5 rounded-lg bg-[#F8F6F0] border border-[#E6E4DC]">
                <span className="text-[#747A73] block mb-0.5 text-[10px] uppercase">DETECTION SOURCE</span>
                <span className="text-[#343A35] font-semibold truncate flex items-center space-x-1" title={detectionSource}>
                  {isVerifiedStatic ? <Terminal className="w-3 h-3 text-[#10B981] shrink-0" /> : <Bot className="w-3 h-3 text-[#6B4E87] shrink-0" />}
                  <span className="truncate">{detectionSource}</span>
                </span>
              </div>

              <div className="p-2.5 rounded-lg bg-[#F8F6F0] border border-[#E6E4DC]">
                <span className="text-[#747A73] block mb-0.5 text-[10px] uppercase">CURRENT STATUS</span>
                <span className={`font-bold flex items-center space-x-1 ${
                  isIgnored ? 'text-[#92400E]' : isResolved ? 'text-[#14532D]' : 'text-[#991B1B]'
                }`}>
                  {isResolved ? <CheckCircle2 className="w-3.5 h-3.5 shrink-0" /> : <Activity className="w-3.5 h-3.5 shrink-0" />}
                  <span>{currentStatus}</span>
                </span>
              </div>
            </div>
          </div>

          {/* Rule Citation Tag */}
          <div className="p-3 rounded-lg bg-[#EADCCB]/70 border border-[#DAC4AD] flex flex-wrap items-center justify-between text-xs font-mono gap-2 text-[#5E4830]">
            <div className="flex items-center space-x-2">
              <Bookmark className="w-4 h-4 text-[#8C7760] shrink-0" />
              <span className="font-semibold">Normative Rule:</span>
              <span className="font-bold">{ruleCitation}</span>
            </div>
            {issue.rule_id && (
              <span className="bg-white px-2 py-0.5 rounded border border-[#DAC4AD]">
                Rule ID: {issue.rule_id}
              </span>
            )}
          </div>

          {/* Description */}
          <div>
            <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-[#747A73] mb-1.5">
              Defect Description
            </h4>
            <div className="p-3.5 rounded-lg bg-[#F8F6F0] border border-[#E6E4DC] text-[#343A35] leading-relaxed font-sans">
              {description}
            </div>
          </div>

          {/* Grounded Remediation Recommendation */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-[#4A6B56]">
                Grounded Remediation Recommendation
              </h4>
              <button
                onClick={handleCopyRecommendation}
                className="flex items-center space-x-1 text-xs text-[#747A73] hover:text-[#343A35] transition-colors cursor-pointer"
                title="Copy recommendation"
              >
                {copiedRec ? <Check className="w-3.5 h-3.5 text-[#10B981]" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedRec ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <div className="p-3.5 rounded-lg bg-[#E8DFF2]/50 border border-[#D4C4E3] text-[#573B72] font-mono text-xs leading-relaxed whitespace-pre-wrap">
              {recommendation}
            </div>
          </div>

          {/* Evidence / Tool Output */}
          {rawOutput && (
            <div>
              <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-[#747A73] mb-1.5 flex items-center space-x-1.5">
                <Terminal className="w-3.5 h-3.5 text-[#4A6B56]" />
                <span>Analyzer Evidence / Code Excerpt</span>
              </h4>
              <pre className="p-3.5 rounded-lg bg-[#F8F6F0] border border-[#E6E4DC] text-[#343A35] font-mono text-xs overflow-x-auto leading-relaxed whitespace-pre-wrap">
                {rawOutput}
              </pre>
            </div>
          )}

          {/* Verification Status & Provenance Notice */}
          <div className="p-3.5 rounded-lg bg-[#F8F6F0] border border-[#E6E4DC] flex items-start space-x-3 text-xs">
            <div className="mt-0.5">
              {isVerifiedStatic ? (
                <Terminal className="w-4 h-4 text-[#10B981] shrink-0" />
              ) : (
                <Bot className="w-4 h-4 text-[#6B4E87] shrink-0" />
              )}
            </div>
            <div>
              <span className="font-bold text-[#343A35] block mb-0.5">
                Verification & Provenance Status: <span className="font-mono text-[#4A6B56]">{verificationStatus}</span>
              </span>
              <p className="text-[#747A73] leading-relaxed font-sans">
                {isVerifiedStatic
                  ? `Corroborated by deterministic static analyzer (${detectionSource}). Guaranteed by deterministic static tool AST/rule matching.`
                  : 'AI-generated heuristic observation derived from multi-agent reasoning. Flagged for engineering review.'}
              </p>
            </div>
          </div>

          {/* Resolution Lifecycle State */}
          <div className="p-3.5 rounded-lg bg-[#F8F6F0] border border-[#E6E4DC] flex items-start space-x-3 text-xs">
            <div className="mt-0.5">
              {isResolved ? (
                <CheckCircle2 className="w-4 h-4 text-[#10B981] shrink-0" />
              ) : isIgnored ? (
                <AlertTriangle className="w-4 h-4 text-[#F59E0B] shrink-0" />
              ) : (
                <ShieldAlert className="w-4 h-4 text-[#EF4444] shrink-0" />
              )}
            </div>
            <div>
              <span className="font-bold text-[#343A35] block mb-0.5">
                Resolution Lifecycle State
              </span>
              <p className="text-[#747A73] leading-relaxed font-sans">
                {resolutionStatus}
              </p>
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[#E6E4DC] bg-[#E7EDE2] flex justify-end">
          <button
            onClick={onClose}
            className="dev-btn-secondary px-4 py-2 text-xs font-semibold"
          >
            Close Details
          </button>
        </div>

      </div>
    </div>
  );
}
