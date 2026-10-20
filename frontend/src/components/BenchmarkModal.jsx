import React, { useState, useEffect } from 'react';
import { 
  X, Zap, Play, CheckCircle2, BarChart3, Database, Shield, AlertTriangle, 
  Cpu, Filter, RefreshCw, Terminal, Layers, ArrowRight, ExternalLink, 
  Check, ChevronDown, ChevronUp, Code2, Sparkles, ShieldCheck, Bug,
  FileCode, Activity, Wrench, AlertCircle
} from 'lucide-react';
import { 
  fetchBenchmarkCatalog, runPipelineBenchmark, runRagBenchmark, fetchBenchmarkStatus 
} from '../services/api';

export default function BenchmarkModal({ isOpen, onClose, onLoadSampleCode }) {
  if (!isOpen) return null;

  const [activeTab, setActiveTab] = useState('pipeline'); // 'pipeline' | 'rag' | 'catalog'
  const [suiteType, setSuiteType] = useState('all'); // 'all' | 'real_world' | 'synthetic'
  const [languageFilter, setLanguageFilter] = useState('');
  
  // Execution states
  const [runningPipeline, setRunningPipeline] = useState(false);
  const [runningRag, setRunningRag] = useState(false);
  const [pipelineResults, setPipelineResults] = useState(null);
  const [ragResults, setRagResults] = useState(null);
  const [catalog, setCatalog] = useState([]);
  const [benchmarkStatus, setBenchmarkStatus] = useState(null);
  const [expandedCaseId, setExpandedCaseId] = useState(null);
  const [error, setError] = useState(null);

  // Load Catalog and Status on mount
  useEffect(() => {
    fetchBenchmarkCatalog()
      .then(data => setCatalog(data.catalog || []))
      .catch(err => console.error("Catalog load error:", err));

    fetchBenchmarkStatus()
      .then(data => setBenchmarkStatus(data))
      .catch(err => console.error("Status load error:", err));
  }, []);

  // Execute Pipeline Benchmark
  const handleRunPipelineBenchmark = async (specificCaseId = null) => {
    setRunningPipeline(true);
    setError(null);
    try {
      const payload = {
        suite_type: specificCaseId ? 'all' : suiteType,
        language: specificCaseId ? null : (languageFilter || null),
        case_id: specificCaseId || null
      };
      const res = await runPipelineBenchmark(payload);
      setPipelineResults(res);
      // Auto-expand first run if single case
      if (res.runs?.length === 1) {
        setExpandedCaseId(res.runs[0].id);
      }
    } catch (err) {
      setError(`Pipeline Benchmark execution failed: ${err.message}`);
    } finally {
      setRunningPipeline(false);
    }
  };

  // Execute RAG Benchmark
  const handleRunRagBenchmark = async () => {
    setRunningRag(true);
    setError(null);
    try {
      const res = await runRagBenchmark();
      setRagResults(res);
    } catch (err) {
      setError(`RAG Benchmark execution failed: ${err.message}`);
    } finally {
      setRunningRag(false);
    }
  };

  const toggleExpand = (id) => {
    setExpandedCaseId(prev => prev === id ? null : id);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-[#142B4A]/50 backdrop-blur-sm animate-in fade-in">
      <div className="max-w-5xl w-full max-h-[92vh] flex flex-col shadow-2xl rounded-xl overflow-hidden border border-[#E2E6EC] bg-white">
        
        {/* Modal Header - Navy Blue #142B4A */}
        <div className="flex items-center justify-between p-4 bg-[#142B4A] text-white">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center text-[#DCE7F5]">
              <Zap className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-sm font-bold text-white tracking-wide">
                  PR Agent Benchmark &amp; Ground-Truth Evaluation Suite
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#E9E2F5] text-[#4A2E7A] border border-[#D5C6E6] font-semibold">
                  PHASE 13
                </span>
              </div>
              <p className="text-[11px] text-[#DCE7F5]/80">
                Isolated, bounded execution calculating non-fabricated Precision, Recall, F1, and Remediation Success across 6 languages.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button 
              onClick={onClose} 
              className="p-1.5 text-white/70 hover:text-white rounded-md hover:bg-white/10 transition-colors cursor-pointer"
              title="Close Benchmark Modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Sub-Tab Navigation Bar */}
        <div className="flex items-center justify-between border-b border-[#E2E6EC] bg-[#F3F5F8] px-4 py-2">
          <div className="flex items-center space-x-1 sm:space-x-2">
            <button
              onClick={() => setActiveTab('pipeline')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center space-x-2 transition-all cursor-pointer ${
                activeTab === 'pipeline'
                  ? 'bg-white text-[#142B4A] border border-[#E2E6EC] shadow-sm'
                  : 'text-[#718096] hover:text-[#142B4A] hover:bg-white/60 border border-transparent'
              }`}
            >
              <Terminal className="w-3.5 h-3.5 text-[#142B4A]" />
              <span>Pipeline Review &amp; Auto-Fix</span>
            </button>

            <button
              onClick={() => setActiveTab('rag')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center space-x-2 transition-all cursor-pointer ${
                activeTab === 'rag'
                  ? 'bg-white text-[#142B4A] border border-[#E2E6EC] shadow-sm'
                  : 'text-[#718096] hover:text-[#142B4A] hover:bg-white/60 border border-transparent'
              }`}
            >
              <Database className="w-3.5 h-3.5 text-[#6B46C1]" />
              <span>RAG Vector Store (128D)</span>
            </button>

            <button
              onClick={() => setActiveTab('catalog')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center space-x-2 transition-all cursor-pointer ${
                activeTab === 'catalog'
                  ? 'bg-white text-[#142B4A] border border-[#E2E6EC] shadow-sm'
                  : 'text-[#718096] hover:text-[#142B4A] hover:bg-white/60 border border-transparent'
              }`}
            >
              <Code2 className="w-3.5 h-3.5 text-[#2B6CB0]" />
              <span>Ground Truth Catalog ({catalog.length})</span>
            </button>
          </div>

          {/* Quick Active Provider Badge */}
          {benchmarkStatus && (
            <div className="hidden md:flex items-center space-x-2 text-[10px] font-mono text-[#718096]">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="font-semibold text-[#142B4A]">{benchmarkStatus.llm_provider?.toUpperCase()}</span>
              <span>•</span>
              <span className="text-[#718096]">{benchmarkStatus.fallback_state || 'standby'}</span>
            </div>
          )}
        </div>

        {/* Error Alert Banner */}
        {error && (
          <div className="p-3 bg-[#FEE2E2] border-b border-[#FECACA] flex items-center space-x-2 text-[#991B1B] text-xs">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Modal Scrollable Body */}
        <div className="p-4 sm:p-5 overflow-y-auto flex-1 space-y-5 bg-[#F3F5F8]">

          {/* ================================================================ */}
          {/* TAB 1: PIPELINE REVIEW & REMEDIATION BENCHMARK                   */}
          {/* ================================================================ */}
          {activeTab === 'pipeline' && (
            <div className="space-y-4">
              
              {/* Filter & Execution Controls Deck */}
              <div className="rounded-lg p-3.5 flex flex-wrap items-center justify-between gap-3 border border-[#E2E6EC] bg-white shadow-sm">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <div className="flex items-center space-x-1.5 text-[#718096]">
                    <Filter className="w-3.5 h-3.5 text-[#142B4A]" />
                    <span className="font-semibold uppercase tracking-wider text-[10px] text-[#142B4A]">Filter Suite:</span>
                  </div>

                  <select
                    value={suiteType}
                    onChange={(e) => setSuiteType(e.target.value)}
                    disabled={runningPipeline}
                    className="bg-[#F3F5F8] border border-[#E2E6EC] rounded px-2.5 py-1 text-[#343A40] focus:outline-none focus:border-[#142B4A] cursor-pointer text-xs"
                  >
                    <option value="all">All 18 Benchmark Cases</option>
                    <option value="real_world">Real-World Applications (6 Languages)</option>
                    <option value="synthetic">Synthetic Test Fixtures (12 Cases)</option>
                  </select>

                  <select
                    value={languageFilter}
                    onChange={(e) => setLanguageFilter(e.target.value)}
                    disabled={runningPipeline}
                    className="bg-[#F3F5F8] border border-[#E2E6EC] rounded px-2.5 py-1 text-[#343A40] focus:outline-none focus:border-[#142B4A] cursor-pointer text-xs"
                  >
                    <option value="">All Six Languages</option>
                    <option value="python">Python</option>
                    <option value="cpp">C++</option>
                    <option value="c">C</option>
                    <option value="java">Java</option>
                    <option value="javascript">JavaScript</option>
                    <option value="ruby">Ruby</option>
                  </select>
                </div>

                <button
                  onClick={() => handleRunPipelineBenchmark()}
                  disabled={runningPipeline}
                  className="dev-btn-primary px-4 py-2 text-xs font-semibold uppercase tracking-wider flex items-center space-x-2 cursor-pointer shadow-sm disabled:opacity-50"
                >
                  {runningPipeline ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Benchmarking Pipeline...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5 fill-current" />
                      <span>Execute Pipeline Benchmark</span>
                    </>
                  )}
                </button>
              </div>

              {/* KPI Summary Banner (Displays when results are loaded) */}
              {pipelineResults && (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
                    <div className="rounded-md p-3 text-center border border-[#BDE8CD] bg-[#DDF2E5]/70 shadow-sm">
                      <span className="text-[10px] uppercase font-bold text-[#1B5E36] block">Overall Precision</span>
                      <span className="text-xl font-bold font-mono text-[#1B5E36]">
                        {(pipelineResults.summary.overall_precision * 100).toFixed(1)}%
                      </span>
                    </div>

                    <div className="rounded-md p-3 text-center border border-[#D5C6E6] bg-[#E9E2F5]/70 shadow-sm">
                      <span className="text-[10px] uppercase font-bold text-[#4A2E7A] block">Overall Recall</span>
                      <span className="text-xl font-bold font-mono text-[#4A2E7A]">
                        {(pipelineResults.summary.overall_recall * 100).toFixed(1)}%
                      </span>
                    </div>

                    <div className="rounded-md p-3 text-center border border-[#BCD4F0] bg-[#DCE7F5]/70 shadow-sm">
                      <span className="text-[10px] uppercase font-bold text-[#142B4A] block">Macro F1-Score</span>
                      <span className="text-xl font-bold font-mono text-[#142B4A]">
                        {pipelineResults.summary.overall_f1_score.toFixed(3)}
                      </span>
                    </div>

                    <div className="rounded-md p-3 text-center border border-[#BDE8CD] bg-[#DDF2E5]/50 shadow-sm">
                      <span className="text-[10px] uppercase font-bold text-[#1B5E36] block">Remediation Rate</span>
                      <span className="text-xl font-bold font-mono text-[#1B5E36]">
                        {pipelineResults.summary.remediation_success_rate}
                      </span>
                    </div>

                    <div className="rounded-md p-3 text-center border border-[#E2E6EC] bg-white shadow-sm">
                      <span className="text-[10px] uppercase font-bold text-[#718096] block">Avg Latency</span>
                      <span className="text-xl font-bold font-mono text-[#142B4A]">
                        {pipelineResults.summary.average_latency_ms}ms
                      </span>
                    </div>

                    <div className="rounded-md p-3 text-center border border-[#E2E6EC] bg-white shadow-sm">
                      <span className="text-[10px] uppercase font-bold text-[#718096] block">Test Cases</span>
                      <span className="text-xl font-bold font-mono text-[#142B4A]">
                        {pipelineResults.summary.total_test_cases} runs
                      </span>
                    </div>
                  </div>

                  {/* Test Conditions & Tool Availability Disclosure */}
                  {pipelineResults.test_conditions && (
                    <div className="p-3 rounded-md bg-white border border-[#E2E6EC] text-[11px] space-y-1.5 font-mono text-[#718096] shadow-sm">
                      <div className="flex flex-wrap items-center justify-between gap-2 text-[#142B4A] font-semibold">
                        <div className="flex items-center space-x-2">
                          <Activity className="w-3.5 h-3.5 text-[#142B4A]" />
                          <span>TEST CONDITIONS &amp; ENVIRONMENT DISCLOSURE</span>
                        </div>
                        <span className="text-[10px] text-[#718096]">
                          {new Date(pipelineResults.test_conditions.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-2 pt-1 text-[10px]">
                        <div>
                          <span className="text-[#718096]">Active LLM Provider: </span>
                          <span className="text-[#142B4A] font-semibold">{pipelineResults.test_conditions.llm_provider}</span>
                          <span className="text-[#718096]"> ({pipelineResults.test_conditions.llm_model})</span>
                        </div>
                        <div>
                          <span className="text-[#718096]">Host Platform: </span>
                          <span className="text-[#343A40]">{pipelineResults.test_conditions.host_platform}</span>
                        </div>
                        <div>
                          <span className="text-[#718096]">Suite Duration: </span>
                          <span className="text-[#92400E] font-semibold">{pipelineResults.test_conditions.suite_duration_seconds}s</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Benchmark Results Table */}
              <div className="border border-[#E2E6EC] rounded-lg overflow-hidden bg-white shadow-sm">
                <div className="overflow-x-auto max-h-96 overflow-y-auto">
                  <table className="w-full text-left text-[11px] font-mono">
                    <thead className="bg-[#F3F5F8] text-[#142B4A] border-b border-[#E2E6EC] uppercase tracking-wider text-[10px] sticky top-0 z-10 font-bold">
                      <tr>
                        <th className="p-3">Test Case ID</th>
                        <th className="p-3">Language</th>
                        <th className="p-3">Type</th>
                        <th className="p-3">Verdict</th>
                        <th className="p-3 text-center">TP / FP / FN</th>
                        <th className="p-3">Precision</th>
                        <th className="p-3">Recall</th>
                        <th className="p-3">F1</th>
                        <th className="p-3">Remediation</th>
                        <th className="p-3 text-right">Latency</th>
                        <th className="p-3 text-center">Inspect</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E2E6EC]">
                      {(!pipelineResults || pipelineResults.runs.length === 0) ? (
                        <tr>
                          <td colSpan={11} className="p-8 text-center text-[#718096] font-sans">
                            <Terminal className="w-8 h-8 text-[#A0AEC0] mx-auto mb-2 opacity-60" />
                            <p className="text-xs text-[#142B4A] font-medium">No benchmark runs executed yet.</p>
                            <p className="text-[11px] text-[#718096] mt-1">
                              Click "Execute Pipeline Benchmark" above to run live tests against documented ground truth.
                            </p>
                          </td>
                        </tr>
                      ) : (
                        pipelineResults.runs.map((run) => (
                          <React.Fragment key={run.id}>
                            <tr className="hover:bg-[#F3F5F8]/60 transition-colors">
                              <td className="p-3 font-semibold text-[#142B4A]">
                                <div className="flex items-center space-x-1.5">
                                  <span>{run.id}</span>
                                  {run.is_intentionally_vulnerable ? (
                                    <span className="px-1.5 py-0.2 rounded bg-[#FEF3C7] text-[#92400E] text-[9px] font-bold border border-[#FDE68A]" title="Intentionally Vulnerable Sample">
                                      VULN
                                    </span>
                                  ) : (
                                    <span className="px-1.5 py-0.2 rounded bg-[#DDF2E5] text-[#1B5E36] text-[9px] font-bold border border-[#BDE8CD]" title="Clean Negative Control">
                                      CLEAN
                                    </span>
                                  )}
                                </div>
                              </td>

                              <td className="p-3 uppercase text-[#142B4A] font-semibold">{run.language}</td>

                              <td className="p-3 text-[#718096] text-[10px]">
                                {run.suite_type === 'real_world' ? 'Real-World' : 'Synthetic'}
                              </td>

                              <td className="p-3">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  run.verdict === 'CLEAN' ? 'bg-[#DDF2E5] text-[#1B5E36] border border-[#BDE8CD]' :
                                  run.verdict === 'NEEDS REVIEW' ? 'bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A]' :
                                  'bg-[#FEE2E2] text-[#991B1B] border border-[#FECACA]'
                                }`}>
                                  {run.verdict}
                                </span>
                              </td>

                              <td className="p-3 text-center font-bold">
                                <span className="text-[#1B5E36]">{run.true_positives}</span>
                                <span className="text-[#A0AEC0]"> / </span>
                                <span className="text-[#92400E]">{run.false_positives}</span>
                                <span className="text-[#A0AEC0]"> / </span>
                                <span className="text-[#991B1B]">{run.false_negatives}</span>
                              </td>

                              <td className="p-3 text-[#1B5E36] font-semibold">{(run.precision * 100).toFixed(0)}%</td>
                              <td className="p-3 text-[#4A2E7A] font-semibold">{(run.recall * 100).toFixed(0)}%</td>
                              <td className="p-3 text-[#142B4A] font-semibold">{run.f1_score.toFixed(2)}</td>

                              <td className="p-3">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                  run.remediation_success ? 'bg-[#DDF2E5] text-[#1B5E36]' :
                                  run.remediation_status === 'PARTIAL' ? 'bg-[#FEF3C7] text-[#92400E]' :
                                  run.remediation_status === 'NOT_REQUIRED' ? 'bg-[#F3F5F8] text-[#718096]' :
                                  'bg-[#FEE2E2] text-[#991B1B]'
                                }`}>
                                  {run.remediation_status}
                                </span>
                              </td>

                              <td className="p-3 text-right text-[#343A40]">{run.latency_ms}ms</td>

                              <td className="p-3 text-center">
                                <button
                                  onClick={() => toggleExpand(run.id)}
                                  className="p-1 rounded hover:bg-[#E2E6EC] text-[#718096] hover:text-[#142B4A] transition-colors cursor-pointer"
                                  title="Inspect Ground Truth Matches"
                                >
                                  {expandedCaseId === run.id ? (
                                    <ChevronUp className="w-4 h-4 text-[#142B4A]" />
                                  ) : (
                                    <ChevronDown className="w-4 h-4" />
                                  )}
                                </button>
                              </td>
                            </tr>

                            {/* Expanded Row Inspector */}
                            {expandedCaseId === run.id && (
                              <tr className="bg-[#F3F5F8]">
                                <td colSpan={11} className="p-4 border-t border-b border-[#E2E6EC]">
                                  <div className="space-y-3 font-sans text-xs">
                                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#E2E6EC] pb-2">
                                      <div>
                                        <h4 className="font-bold text-[#142B4A]">{run.name} ({run.filename})</h4>
                                        <p className="text-[11px] text-[#718096]">
                                          Detected {run.detected_issues_count} issue(s) vs {run.expected_issues_count} ground-truth defect(s).
                                        </p>
                                      </div>

                                      <div className="flex items-center space-x-2">
                                        <span className="text-[11px] text-[#718096]">Native Tools: </span>
                                        {run.native_tools?.map((t, idx) => (
                                          <span key={idx} className="px-1.5 py-0.5 rounded bg-white text-[#142B4A] font-mono text-[10px] border border-[#E2E6EC]">
                                            {t}
                                          </span>
                                        ))}
                                      </div>
                                    </div>

                                    {/* Matched Defects Telemetry */}
                                    {run.matches && run.matches.length > 0 ? (
                                      <div className="space-y-1.5">
                                        <span className="text-[10px] uppercase font-bold tracking-wider text-[#1B5E36] block font-mono">
                                          ✓ Corroborated Ground-Truth Matches (True Positives: {run.matches.length})
                                        </span>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                          {run.matches.map((m, mIdx) => (
                                            <div key={mIdx} className="p-2.5 rounded bg-white border border-[#BDE8CD] text-[11px] space-y-1 shadow-sm">
                                              <div className="flex items-center justify-between font-mono text-[10px]">
                                                <span className="text-[#1B5E36] font-bold">{m.actual.cwe || m.expected.cwe}</span>
                                                <span className="text-[#718096]">{m.match_reason}</span>
                                              </div>
                                              <div className="text-[#142B4A] font-medium">{m.expected.title}</div>
                                              <div className="text-[10px] text-[#718096] font-mono">
                                                Line ~{m.expected.line_hint} (Actual: L{m.actual.line}) | Source: {m.actual.detection_source}
                                              </div>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    ) : (
                                      run.is_intentionally_vulnerable && (
                                        <p className="text-[#92400E] text-xs italic">
                                          No ground-truth matches detected for this test case.
                                        </p>
                                      )
                                    )}

                                    {/* Tool Limitations Notice if present */}
                                    {run.missing_tools && run.missing_tools.length > 0 && (
                                      <div className="p-2.5 rounded bg-[#FEF3C7] border border-[#FDE68A] text-[11px] text-[#92400E] flex items-start space-x-2">
                                        <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                                        <div>
                                          <span className="font-semibold">Tool Limitations Reported: </span>
                                          Missing system binary: {run.missing_tools.join(', ')}.
                                          <span className="text-[#718096] block text-[10px] mt-0.5">
                                            {run.install_hint}
                                          </span>
                                        </div>
                                      </div>
                                    )}

                                    {/* Action to load this sample directly into Code Studio */}
                                    <div className="flex justify-end pt-1">
                                      <button
                                        onClick={() => {
                                          if (onLoadSampleCode) onLoadSampleCode(run.language);
                                          onClose();
                                        }}
                                        className="text-xs text-[#142B4A] hover:text-[#1E4370] font-semibold flex items-center space-x-1 cursor-pointer"
                                      >
                                        <span>Load Code into Code Studio Editor</span>
                                        <ArrowRight className="w-3.5 h-3.5" />
                                      </button>
                                    </div>
                                  </div>
                                </td>
                              </tr>
                            )}
                          </React.Fragment>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          )}

          {/* ================================================================ */}
          {/* TAB 2: RAG VECTOR STORE BENCHMARK SUITE                         */}
          {/* ================================================================ */}
          {activeTab === 'rag' && (
            <div className="space-y-4">
              <div className="rounded-lg p-3.5 flex flex-wrap items-center justify-between gap-3 border border-[#E2E6EC] bg-white shadow-sm">
                <div>
                  <h4 className="text-xs font-bold text-[#142B4A] uppercase tracking-wider">
                    In-Memory 128D Dense N-Gram Vector Index
                  </h4>
                  <p className="text-[11px] text-[#718096] mt-0.5">
                    Evaluates cosine similarity ranking, retrieval latency, and Precision@1 normative rule attribution.
                  </p>
                </div>

                <button
                  onClick={handleRunRagBenchmark}
                  disabled={runningRag}
                  className="dev-btn-primary px-4 py-2 text-xs font-semibold uppercase tracking-wider flex items-center space-x-2 cursor-pointer shadow-sm disabled:opacity-50"
                >
                  {runningRag ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Benchmarking Vectors...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5 fill-current" />
                      <span>Execute RAG Benchmark</span>
                    </>
                  )}
                </button>
              </div>

              {/* RAG Metrics Bar */}
              {ragResults && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="rounded-md p-3 text-center border border-[#E2E6EC] bg-white shadow-sm">
                    <span className="text-[10px] uppercase font-bold text-[#718096] block">Avg Latency</span>
                    <span className="text-lg font-bold font-mono text-[#142B4A]">{ragResults.average_latency_ms}ms</span>
                  </div>

                  <div className="rounded-md p-3 text-center border border-[#BDE8CD] bg-[#DDF2E5]/70 shadow-sm">
                    <span className="text-[10px] uppercase font-bold text-[#1B5E36] block">Precision@1</span>
                    <span className="text-lg font-bold font-mono text-[#1B5E36]">{ragResults.precision_at_1}</span>
                  </div>

                  <div className="rounded-md p-3 text-center border border-[#D5C6E6] bg-[#E9E2F5]/70 shadow-sm">
                    <span className="text-[10px] uppercase font-bold text-[#4A2E7A] block">Test Query Set</span>
                    <span className="text-lg font-bold font-mono text-[#4A2E7A]">{ragResults.total_queries} queries</span>
                  </div>

                  <div className="rounded-md p-3 text-center border border-[#BCD4F0] bg-[#DCE7F5]/70 shadow-sm">
                    <span className="text-[10px] uppercase font-bold text-[#142B4A] block">Vector Index</span>
                    <span className="text-lg font-bold font-mono text-[#142B4A]">{ragResults.vector_count} docs (128D)</span>
                  </div>
                </div>
              )}

              {/* RAG Table */}
              <div className="border border-[#E2E6EC] rounded-md overflow-hidden max-h-72 overflow-y-auto bg-white shadow-sm">
                <table className="w-full text-left text-[11px] font-mono">
                  <thead className="bg-[#F3F5F8] text-[#142B4A] border-b border-[#E2E6EC] uppercase tracking-wider text-[10px] sticky top-0 font-bold">
                    <tr>
                      <th className="p-3">Test Vector Query</th>
                      <th className="p-3">Category</th>
                      <th className="p-3">Target Standard</th>
                      <th className="p-3">Top Matched Document</th>
                      <th className="p-3">Similarity</th>
                      <th className="p-3 text-right">Latency</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E2E6EC]">
                    {(!ragResults || ragResults.runs.length === 0) ? (
                      <tr>
                        <td colSpan={6} className="p-8 text-center text-[#718096] font-sans">
                          Click "Execute RAG Benchmark" above to test vector retrieval latency and accuracy.
                        </td>
                      </tr>
                    ) : (
                      ragResults.runs.map((item, idx) => (
                        <tr key={idx} className="hover:bg-[#F3F5F8]/60 transition-colors">
                          <td className="p-3 text-[#142B4A] font-sans font-medium">{item.query}</td>
                          <td className="p-3 text-[#718096]">{item.category}</td>
                          <td className="p-3 text-[#142B4A] font-bold">{item.target}</td>
                          <td className="p-3">
                            <span className={item.success ? 'text-[#1B5E36] font-semibold' : 'text-[#92400E]'}>
                              {item.top_match}
                            </span>
                          </td>
                          <td className="p-3 text-[#4A2E7A] font-medium">{item.similarity}</td>
                          <td className="p-3 text-right text-[#718096]">{item.latency_ms}ms</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ================================================================ */}
          {/* TAB 3: GROUND-TRUTH DATASET & DEFECT CATALOG                    */}
          {/* ================================================================ */}
          {activeTab === 'catalog' && (
            <div className="space-y-4">
              <div className="rounded-lg p-3.5 border border-[#E2E6EC] bg-white flex flex-wrap items-center justify-between gap-3 shadow-sm">
                <div>
                  <h4 className="text-xs font-bold text-[#142B4A] uppercase tracking-wider">
                    Documented Ground-Truth Dataset ({catalog.length} Test Cases)
                  </h4>
                  <p className="text-[11px] text-[#718096] mt-0.5">
                    Rigorous ground-truth annotations across all 6 supported languages, spanning syntax, boundary, runtime, resource, performance, and security defect classes.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-96 overflow-y-auto pr-1">
                {catalog.map((c) => (
                  <div key={c.id} className="p-3.5 rounded-lg border border-[#E2E6EC] bg-white space-y-2.5 hover:border-[#142B4A]/50 shadow-sm transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-xs font-bold text-[#142B4A]">{c.id}</span>
                        <span className="px-1.5 py-0.2 rounded bg-[#DCE7F5] text-[#142B4A] text-[10px] font-mono uppercase font-semibold">
                          {c.language}
                        </span>
                        <span className="px-1.5 py-0.2 rounded bg-[#F3F5F8] text-[#718096] text-[9px] font-mono border border-[#E2E6EC]">
                          {c.suite_type}
                        </span>
                      </div>

                      {c.is_intentionally_vulnerable ? (
                        <span className="px-2 py-0.5 rounded bg-[#FEF3C7] text-[#92400E] text-[10px] font-bold border border-[#FDE68A] flex items-center space-x-1">
                          <AlertTriangle className="w-3 h-3" />
                          <span>Vulnerable</span>
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-[#DDF2E5] text-[#1B5E36] text-[10px] font-bold border border-[#BDE8CD] flex items-center space-x-1">
                          <ShieldCheck className="w-3 h-3" />
                          <span>Clean Control</span>
                        </span>
                      )}
                    </div>

                    <div>
                      <div className="text-xs font-semibold text-[#142B4A]">{c.name}</div>
                      <div className="text-[11px] font-mono text-[#718096] mt-0.5">{c.filename}</div>
                    </div>

                    {/* Defect Categories Badges */}
                    {c.defect_categories && c.defect_categories.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1">
                        {c.defect_categories.map((cat, idx) => (
                          <span key={idx} className="px-1.5 py-0.2 rounded bg-[#F3F5F8] text-[#718096] font-mono text-[9px] border border-[#E2E6EC] capitalize">
                            {cat}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Expected Defects Summary */}
                    <div className="pt-2 border-t border-[#E2E6EC] flex items-center justify-between text-[11px]">
                      <span className="text-[#718096]">
                        {c.expected_defects_count} documented defect(s)
                      </span>

                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => {
                            if (onLoadSampleCode) onLoadSampleCode(c.language);
                            onClose();
                          }}
                          className="text-xs text-[#142B4A] hover:text-[#1E4370] font-semibold cursor-pointer flex items-center space-x-1"
                        >
                          <span>Load Sample</span>
                          <ArrowRight className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="p-3 sm:p-4 border-t border-[#E2E6EC] bg-[#F3F5F8] flex items-center justify-between text-xs">
          <div className="flex items-center space-x-2 text-[#718096] text-[11px]">
            <Shield className="w-4 h-4 text-[#142B4A]" />
            <span>Strict zero-fabrication commitment: metrics computed exclusively from live outputs vs ground truth.</span>
          </div>

          <button
            onClick={onClose}
            className="dev-btn-secondary px-4 py-1.5 text-xs font-medium cursor-pointer"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
}
