import React, { memo } from 'react';
import { FileCode, Clock, ShieldCheck, Terminal, Cpu, CheckCircle2, AlertTriangle, ShieldAlert, Hash } from 'lucide-react';

function ReviewHeader({
  filename = 'source_code.txt',
  language = 'python',
  reviewId = null,
  verdict = 'PENDING',
  remediationStatus = 'NOT_REQUIRED',
  mcpTools = [],
  gatewayStatus = null,
  executionStatus = 'Ready',
  executionTime = null
}) {
  const isClean = verdict === 'CLEAN' || verdict === 'PASS';
  const isDegraded = ['ANALYZER UNAVAILABLE', 'MCP UNAVAILABLE', 'DEGRADED', 'RAG UNAVAILABLE', 'DEPENDENCY MISSING', 'LLM UNAVAILABLE'].some(v => (verdict || '').includes(v));
  const isAnalyzing = verdict === 'ANALYZING...' || executionStatus.includes('Running') || executionStatus.includes('Applying');

  const provider = (gatewayStatus?.provider || 'OLLAMA').toUpperCase();
  const model = gatewayStatus?.model || 'qwen2.5-coder:7b';
  const analyzerText = mcpTools && mcpTools.length > 0 ? (Array.isArray(mcpTools) ? mcpTools.join(', ') : String(mcpTools)) : 'Language Static Linters';

  const hasRun = Boolean(reviewId) || isAnalyzing;

  return (
    <div className="dev-card px-5 py-3.5 rounded-xl flex flex-wrap items-center justify-between gap-3 text-xs sm:text-sm bg-white border border-[#E2E6EC] shadow-2xs">
      
      {/* Left: Active File & Review Identification */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2 bg-[#F3F5F8] border border-[#E2E6EC] px-3 py-1.5 rounded-lg">
          <FileCode className="w-4 h-4 text-[#142B4A] shrink-0" />
          <span className="font-mono font-semibold text-[#142B4A]">{filename}</span>
          <span className="text-[#606973] font-sans text-xs">({language})</span>
        </div>

        {reviewId && (
          <div className="flex items-center space-x-1.5 font-mono text-[#4A2E7A] bg-[#E9E2F5] border border-[#D7C7ED] px-2.5 py-1.5 rounded-lg">
            <Hash className="w-3.5 h-3.5 text-[#4A2E7A]" />
            <span className="font-semibold">{reviewId}</span>
          </div>
        )}

        {/* Dynamic Execution Pulse */}
        {isAnalyzing ? (
          <div className="flex items-center space-x-2 text-[#142B4A] bg-[#DCE7F5] border border-[#B8D0EC] px-3 py-1.5 rounded-lg animate-pulse">
            <span className="w-2 h-2 rounded-full bg-[#142B4A] animate-ping shrink-0" />
            <span className="font-semibold text-xs">{executionStatus}</span>
          </div>
        ) : (
          <span className="text-[#606973] text-xs hidden sm:inline-block">
            {executionStatus} {executionTime ? `(${executionTime})` : ''}
          </span>
        )}
      </div>

      {/* Right: Verdict, Linters, & Engine Meta */}
      <div className="flex items-center space-x-3">
        
        {/* Review Verdict Badge */}
        {hasRun && (
          <span className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-lg font-bold uppercase tracking-wider text-xs border ${
            isClean
              ? 'bg-[#DDF2E5] text-[#1B5E36] border-[#C4E7D0]'
              : isDegraded
              ? 'bg-[#FEF3C7] text-[#92400E] border-[#FDE68A]'
              : isAnalyzing
              ? 'bg-[#DCE7F5] text-[#142B4A] border-[#B8D0EC]'
              : 'bg-[#FEE2E2] text-[#991B1B] border-[#FECACA]'
          }`}>
            {isClean ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-[#10B981] shrink-0" />
            ) : isDegraded ? (
              <AlertTriangle className="w-3.5 h-3.5 text-[#F59E0B] shrink-0" />
            ) : isAnalyzing ? (
              <span className="w-2 h-2 rounded-full bg-[#142B4A] animate-ping shrink-0" />
            ) : (
              <ShieldAlert className="w-3.5 h-3.5 text-[#EF4444] shrink-0" />
            )}
            <span>{verdict}</span>
          </span>
        )}

        {/* Static Analyzer Tool Tag */}
        <div className="hidden md:flex items-center space-x-2 text-[#343A40] bg-[#F3F5F8] border border-[#E2E6EC] px-3 py-1.5 rounded-lg font-mono text-xs" title={`MCP Tools: ${analyzerText}`}>
          <Terminal className="w-3.5 h-3.5 text-[#142B4A]" />
          <span className="truncate max-w-[160px] lg:max-w-[220px]">{analyzerText}</span>
        </div>

        {/* LLM Engine Chip */}
        <div className="hidden lg:flex items-center space-x-1.5 text-[#142B4A] bg-[#DCE7F5] border border-[#B8D0EC] px-2.5 py-1.5 rounded-lg font-mono text-xs font-semibold" title={`LLM Engine: ${provider} (${model})`}>
          <Cpu className="w-3.5 h-3.5 text-[#142B4A]" />
          <span>{provider}</span>
        </div>

      </div>

    </div>
  );
}

export default memo(ReviewHeader);
