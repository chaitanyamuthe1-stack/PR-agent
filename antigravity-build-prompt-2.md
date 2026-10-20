# Build Prompt: AI-Based Multilingual Code Review & Auto-Correction System

Build a full-stack web application called **"AntigravitySystems"** — a multilingual, multi-agent AI code review and auto-correction engine. Implement real, working functionality end-to-end (not a UI mockup with hardcoded data) — every screen must be backed by an actual running pipeline.

## 1. Core Concept

A user uploads a source code file. The system runs it through a deterministic static-analysis pass, retrieves relevant grounding context (style guides, security rules, existing codebase), then runs it through a multi-agent LLM review-and-fix loop. Output: a severity-tagged issue report, a health score, and an automatically corrected file the user can download.

## 2. Tech Stack

- **Backend:** Python 3.10+, FastAPI (async routes: `/upload`, `/review`, `/status`, `/download`)
- **Frontend:** React + Tailwind, dark theme (see UI spec below)
- **Orchestration:** LangGraph for the agent loop, LangChain for prompt chaining
- **LLM Gateway:** `llm_gateway.py` — provider-agnostic wrapper
  - Primary: Gemini API (currently "Gemini 3.8 Flash" or latest flash-tier model) or Groq API (free tier)
  - Fallback: Qwen2.5-Coder (3B or 7B, quantized GGUF) via Ollama, running locally — must fit within 4GB VRAM
  - Fallback triggers automatically on primary API failure (timeout, rate limit, no internet) — never runs both simultaneously
- **Static Analysis (MCP layer):** Model Context Protocol used as the tool-calling layer for linters, invoked *before* any LLM call:
  - Python → `pylint` + `bandit`
  - C / C++ → `cppcheck`
  - Java → `checkstyle`
  - JavaScript → `eslint`
  - Ruby → `rubocop`
- **RAG + Vector Store:** Chroma or FAISS (dedicated, no server dependency). Embeddings via Gemini's embedding API (or `sentence-transformers` locally for the offline path). Index contains: language style guides (e.g., PEP 8), security rule sets (OWASP Top 10 mappings), and the user's own uploaded codebase for compatibility checks.
- **Config:** `.env` for Gemini/Groq API keys; Ollama runtime installed locally for fallback.

## 3. Pipeline — exact order (implement as LangGraph nodes)

1. **Upload** — user submits a file, target language auto-detected or user-selected (Python, C++, C, Java, Ruby, JavaScript)
2. **Layer 2 — Static Analysis (MCP)** — run the matching linter(s) for the detected language; output structured findings (rule ID, line, message)
3. **Layer 3 — RAG Retrieval** — embed the uploaded code, query the vector store for relevant style/security rules and related existing-codebase context; return top-k results
4. **Layer 4 — LLM Gateway** — route the assembled prompt (code + static-analysis findings + RAG context) to the primary or fallback LLM
5. **Multi-Agent Review Layer (parallel):**
   - **Security Agent** — flags vulnerabilities, cites the specific CWE/OWASP rule
   - **Bug-Detection Agent** — flags logic errors, edge cases, runs in parallel with the Security Agent
6. **Summary Agent** — merges both agents' findings into one report, assigns severity per issue (**critical / high / medium / low**) and computes an overall **health score out of 10**
7. **Coder Agent** — if health score is below target (e.g. 8/10), rewrites the code to fix all flagged issues, grounded in the RAG-retrieved patterns
8. **Re-check loop** — corrected code goes back through the Security + Bug-Detection agents (not back through static analysis) to verify; repeat until score passes or a max iteration cap (e.g. 5) is hit
9. **Output** — final triage report + downloadable corrected file + audit report

## 4. UI Spec (match this exactly — it's already validated)

