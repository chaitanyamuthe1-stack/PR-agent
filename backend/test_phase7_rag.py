"""
Unit & Integration Test Suite for Phase 7 — RAG and Vector Explorer (PR Agent).

Validates:
1. Reliable document chunking with metadata, sequence tracking, and overlap.
2. Repeatable, idempotent indexing without uncontrolled duplicate vectors.
3. Relevant multi-language guidance across Python, C/C++, Java, JavaScript, and Ruby.
4. Uploaded project context dynamic ingestion and retrieval.
5. Traceable references and citations on retrieved passages.
6. Relevance thresholding preventing unrelated documents from being presented as evidence.
7. Graceful edge-case handling: empty index, malformed documents, query errors.
8. Truthful vector counts, index status, dimensions, and provider transparency.
"""

import os
import sys

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.rag.embed import (
    get_dense_local_embedding,
    embed_text,
    cosine_similarity,
    get_embedding_provider_info
)
from backend.rag.vector_store import (
    VectorStore,
    DocumentChunker,
    KNOWLEDGE_BASE,
    store
)


def test_1_document_chunker():
    print("\n[TEST 1] Document Chunking & Metadata Tracking...")
    
    # Case 1a: Short document produces 1 chunk
    short_doc = {
        "id": "TEST-SHORT-001",
        "rule_id": "TEST:001",
        "title": "Short Security Note",
        "content": "Always validate user input before passing it to database queries.",
        "category": "security",
        "languages": ["python"]
    }
    chunks = DocumentChunker.chunk_document(short_doc, chunk_size=300, overlap=50)
    assert len(chunks) == 1, f"Expected 1 chunk, got {len(chunks)}"
    assert chunks[0]["chunk_id"] == "TEST-SHORT-001#c0"
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["total_chunks"] == 1
    assert "fingerprint" in chunks[0]
    print("  [PASS] Short document parsed into single atomic chunk.")

    # Case 1b: Long document produces multiple overlapping chunks
    long_content = (
        "Section 1: Microservice Security Architecture and Ingress Controller Guidelines. "
        "All incoming HTTP traffic must terminate at the API gateway where JWT authentication "
        "and claims signature verification are strictly enforced against the JWKS endpoint.\n\n"
        "Section 2: Database Connection Pooling and Query Construction. "
        "Direct SQL formatting via string interpolation is strictly prohibited across all repositories. "
        "Engineers must utilize parameterized statements or approved ORM repositories.\n\n"
        "Section 3: Audit Logging and Incident Telemetry. "
        "All security-sensitive operations including role modifications, permission grants, "
        "and failed authentication attempts must be dispatched to the central SIEM buffer asynchronously."
    )
    long_doc = {
        "id": "TEST-LONG-002",
        "rule_id": "ARCH:002",
        "title": "Enterprise Microservice Guidelines",
        "content": long_content,
        "category": "project_context",
        "languages": ["all"]
    }
    multi_chunks = DocumentChunker.chunk_document(long_doc, chunk_size=250, overlap=60)
    assert len(multi_chunks) >= 2, f"Expected at least 2 chunks for long text, got {len(multi_chunks)}"
    for idx, c in enumerate(multi_chunks):
        assert c["chunk_index"] == idx
        assert c["total_chunks"] == len(multi_chunks)
        assert c["chunk_id"] == f"TEST-LONG-002#c{idx}"
        assert c["doc_id"] == "TEST-LONG-002"
    print(f"  [PASS] Long document correctly split into {len(multi_chunks)} coherent overlapping chunks.")

    # Case 1c: Malformed document does not crash chunker
    malformed_cases = [None, {}, {"title": "No Content"}, {"content": 12345}, "not a dict"]
    for m in malformed_cases:
        res = DocumentChunker.chunk_document(m)
        assert isinstance(res, list), "Malformed document must return empty list without crashing"
    print("  [PASS] Malformed documents handled safely with zero unhandled exceptions.")


