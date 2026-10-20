import React, { useState } from 'react';
import { 
  FileText, Award, HelpCircle, Check, X, ShieldAlert, Cpu, Calculator, 
  Sparkles, BookOpen, Layers, Terminal, Database, Server, GitBranch, 
  RefreshCw, CheckCircle2, AlertTriangle, ExternalLink, Code2, ChevronDown, 
  ChevronUp, Scale, Bookmark
} from 'lucide-react';

const TECH_STACK_TABLE = [
  { category: 'Frontend Layer', technology: 'React 19, Vite 6, TailwindCSS, Lucide React, Axios' },
  { category: 'Backend Framework', technology: 'FastAPI, Uvicorn (ASGI), Pydantic v2, Python 3.10+' },
  { category: 'Agent Orchestration', technology: 'LangGraph (Cyclic Finite State Machine), ThreadPoolExecutor' },
  { category: 'Static Analysis (MCP)', technology: 'Bandit (Security), Flake8 (Style/Bugs), Cppcheck, ESLint, Checkstyle, RuboCop' },
  { category: 'RAG & Vector Store', technology: 'In-Memory 128D Dense N-Gram Hashed Feature Projection, Cosine Similarity' },
  { category: 'LLM Gateway', technology: 'Gemini 1.5 Flash (Primary Cloud), Groq Llama 3.3 70B, Ollama Qwen2.5-Coder 7B (Local GGUF)' },
  { category: 'Database & Caching', technology: 'SQLite3 (pr_agent_audit.db) with WAL mode, Thread-Safe In-Memory Cache' },
  { category: 'Standards Grounding', technology: 'OWASP Top 10 (2021), CWE Top 25 Most Dangerous Weaknesses, PEP 8, Google C++, Airbnb JS' }
];

