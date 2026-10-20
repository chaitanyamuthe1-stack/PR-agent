import React, { useState } from 'react';
import { 
  Layers, Terminal, Database, Server, GitBranch, RefreshCw, CheckCircle2, 
  ArrowRight, ShieldCheck, Zap, Cpu, FileCode, Workflow, Network, HardDrive, 
  AlertTriangle, Lock, ShieldAlert, Sparkles, Check, ChevronRight, Activity,
  Maximize2, SplitSquareVertical
} from 'lucide-react';

const PIPELINE_NODES = [
  {
    id: 'node-router',
    step: '01',
    layer: 'Ingestion & AST Router',
    title: 'Source Validation & Language Router',
    file: 'backend/graph.py (run_full_pipeline)',
    icon: FileCode,
    color: 'bg-[#DCE8D8] text-[#2D5A43]',
    borderColor: 'border-[#C2DFD9]',
    bgTint: 'bg-[#DCE8D8]/30',
    inputs: 'Raw source text, filename, language override, provider preference',
    outputs: 'Validated AgentState with sanitized filename, line counts, and active language toolset',
    guarantee: 'Payload size capped at 5MB; path traversal sequences stripped; language validated against supported set (Python, C, C++, Java, JS, Ruby).',
    description: 'Validates source code payload against whitespace and size constraints. Sanitizes input filenames against directory traversal. Resolves target programming language via explicit selection or file extension mapping.'
  },
  {
    id: 'node-mcp',
    step: '02',
    layer: 'Deterministic Ground Truth',
    title: 'Static Analysis (MCP Tool Layer)',
    file: 'backend/mcp_tools.py (run_static_analysis)',
    icon: Terminal,
    color: 'bg-[#D8E9E5] text-[#1E4332]',
    borderColor: 'border-[#C2DFD9]',
    bgTint: 'bg-[#D8E9E5]/30',
    inputs: 'Source code, validated language identifier',
    outputs: 'Normalized static_findings array with rule_id, line, severity, CWE, and tool provenance',
    guarantee: 'Invokes actual language linters (bandit, flake8, cppcheck, checkstyle, eslint, rubocop) on isolated temp files; reports clean vs tool-unavailable truthfully.',
    description: 'Executes language-specific static analyzers via native subprocess dispatch before any generative LLM inference. Normalizes linter outputs into an immutable finding schema with exact line numbers and rule IDs.'
  },
  {
    id: 'node-rag',
    step: '03',
    layer: 'Semantic Vector Store',
    title: 'RAG Retrieval & Normative Grounding',
    file: 'backend/rag/vector_store.py (store.search)',
    icon: Database,
    color: 'bg-[#E8DFF2] text-[#4A3B69]',
    borderColor: 'border-[#D5C6E6]',
    bgTint: 'bg-[#E8DFF2]/30',
    inputs: 'Language identifier, detected defect titles, top_k=4 parameter',
    outputs: 'Retrieved rag_context passages with rule_id, CWE, OWASP standard, and remediation guides',
    guarantee: '100% in-memory deterministic dense n-gram hashed vector engine (128D); zero external API dependency; idempotent document indexing.',
    description: 'Embeds code context into 128-dimensional dense vectors and performs cosine similarity search against pre-indexed OWASP Top 10, CWE Top 25, and official style guides. Injects verifiable remediation guidance.'
  },
  {
    id: 'node-gateway',
    step: '04',
    layer: 'Resilient LLM Routing',
    title: 'LLM Gateway & Failover Circuit Breaker',
    file: 'backend/llm_gateway.py (gateway.generate)',
    icon: Server,
    color: 'bg-[#E8DFF2] text-[#4A3B69]',
    borderColor: 'border-[#D5C6E6]',
    bgTint: 'bg-[#E8DFF2]/30',
    inputs: 'System instruction, bounded prompt (max 50,000 chars), provider preference',
    outputs: 'Structured LLM completion text, latency telemetry, active provider metadata',
    guarantee: 'Tri-tier fallback (Gemini Flash -> Groq Llama -> Local Ollama Qwen2.5 -> Offline Heuristics); zero API keys exposed to browser; 4GB VRAM safety.',
    description: 'Manages LLM request dispatch with configurable providers, bounded timeouts (25s cloud, 60s local), exponential backoff retries, and automated failover logging. Protects consumer GPUs with calibrated quantization.'
  },
  {
    id: 'node-parallel',
    step: '05',
    layer: 'Concurrent Agent Review',
    title: 'Parallel Security & Bug Detection Agents',
    file: 'backend/agents/security_agent.py & bug_agent.py',
    icon: GitBranch,
    color: 'bg-[#FEF3C7] text-[#92400E]',
    borderColor: 'border-[#FDE68A]',
    bgTint: 'bg-[#FEF3C7]/30',
    inputs: 'Source code, static findings, RAG normative passages',
    outputs: 'security_findings (CWE/OWASP exploit vectors) & bug_findings (logic, syntax, leaks, style)',
    guarantee: 'Executed in parallel via ThreadPoolExecutor; every finding mapped to real rule citations; strict separation of security vs logic concerns.',
    description: 'Dispatches two specialized agents concurrently in LangGraph: the Security Agent isolates exploit paths and injection vectors citing OWASP/CWE standards; the Bug Agent discovers off-by-one errors, resource leaks, and delimiter faults.'
  },
  {
    id: 'node-summary',
    step: '06',
    layer: 'Synthesis & Health Scoring',
    title: 'Summary Agent & Deterministic Triage',
    file: 'backend/agents/summary_agent.py (calculate_health_score)',
    icon: ShieldCheck,
    color: 'bg-[#EADCCB] text-[#6B5338]',
    borderColor: 'border-[#D8C7B5]',
    bgTint: 'bg-[#EADCCB]/30',
    inputs: 'Merged security and bug findings, static tool observations',
    outputs: '16-field unified issue schema, health_score (0.5 - 10.0), verdict (CLEAN, NEEDS REVIEW, FIX REQUIRED)',
    guarantee: 'Deterministic deduction policy (Critical: -3.0, High: -1.5, Medium: -0.75, Low: -0.25); safety ceiling caps; non-mathematical safety proof disclaimer.',
    description: 'Deduplicates overlapping issues, corroborates static detections against AI observations, calculates defensible codebase health score, and synthesizes executive triage verdict with explicit provenance badges.'
  },
  {
    id: 'node-coder',
    step: '07',
    layer: 'Remediation & Re-Check',
    title: 'Coder Agent Auto-Correction & LangGraph Cycle',
    file: 'backend/agents/coder_agent.py & backend/graph.py',
    icon: RefreshCw,
    color: 'bg-[#D8E9E5] text-[#2D5A43]',
    borderColor: 'border-[#C2DFD9]',
    bgTint: 'bg-[#D8E9E5]/30',
    inputs: 'Original code, unresolved findings, grounded RAG remediations',
    outputs: 'Corrected source, refactoring changelog, structural syntax validation, re-check verification',
    guarantee: 'AST syntax check rejects corrupted rewrites; iteration count capped (default 2, max 5); original code preserved in state; no false clean claims.',
    description: 'Rewrites code to eradicate flagged defects grounded in RAG guidance. Validates structural syntax via Python AST and delimiter balancer. Re-routes into parallel review to confirm defect resolution until CLEAN or capped.'
  }
];

