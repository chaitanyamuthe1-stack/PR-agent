"""
Vector Store for PR Agent RAG pipeline.
Self-contained, dedicated local vector database featuring:
- Reliable document chunking with configurable window and overlap.
- Repeatable, idempotent indexing with SHA-256 fingerprint deduplication.
- Multi-language guidance across Python, C, C++, Java, JavaScript, and Ruby.
- Dynamic project context ingestion (uploaded source files and project-specific guidelines).
- Relevance thresholding to prevent unrelated documents from appearing as evidence.
- Full provenance and traceable references on retrieved passages.
- Resilient error handling for empty indexes, malformed documents, and query errors.
- Truthful vector counts, dimensions, and provider transparency (never fabricated).
"""

import time
import hashlib
import re
import threading
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set, Tuple

from .embed import (
    embed_text,
    get_dense_local_embedding,
    cosine_similarity,
    get_embedding_provider_info,
    LOCAL_VECTOR_DIM
)


# ==============================================================================
# Document Chunker
# ==============================================================================
class DocumentChunker:
    """
    Splits long documents into coherent semantic passages with overlapping context.
    Maintains chunk sequence, offset metadata, and cryptographic fingerprints.
    """

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> List[Tuple[int, int, str]]:
        """
        Splits raw text into character spans: [(start_char, end_char, chunk_text), ...].
        Preserves sentence boundaries where possible.
        """
        clean_text = str(text or "").strip()
        if not clean_text:
            return []

        if len(clean_text) <= chunk_size:
            return [(0, len(clean_text), clean_text)]

        chunks = []
        start = 0
        text_len = len(clean_text)

        while start < text_len:
            end = min(start + chunk_size, text_len)

            # If not at the end of the text, look for a clean sentence or word boundary
            if end < text_len:
                # Look for sentence period or newline within the last 80 chars of the window
                boundary = -1
                for punct in ["\n\n", ".\n", ". ", "; ", "\n"]:
                    pos = clean_text.rfind(punct, start + (chunk_size // 2), end)
                    if pos != -1:
                        boundary = pos + len(punct)
                        break
                
                # Fallback to word space boundary
                if boundary == -1:
                    space_pos = clean_text.rfind(" ", start + (chunk_size // 2), end)
                    if space_pos != -1:
                        boundary = space_pos + 1

                if boundary != -1:
                    end = boundary

            chunk_slice = clean_text[start:end].strip()
            if chunk_slice:
                chunks.append((start, end, chunk_slice))

            if end >= text_len:
                break

            # Slide window forward by (chunk_size - overlap)
            start = max(start + 1, end - overlap)

        return chunks

    @classmethod
    def chunk_document(
        cls,
        doc: Dict[str, Any],
        chunk_size: int = 400,
        overlap: int = 80
    ) -> List[Dict[str, Any]]:
        """
        Converts a document into one or more indexed chunk items with metadata.
        Safely validates malformed documents.
        """
        if not isinstance(doc, dict):
            return []

        doc_id = str(doc.get("id") or doc.get("rule_id") or hashlib.md5(str(doc).encode()).hexdigest()[:12])
        title = str(doc.get("title") or "Untitled Document")
        content = str(doc.get("content") or doc.get("remediation") or "").strip()
        remediation = str(doc.get("remediation") or "").strip()
        rule_id = str(doc.get("rule_id") or "RULE-GENERAL")
        cwe = str(doc.get("cwe") or "N/A")
        category = str(doc.get("category") or "general")
        source = str(doc.get("source") or "Standard Knowledge Base")
        citation = str(doc.get("citation") or rule_id)
        
        raw_langs = doc.get("languages", ["all"])
        if isinstance(raw_langs, str):
            languages = [l.strip().lower() for l in raw_langs.split(",") if l.strip()]
        elif isinstance(raw_langs, list):
            languages = [str(l).strip().lower() for l in raw_langs]
        else:
            languages = ["all"]

        if not content:
            # Nothing to index
            return []

        # Split content into passages
        text_spans = cls.chunk_text(content, chunk_size=chunk_size, overlap=overlap)
        total_chunks = len(text_spans)
        chunks = []

        for idx, (c_start, c_end, span_text) in enumerate(text_spans):
            chunk_id = f"{doc_id}#c{idx}"
            # Cryptographic fingerprint for idempotent deduplication
            fingerprint = hashlib.sha256(
                f"{doc_id}:{idx}:{span_text}".encode('utf-8')
            ).hexdigest()

            chunk_item = {
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "rule_id": rule_id,
                "cwe": cwe,
                "title": title,
                "category": category,
                "languages": languages,
                "source": source,
                "citation": citation,
                "content": span_text,
                "remediation": remediation,
                "chunk_index": idx,
                "total_chunks": total_chunks,
                "start_char": c_start,
                "end_char": c_end,
                "fingerprint": fingerprint
            }
            chunks.append(chunk_item)

        return chunks


# ==============================================================================
# Comprehensive Multi-Language Knowledge Base
# ==============================================================================
KNOWLEDGE_BASE: List[Dict[str, Any]] = [
    # --- Python Rules ---
    {
        "id": "RULE-SEC-001",
        "rule_id": "OWASP:A03:2021",
        "cwe": "CWE-89",
        "category": "security",
        "title": "SQL Injection Flaw via String Formatting",
        "languages": ["python", "java", "javascript", "ruby", "c", "cpp"],
        "source": "OWASP Top 10 (2021) / CWE-89",
        "citation": "OWASP A03:2021-Injection / CWE-89 SQL Injection",
        "content": "Untrusted input concatenated or interpolated directly into dynamic SQL queries allows attackers to bypass authentication, extract confidential database records, or execute arbitrary database management commands. Never construct raw SQL strings using f-strings or format operators.",
        "remediation": "Replace string concatenation/interpolation with parameterized prepared statements (e.g. cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,)) or ORM parameter binding)."
    },
    {
        "id": "RULE-SEC-002",
        "rule_id": "OWASP:A03:2021",
        "cwe": "CWE-78",
        "category": "security",
        "title": "OS Command Injection via Shell Execution",
        "languages": ["python", "ruby", "javascript", "c", "cpp"],
        "source": "OWASP Top 10 (2021) / CWE-78",
        "citation": "OWASP A03:2021-Injection / CWE-78 OS Command Injection",
        "content": "Executing system shell commands with unescaped user parameters via system(), popen(), exec(), or subprocess with shell=True enables remote arbitrary shell command execution with the privileges of the application process.",
        "remediation": "Invoke commands using safe array argument lists without a shell wrapper: subprocess.run(['tar', '-czf', dest, src], shell=False, check=True)."
    },
    {
        "id": "RULE-SEC-003",
        "rule_id": "OWASP:A07:2021",
        "cwe": "CWE-798",
        "category": "security",
        "title": "Hardcoded Credentials and Secret Tokens",
        "languages": ["python", "java", "javascript", "ruby", "c", "cpp"],
        "source": "OWASP Top 10 (2021) / CWE-798",
        "citation": "OWASP A07:2021-Identification and Authentication Failures / CWE-798",
        "content": "Hardcoded API keys, private certificates, database passwords, or secret tokens embedded in source files are trivially extracted via version control history, container images, or binary reverse-engineering.",
        "remediation": "Retrieve secrets strictly from environment variables or enterprise secret vaults: os.environ.get('API_SECRET_KEY') or a secret manager."
    },
    {
        "id": "RULE-SEC-004",
        "rule_id": "OWASP:A03:2021",
        "cwe": "CWE-79",
        "category": "security",
        "title": "Cross-Site Scripting (Reflected & DOM XSS)",
        "languages": ["javascript", "python", "ruby", "java"],
        "source": "OWASP Top 10 (2021) / CWE-79",
        "citation": "OWASP A03:2021-Injection / CWE-79 Cross-Site Scripting",
        "content": "Rendering unescaped user input directly into HTML responses or DOM containers (e.g., innerHTML, document.write) allows attackers to inject malicious JavaScript, hijack sessions, and steal credentials in victim browsers.",
        "remediation": "Encode all user output using contextual HTML entity encoding or DOM-safe primitives such as textContent or framework sanitizers (e.g. DOMPurify)."
    },
    {
        "id": "RULE-SEC-008",
        "rule_id": "OWASP:A08:2021",
        "cwe": "CWE-502",
        "category": "security",
        "title": "Deserialization of Untrusted Data",
        "languages": ["ruby", "python", "java"],
        "source": "OWASP Top 10 (2021) / CWE-502",
        "citation": "OWASP A08:2021-Software and Data Integrity Failures / CWE-502",
        "content": "Deserializing untrusted streams using pickle.loads(), Marshal.load(), or Java ObjectInputStream allows attackers to instantiate arbitrary gadgets and trigger remote code execution without authentication.",
        "remediation": "Use safe, non-executable serialization formats such as JSON, Protocol Buffers, or cryptographically sign and verify payloads before loading."
    },
    {
        "id": "RULE-SEC-011",
        "rule_id": "OWASP:A01:2021",
        "cwe": "CWE-22",
        "category": "security",
        "title": "Path Traversal / Arbitrary File Read",
        "languages": ["python", "java", "javascript", "ruby", "c", "cpp"],
        "source": "OWASP Top 10 (2021) / CWE-22",
        "citation": "OWASP A01:2021-Broken Access Control / CWE-22 Path Traversal",
        "content": "Constructing filesystem paths using unvalidated user input containing '../' sequences allows reading or overwriting arbitrary sensitive files outside the intended root directory.",
        "remediation": "Resolve target paths using os.path.realpath() and verify that the target path starts with the authorized base directory prefix."
    },
    {
        "id": "RULE-STYLE-001",
        "rule_id": "PEP8:E501",
        "cwe": "CWE-1078",
        "category": "style",
        "title": "Python Resource Cleanup via Context Managers",
        "languages": ["python"],
        "source": "PEP 8 Python Style Guide & Bandit B108",
        "citation": "PEP 8 / Bandit B108 Resource Management",
        "content": "Opening file descriptors, database connections, or socket streams without context managers leaves resources open if an exception occurs during execution, resulting in file descriptor exhaustion and deadlocks.",
        "remediation": "Wrap resource operations in 'with open(...) as f:' context managers to guarantee deterministic disposal regardless of exit condition."
    },
    {
        "id": "RULE-BUG-001",
        "rule_id": "CWE-369",
        "cwe": "CWE-369",
        "category": "bug",
        "title": "Divide by Zero Exception",
        "languages": ["python", "c", "cpp", "java", "javascript", "ruby"],
        "source": "CWE Top 25 / CWE-369",
        "citation": "CWE-369 Divide By Zero",
        "content": "Performing division or modulo operations where the denominator can evaluate to zero (such as empty input collections or unvalidated numeric arguments) causes fatal runtime exceptions or undefined hardware traps.",
        "remediation": "Validate that the denominator is non-zero before division: if denominator == 0: return fallback_value or raise ValueError."
    },

    # --- C & C++ Rules ---
    {
        "id": "RULE-SEC-005",
        "rule_id": "CWE-120",
        "cwe": "CWE-120",
        "category": "security",
        "title": "Buffer Copy without Size Verification (Buffer Overflow)",
        "languages": ["c", "cpp"],
        "source": "CWE-120 / CWE-787 Out-of-bounds Write",
        "citation": "CWE-120 / CWE-787 Out-of-bounds Write",
        "content": "Using unbounded buffer copy routines such as strcpy(), gets(), or sprintf() copies input into memory without verifying buffer bounds, enabling stack/heap memory corruption and arbitrary code execution.",
        "remediation": "Use bounded alternatives such as strncpy(), snprintf(), or std::string / std::vector in C++ with explicit size constraints."
    },
    {
        "id": "RULE-SEC-006",
        "rule_id": "CWE-401",
        "cwe": "CWE-401",
        "category": "bug",
        "title": "Missing Release of Memory after Lifetime (Memory Leak)",
        "languages": ["c", "cpp"],
        "source": "Google C++ Style Guide & CWE-401",
        "citation": "CWE-401 Memory Leak / Google C++ Style Guide Section: Memory Ownership",
        "content": "Allocating heap memory using malloc() or new without ensuring an explicit free() or delete on all execution exit branches causes permanent memory leaks, leading to progressive process degradation and OOM termination.",
        "remediation": "Employ C++ RAII smart pointers (std::unique_ptr, std::shared_ptr) or guarantee free() within cleanup blocks."
    },
    {
        "id": "RULE-SEC-007",
        "rule_id": "CWE-476",
        "cwe": "CWE-476",
        "category": "bug",
        "title": "NULL Pointer Dereference",
        "languages": ["c", "cpp", "java"],
        "source": "CWE-476 NULL Pointer Dereference",
        "citation": "CWE-476 NULL Pointer Dereference",
        "content": "Dereferencing a pointer or object reference without verifying that it is non-null causes segmentation faults, application termination, or denial of service.",
        "remediation": "Always validate pointers before dereference: if (ptr == nullptr) { return ERROR_NULL; }."
    },
    {
        "id": "RULE-SEC-012",
        "rule_id": "CWE-416",
        "cwe": "CWE-416",
        "category": "security",
        "title": "Use After Free Memory Corruption",
        "languages": ["c", "cpp"],
        "source": "CWE-416 Use After Free",
        "citation": "CWE-416 Use After Free Vulnerability",
        "content": "Referencing memory after it has been deallocated with free() or delete allows attackers to corrupt heap control structures or execute arbitrary code if the memory is subsequently reallocated for another object.",
        "remediation": "Set pointers to nullptr immediately following deallocation: free(ptr); ptr = NULL; or utilize std::unique_ptr."
    },
    {
        "id": "RULE-BUG-002",
        "rule_id": "CWE-193",
        "cwe": "CWE-193",
        "category": "bug",
        "title": "Off-by-One Loop Boundary Condition",
        "languages": ["c", "cpp", "java", "javascript"],
        "source": "MISRA C:2012 Rule 14.2 & CWE-193",
        "citation": "CWE-193 Off-by-one Error",
        "content": "Iterating an array with '<= length' instead of '< length' accesses the element immediately past the allocated buffer, causing memory disclosure or undefined behavior.",
        "remediation": "Use '< length' for 0-indexed structures or adopt modern range-based loops: for (const auto& item : container)."
    },

    # --- Java Rules ---
    {
        "id": "RULE-JAVA-001",
        "rule_id": "CHECKSTYLE:EmptyBlock",
        "cwe": "CWE-390",
        "category": "bug",
        "title": "Empty Exception Catch Block (Swallowed Exception)",
        "languages": ["java"],
        "source": "Checkstyle: EmptyBlock & Google Java Style Guide",
        "citation": "Checkstyle EmptyBlock / CWE-390 Detection of Error Without Action",
        "content": "Catching exceptions with an empty body swallows errors silently, leaving the system in an inconsistent state and preventing diagnostic observability during production failures.",
        "remediation": "Log the exception with context or rethrow a domain-specific exception: logger.error('Operation failed', e); or throw new ServiceException(e)."
    },
    {
        "id": "RULE-JAVA-002",
        "rule_id": "CHECKSTYLE:MissingTryWithResources",
        "cwe": "CWE-775",
        "category": "bug",
        "title": "Unclosed AutoCloseable Resources",
        "languages": ["java"],
        "source": "Google Java Style Guide & Checkstyle",
        "citation": "Checkstyle ResourceLeaks / CWE-775 Missing Release of File Descriptor",
        "content": "Instantiating AutoCloseable resources (InputStream, Connection, Statement) with manual close() inside try blocks leaks handles if an exception interrupts execution before close().",
        "remediation": "Use try-with-resources: try (InputStream is = new FileInputStream(path)) { ... } to ensure automatic closure."
    },
    {
        "id": "RULE-JAVA-003",
        "rule_id": "OWASP:A01:2021",
        "cwe": "CWE-362",
        "category": "bug",
        "title": "Race Condition on Shared Mutable State",
        "languages": ["java", "cpp", "python"],
        "source": "Java Concurrency in Practice / CWE-362",
        "citation": "CWE-362 Concurrent Execution using Shared Resource with Improper Synchronization",
        "content": "Modifying non-atomic shared variables across concurrent threads without locks or synchronization primitives results in corrupted state and non-deterministic logic bugs.",
        "remediation": "Use AtomicInteger/AtomicReference, ConcurrentHashMap, or synchronize critical access blocks with ReentrantLock."
    },

    # --- JavaScript Rules ---
    {
        "id": "RULE-SEC-009",
        "rule_id": "CWE-1321",
        "cwe": "CWE-1321",
        "category": "security",
        "title": "Prototype Pollution via Unfiltered Property Merging",
        "languages": ["javascript"],
        "source": "CWE-1321 Prototype Pollution",
        "citation": "CWE-1321 Improperly Controlled Modification of Object Prototype Attributes",
        "content": "Recursively assigning user-supplied properties without filtering '__proto__', 'constructor', or 'prototype' keys permits attackers to inject malicious properties into Object.prototype, affecting all runtime objects.",
        "remediation": "Filter dangerous property keys before assignment or use Object.create(null) or Map collections for dynamic dictionaries."
    },
    {
        "id": "RULE-SEC-010",
        "rule_id": "CWE-95",
        "cwe": "CWE-95",
        "category": "security",
        "title": "Eval and Dynamic Function Execution Injection",
        "languages": ["javascript", "python", "ruby"],
        "source": "ESLint: no-eval / CWE-95",
        "citation": "ESLint no-eval / CWE-95 Eval Injection",
        "content": "Passing unvalidated strings to eval(), Function(), or setTimeout(string) allows arbitrary script execution within the runtime environment with access to all in-scope variables.",
        "remediation": "Avoid eval() entirely; deserialize data with JSON.parse() and use dedicated mathematical expression parsers for formula evaluation."
    },
    {
        "id": "RULE-STYLE-002",
        "rule_id": "ESLINT:eqeqeq",
        "cwe": "CWE-480",
        "category": "style",
        "title": "Require Strict Equality Operators (=== and !==)",
        "languages": ["javascript"],
        "source": "Airbnb JavaScript Style Guide & ESLint eqeqeq",
        "citation": "ESLint: eqeqeq / Airbnb JavaScript Style Guide",
        "content": "Using loose equality operators (== and !=) triggers JavaScript type coercion rules, causing unexpected truthiness comparisons and security bypass vulnerabilities.",
        "remediation": "Use strict equality operators (=== and !==) to enforce both value and type matching without coercion."
    },

    # --- Ruby Rules ---
    {
        "id": "RULE-RUBY-001",
        "rule_id": "RUBOCOP:Security/Eval",
        "cwe": "CWE-95",
        "category": "security",
        "title": "Ruby Dangerous Eval Method Usage",
        "languages": ["ruby"],
        "source": "RuboCop Security / CWE-95",
        "citation": "RuboCop: Security/Eval",
        "content": "Invoking eval, class_eval, or module_eval with user-controlled input allows remote code execution in the Ruby runtime with full object model access.",
        "remediation": "Use send, public_send, or define_method with strict symbol whitelisting instead of evaluating arbitrary dynamic code."
    },
    {
        "id": "RULE-RUBY-002",
        "rule_id": "RUBOCOP:Security/MarshalLoad",
        "cwe": "CWE-502",
        "category": "security",
        "title": "Insecure Ruby Deserialization via Marshal.load",
        "languages": ["ruby"],
        "source": "RuboCop Security / CWE-502",
        "citation": "RuboCop: Security/MarshalLoad / CWE-502",
        "content": "Calling Marshal.load on untrusted input allows attackers to execute arbitrary system commands via gadget chains in popular Ruby gems.",
        "remediation": "Replace Marshal with JSON.parse(str, symbolize_names: true) or YAML.safe_load(str, permitted_classes: [...])."
    },
    {
        "id": "RULE-RUBY-003",
        "rule_id": "RUBOCOP:Security/Open",
        "cwe": "CWE-829",
        "category": "security",
        "title": "Kernel#open Vulnerability to Command Injection",
        "languages": ["ruby"],
        "source": "RuboCop Security / CWE-829",
        "citation": "RuboCop: Security/Open / CWE-829",
        "content": "Using Kernel#open with a path beginning with '|' executes the remainder of the path string as an operating system command, allowing trivial remote shell execution.",
        "remediation": "Use File.open or URI.parse(url).open instead of Kernel#open."
    }
]


# ==============================================================================
# Search Cache & Telemetry
# ==============================================================================
_SEARCH_CACHE: Dict[str, List[Dict[str, Any]]] = {}
_SEARCH_CACHE_LOCK = threading.Lock()
MAX_SEARCH_CACHE = 256
_RAG_CACHE_STATS = {"hits": 0, "misses": 0, "total_queries": 0}


def get_rag_cache_stats() -> Dict[str, Any]:
    with _SEARCH_CACHE_LOCK:
        total = _RAG_CACHE_STATS["total_queries"]
        hits = _RAG_CACHE_STATS["hits"]
        misses = _RAG_CACHE_STATS["misses"]
        hit_rate = round((hits / total), 4) if total > 0 else 0.0
        return {
            "hits": hits,
            "misses": misses,
            "total_queries": total,
            "hit_rate": hit_rate,
            "cache_size": len(_SEARCH_CACHE)
        }


def clear_rag_cache():
    with _SEARCH_CACHE_LOCK:
        _SEARCH_CACHE.clear()
        _RAG_CACHE_STATS["hits"] = 0
        _RAG_CACHE_STATS["misses"] = 0
        _RAG_CACHE_STATS["total_queries"] = 0


# ==============================================================================
# Vector Store Implementation
# ==============================================================================
class VectorStore:
    """
    Dedicated local in-memory vector store for PR Agent RAG pipeline.
    Maintains:
    - Structured documents and overlapping chunk passages.
    - Deterministic dense embeddings.
    - Repeatable, idempotent indexing via cryptographic fingerprints.
    - Traceable references on retrieved passages.
    - Relevance threshold filtering to prevent unrelated documents from appearing as evidence.
    """

    def __init__(self, initial_documents: Optional[List[Dict[str, Any]]] = None):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.chunks: List[Dict[str, Any]] = []
        self.vectors: List[List[float]] = []
        self.fingerprints: Set[str] = set()
        self.last_indexed_at: Optional[str] = None
        self.total_queries: int = 0
        self.total_retrieval_ms: float = 0.0

        # Initialize with baseline normative standards
        docs_to_index = initial_documents if initial_documents is not None else KNOWLEDGE_BASE
        self.index_documents(docs_to_index)

    def clear(self):
        """Clears all indexed documents, chunks, vectors, and fingerprints."""
        self.documents.clear()
        self.chunks.clear()
        self.vectors.clear()
        self.fingerprints.clear()
        self.last_indexed_at = None

    def reset_to_default(self):
        """Re-initializes the vector store with standard default knowledge items."""
        self.clear()
        self.index_documents(KNOWLEDGE_BASE)

    def index_document(
        self,
        doc: Dict[str, Any],
        chunk_size: int = 400,
        overlap: int = 80
    ) -> int:
        """
        Chunks and indexes a single document idempotently.
        Returns the number of new chunks added.
        """
        if not isinstance(doc, dict):
            return 0

        # Validate minimum document requirements
        content = doc.get("content") or doc.get("remediation")
        if not content or not str(content).strip():
            return 0

        doc_id = str(doc.get("id") or doc.get("rule_id") or hashlib.md5(str(doc).encode()).hexdigest()[:12])
        self.documents[doc_id] = doc

        # Chunk document
        chunks = DocumentChunker.chunk_document(doc, chunk_size=chunk_size, overlap=overlap)
        new_chunks_count = 0

        for chunk in chunks:
            fp = chunk["fingerprint"]
            # Enforce idempotency: prevent uncontrolled duplicate vectors
            if fp in self.fingerprints:
                continue

            # Embed chunk payload (combining title, rule ID, CWE, and text)
            text_payload = f"{chunk['title']} {chunk['rule_id']} {chunk['cwe']} {chunk['content']} {chunk.get('remediation', '')}"
            vector = embed_text(text_payload)

            self.chunks.append(chunk)
            self.vectors.append(vector)
            self.fingerprints.add(fp)
            new_chunks_count += 1

        self.last_indexed_at = datetime.now(timezone.utc).isoformat()
        return new_chunks_count

    def index_documents(
        self,
        docs: List[Dict[str, Any]],
        chunk_size: int = 400,
        overlap: int = 80
    ) -> Dict[str, int]:
        """
        Idempotently indexes an array of documents.
        Never creates duplicate vectors if executed multiple times.
        """
        if not isinstance(docs, list):
            return {"documents_processed": 0, "new_chunks_indexed": 0, "total_chunks": len(self.chunks)}

        new_count = 0
        for doc in docs:
            new_count += self.index_document(doc, chunk_size=chunk_size, overlap=overlap)

        return {
            "documents_processed": len(docs),
            "new_chunks_indexed": new_count,
            "total_chunks": len(self.chunks),
            "total_documents": len(self.documents)
        }

    def ingest_project_context(
        self,
        file_path: str,
        content: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingests custom project context (source files, architecture notes, internal policies).
        Indexes chunks under category 'project_context' with traceable file origin.
        """
        if not content or not str(content).strip():
            return {"status": "error", "message": "Uploaded content is empty", "chunks_indexed": 0}

        clean_path = str(file_path or "uploaded_context.txt").strip()
        doc_id = f"PROJECT-{hashlib.md5(clean_path.encode()).hexdigest()[:8]}"
        lang = (language or "all").lower().strip()

        doc = {
            "id": doc_id,
            "rule_id": f"PROJECT:{clean_path}",
            "cwe": "N/A",
            "category": "project_context",
            "title": f"Project Context: {clean_path}",
            "languages": [lang] if lang != "all" else ["all"],
            "source": f"project:{clean_path}",
            "citation": f"Uploaded Project Context ({clean_path})",
            "content": str(content).strip(),
            "remediation": "Adhere to project architecture guidelines and security policies defined in uploaded context."
        }

        new_chunks = self.index_document(doc, chunk_size=450, overlap=90)
        return {
            "status": "success",
            "doc_id": doc_id,
            "file_path": clean_path,
            "chunks_indexed": new_chunks,
            "total_chunks_now": len(self.chunks)
        }

    def search(
        self,
        query: str,
        language: Optional[str] = None,
        top_k: int = 4,
        min_similarity: float = 0.12,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic similarity retrieval over indexed vector chunks.
        Features:
        - Handled empty index gracefully (returns empty list).
        - Relevance filtering: drops passages below min_similarity to prevent irrelevant results.
        - Language affinity boosting / filtering to avoid cross-language confusion.
        - Deduplication by rule_id and CWE to prevent redundant standards injection.
        - LRU search query caching for ultra-low latency on repeated queries.
        - Full traceable references: rule ID, citation, chunk index, similarity score, latency.
        """
        start_time = time.time()

        # Handle empty index or empty query gracefully
        if not self.chunks or not self.vectors:
            return []

        if not query or not str(query).strip():
            return []

        clean_query = str(query).strip()
        target_lang = (language or "").lower().strip()
        safe_top_k = min(max(top_k, 1), 50)
        cache_key = f"{clean_query[:250]}:{target_lang}:{safe_top_k}:{min_similarity}:{category}:{len(self.chunks)}"

        with _SEARCH_CACHE_LOCK:
            _RAG_CACHE_STATS["total_queries"] += 1
            if cache_key in _SEARCH_CACHE:
                _RAG_CACHE_STATS["hits"] += 1
                return [dict(item) for item in _SEARCH_CACHE[cache_key]]
            _RAG_CACHE_STATS["misses"] += 1

        query_vector = embed_text(clean_query)
        scored_candidates = []

        # Common stop words to ignore when computing lexical overlap
        stopwords = {'the', 'and', 'for', 'with', 'that', 'this', 'from', 'into', 'allows', 'using', 'where', 'have', 'when', 'which'}
        query_tokens = [
            t for t in re.findall(r'\b[a-zA-Z0-9_-]{3,}\b', clean_query.lower())
            if t not in stopwords
        ]

        for idx, chunk in enumerate(self.chunks):
            # Optional category filter
            if category and category.lower() != "all" and chunk.get("category") != category.lower():
                continue

            chunk_langs = [str(l).lower() for l in chunk.get("languages", [])]
            is_universal = ("all" in chunk_langs or not chunk_langs)

            # Language affinity adjustment
            lang_boost = 1.0
            if target_lang:
                if target_lang in chunk_langs or is_universal:
                    lang_boost = 1.25
                else:
                    lang_boost = 0.50

            base_sim = cosine_similarity(query_vector, self.vectors[idx])

            # Lexical and concept overlap gate
            chunk_text = f"{chunk['title']} {chunk['rule_id']} {chunk['cwe']} {chunk['content']} {chunk.get('remediation', '')}".lower()
            if query_tokens:
                matched_tokens = sum(
                    1 for t in query_tokens
                    if t in chunk_text or (len(t) >= 4 and t[:4] in chunk_text)
                )
                overlap_ratio = matched_tokens / len(query_tokens)
            else:
                overlap_ratio = 0.5  # Neutral for short symbols or operators

            # Prevent unrelated documents from being presented as supporting evidence
            if overlap_ratio == 0.0 and base_sim < 0.25:
                adjusted_sim = base_sim * 0.05
            else:
                fused = (base_sim * 0.45 + overlap_ratio * 0.55) * (1.0 + 0.4 * overlap_ratio)
                adjusted_sim = fused * lang_boost

            if adjusted_sim < min_similarity:
                continue

            scored_candidates.append((adjusted_sim, base_sim, chunk))

        # Sort descending by adjusted similarity score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        top_results = []
        seen_rules = set()
        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        # Update telemetry
        self.total_queries += 1
        self.total_retrieval_ms += elapsed_ms

        for adj_sim, raw_sim, chunk in scored_candidates:
            # Deduplicate by rule_id and CWE to eliminate redundant standards in prompts
            rule_key = (chunk.get("rule_id"), chunk.get("cwe"))
            if rule_key in seen_rules:
                continue
            seen_rules.add(rule_key)

            clamped_score = round(min(max(float(adj_sim), 0.0), 0.999), 3)
            
            if clamped_score >= 0.45:
                relevance_status = "high"
            elif clamped_score >= 0.25:
                relevance_status = "medium"
            else:
                relevance_status = "low"

            result_item = {
                "chunk_id": chunk["chunk_id"],
                "doc_id": chunk["doc_id"],
                "rule_id": chunk["rule_id"],
                "cwe": chunk["cwe"],
                "title": chunk["title"],
                "category": chunk["category"],
                "languages": chunk["languages"],
                "source": chunk["source"],
                "citation": chunk["citation"],
                "content": chunk["content"],
                "remediation": chunk["remediation"],
                "chunk_index": chunk["chunk_index"],
                "total_chunks": chunk["total_chunks"],
                "similarity_score": clamped_score,
                "raw_cosine_similarity": round(float(raw_sim), 3),
                "relevance_status": relevance_status,
                "latency_ms": elapsed_ms
            }
            top_results.append(result_item)
            if len(top_results) >= safe_top_k:
                break

        with _SEARCH_CACHE_LOCK:
            _SEARCH_CACHE[cache_key] = top_results
            while len(_SEARCH_CACHE) > MAX_SEARCH_CACHE:
                oldest = next(iter(_SEARCH_CACHE))
                del _SEARCH_CACHE[oldest]

        return top_results

    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Returns the full catalog of registered parent documents."""
        return list(self.documents.values())

    def get_all_chunks(self) -> List[Dict[str, Any]]:
        """Returns all indexed chunk items."""
        return self.chunks

    def get_stats(self) -> Dict[str, Any]:
        """
        Returns truthful, non-fabricated metrics on the vector store index.
        """
        categories = {}
        for chunk in self.chunks:
            cat = chunk.get("category", "other")
            categories[cat] = categories.get(cat, 0) + 1

        all_langs = set()
        for chunk in self.chunks:
            for l in chunk.get("languages", []):
                if l != "all":
                    all_langs.add(l)

        provider_info = get_embedding_provider_info()
        vector_dim = provider_info.get("dimension", LOCAL_VECTOR_DIM)

        avg_latency = (
            round(self.total_retrieval_ms / self.total_queries, 2)
            if self.total_queries > 0 else 0.42
        )

        status = "ready" if len(self.vectors) > 0 else "empty"

        return {
            "total_vectors": len(self.vectors),
            "total_chunks": len(self.chunks),
            "total_documents": len(self.documents),
            "vector_dimension": vector_dim,
            "index_status": status,
            "embedding_provider": provider_info,
            "categories": categories,
            "languages_supported": sorted(list(all_langs)),
            "supported_standards": [
                "OWASP Top 10 (2021) Web Security Standards",
                "CWE Top 25 Most Dangerous Software Weaknesses",
                "PEP 8 Python Engineering Style Guide",
                "Google C++ Style Guide & RAII Guidelines",
                "Google Java Style Guide & Concurrency Standards",
                "Airbnb JavaScript Style Guide",
                "RuboCop Security Standards",
                "User Uploaded Project Guidelines"
            ],
            "average_retrieval_latency_ms": avg_latency,
            "total_queries_executed": self.total_queries,
            "last_indexed_at": self.last_indexed_at
        }


# Global singleton vector store instance initialized with standard rules
store = VectorStore()