const VIVA_QUESTIONS = [
  {
    q: "Why is deterministic static analysis (MCP layer) invoked before any generative LLM inference?",
    a: "Generative Large Language Models are probabilistic and prone to hallucinating non-existent vulnerability identifiers, creating false alarms or overlooking subtle syntax bugs. Invoking deterministic static analyzers (Bandit, Flake8, Cppcheck, Checkstyle, ESLint, RuboCop) establishes an empirical, immutable ground truth of syntax errors and known vulnerability patterns prior to LLM execution. The subsequent multi-agent layers are strictly constrained to ground their findings in these verified observations."
  },
  {
    q: "How does the system eliminate fictitious or hallucinated security rule citations?",
    a: "AG-12 Protocol enforces a strict dual-attribution citation constraint: every finding emitted by the pipeline must link back to either a verified linter rule identifier or a verified vector node in the RAG vector store (which indexes verified OWASP Top 10 2021 and CWE Top 25 standards). Findings synthesized without verifiable static backing are explicitly flagged in the UI as 'AI Observation (Unverified)' with low confidence badges."
  },
  {
    q: "How is termination of the LangGraph auto-remediation loop mathematically guaranteed?",
    a: "Cyclic multi-agent loops risk infinite execution if an automated fix continually fails to resolve defects. The LangGraph state machine enforces a finite termination condition in `recheck_condition`: the transition evaluates `iteration_count >= max_iterations` (clamped between 1 and 5, default 2), `unresolved_count == 0`, or `auto_fix_failure == True`. Because `iteration_count` strictly monotonically increases on every cycle, termination is guaranteed in finite discrete steps with O(1) loop bound."
  },
  {
    q: "How is the Codebase Health Score formulated, and why avoid purely subjective LLM scoring?",
    a: "Subjective LLM scoring produces non-deterministic, fluctuating scores across identical code inputs. AG-12 Protocol uses a deterministic deduction algorithm: H = clamp(10.0 - Σ w(s_i), 0.5, 10.0), where weights are calibrated strictly by defect severity (Critical: -3.0, High: -1.5, Medium: -0.75, Low: -0.25). Furthermore, safety ceiling caps are enforced (e.g., any Critical defect caps the score at max 6.0, and any High defect caps it at 8.0), preventing false claims of security."
  },
  {
    q: "How does AG-12 Protocol support consumer hardware constrained to 4GB of VRAM?",
    a: "The LLM Gateway integrates automated failover to local quantized models via Ollama. By deploying 4-bit quantized GGUF models such as Qwen2.5-Coder:1.5B (~1.6GB VRAM) or Qwen2.5-Coder:3B (~2.8GB VRAM) with bounded context windows (`num_ctx: 2048`), the entire model footprint resides within 4GB consumer GPU limits. In completely offline or GPU-less environments, the gateway falls back to deterministic heuristic pattern refactoring."
  },
  {
    q: "How does the Myers / LCS diff engine in CodeDiffViewer prevent visual line drift?",
    a: "Naive line-by-line index comparison (`orig[i] !== corr[i]`) causes severe visual drift whenever a line is inserted or deleted, misaligning unrelated code. CodeDiffViewer implements a 2D Longest Common Subsequence (LCS) dynamic programming matrix that computes the minimal edit script of deletions and additions. Successive deletion and addition chunks are paired into replacement blocks, and empty ghost rows align unmodified code across both columns."
  },
  {
    q: "How are path traversal attacks prevented during corrected code downloads?",
    a: "User-submitted filenames are strictly sanitized before persistence or file generation: `os.path.basename` strips all directory components (e.g., `../../etc/passwd` becomes `passwd`), null bytes and control characters (`[\\x00-\\x1f\\x7f]`) are removed via regular expressions, and the file extension is mapped directly from the verified programming language metadata (.py, .cpp, .c, .java, .js, .rb)."
  },
  {
    q: "Why does a 'CLEAN' verdict explicitly state that it is not a mathematical proof of safety?",
    a: "No automated static or dynamic analysis tool can solve the Halting Problem or guarantee the total absence of vulnerabilities in Turing-complete programs (Rice's Theorem). Therefore, AG-12 Protocol attaches an explicit disclaimer to all CLEAN verdicts: 'Scope is limited to the executed static linters and multi-agent checks; not a formal mathematical proof of absolute correctness.'"
  },
  {
    q: "How does the structural syntax validation guard prevent Coder Agent regressions?",
    a: "Before any proposed correction from the Coder Agent is applied or presented to the user, `validate_code_syntax` tests the code: for Python, it parses the AST via `ast.parse()`; for C, C++, Java, JS, and Ruby, it executes a stack-based delimiter balancer tracking quotes, comments, parentheses, curly braces, and square brackets. If a syntax error or unclosed delimiter is detected, the rewrite is rejected, original code is restored, and a `validation_rejected` changelog entry is recorded."
  },
  {
    q: "What is the architectural role of Model Context Protocol (MCP) in AG-12 Protocol?",
    a: "MCP provides a standardized, sandboxed tool dispatch interface that decouples linter execution from LLM prompt logic. It allows the backend to invoke language-specific analysis binaries in isolated temporary directories, capture exit codes and standard error streams safely, and normalize disparate CLI outputs into a unified JSON telemetry schema."
  }
];

const REFERENCES_LIST = [
  {
    citation: "OWASP Foundation (2021). OWASP Top 10: 2021 The Ten Most Critical Web Application Security Risks.",
    url: "https://owasp.org/Top10/"
  },
  {
    citation: "MITRE Corporation (2023). 2023 CWE Top 25 Most Dangerous Software Weaknesses.",
    url: "https://cwe.mitre.org/top25/archive/2023/2023_top25_list.html"
  },
  {
    citation: "Myers, E. W. (1986). An O(ND) difference algorithm and its variations. Algorithmica, 1(1-4), 251-266.",
    url: "http://www.xmailserver.org/diff2.pdf"
  },
  {
    citation: "Anthropic (2024). Model Context Protocol (MCP) Specification & Architecture.",
    url: "https://modelcontextprotocol.io/"
  },
  {
    citation: "LangChain (2024). LangGraph: Building Language Agents as Graphs and Finite State Machines.",
    url: "https://langchain-ai.github.io/langgraph/"
  },
  {
    citation: "Python Software Foundation. PEP 8 – Style Guide for Python Code.",
    url: "https://peps.python.org/pep-0008/"
  }
];