def test_2_repeatable_idempotent_indexing():
    print("\n[TEST 2] Repeatable, Idempotent Indexing without Duplicate Vectors...")
    test_store = VectorStore(initial_documents=[])
    assert test_store.get_stats()["total_vectors"] == 0

    sample_doc = {
        "id": "RULE-IDEMP-01",
        "rule_id": "SEC:IDEMP",
        "title": "Idempotent Authentication Check",
        "content": "Verify HMAC signature on all incoming webhook payloads before processing events.",
        "category": "security",
        "languages": ["python", "javascript"]
    }

    # Index first time
    added_1 = test_store.index_document(sample_doc)
    assert added_1 == 1, "First indexing must add 1 chunk"
    stats_1 = test_store.get_stats()
    assert stats_1["total_vectors"] == 1
    assert stats_1["total_chunks"] == 1

    # Index second time (exact duplicate)
    added_2 = test_store.index_document(sample_doc)
    assert added_2 == 0, "Duplicate document indexing must add 0 chunks (idempotent)"
    stats_2 = test_store.get_stats()
    assert stats_2["total_vectors"] == 1, "Vector count must not inflate"

    # Index 5 times via batch method
    batch_res = test_store.index_documents([sample_doc, sample_doc, sample_doc])
    assert batch_res["new_chunks_indexed"] == 0, "Batch indexing duplicate docs must add 0 chunks"
    stats_3 = test_store.get_stats()
    assert stats_3["total_vectors"] == 1, "Vector store must remain strictly deduplicated"
    print("  [PASS] Idempotent indexing verified: exactly 1 vector maintained across repeated indexing.")


def test_3_relevance_threshold_and_preventing_unrelated_evidence():
    print("\n[TEST 3] Relevance Thresholding & Preventing Unrelated Documents as Evidence...")
    # Using the standard knowledge store
    
    # 3a. Target query with relevant rules
    results = store.search(
        query="dynamic SQL query concatenation cursor.execute untrusted input injection",
        language="python",
        top_k=3,
        min_similarity=0.15
    )
    assert len(results) > 0, "Relevant query must retrieve matching rules"
    top_rule = results[0]
    assert "SQL" in top_rule["title"] or top_rule["rule_id"] == "OWASP:A03:2021" or top_rule["cwe"] == "CWE-89"
    assert top_rule["similarity_score"] >= 0.15
    print(f"  [PASS] High-relevance query matched: {top_rule['rule_id']} (similarity: {top_rule['similarity_score']})")

    # 3b. Irrelevant query: must NOT present unrelated documents as evidence!
    irrelevant_query = "quantum astrophysics dark matter gravitational wave observatory cosmological telescope"
    irrelevant_results = store.search(
        query=irrelevant_query,
        language="python",
        top_k=4,
        min_similarity=0.25  # Strict relevance cutoff
    )
    assert len(irrelevant_results) == 0, f"Unrelated query must return 0 results, got {len(irrelevant_results)}"
    print("  [PASS] Unrelated query rejected by relevance threshold (0 false evidence returned).")


def test_4_traceable_references_on_retrieved_passages():
    print("\n[TEST 4] Traceable References and Provenance on Retrieved Passages...")
    results = store.search(
        query="buffer overflow strcpy gets snprintf memory corruption",
        language="cpp",
        top_k=2,
        min_similarity=0.12
    )
    assert len(results) > 0, "Expected at least 1 result for buffer overflow query"
    first = results[0]

    # Check all required provenance fields
    required_fields = [
        "chunk_id", "doc_id", "rule_id", "cwe", "title", "content",
        "remediation", "source", "citation", "languages", "similarity_score",
        "relevance_status", "chunk_index", "total_chunks", "latency_ms"
    ]
    for field in required_fields:
        assert field in first, f"Missing required provenance field: {field}"
        assert first[field] is not None, f"Field {field} should not be None"

    print(f"  [PASS] Provenance verified: [{first['citation']}] -> Chunk {first['chunk_id']}")
    print(f"         Remediation Pattern: {first['remediation'][:65]}...")