**Header:** Product name "AntigravitySystems" with "AG-12 Protocol" badge, tagline "Multilingual Code Review & Auto-Correction Engine". Tabs: **Code Studio | Architecture | RAG Vectors | Paper & Viva**, plus a "RAG Benchmark" button and a live gateway status badge (e.g. "GEMINI 3.8 FLASH — LIVE SERVER API").

**Code Studio tab:**
- Source code workspace with filename, line count, and the specific MCP tool(s) invoked shown inline (e.g. "MCP Tool: pylint / bandit") — this must reflect the *actual* tools run for that file's language, not a static list
- Target language selector: Python / C++ / C / Java / Ruby / JavaScript
- "Upload Source" button
- Gateway selector dropdown, showing current provider AND fallback state explicitly (e.g. a small "fallback: standby" / "fallback: active" indicator next to the gateway badge — this must be visible on screen at all times, not just implemented in code)
- "Run Multi-Agent Review & Auto-Fix" primary action button

**Pipeline Telemetry & State Machine panel:** one card per stage — Static Analysis (MCP), RAG Retrieval, LLM Gateway, Security & Bug Agents (LangGraph), Summary Agent (Synthesis), Coder Agent Fix Loop (Remediation). Each card shows its stage name, what it did (e.g. "MCP tools invoked", "Top-k rules injected", "Parallel scan done"), and a **stage-status icon that is distinct from a pass/fail indicator** — use a neutral "complete" glyph (e.g. a dot or arrow), not a green checkmark, since "this stage ran" and "this stage found no issues" are different facts and must not look the same.

**Triage Verdict panel:** one large health-score number (e.g. 2.9/10) as the primary visual hero, a verdict badge ("FIX REQUIRED" / "CLEAN"), and a one-line summary. Show critical/high/medium/low counts as smaller, clearly secondary chips underneath the hero score — do not give them equal visual weight to the score itself.

**Traceable Issue Telemetry list:** one card per issue, each showing: line number, severity tag, category tag (security/bug/style/performance), a plain-language description, a "Grounded Recommendation" (concrete fix instruction), and a citation tag showing exactly which rule fired (e.g. "RAG: OWASP A03:2021 + MCP: Bandit B608") — every issue must be traceable to a real rule ID, never an unattributed LLM claim. Include category filter tabs (All / Security / Bug / Style / Performance).

**Coder Agent Auto-Correction panel:** side-by-side diff view (toggle: Side-by-Side / Corrected Only) with original vs. corrected code, line-level highlighting of changes, a "Refactoring Changelog" listing each modification in plain language, and buttons for Copy Code / Download Source / Audit Report.

## 5. Non-functional requirements

- Must run the fallback model within 4GB VRAM (quantized GGUF via Ollama only — never load full-precision 7B+ models directly)
- Primary API usage must stay within free-tier limits during normal testing
- Every severity/score/recommendation shown in the UI must originate from an actual pipeline run — no hardcoded demo data in the shipped version
- Support all 6 languages listed above with correct per-language linter routing

## 6. Suggested file structure

```
antigravitysystems/
├── backend/
│   ├── main.py                 # FastAPI app
│   ├── llm_gateway.py
│   ├── mcp_tools.py             # linter invocation per language
│   ├── rag/
│   │   ├── embed.py
│   │   └── vector_store.py
│   ├── agents/
│   │   ├── security_agent.py
│   │   ├── bug_agent.py
│   │   ├── summary_agent.py
│   │   └── coder_agent.py
│   ├── graph.py                 # LangGraph pipeline definition
│   └── .env
└── frontend/
    ├── src/
    │   ├── pages/CodeStudio.jsx
    │   ├── pages/Architecture.jsx
    │   ├── pages/RagVectors.jsx
    │   └── components/
    └── package.json
```

## 7. Deliverable

A working local dev build (`uvicorn` backend + Vite/React frontend) that a user can run, upload a real buggy file to, and receive an accurate, non-hardcoded triage report and downloadable fixed file — reflecting the exact pipeline and UI described above.
