# PR Agent

**Multilingual AI Code Review, Static Analysis (MCP), Normative RAG Grounding & Auto-Correction Platform**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite)](https://vitejs.dev)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python)](https://www.python.org)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-FF4F00)](https://github.com/langchain-ai/langgraph)

---

## Overview

**PR Agent** is an enterprise-grade AI code review and auto-correction platform. It bridges deterministic static analysis (via the Model Context Protocol tool layer) with normative security rule retrieval (via a dedicated 128-dimensional in-memory vector store) and multi-agent cyclic reasoning (orchestrated via LangGraph).

The system ingests source code across six programming languages (**Python, C++, C, Java, JavaScript, Ruby**), executes language-specific linters, retrieves relevant OWASP Top 10 and CWE Top 25 standards, runs parallel Security and Bug-Detection agents, computes an objective health score out of 10.0, and executes an automated remediation loop with verification re-checks.

---

## Key Features

- **Multi-Language Support:** First-class parsing, linter invocation, and remediation across Python, C, C++, Java, JavaScript, and Ruby.
- **Deterministic Static Tool Layer (MCP):** Integrates Bandit, Flake8/Pylint, Cppcheck, Checkstyle, ESLint, and RuboCop before any LLM inference, backed by deterministic AST fallbacks.
- **128D Semantic RAG Grounding:** Dedicated, zero-external-dependency vector store projecting code patterns into a 128-dimensional dense n-gram space for cosine similarity matching against OWASP Top 10 and CWE Top 25 directives.
- **Tri-Tier Provider-Agnostic LLM Gateway:**
  1. Primary Cloud: Google Gemini (`gemini-2.0-flash`, `gemini-1.5-flash`)
  2. Secondary Cloud: Groq (`llama-3.3-70b-versatile`)
  3. Local Offline Runtime: Ollama (`qwen2.5-coder:7b`)
  4. Offline Heuristic Fallback: Zero-credential heuristic synthesis engine (`pr-agent-deterministic-v1`)
- **Parallel Multi-Agent Review:** LangGraph-coordinated parallel execution of specialized Security and Bug-Detection agents.
- **Zero False-Clean Invariant:** The `CLEAN` verdict is mathematically unreachable if any actionable defect remains unresolved.
- **Side-by-Side Myers Diff & Remediation:** Interactive 2D dynamic programming Myers diff viewer with Side-by-Side, Unified, and Corrected views, changelog summary, and one-click code/audit downloads.
- **Comprehensive Benchmarking:** Built-in ground-truth evaluation suite with 18 benchmark cases across real-world and synthetic fixtures.

---

## Architecture

```
                  +-----------------------------------+
                  |             PR Agent              |
                  |     (FastAPI + React 18 / Vite)   |
                  +-----------------+-----------------+
                                    |
          +-------------------------+-------------------------+
          |                         |                         |
          v                         v                         v
 [Layer 2: MCP Tools]     [Layer 3: 128D RAG]      [Layer 4: LLM Gateway]
  Bandit / Cppcheck /       OWASP Top 10 /          Gemini / Groq / Ollama /
  ESLint / AST Fallback     CWE Top 25 Vectors      Offline Heuristics
          |                         |                         |
          +-------------------------+-------------------------+
                                    |
                                    v
                     [Layer 5: Parallel Agents]
                      Security Agent & Bug Agent
                                    |
                                    v
                     [Layer 6: Summary & Scoring]
                      Weighted 10.0 Health Score
                                    |
                                    v
                     [Layer 7: Coder Remediation]
                      Automated Fix & Re-Check Loop
```

---

## Project Structure

```text
PR_Agent/
├── frontend/                  # React 18 + Vite + Tailwind CSS User Interface
│   ├── src/
│   │   ├── components/        # Diff viewer, telemetry cards, triage verdict
│   │   ├── pages/             # CodeStudio, Architecture, RagVectors, PaperViva
│   │   └── services/          # API gateway client
│   └── package.json
├── backend/                   # FastAPI Multi-Agent Engine
│   ├── agents/                # Security, Bug-Detection, Summary, and Coder agents
│   ├── rag/                   # 128D Semantic Vector Store (OWASP & CWE)
│   ├── database.py            # Persistence layer (SQLite with graceful in-memory fallback)
│   ├── llm_gateway.py         # Tri-tier provider routing (Gemini, Groq, Ollama)
│   ├── mcp_tools.py           # Language-specific linters and AST fallbacks
│   └── main.py                # REST API routes (/upload, /review, /status, /audit)
├── supabase/                  # Supabase Database Configuration & Migrations
│   ├── config.toml            # Local development & CLI configuration
│   └── migrations/            # SQL migration scripts (PostgreSQL + pgvector)
│       └── 20261020000000_create_reviews_schema.sql
└── README.md
```

---

## Database & Supabase Integration

PR Agent supports persistence for review audits, health metrics, and normative security embeddings:

- **Local Default:** Embedded SQLite (`backend/pr_agent_audit.db`) with automatic thread-safe WAL mode and graceful degradation to an in-memory cache if file I/O is unavailable.
- **Enterprise / Cloud:** **Supabase (PostgreSQL + pgvector)** configured via `supabase/`:
  - **`reviews` Table:** Stores complete review telemetry, 10.0-scale health scores, remediation statuses, and JSONB reports.
  - **`rag_knowledge_vectors` Table:** Stores OWASP Top 10 and CWE Top 25 directives indexed with `vector(128)` for dense semantic similarity search.
  - **Row Level Security (RLS):** Enabled out-of-the-box with fine-grained access policies for public inspection and service-role ingestion.

### Supabase CLI Commands

To run Supabase locally using Docker and the Supabase CLI:

```bash
# Initialize / start local Supabase instance
npx supabase start

# Apply database migrations
npx supabase db reset

# Create a new database migration
npx supabase migration new <migration_name>

# View local Supabase Studio dashboard
# Open http://localhost:54323 in your browser
```

---

## Quick Start


### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- (Optional) [Ollama](https://ollama.com) for local offline LLM inference

### 2. Backend Setup
```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Configure environment variables (optional cloud API keys)
cp backend/.env.example backend/.env

# Start FastAPI backend server (port 8000)
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Frontend Setup
```bash
# Navigate to frontend directory and install dependencies
cd frontend
npm install

# Start development server (port 5173)
npm run dev
```

### 4. Single-Command Launch (Windows PowerShell)
```powershell
.\run.ps1
```

Once running, access the interfaces:
- **Web UI:** [http://localhost:5173](http://localhost:5173)
- **API Documentation (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Status:** [http://localhost:8000/status](http://localhost:8000/status)

---

## Testing & Verification

Run the comprehensive test suites across backend and full-stack modules:

```bash
# Run API & Database integration tests
python -m pytest backend/test_phase14_api_database.py

# Run LLM Gateway and failover tests
python -m pytest backend/test_phase8_llm_gateway.py

# Run Static Analysis & Linter fallback tests
python -m pytest backend/test_phase6_static_analysis.py

# Run RAG Vector Store tests
python -m pytest backend/test_phase7_rag.py

# Run Triage & Health Score tests
python -m pytest backend/test_phase9_triage_health_score.py

# Run Code Diff tests
python -m pytest backend/test_phase10_code_diff.py

# Run Benchmark suite tests
python -m pytest backend/test_phase13_benchmark.py

# Build frontend production bundle
npm --prefix frontend run build
```

---

## License & Compliance

Confidential — Generated by PR Agent Multi-Agent Engine.
All analysis and auto-remediation operations adhere to OWASP Top 10 and MITRE CWE Top 25 security benchmarks.