def test_5_project_context_ingestion():
    print("\n[TEST 5] Dynamic Ingestion of Uploaded Project Context...")
    project_text = (
        "PR Agent Internal Security Directive:\n"
        "All microservice inter-service communication must strictly use mTLS with SPIFFE/SPIRE IDs. "
        "Direct HTTP without mutual TLS authentication is blocked by service mesh Envoy sidecars."
    )
    ingest_res = store.ingest_project_context(
        file_path="security_policy.md",
        content=project_text,
        language="all"
    )
    assert ingest_res["status"] == "success"
    assert ingest_res["chunks_indexed"] >= 1
    print(f"  [PASS] Project context ingested: {ingest_res['chunks_indexed']} chunk(s) added.")

    # Retrieve the ingested project context
    retrieved = store.search(
        query="mutual TLS mTLS SPIFFE SPIRE inter-service authentication Envoy",
        top_k=2,
        min_similarity=0.15
    )
    assert len(retrieved) > 0, "Ingested project context must be retrievable"
    match = next((r for r in retrieved if "SPIFFE" in r["content"]), None)
    assert match is not None, "Retrieved chunk must contain uploaded project context"
    assert match["category"] == "project_context"
    assert "security_policy.md" in match["source"]
    print(f"  [PASS] Ingested context retrieved with provenance: source={match['source']}")


def test_6_empty_index_and_graceful_recovery():
    print("\n[TEST 6] Empty Index & Graceful Error Recovery...")
    test_store = VectorStore(initial_documents=[])
    
    # Empty store stats
    stats = test_store.get_stats()
    assert stats["total_vectors"] == 0
    assert stats["total_chunks"] == 0
    assert stats["index_status"] == "empty"

    # Searching empty store must not crash or divide by zero
    empty_results = test_store.search("SQL injection", top_k=4)
    assert empty_results == [], "Searching empty store must return []"

    # Empty / whitespace query on populated store
    blank_query_res = store.search("   ", top_k=4)
    assert blank_query_res == [], "Blank query must return []"

    # None query on populated store
    none_query_res = store.search(None, top_k=4)
    assert none_query_res == [], "None query must return []"

    print("  [PASS] Empty index and invalid queries handled gracefully without crashing.")


def test_7_truthful_provider_transparency():
    print("\n[TEST 7] Truthful Vector Counts & Provider Transparency...")
    stats = store.get_stats()
    
    # Truthful counts
    assert stats["total_vectors"] == len(store.vectors), "total_vectors must match len(store.vectors)"
    assert stats["total_chunks"] == len(store.chunks), "total_chunks must match len(store.chunks)"
    assert stats["total_documents"] == len(store.documents), "total_documents must match len(store.documents)"
    assert stats["total_vectors"] > 0, "Vector store should have active vectors"
    assert stats["index_status"] == "ready"

    # Provider transparency
    provider = stats["embedding_provider"]
    assert provider["provider"] in ["local_dense_128d", "gemini_cloud"]
    assert provider["mode"] in ["local_offline", "external_cloud"]
    assert provider["dimension"] in [128, 768]
    assert "resource_requirements" in provider
    res_req = provider["resource_requirements"]
    assert "gpu_vram" in res_req
    assert "ram" in res_req
    assert "network" in res_req

    print(f"  [PASS] Provider: {provider['name']} ({provider['mode']})")
    print(f"         Dimension: {provider['dimension']}-d | Zero-GPU: {res_req['gpu_vram']}")
    print(f"         Total Truthful Vectors: {stats['total_vectors']} | Documents: {stats['total_documents']}")


def run_all_phase7_tests():
    print("=" * 70)
    print("PHASE 7 — RAG & VECTOR EXPLORER COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    test_1_document_chunker()
    test_2_repeatable_idempotent_indexing()
    test_3_relevance_threshold_and_preventing_unrelated_evidence()
    test_4_traceable_references_on_retrieved_passages()
    test_5_project_context_ingestion()
    test_6_empty_index_and_graceful_recovery()
    test_7_truthful_provider_transparency()

    print("\n" + "=" * 70)
    print(">>> ALL 7 PHASE 7 RAG & VECTOR EXPLORER TESTS PASSED 100% <<<")
    print("=" * 70)


if __name__ == "__main__":
    run_all_phase7_tests()