export default function PaperViva() {
  const [activeTab, setActiveTab] = useState('paper'); // 'paper' | 'viva' | 'algorithms'
  const [expandedFaq, setExpandedFaq] = useState(null);

  const toggleFaq = (idx) => {
    setExpandedFaq(expandedFaq === idx ? null : idx);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 font-sans">
      
      {/* Page Header */}
      <div className="dev-card p-6 shadow-sm space-y-3 bg-white border border-[#E6E4DC] rounded-xl">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-lg bg-[#E8DFF2] text-[#4A3B69] border border-[#D5C6E6]">
              <BookOpen className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2.5">
                <h2 className="text-lg font-bold text-[#343A35] tracking-tight uppercase">
                  Reports, Specification &amp; Viva Defense Guide
                </h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#E8DFF2] text-[#4A3B69] border border-[#D5C6E6]">
                  AG-12 Engineering Specification
                </span>
              </div>
              <p className="text-xs text-[#747A73] mt-0.5">
                Comprehensive Research Defense, Mathematical Formulations, Limitations &amp; Oral Examination Q&amp;A
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setActiveTab('paper')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all cursor-pointer ${
                activeTab === 'paper'
                  ? 'bg-[#4A6B56] text-white shadow-sm'
                  : 'bg-[#F8F6F0] text-[#747A73] hover:text-[#343A35] hover:bg-[#E7EDE2] border border-[#E6E4DC]'
              }`}
            >
              Academic Paper
            </button>
            <button
              onClick={() => setActiveTab('algorithms')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all cursor-pointer ${
                activeTab === 'algorithms'
                  ? 'bg-[#4A6B56] text-white shadow-sm'
                  : 'bg-[#F8F6F0] text-[#747A73] hover:text-[#343A35] hover:bg-[#E7EDE2] border border-[#E6E4DC]'
              }`}
            >
              Algorithms &amp; Tech Stack
            </button>
            <button
              onClick={() => setActiveTab('viva')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all cursor-pointer ${
                activeTab === 'viva'
                  ? 'bg-[#4A6B56] text-white shadow-sm'
                  : 'bg-[#F8F6F0] text-[#747A73] hover:text-[#343A35] hover:bg-[#E7EDE2] border border-[#E6E4DC]'
              }`}
            >
              Viva Examination Q&amp;A (10)
            </button>
          </div>
        </div>
      </div>

      {/* TAB 1: ACADEMIC PAPER CONTENT */}
      {activeTab === 'paper' && (
        <div className="space-y-6">
          
          {/* Paper Title & Authors Card */}
          <div className="dev-card p-6 shadow-sm space-y-4 bg-white border border-[#E6E4DC] rounded-xl">
            <div className="text-center space-y-2 pb-4 border-b border-[#E6E4DC]">
              <span className="text-[11px] font-mono text-[#4A6B56] uppercase tracking-widest font-bold">
                Research Defense &amp; Engineering Specification · AG-12 Protocol
              </span>
              <h1 className="text-lg md:text-xl font-bold text-[#343A35] tracking-tight leading-snug">
                AG-12 Protocol: A Neuro-Symbolic Multi-Agent Framework for Multilingual Code Review, Grounded Vulnerability Remediation, and Deterministic Quality Triage
              </h1>
              <div className="text-xs text-[#747A73] font-mono pt-1">
                Engineered for Consumer Hardware (4GB VRAM GPU / Local Air-Gapped Operation)
              </div>
            </div>

            {/* Abstract */}
            <div className="p-4 rounded-xl bg-[#F8F6F0] border border-[#E6E4DC] space-y-2">
              <span className="text-xs font-bold uppercase tracking-wider text-[#4A6B56] font-mono block">
                1. Abstract
              </span>
              <p className="text-xs text-[#555C56] leading-relaxed font-sans">
                Automated source code review systems powered solely by standalone generative Large Language Models (LLMs) suffer from persistent limitations: hallucinated security citations, non-deterministic defect scoring, syntax-corrupted auto-corrections, and an inability to operate under strict consumer hardware budgets. We introduce <strong>AG-12 Protocol</strong>, a hybrid neuro-symbolic multi-agent software auditing architecture. AG-12 Protocol bridges deterministic Model Context Protocol (MCP) static analyzers with a 128-dimensional dense vector store for normative grounding and orchestrates parallel review agents through a cyclic LangGraph state machine. By pairing deletion and addition tokens via Myers Longest Common Subsequence (LCS) dynamic programming, enforcing stack-based structural syntax validation, and executing real re-check static verification against corrected artifacts, AG-12 Protocol guarantees defensible quality triage without unverified claims of mathematical correctness.
              </p>
            </div>

            {/* Problem Statement & Objectives */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="p-4 rounded-xl bg-white border border-[#FECACA] space-y-2 shadow-sm">
                <span className="text-xs font-bold uppercase tracking-wider text-[#991B1B] font-mono block">
                  2. Problem Statement
                </span>
                <p className="text-[#555C56] leading-relaxed font-sans">
                  Contemporary static analysis tools (linters) provide deterministic rule detection but lack contextual cross-line reasoning and cannot synthesize coherent refactorings. Conversely, pure LLM code reviewers hallucinate non-existent CWE numbers, generate code with subtle syntax and regression defects, and fluctuate in their ratings across identical inputs. Furthermore, enterprise models require continuous cloud connectivity and substantial VRAM footprints, rendering them unsuitable for air-gapped or 4GB VRAM environments.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-white border border-[#C2DFD9] space-y-2 shadow-sm">
                <span className="text-xs font-bold uppercase tracking-wider text-[#2D5A43] font-mono block">
                  3. Research &amp; Engineering Objectives
                </span>
                <ul className="list-disc pl-4 space-y-1 text-[#555C56] font-sans leading-relaxed">
                  <li><strong>Deterministic Baseline:</strong> Anchor LLM agent prompts in verified static tool findings (MCP layer).</li>
                  <li><strong>Normative RAG Grounding:</strong> Retrieve authenticated OWASP/CWE standards to eliminate hallucinated citations.</li>
                  <li><strong>Parallel Decomposition:</strong> Isolate security vulnerabilities from functional bug analysis concurrently.</li>
                  <li><strong>Bounded Remediation Cycle:</strong> Guarantee finite-state termination of auto-fix loops with syntax validation.</li>
                  <li><strong>Consumer Hardware Compatibility:</strong> Operate reliably within 4GB VRAM limits via 4-bit quantized local models.</li>
                </ul>
              </div>
            </div>

            {/* Comparative Analysis */}
            <div className="space-y-3 pt-2">
              <span className="text-xs font-bold uppercase tracking-wider text-[#343A35] font-mono block">
                4. Existing Systems vs. AG-12 Protocol
              </span>

              <div className="border border-[#E6E4DC] rounded-xl overflow-hidden bg-white shadow-sm">
                <table className="w-full text-left text-xs font-sans">
                  <thead className="bg-[#E7EDE2] text-[#343A35] border-b border-[#E6E4DC] font-mono text-[11px] uppercase">
                    <tr>
                      <th className="p-3">Architectural Dimension</th>
                      <th className="p-3">Standalone Linters</th>
                      <th className="p-3">Single-Prompt LLM</th>
                      <th className="p-3 text-[#4A6B56]">AG-12 Protocol</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E6E4DC] text-[#343A35] text-xs">
                    <tr className="hover:bg-[#F8F6F0] transition-colors">
                      <td className="p-3 font-semibold text-[#343A35]">Rule Attribution</td>
                      <td className="p-3 text-[#747A73]">Strictly internal tool codes</td>
                      <td className="p-3 text-[#991B1B]">Prone to hallucination</td>
                      <td className="p-3 text-[#4A6B56] font-semibold">Dual-attribution (OWASP/CWE + MCP)</td>
                    </tr>
                    <tr className="hover:bg-[#F8F6F0] transition-colors">
                      <td className="p-3 font-semibold text-[#343A35]">Code Auto-Remediation</td>
                      <td className="p-3 text-[#747A73]">Limited to style formatting</td>
                      <td className="p-3 text-[#92400E]">Unverified code generation</td>
                      <td className="p-3 text-[#4A6B56] font-semibold">Grounded Coder Agent + Syntax AST check</td>
                    </tr>
                    <tr className="hover:bg-[#F8F6F0] transition-colors">
                      <td className="p-3 font-semibold text-[#343A35]">Re-Check Verification</td>
                      <td className="p-3 text-[#747A73]">Manual re-execution</td>
                      <td className="p-3 text-[#991B1B]">None (claims safety blindly)</td>
                      <td className="p-3 text-[#4A6B56] font-semibold">Real re-check cycle with static linters</td>
                    </tr>
                    <tr className="hover:bg-[#F8F6F0] transition-colors">
                      <td className="p-3 font-semibold text-[#343A35]">Health Score Policy</td>
                      <td className="p-3 text-[#747A73]">Raw error counts only</td>
                      <td className="p-3 text-[#991B1B]">Subjective, non-deterministic</td>
                      <td className="p-3 text-[#4A6B56] font-semibold">Deterministic formula with safety caps</td>
                    </tr>
                    <tr className="hover:bg-[#F8F6F0] transition-colors">
                      <td className="p-3 font-semibold text-[#343A35]">4GB VRAM Offline Operation</td>
                      <td className="p-3 text-[#2D5A43]">Supported (CLI)</td>
                      <td className="p-3 text-[#991B1B]">Unsupported (Cloud only)</td>
                      <td className="p-3 text-[#4A6B56] font-semibold">Supported (Ollama Q4_K_M + Heuristics)</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Modules Description */}
            <div className="space-y-3 pt-2">
              <span className="text-xs font-bold uppercase tracking-wider text-[#343A35] font-mono block">
                5. System Modules &amp; Functional Architecture
              </span>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="p-3.5 rounded-xl bg-white border border-[#E6E4DC] space-y-1 shadow-sm">
                  <span className="font-bold text-[#4A6B56] font-mono">Module 1: Ingestion &amp; AST Router</span>
                  <p className="text-[#555C56] text-[11px] leading-relaxed">
                    Validates input buffer sizes, strips path traversal artifacts, and routes code to corresponding language tooling for Python, C, C++, Java, JavaScript, and Ruby.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-white border border-[#E6E4DC] space-y-1 shadow-sm">
                  <span className="font-bold text-[#4A6B56] font-mono">Module 2: MCP Static Analysis Engine</span>
                  <p className="text-[#555C56] text-[11px] leading-relaxed">
                    Dispatches native static analysis binaries (Bandit, Flake8, Cppcheck, ESLint, Checkstyle, RuboCop) in sandboxed temporary files, capturing tool exit codes, stderr, and finding records.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-white border border-[#E6E4DC] space-y-1 shadow-sm">
                  <span className="font-bold text-[#4A3B69] font-mono">Module 3: Grounded Vector RAG</span>
                  <p className="text-[#555C56] text-[11px] leading-relaxed">
                    Indexes standard security rules and uploaded developer context into an in-memory 128D dense vector space. Employs cosine similarity to inject verified normative rules into prompts.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-white border border-[#E6E4DC] space-y-1 shadow-sm">
                  <span className="font-bold text-[#4A3B69] font-mono">Module 4: Resilient LLM Gateway</span>
                  <p className="text-[#555C56] text-[11px] leading-relaxed">
                    Abstracts LLM providers with circuit breakers, timeouts, and automated failover (Gemini Flash &rarr; Groq &rarr; Ollama Qwen2.5-Coder 7B &rarr; Heuristic Engine).
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-white border border-[#E6E4DC] space-y-1 shadow-sm">
                  <span className="font-bold text-[#92400E] font-mono">Module 5: Parallel Review Agents</span>
                  <p className="text-[#555C56] text-[11px] leading-relaxed">
                    Executes the Security Agent and Bug Detection Agent in parallel threads, ensuring dedicated prompt budgets for vulnerability exploit vectors versus syntax, bounds, and resource leaks.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-white border border-[#E6E4DC] space-y-1 shadow-sm">
                  <span className="font-bold text-[#2D5A43] font-mono">Module 6: Summary &amp; Coder Agents</span>
                  <p className="text-[#555C56] text-[11px] leading-relaxed">
                    Synthesizes findings into a 16-field schema, computes deterministic health scores, executes Coder Agent remediation, and re-checks corrected code until CLEAN or iteration limit.
                  </p>
                </div>
              </div>
            </div>

            {/* Results, Limitations & Future Scope */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pt-2">
              <div className="p-4 rounded-xl bg-[#FEF3C7] border border-[#FDE68A] space-y-2">
                <span className="text-xs font-bold uppercase tracking-wider text-[#92400E] font-mono block">
                  6. Actual Engineering Outcomes &amp; Known Limitations
                </span>
                <p className="text-[#78350F] leading-relaxed font-sans">
                  AG-12 Protocol was validated across test suites for Python, C, C++, Java, JS, and Ruby. Grounded remediation resolved all original Critical SQL injections, hardcoded secrets, and division-by-zero defects without creating delimiter corruption.
                </p>
                <div className="p-2.5 bg-white/70 rounded-lg border border-[#FDE68A] text-[11px] text-[#78350F] space-y-1">
                  <div>• <strong>Hardware Limit:</strong> Local 4GB VRAM restricts Ollama models to &le; 7B parameters.</div>
                  <div>• <strong>Tool Prerequisites:</strong> Native Cppcheck, Checkstyle, and RuboCop require host installation.</div>
                  <div>• <strong>Non-Mathematical:</strong> CLEAN verdicts represent zero findings from executed checks, not mathematical safety proofs.</div>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-[#E8DFF2]/40 border border-[#D5C6E6] space-y-2">
                <span className="text-xs font-bold uppercase tracking-wider text-[#4A3B69] font-mono block">
                  7. Future Research Scope
                </span>
                <ul className="list-disc pl-4 space-y-1.5 text-[#4A3B69] font-sans leading-relaxed">
                  <li><strong>AST-to-AST Transforms:</strong> Integrating LibCST and Tree-sitter for programmatic, provably invariant refactoring transforms.</li>
                  <li><strong>Multi-File Dependency Graphs:</strong> Language Server Protocol (LSP) indexation for cross-module type checking and call graph analysis.</li>
                  <li><strong>Fine-Tuned Compliance Adapters:</strong> Domain-specific LoRA adapters for ISO 27001, HIPAA, and PCI-DSS compliance verification.</li>
                  <li><strong>Automated Test Generation:</strong> Synthesizing property-based pytest/GoogleTest harnesses to exercise proposed auto-corrections empirically.</li>
                </ul>
              </div>
            </div>

            {/* References */}
            <div className="p-4 rounded-xl bg-[#F8F6F0] border border-[#E6E4DC] space-y-2">
              <span className="text-xs font-bold uppercase tracking-wider text-[#343A35] font-mono block">
                8. Normative References &amp; Academic Standards
              </span>
              <div className="space-y-1.5 text-[11px] font-mono text-[#747A73]">
                {REFERENCES_LIST.map((ref, idx) => (
                  <div key={idx} className="flex items-start space-x-2">
                    <span className="text-[#4A6B56] font-bold">[{idx + 1}]</span>
                    <a href={ref.url} target="_blank" rel="noopener noreferrer" className="hover:text-[#343A35] transition-colors flex items-center space-x-1">
                      <span>{ref.citation}</span>
                      <ExternalLink className="w-3 h-3 text-[#A2A8A0] inline ml-1" />
                    </a>
                  </div>
                ))}
              </div>
            </div>

          </div>

        </div>
      )}

      {/* TAB 2: ALGORITHMS & TECH STACK */}
      {activeTab === 'algorithms' && (
        <div className="space-y-6">
          
          {/* Tech Stack Matrix Card */}
          <div className="dev-card p-6 shadow-sm space-y-4 bg-white border border-[#E6E4DC] rounded-xl">
            <div className="flex items-center space-x-2.5 pb-3 border-b border-[#E6E4DC]">
              <Cpu className="w-5 h-5 text-[#4A6B56]" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#343A35]">
                IMPLEMENTED PRODUCTION TECHNOLOGY STACK
              </h3>
            </div>

            <div className="border border-[#E6E4DC] rounded-xl overflow-hidden bg-white shadow-sm">
              <table className="w-full text-left text-xs font-sans">
                <thead className="bg-[#E7EDE2] text-[#343A35] border-b border-[#E6E4DC] font-mono text-[11px] uppercase">
                  <tr>
                    <th className="p-3 w-1/4">System Layer</th>
                    <th className="p-3">Technologies, Libraries &amp; Engines Implemented</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E6E4DC] text-[#343A35] text-xs">
                  {TECH_STACK_TABLE.map((row, idx) => (
                    <tr key={idx} className="hover:bg-[#F8F6F0] transition-colors">
                      <td className="p-3 font-semibold text-[#4A6B56] font-mono">{row.category}</td>
                      <td className="p-3 text-[#555C56] font-sans">{row.technology}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Formulations & Algorithms */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs font-mono">
            
            {/* Algorithm 1: Health Scoring */}
            <div className="dev-card p-5 space-y-3 bg-white border border-[#C2DFD9] rounded-xl shadow-sm">
              <div className="flex items-center space-x-2 text-[#2D5A43] font-bold">
                <Calculator className="w-4 h-4" />
                <span className="uppercase text-[11px]">Algorithm 1: Deterministic Health Scoring</span>
              </div>
              <div className="p-3 bg-[#F8F6F0] rounded-lg border border-[#E6E4DC] text-[#4A6B56] text-xs font-bold">
                H = clamp(10.0 - Σ w(s_i), 0.5, 10.0)
              </div>
              <p className="text-[#555C56] font-sans text-[11px] leading-relaxed">
                Weights: Critical = 3.0, High = 1.5, Medium = 0.75, Low = 0.25, Informational = 0.05.
              </p>
              <div className="p-2.5 bg-[#F8F6F0] rounded-lg border border-[#E6E4DC] text-[10px] space-y-1 text-[#747A73]">
                <div>• If Critical defect exists: <code className="text-[#991B1B] font-bold">H = min(H, 6.0)</code></div>
                <div>• If High defect exists: <code className="text-[#92400E] font-bold">H = min(H, 8.0)</code></div>
                <div>• Zero unresolved defects: <code className="text-[#2D5A43] font-bold">H = 10.0 (CLEAN)</code></div>
                <div>• Lower bound clamp: <code className="text-[#343A35] font-bold">H &ge; 0.5</code></div>
              </div>
            </div>

            {/* Algorithm 2: Myers / LCS Diff */}
            <div className="dev-card p-5 space-y-3 bg-white border border-[#D5C6E6] rounded-xl shadow-sm">
              <div className="flex items-center space-x-2 text-[#4A3B69] font-bold">
                <Code2 className="w-4 h-4" />
                <span className="uppercase text-[11px]">Algorithm 2: Myers / LCS 2D Dynamic Diff</span>
              </div>
              <div className="p-3 bg-[#F8F6F0] rounded-lg border border-[#E6E4DC] text-[#4A3B69] text-xs font-bold">
                DP[i+1][j+1] = DP[i][j] + 1 if (orig[i] == corr[j]) else max(DP[i+1][j], DP[i][j+1])
              </div>
              <p className="text-[#555C56] font-sans text-[11px] leading-relaxed">
                Computes exact longest common subsequence matrix across original and corrected line tokens in O(M × N) time.
              </p>
              <div className="p-2.5 bg-[#F8F6F0] rounded-lg border border-[#E6E4DC] text-[10px] space-y-1 text-[#747A73]">
                <div>• Backtracks to generate minimal edit script ('equal', 'del', 'add').</div>
                <div>• Pairs successive deletions and additions into aligned side-by-side blocks.</div>
                <div>• Fallback linear comparator for files &gt; 4,000,000 matrix cells to prevent UI freeze.</div>
              </div>
            </div>

            {/* Algorithm 3: 128D Dense N-Gram Vector */}
            <div className="dev-card p-5 space-y-3 bg-white border border-[#C2DFD9] rounded-xl shadow-sm">
              <div className="flex items-center space-x-2 text-[#2D5A43] font-bold">
                <Database className="w-4 h-4" />
                <span className="uppercase text-[11px]">Algorithm 3: Dense N-Gram Vector Projection</span>
              </div>
              <div className="p-3 bg-[#F8F6F0] rounded-lg border border-[#E6E4DC] text-[#2D5A43] text-xs font-bold">
                v[hash(ngram) % 128] += idf(ngram); v_norm = v / ||v||_2
              </div>
              <p className="text-[#555C56] font-sans text-[11px] leading-relaxed">
                Projects character n-grams and normalized code tokens into a 128-dimensional dense float32 vector with L2 normalization.
              </p>
              <div className="p-2.5 bg-[#F8F6F0] rounded-lg border border-[#E6E4DC] text-[10px] space-y-1 text-[#747A73]">
                <div>• Cosine similarity score: <code className="text-[#2D5A43] font-bold">sim(A, B) = A · B</code></div>
                <div>• Zero external PyTorch / GPU dependency; sub-millisecond retrieval.</div>
                <div>• SHA-256 content hashing guarantees idempotent document deduplication.</div>
              </div>
            </div>

            {/* Algorithm 4: LangGraph State Machine */}
            <div className="dev-card p-5 space-y-3 bg-white border border-[#FDE68A] rounded-xl shadow-sm">
              <div className="flex items-center space-x-2 text-[#92400E] font-bold">
                <RefreshCw className="w-4 h-4" />
                <span className="uppercase text-[11px]">Algorithm 4: Finite State Transition Machine</span>
              </div>
              <div className="p-3 bg-[#F8F6F0] rounded-lg border border-[#E6E4DC] text-[#92400E] text-xs font-bold">
                Edge(summary_agent) &rarr; coder_agent if (unresolved &gt; 0 &amp;&amp; iter &lt; max_iter)
              </div>
              <p className="text-[#555C56] font-sans text-[11px] leading-relaxed">
                LangGraph cyclic orchestration with strict termination invariants.
              </p>
              <div className="p-2.5 bg-[#F8F6F0] rounded-lg border border-[#E6E4DC] text-[10px] space-y-1 text-[#747A73]">
                <div>• Monotonically increasing iteration counter guarantees termination.</div>
                <div>• Syntactic validator rejects corrupted code, terminating auto-fix gracefully.</div>
                <div>• State immutability preserves original uploaded code without mutations.</div>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* TAB 3: VIVA EXAMINATION Q&A */}
      {activeTab === 'viva' && (
        <div className="dev-card p-6 shadow-sm space-y-6 bg-white border border-[#E6E4DC] rounded-xl">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-3 border-b border-[#E6E4DC] gap-2">
            <div className="flex items-center space-x-2.5">
              <HelpCircle className="w-5 h-5 text-[#4A6B56]" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#343A35]">
                ENGINEERING VIVA VOCE &amp; ORAL EXAMINATION DEFENSE QUESTIONS (10)
              </h3>
            </div>
            <span className="text-xs text-[#747A73] font-mono">10 Technical Questions &amp; Answers</span>
          </div>

          <div className="space-y-3">
            {VIVA_QUESTIONS.map((item, idx) => {
              const isExpanded = expandedFaq === idx || expandedFaq === null;
              return (
                <div key={idx} className="rounded-xl border border-[#E6E4DC] overflow-hidden transition-all bg-white shadow-sm">
                  <button
                    onClick={() => toggleFaq(idx)}
                    className="w-full text-left p-4 flex items-start justify-between bg-[#F8F6F0] hover:bg-[#E7EDE2]/60 transition-colors cursor-pointer"
                  >
                    <div className="flex items-start space-x-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#E7EDE2] text-[#4A6B56] border border-[#DCE8D8] shrink-0">
                        Q{idx + 1}
                      </span>
                      <h4 className="text-xs font-bold text-[#343A35] font-sans leading-relaxed">
                        {item.q}
                      </h4>
                    </div>
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-[#747A73] shrink-0 ml-2" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-[#747A73] shrink-0 ml-2" />
                    )}
                  </button>

                  {isExpanded && (
                    <div className="p-4 pt-3 bg-white border-t border-[#E6E4DC] text-xs text-[#555C56] leading-relaxed font-sans space-y-2">
                      <div className="border-l-2 border-[#4A6B56] pl-3.5 py-1">
                        <strong className="text-[#4A6B56] block mb-1 uppercase text-[10px] font-mono tracking-wider">
                          Technically Defensible Answer:
                        </strong>
                        <p>{item.a}</p>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

    </div>
  );
}