const ARCHITECTURE_SECTIONS = [
  { id: 'flowchart', label: 'Interactive Flowchart & Pipeline', icon: Workflow },
  { id: 'layers', label: 'Layer Specification Matrix', icon: Layers },
  { id: 'api', label: 'REST API & Data Contracts', icon: Network },
  { id: 'storage', label: 'Storage & Vector Architecture', icon: HardDrive },
  { id: 'failover', label: 'Failover & 4GB VRAM Budget', icon: Cpu }
];

export default function Architecture() {
  const [activeSection, setActiveSection] = useState('flowchart');
  const [selectedNode, setSelectedNode] = useState(PIPELINE_NODES[0]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 font-sans">
      
      {/* Header Banner */}
      <div className="dev-card p-6 shadow-sm space-y-3 bg-white border border-[#E6E4DC] rounded-xl">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-lg bg-[#E7EDE2] text-[#4A6B56] border border-[#DCE8D8]">
              <Workflow className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2.5">
                <h2 className="text-lg font-bold text-[#343A35] tracking-tight uppercase">
                  AG-12 Protocol Architecture
                </h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#E8DFF2] text-[#4A3B69] border border-[#D5C6E6]">
                  v1.2 Production
                </span>
              </div>
              <p className="text-xs text-[#747A73] mt-0.5">
                Multi-Agent LangGraph Orchestration · Model Context Protocol (MCP) · In-Memory Dense Vector RAG · Tri-Tier Resilient Gateway
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-mono font-semibold bg-[#D8E9E5] text-[#2D5A43] border border-[#C2DFD9]">
              <span className="w-2 h-2 rounded-full bg-[#2D5A43] animate-pulse" />
              <span>Full Neuro-Symbolic Pipeline Active</span>
            </span>
          </div>
        </div>

        <p className="text-xs text-[#555C56] leading-relaxed max-w-4xl pt-1">
          AG-12 Protocol implements a <strong>hybrid neuro-symbolic software audit architecture</strong>. 
          By coupling deterministic static analyzers (MCP Layer) with semantic vector retrieval (RAG Layer) and a cyclic LangGraph state machine, 
          the system overcomes the fundamental limitations of single-prompt LLM code reviews: hallucinated vulnerability identifiers, syntax-corrupted rewrites, 
          and unverified remediations.
        </p>

        {/* Navigation Tabs */}
        <div className="flex flex-wrap gap-2 pt-3 border-t border-[#E6E4DC]">
          {ARCHITECTURE_SECTIONS.map(sec => {
            const Icon = sec.icon;
            const isActive = activeSection === sec.id;
            return (
              <button
                key={sec.id}
                onClick={() => setActiveSection(sec.id)}
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all cursor-pointer ${
                  isActive
                    ? 'bg-[#4A6B56] text-white shadow-sm border border-[#3E5C49]'
                    : 'bg-[#F8F6F0] text-[#747A73] hover:text-[#343A35] hover:bg-[#E7EDE2] border border-[#E6E4DC]'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{sec.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* SECTION 1: INTERACTIVE FLOWCHART & PIPELINE */}
      {activeSection === 'flowchart' && (
        <div className="space-y-6">
          
          {/* Visual Architecture SVG / Flowchart Canvas */}
          <div className="dev-card p-6 shadow-sm space-y-4 bg-white border border-[#E6E4DC] rounded-xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#E6E4DC]">
              <div className="flex items-center space-x-2.5">
                <Network className="w-4 h-4 text-[#4A6B56]" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#343A35]">
                  END-TO-END PIPELINE FLOWCHART &amp; LANGGRAPH STATE MACHINE
                </h3>
              </div>
              <span className="text-[11px] font-mono text-[#747A73]">Click any stage to inspect runtime contracts</span>
            </div>

            {/* Pipeline Stage Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
              {PIPELINE_NODES.map((node) => {
                const Icon = node.icon;
                const isSelected = selectedNode.id === node.id;
                return (
                  <div
                    key={node.id}
                    onClick={() => setSelectedNode(node)}
                    className={`p-4 rounded-xl border transition-all cursor-pointer relative overflow-hidden flex flex-col justify-between ${
                      isSelected
                        ? 'border-[#4A6B56] bg-[#F8F6F0] shadow-sm ring-1 ring-[#4A6B56]'
                        : 'border-[#E6E4DC] hover:border-[#4A6B56]/50 bg-white shadow-sm'
                    }`}
                  >
                    <div className="space-y-2.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-[#E7EDE2] border border-[#E6E4DC] text-[#4A6B56]">
                          STAGE {node.step}
                        </span>
                        <span className="text-[10px] font-mono text-[#747A73]">{node.layer}</span>
                      </div>

                      <div className="flex items-center space-x-2.5 pt-1">
                        <div className={`p-2 rounded-lg ${node.color} shadow-sm shrink-0 border border-black/5`}>
                          <Icon className="w-4 h-4" />
                        </div>
                        <h4 className="text-xs font-bold text-[#343A35] leading-tight">
                          {node.title}
                        </h4>
                      </div>

                      <p className="text-[11px] text-[#747A73] line-clamp-2 leading-relaxed pt-1">
                        {node.description}
                      </p>
                    </div>

                    <div className="pt-3 mt-3 border-t border-[#E6E4DC] flex items-center justify-between text-[10px] font-mono">
                      <span className="text-[#747A73] truncate max-w-[130px]">{node.file.split(' ')[0]}</span>
                      <span className={`font-bold flex items-center space-x-1 ${isSelected ? 'text-[#4A6B56]' : 'text-[#A2A8A0]'}`}>
                        <span>Inspect</span>
                        <ChevronRight className="w-3 h-3" />
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Cyclic LangGraph Loop Visualizer */}
            <div className="p-4 rounded-lg bg-[#F8F6F0] border border-[#E6E4DC] space-y-3 font-mono text-xs shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-[11px] font-bold text-[#4A6B56] uppercase tracking-wider flex items-center space-x-2">
                  <Workflow className="w-3.5 h-3.5" />
                  <span>LangGraph Conditional Cyclic Transitions</span>
                </span>
                <span className="text-[11px] text-[#92400E] font-semibold">
                  recheck_condition: (iteration &lt; max_iter) &amp;&amp; (unresolved &gt; 0) &amp;&amp; (!auto_fix_failed)
                </span>
              </div>

              <div className="p-3 bg-white rounded border border-[#E6E4DC] flex flex-wrap items-center justify-center gap-2 text-[11px]">
                <span className="px-2.5 py-1 rounded bg-[#E7EDE2] border border-[#E6E4DC] text-[#343A35]">START</span>
                <span className="text-[#A2A8A0] font-bold">→</span>
                <span className="px-2.5 py-1 rounded bg-[#D8E9E5] border border-[#C2DFD9] text-[#2D5A43]">static_analysis</span>
                <span className="text-[#A2A8A0] font-bold">→</span>
                <span className="px-2.5 py-1 rounded bg-[#E8DFF2] border border-[#D5C6E6] text-[#4A3B69]">rag_retrieval</span>
                <span className="text-[#A2A8A0] font-bold">→</span>
                <span className="px-2.5 py-1 rounded bg-[#E8DFF2] border border-[#D5C6E6] text-[#4A3B69]">llm_gateway</span>
                <span className="text-[#A2A8A0] font-bold">→</span>
                <span className="px-2.5 py-1 rounded bg-[#FEF3C7] border border-[#FDE68A] text-[#92400E]">parallel_review</span>
                <span className="text-[#A2A8A0] font-bold">→</span>
                <span className="px-2.5 py-1 rounded bg-[#EADCCB] border border-[#D8C7B5] text-[#6B5338]">summary_agent</span>
                <span className="text-[#A2A8A0] font-bold">→</span>
                <span className="px-2.5 py-1 rounded bg-[#D8E9E5] border border-[#C2DFD9] text-[#2D5A43] font-bold">coder_agent</span>
                <span className="text-[#92400E] font-bold px-2 py-0.5 rounded bg-[#FEF3C7] border border-[#FDE68A]">
                  ↺ Re-check Loop
                </span>
                <span className="text-[#A2A8A0] font-bold">→</span>
                <span className="px-2.5 py-1 rounded bg-[#E7EDE2] border border-[#E6E4DC] text-[#343A35]">END</span>
              </div>
            </div>

            {/* Selected Stage Detail Inspector */}
            <div className="p-5 bg-white border border-[#E6E4DC] rounded-xl space-y-4 shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-3 border-b border-[#E6E4DC] gap-2">
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded-lg ${selectedNode.color} border border-black/5`}>
                    <selectedNode.icon className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-[10px] font-mono font-bold text-[#4A6B56] uppercase">
                      Stage {selectedNode.step} Deep-Dive Inspector
                    </span>
                    <h3 className="text-sm font-bold text-[#343A35]">{selectedNode.title}</h3>
                  </div>
                </div>

                <div className="text-xs font-mono text-[#747A73] bg-[#F8F6F0] px-2.5 py-1 rounded border border-[#E6E4DC]">
                  Code: <code className="text-[#4A6B56] font-semibold">{selectedNode.file}</code>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
                <div className="p-3 rounded-lg bg-[#F8F6F0] border border-[#E6E4DC] space-y-1.5">
                  <span className="text-[10px] uppercase font-bold text-[#747A73] block">Input State Contract</span>
                  <p className="text-[#343A35] font-sans leading-relaxed text-[11px]">{selectedNode.inputs}</p>
                </div>

                <div className="p-3 rounded-lg bg-[#F8F6F0] border border-[#E6E4DC] space-y-1.5">
                  <span className="text-[10px] uppercase font-bold text-[#2D5A43] block">Output State Mutations</span>
                  <p className="text-[#343A35] font-sans leading-relaxed text-[11px]">{selectedNode.outputs}</p>
                </div>

                <div className="p-3 rounded-lg bg-[#F8F6F0] border border-[#E6E4DC] space-y-1.5">
                  <span className="text-[10px] uppercase font-bold text-[#92400E] block">Architectural Guarantee</span>
                  <p className="text-[#343A35] font-sans leading-relaxed text-[11px]">{selectedNode.guarantee}</p>
                </div>
              </div>
            </div>

          </div>

        </div>
      )}

      {/* SECTION 2: LAYER SPECIFICATION MATRIX */}
      {activeSection === 'layers' && (
        <div className="dev-card p-6 shadow-sm space-y-6 bg-white border border-[#E6E4DC] rounded-xl">
          <div className="flex items-center justify-between pb-3 border-b border-[#E6E4DC]">
            <div className="flex items-center space-x-2.5">
              <Layers className="w-4 h-4 text-[#4A6B56]" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#343A35]">
                7-LAYER HYBRID ARCHITECTURE SPECIFICATION MATRIX
              </h3>
            </div>
            <span className="text-xs text-[#747A73] font-mono">PR Agent Engineering Standards</span>
          </div>

          <div className="overflow-x-auto border border-[#E6E4DC] rounded-lg">
            <table className="w-full text-left text-xs font-sans">
              <thead className="bg-[#E7EDE2] text-[#343A35] border-b border-[#E6E4DC] font-mono text-[11px] uppercase">
                <tr>
                  <th className="p-3.5">Layer</th>
                  <th className="p-3.5">Target Responsibility</th>
                  <th className="p-3.5">Underlying Engine / Library</th>
                  <th className="p-3.5">Deterministic Invariant</th>
                  <th className="p-3.5">Fallback Policy</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E6E4DC] text-[#343A35] text-xs bg-white">
                <tr className="hover:bg-[#F8F6F0] transition-colors">
                  <td className="p-3.5 font-bold font-mono text-[#4A6B56]">Layer 1</td>
                  <td className="p-3.5 font-semibold text-[#343A35]">Source Ingestion &amp; Router</td>
                  <td className="p-3.5 font-mono text-[#747A73]">FastAPI, Python AST</td>
                  <td className="p-3.5 text-[#555C56]">Sanitizes filenames against traversal; rejects payloads &gt; 5MB</td>
                  <td className="p-3.5 font-mono text-[#92400E]">HTTP 400 / 413 Error Response</td>
                </tr>
                <tr className="hover:bg-[#F8F6F0] transition-colors">
                  <td className="p-3.5 font-bold font-mono text-[#4A6B56]">Layer 2</td>
                  <td className="p-3.5 font-semibold text-[#343A35]">Deterministic Static Analysis (MCP)</td>
                  <td className="p-3.5 font-mono text-[#747A73]">Bandit, Flake8, Cppcheck, ESLint, Checkstyle, RuboCop</td>
                  <td className="p-3.5 text-[#555C56]">Captures exact tool exit codes, latency, and rule IDs before LLM inference</td>
                  <td className="p-3.5 font-mono text-[#2D5A43]">Truthful ANALYZER_UNAVAILABLE status</td>
                </tr>
                <tr className="hover:bg-[#F8F6F0] transition-colors">
                  <td className="p-3.5 font-bold font-mono text-[#4A6B56]">Layer 3</td>
                  <td className="p-3.5 font-semibold text-[#343A35]">RAG Retrieval &amp; Vector Store</td>
                  <td className="p-3.5 font-mono text-[#747A73]">128D Dense N-Gram Hash Vector Engine</td>
                  <td className="p-3.5 text-[#555C56]">Matches queries against OWASP Top 10 (2021) and CWE Top 25</td>
                  <td className="p-3.5 font-mono text-[#92400E]">DEGRADED (RAG UNAVAILABLE) verdict</td>
                </tr>
                <tr className="hover:bg-[#F8F6F0] transition-colors">
                  <td className="p-3.5 font-bold font-mono text-[#4A6B56]">Layer 4</td>
                  <td className="p-3.5 font-semibold text-[#343A35]">Resilient LLM Gateway</td>
                  <td className="p-3.5 font-mono text-[#747A73]">Gemini 1.5 Flash, Groq, Ollama Qwen2.5-Coder 7B</td>
                  <td className="p-3.5 text-[#555C56]">Zero keys to frontend; 4GB VRAM safety bounds (max 4096 tokens)</td>
                  <td className="p-3.5 font-mono text-[#92400E]">Tri-tier automatic failover</td>
                </tr>
                <tr className="hover:bg-[#F8F6F0] transition-colors">
                  <td className="p-3.5 font-bold font-mono text-[#4A6B56]">Layer 5</td>
                  <td className="p-3.5 font-semibold text-[#343A35]">Parallel Multi-Agent Review</td>
                  <td className="p-3.5 font-mono text-[#747A73]">Concurrent ThreadPoolExecutor in LangGraph</td>
                  <td className="p-3.5 text-[#555C56]">Security Agent and Bug Agent execute independently without context cross-bleed</td>
                  <td className="p-3.5 font-mono text-[#92400E]">Synthesizes static findings into fallback findings</td>
                </tr>
                <tr className="hover:bg-[#F8F6F0] transition-colors">
                  <td className="p-3.5 font-bold font-mono text-[#4A6B56]">Layer 6</td>
                  <td className="p-3.5 font-semibold text-[#343A35]">Summary Synthesis &amp; Scoring</td>
                  <td className="p-3.5 font-mono text-[#747A73]">Deterministic Health Score Formula</td>
                  <td className="p-3.5 text-[#555C56]">Deduplicates issues; computes score 0.5 - 10.0; enforces safety ceilings</td>
                  <td className="p-3.5 font-mono text-[#92400E]">Mathematical disclaimer on CLEAN verdict</td>
                </tr>
                <tr className="hover:bg-[#F8F6F0] transition-colors">
                  <td className="p-3.5 font-bold font-mono text-[#4A6B56]">Layer 7</td>
                  <td className="p-3.5 font-semibold text-[#343A35]">Coder Agent &amp; Re-Check Cycle</td>
                  <td className="p-3.5 font-mono text-[#747A73]">LangGraph Cyclic Edge + Myers LCS Diff</td>
                  <td className="p-3.5 text-[#555C56]">Syntax AST verification rejects corrupted rewrites; caps max iterations at 2-5</td>
                  <td className="p-3.5 font-mono text-[#92400E]">Rolls back to original code; flags auto_fix_failure</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SECTION 3: REST API & DATA CONTRACTS */}
      {activeSection === 'api' && (
        <div className="dev-card p-6 shadow-sm space-y-6 bg-white border border-[#E6E4DC] rounded-xl">
          <div className="flex items-center justify-between pb-3 border-b border-[#E6E4DC]">
            <div className="flex items-center space-x-2.5">
              <Network className="w-4 h-4 text-[#4A6B56]" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#343A35]">
                REST API INTERFACE &amp; CLIENT-SERVER DATA CONTRACTS
              </h3>
            </div>
            <span className="text-xs text-[#747A73] font-mono">FastAPI ASGI Server (Port 8000)</span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 text-xs font-mono">
            
            {/* Review & Fix Endpoints */}
            <div className="p-4 rounded-xl bg-white border border-[#E6E4DC] space-y-3 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-[#343A35] uppercase font-sans">Core Pipeline Execution</span>
                <span className="px-2 py-0.5 rounded text-[10px] bg-[#E7EDE2] text-[#4A6B56] border border-[#E6E4DC]">
                  Thread-Safe Cached
                </span>
              </div>

              <div className="space-y-2 text-[11px]">
                <div className="p-2.5 bg-[#F8F6F0] rounded-lg border border-[#E6E4DC]">
                  <div className="flex items-center space-x-2 text-[#4A6B56] font-bold">
                    <span className="px-1.5 py-0.5 bg-[#D8E9E5] text-[#2D5A43] rounded text-[10px]">POST</span>
                    <span>/api/review</span>
                  </div>
                  <p className="text-[#747A73] text-[10px] font-sans mt-1">
                    Executes the complete 7-stage review and auto-fix pipeline. Returns full issue list, health score, verdict, and telemetry.
                  </p>
                </div>

                <div className="p-2.5 bg-[#F8F6F0] rounded-lg border border-[#E6E4DC]">
                  <div className="flex items-center space-x-2 text-[#4A6B56] font-bold">
                    <span className="px-1.5 py-0.5 bg-[#D8E9E5] text-[#2D5A43] rounded text-[10px]">POST</span>
                    <span>/api/remediate</span>
                  </div>
                  <p className="text-[#747A73] text-[10px] font-sans mt-1">
                    Directly invokes Coder Agent with specific unresolved issues. Validates syntax before returning code and refactoring changelog.
                  </p>
                </div>

                <div className="p-2.5 bg-[#F8F6F0] rounded-lg border border-[#E6E4DC]">
                  <div className="flex items-center space-x-2 text-[#4A6B56] font-bold">
                    <span className="px-1.5 py-0.5 bg-[#D8E9E5] text-[#2D5A43] rounded text-[10px]">POST</span>
                    <span>/api/recheck</span>
                  </div>
                  <p className="text-[#747A73] text-[10px] font-sans mt-1">
                    Executes real static analysis linters against corrected code, recalculating health score and verifying defect eradication.
                  </p>
                </div>
              </div>
            </div>

            {/* RAG & Download Endpoints */}
            <div className="p-4 rounded-xl bg-white border border-[#E6E4DC] space-y-3 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-[#343A35] uppercase font-sans">RAG, Gateway &amp; Artifact Downloads</span>
                <span className="px-2 py-0.5 rounded text-[10px] bg-[#E8DFF2] text-[#4A3B69] border border-[#D5C6E6]">
                  Path-Safe / Sandboxed
                </span>
              </div>

              <div className="space-y-2 text-[11px]">
                <div className="p-2.5 bg-[#F8F6F0] rounded-lg border border-[#E6E4DC]">
                  <div className="flex items-center space-x-2 text-[#4A6B56] font-bold">
                    <span className="px-1.5 py-0.5 bg-[#EADCCB] text-[#6B5338] rounded text-[10px]">GET</span>
                    <span>/api/download?review_id=...</span>
                  </div>
                  <p className="text-[#747A73] text-[10px] font-sans mt-1">
                    Streams corrected source with safe filename (path traversal stripped) and correct extension (.py, .cpp, .java, etc.).
                  </p>
                </div>

                <div className="p-2.5 bg-[#F8F6F0] rounded-lg border border-[#E6E4DC]">
                  <div className="flex items-center space-x-2 text-[#4A6B56] font-bold">
                    <span className="px-1.5 py-0.5 bg-[#EADCCB] text-[#6B5338] rounded text-[10px]">GET</span>
                    <span>/api/audit-report?review_id=...</span>
                  </div>
                  <p className="text-[#747A73] text-[10px] font-sans mt-1">
                    Generates and downloads certified Markdown audit report including executive summary, tool provenance, and changelog.
                  </p>
                </div>

                <div className="p-2.5 bg-[#F8F6F0] rounded-lg border border-[#E6E4DC]">
                  <div className="flex items-center space-x-2 text-[#4A6B56] font-bold">
                    <span className="px-1.5 py-0.5 bg-[#D8E9E5] text-[#2D5A43] rounded text-[10px]">POST</span>
                    <span>/api/rag/query</span>
                  </div>
                  <p className="text-[#747A73] text-[10px] font-sans mt-1">
                    Executes vector cosine similarity query against pre-indexed normative standards with configurable top_k and min_similarity.
                  </p>
                </div>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* SECTION 4: STORAGE & VECTOR ARCHITECTURE */}
      {activeSection === 'storage' && (
        <div className="dev-card p-6 shadow-sm space-y-6 bg-white border border-[#E6E4DC] rounded-xl">
          <div className="flex items-center justify-between pb-3 border-b border-[#E6E4DC]">
            <div className="flex items-center space-x-2.5">
              <HardDrive className="w-4 h-4 text-[#4A6B56]" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#343A35]">
                STORAGE, DATABASE &amp; VECTOR PERSISTENCE ARCHITECTURE
              </h3>
            </div>
            <span className="text-xs text-[#747A73] font-mono">SQLite + In-Memory Dense Store</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs leading-relaxed">
            
            {/* Relational Database */}
            <div className="p-4 rounded-xl bg-white border border-[#E6E4DC] space-y-3 shadow-sm">
              <div className="flex items-center space-x-2 text-[#4A6B56] font-bold text-sm">
                <Database className="w-4 h-4" />
                <span>SQLite Audit Store (`pr_agent_audit.db`)</span>
              </div>
              <p className="text-[#555C56] font-sans">
                Persistent local database initialized with safe pragmas (WAL mode, foreign keys, synchronous=NORMAL). 
                Stores full historical review runs, static tool telemetry, and refactoring audit trails.
              </p>
              <div className="p-3 bg-[#F8F6F0] rounded-lg border border-[#E6E4DC] font-mono text-[11px] space-y-1 text-[#343A35]">
                <span className="text-[#747A73] uppercase text-[10px] font-bold block">Table: review_records</span>
                <div>- <span className="text-[#4A6B56] font-semibold">review_id</span>: TEXT PRIMARY KEY</div>
                <div>- <span className="text-[#4A6B56] font-semibold">timestamp</span>: DATETIME DEFAULT CURRENT_TIMESTAMP</div>
                <div>- <span className="text-[#4A6B56] font-semibold">filename, language</span>: TEXT</div>
                <div>- <span className="text-[#4A6B56] font-semibold">health_score, post_fix_score</span>: REAL</div>
                <div>- <span className="text-[#4A6B56] font-semibold">verdict, summary, full_data</span>: JSON TEXT</div>
              </div>
            </div>

            {/* In-Memory Vector Store */}
            <div className="p-4 rounded-xl bg-white border border-[#E6E4DC] space-y-3 shadow-sm">
              <div className="flex items-center space-x-2 text-[#4A3B69] font-bold text-sm">
                <HardDrive className="w-4 h-4" />
                <span>Deterministic Dense Vector Store (`VectorStore`)</span>
              </div>
              <p className="text-[#555C56] font-sans">
                Air-gapped, zero-GPU vector engine projecting text tokens into 128-dimensional dense vectors using hashed feature projection with L2 normalization.
                Guarantees sub-millisecond retrieval latency without downloading multi-gigabyte PyTorch/HuggingFace checkpoints.
              </p>
              <div className="p-3 bg-[#F8F6F0] rounded-lg border border-[#E6E4DC] font-mono text-[11px] space-y-1 text-[#343A35]">
                <span className="text-[#747A73] uppercase text-[10px] font-bold block">Vector Specifications</span>
                <div>- <span className="text-[#4A3B69] font-semibold">Dimension</span>: 128 float32 components</div>
                <div>- <span className="text-[#4A3B69] font-semibold">Distance Metric</span>: Cosine Similarity (A · B / (||A|| ||B||))</div>
                <div>- <span className="text-[#4A3B69] font-semibold">Indexed Standards</span>: OWASP Top 10, CWE Top 25, PEP 8, Google C++, Airbnb JS</div>
                <div>- <span className="text-[#4A3B69] font-semibold">Deduplication</span>: SHA-256 content-hash idempotency</div>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* SECTION 5: FAILOVER & 4GB VRAM BUDGET */}
      {activeSection === 'failover' && (
        <div className="dev-card p-6 shadow-sm space-y-6 bg-white border border-[#E6E4DC] rounded-xl">
          <div className="flex items-center justify-between pb-3 border-b border-[#E6E4DC]">
            <div className="flex items-center space-x-2.5">
              <Cpu className="w-4 h-4 text-[#4A6B56]" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#343A35]">
                ERROR RECOVERY, PROVIDER FAILOVER &amp; 4GB VRAM BUDGETING
              </h3>
            </div>
            <span className="text-xs text-[#747A73] font-mono">Resource Constraint Protocol</span>
          </div>

          <div className="space-y-4 text-xs leading-relaxed text-[#555C56]">
            <p className="font-sans">
              To operate reliably in offline environments and on consumer laptops equipped with modest hardware (such as 4GB VRAM GPUs or integrated graphics), 
              AG-12 Protocol enforces strict parameter and quantization bounds:
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
              <div className="p-4 rounded-xl bg-white border border-[#D8E9E5] space-y-2 shadow-sm">
                <span className="text-[#2D5A43] font-bold block uppercase text-[11px]">Primary: Gemini Flash / Groq</span>
                <span className="text-[#555C56] block text-[11px]">High-speed cloud inference (average latency 1.2s - 2.8s)</span>
                <span className="text-[#747A73] block text-[10px]">Bounded timeout: 25.0s</span>
              </div>

              <div className="p-4 rounded-xl bg-white border border-[#FEF3C7] space-y-2 shadow-sm">
                <span className="text-[#92400E] font-bold block uppercase text-[11px]">Secondary: Local Ollama (Qwen2.5)</span>
                <span className="text-[#555C56] block text-[11px]">Q4_K_M quantized GGUF (fits inside 2.8GB - 3.8GB memory footprint)</span>
                <span className="text-[#747A73] block text-[10px]">Bounded timeout: 60.0s</span>
              </div>

              <div className="p-4 rounded-xl bg-white border border-[#E8DFF2] space-y-2 shadow-sm">
                <span className="text-[#4A3B69] font-bold block uppercase text-[11px]">Fallback: Offline Heuristic Engine</span>
                <span className="text-[#555C56] block text-[11px]">100% deterministic pattern refactorer based on MCP linter output</span>
                <span className="text-[#747A73] block text-[10px]">Zero GPU / zero network required</span>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-[#F8F6F0] border border-[#E6E4DC] font-mono text-[11px] space-y-2 shadow-sm">
              <span className="text-[#92400E] font-bold uppercase tracking-wider block text-[10px]">
                4GB VRAM Safe Operating Rules
              </span>
              <ul className="list-disc pl-5 space-y-1 text-[#555C56]">
                <li>Never download large multi-gigabyte models automatically on application startup.</li>
                <li>Keep inference context window bounded (<code className="text-[#4A6B56] font-semibold">num_ctx: 2048</code>) to prevent KV cache VRAM overflow.</li>
                <li>If Ollama is unresponsive or throws OutOfMemory, automatically fail over to the deterministic pattern refactorer without crashing the server.</li>
              </ul>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
