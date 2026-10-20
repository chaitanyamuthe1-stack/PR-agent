"""
Benchmark Script for PR Agent Pipeline Optimization.
Compares Cold Run vs Hot Cached Run on vulnerable_app.py fixture.
Measures:
- End-to-end total latency
- Per-stage latency across all 6 stages
- Cache hit rates (Static Analysis & RAG)
- Security defect detection accuracy (CWE-89, CWE-78, CWE-798)
- Codebase health score precision
"""

import os
import sys
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.graph import run_full_pipeline
from backend.mcp_tools import clear_static_cache, get_static_cache_stats
from backend.rag.vector_store import clear_rag_cache, get_rag_cache_stats
from backend.samples import SAMPLES


def run_benchmark():
    sample = SAMPLES["python"]
    code = sample["code"]
    filename = "vulnerable_app.py"

    print("=" * 75)
    print("PR AGENT OPTIMIZATION BENCHMARK — REAL FIXTURE: vulnerable_app.py")
    print("=" * 75)

    # -------------------------------------------------------------
    # 1. COLD RUN (Uncached, full concurrent linters + RAG embed)
    # -------------------------------------------------------------
    clear_static_cache()
    clear_rag_cache()
    
    print("\n[RUN 1: COLD EXECUTION (Uncached Linters & RAG)]")
    t0_cold = time.perf_counter()
    res_cold = run_full_pipeline(code, "python", filename)
    cold_total_elapsed = round((time.perf_counter() - t0_cold) * 1000, 2)
    static_stats_cold = get_static_cache_stats()
    rag_stats_cold = get_rag_cache_stats()

    print(f"  Cold Total Elapsed: {cold_total_elapsed:.1f}ms (Reported Pipeline: {res_cold.get('total_elapsed_ms', 0):.1f}ms)")
    print(f"  Verdict: {res_cold.get('verdict')}")
    print(f"  Health Score: {res_cold.get('health_score')}/10.0 (Status: {res_cold.get('score_status', 'ASSESSED')})")
    print(f"  Unresolved Issues Detected: {res_cold.get('unresolved_count')}")
    print("  Per-Stage Telemetry:")
    cold_stages = {}
    for t in res_cold.get("telemetry", []):
        stage = t["stage"]
        dur = t.get("latency_ms", t.get("duration_ms", 0.0))
        status = t.get("status")
        cold_stages[stage] = dur
        print(f"    - {stage:22}: {dur:8.2f}ms [{status}]")

    # -------------------------------------------------------------
    # 2. HOT RUN (Warm Cache: Composite static cache + RAG query cache)
    # -------------------------------------------------------------
    print("\n[RUN 2: HOT EXECUTION (Cached Static Analysis & RAG Query Cache)]")
    t0_hot = time.perf_counter()
    res_hot = run_full_pipeline(code, "python", filename)
    hot_total_elapsed = round((time.perf_counter() - t0_hot) * 1000, 2)
    static_stats_hot = get_static_cache_stats()
    rag_stats_hot = get_rag_cache_stats()

    print(f"  Hot Total Elapsed: {hot_total_elapsed:.1f}ms (Reported Pipeline: {res_hot.get('total_elapsed_ms', 0):.1f}ms)")
    print(f"  Verdict: {res_hot.get('verdict')}")
    print(f"  Health Score: {res_hot.get('health_score')}/10.0 (Status: {res_hot.get('score_status', 'ASSESSED')})")
    print(f"  Unresolved Issues Detected: {res_hot.get('unresolved_count')}")
    print("  Per-Stage Telemetry:")
    hot_stages = {}
    for t in res_hot.get("telemetry", []):
        stage = t["stage"]
        dur = t.get("latency_ms", t.get("duration_ms", 0.0))
        status = t.get("status")
        hot_stages[stage] = dur
        speedup = f"{(cold_stages.get(stage, 1) / max(dur, 0.01)):.1f}x speedup" if dur < cold_stages.get(stage, 0) else "identical"
        print(f"    - {stage:22}: {dur:8.2f}ms [{status}] ({speedup})")

    # -------------------------------------------------------------
    # 3. BENCHMARK SUMMARY & SPEEDUP COMPARISON
    # -------------------------------------------------------------
    overall_speedup = cold_total_elapsed / max(hot_total_elapsed, 1.0)
    static_speedup = cold_stages.get("static_analysis", 1.0) / max(hot_stages.get("static_analysis", 0.01), 0.01)
    rag_speedup = cold_stages.get("rag_retrieval", 1.0) / max(hot_stages.get("rag_retrieval", 0.01), 0.01)

    print("\n" + "=" * 75)
    print("PERFORMANCE & OPTIMIZATION RESULTS SUMMARY")
    print("=" * 75)
    print(f"Cold Total Elapsed:          {cold_total_elapsed:.1f}ms")
    print(f"Hot Total Elapsed:           {hot_total_elapsed:.1f}ms ({overall_speedup:.2f}x Overall Speedup)")
    print(f"Static Analysis Latency:     {cold_stages.get('static_analysis', 0):.1f}ms -> {hot_stages.get('static_analysis', 0):.1f}ms ({static_speedup:.1f}x speedup)")
    print(f"RAG Retrieval Latency:       {cold_stages.get('rag_retrieval', 0):.1f}ms -> {hot_stages.get('rag_retrieval', 0):.1f}ms ({rag_speedup:.1f}x speedup)")
    print(f"Static Cache Stats:          {static_stats_hot}")
    print(f"RAG Cache Stats:             {rag_stats_hot}")
    print(f"Issues Detected:             {res_hot.get('unresolved_count')} findings")
    
    # Verify ground truth findings preserved
    cwes = {str(i.get('cwe', '')).upper() for i in res_hot.get('issues', [])}
    rule_ids = {str(i.get('rule_id', '')).upper() for i in res_hot.get('issues', [])}
    print("Vulnerability Accuracy:")
    print(f"  - SQL Injection (CWE-89 / B608):        {'DETECTED' if ('CWE-89' in cwes or 'B608' in rule_ids or 'BANDIT:B608' in rule_ids) else 'MISSED'}")
    print(f"  - Command Injection (CWE-78 / B602):    {'DETECTED' if ('CWE-78' in cwes or 'B602' in rule_ids or 'B605' in rule_ids or 'BANDIT:B605' in rule_ids) else 'MISSED'}")
    print(f"  - Hardcoded Secret (CWE-798 / B105):   {'DETECTED' if ('CWE-798' in cwes or 'B105' in rule_ids or 'BANDIT:B105' in rule_ids) else 'MISSED'}")
    print("=" * 75)

    return {
        "cold_elapsed_ms": cold_total_elapsed,
        "hot_elapsed_ms": hot_total_elapsed,
        "overall_speedup": round(overall_speedup, 2),
        "static_speedup": round(static_speedup, 2),
        "rag_speedup": round(rag_speedup, 2),
        "cold_stages": cold_stages,
        "hot_stages": hot_stages,
        "health_score": res_hot.get("health_score"),
        "unresolved_count": res_hot.get("unresolved_count")
    }


if __name__ == "__main__":
    run_benchmark()
