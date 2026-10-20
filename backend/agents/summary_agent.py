"""
Summary Agent for PR Agent.
Merges security and bug detection findings into a unified triage report.
Computes an overall deterministic Health Score out of 10 and assigns verdict badge.
Enforces the Phase 9 unified issue schema with verified vs unverified observation telemetry.
"""

import re
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

# Phase 9 Standard Schema Specifications
VALID_SEVERITIES = {"critical", "high", "medium", "low", "informational"}
VALID_CATEGORIES = {"security", "bug", "style", "performance", "reliability"}


@dataclass
class ScoringCriteria:
    """
    Documented, configurable criteria for codebase health score computation.
    
    Attributes:
      base_score: Initial baseline score (default: 10.0)
      critical_deduction: Points deducted per critical finding (default: 3.0)
      high_deduction: Points deducted per high finding (default: 1.5)
      medium_deduction: Points deducted per medium finding (default: 0.75)
      low_deduction: Points deducted per low finding (default: 0.25)
      info_deduction: Points deducted per informational finding (default: 0.05)
      verified_weight: Multiplier applied to verified static findings (default: 1.0)
      unverified_weight: Multiplier applied to unverified heuristic observations (default: 0.5)
      critical_cap: Maximum health score allowed when >= 1 critical finding exists (default: 6.0)
      two_high_cap: Maximum health score allowed when >= 2 high findings exist (default: 7.0)
      min_score: Lower bound clamp (default: 0.5)
      max_score: Upper bound clamp (default: 10.0)
      weight_by_verification: Whether to scale deductions by verification status (default: False)
    """
    base_score: float = 10.0
    critical_deduction: float = 3.0
    high_deduction: float = 1.5
    medium_deduction: float = 0.75
    low_deduction: float = 0.25
    info_deduction: float = 0.05
    verified_weight: float = 1.0
    unverified_weight: float = 0.5
    critical_cap: float = 6.0
    two_high_cap: float = 7.0
    min_score: float = 0.5
    max_score: float = 10.0
    weight_by_verification: bool = False


def calculate_health_score(
    issues: List[Dict[str, Any]],
    criteria: Optional[ScoringCriteria] = None,
    pipeline_stages_failed: bool = False,
    pipeline_stages_skipped: bool = False
) -> float:
    """
    Computes an engineering health score out of 10 based on documented, configurable criteria.
    Distinguishes an unassessed score from a genuine score of zero or ten:
    - If analysis stages failed, returns 0.0 (or degraded failure score; never 10.0).
    - If analysis stages were skipped, returns 5.0 (cannot award a perfect score when analysis is skipped).
    - Otherwise calculates deterministic deductions and safety caps based on verified findings and test results.
    """
    crit = criteria or ScoringCriteria()

    if pipeline_stages_failed:
        return 0.0
    if pipeline_stages_skipped and not issues:
        return 5.0

    if not issues:
        return crit.max_score

    score = crit.base_score
    critical_count = 0
    high_count = 0

    for issue in issues:
        if issue.get("ignored"):
            continue
        sev = str(issue.get("severity", "medium")).lower().strip()
        if sev == "critical":
            deduction = crit.critical_deduction
            critical_count += 1
        elif sev == "high":
            deduction = crit.high_deduction
            high_count += 1
        elif sev == "medium":
            deduction = crit.medium_deduction
        elif sev == "low":
            deduction = crit.low_deduction
        elif sev == "informational":
            deduction = crit.info_deduction
        else:
            deduction = crit.medium_deduction

        if crit.weight_by_verification:
            is_verified = issue.get("verified", False) or issue.get("verification_status") == "verified_static"
            weight = crit.verified_weight if is_verified else crit.unverified_weight
            deduction *= weight

        score -= deduction

    # Apply safety caps: critical defects prevent inflated health scores
    if critical_count >= 1:
        score = min(score, crit.critical_cap)
    elif high_count >= 2:
        score = min(score, crit.two_high_cap)

    final_score = max(crit.min_score, min(crit.max_score, score))
    return round(final_score, 1)


def run_summary_agent(
    security_findings: List[Dict[str, Any]],
    bug_findings: List[Dict[str, Any]],
    filename: str = "source_code.txt",
    static_findings: Optional[List[Dict[str, Any]]] = None,
    criteria: Optional[ScoringCriteria] = None,
    pipeline_stages_failed: bool = False,
    pipeline_stages_skipped: bool = False
) -> Dict[str, Any]:
    """
    Merges findings from parallel Security and Bug-Detection agents.
    Normalizes severity, categories, source locations, evidence, recommendations,
    and classifies detection_source and verification_status (verified_static vs unverified_llm_observation).
    Deduplicates findings, calculates deterministic health score, counts, verdict, and summary.
    
    CRITICAL: Verdict is determined strictly from actual unresolved findings:
    - unresolved_findings == 0 -> CLEAN (with explicit limited scope disclaimer)
    - unresolved_findings > 0 with only low/info -> NEEDS REVIEW
    - unresolved_findings > 0 with critical/high/medium -> FIX REQUIRED
    A high health score does NOT override actionable unresolved defects.
    """
    combined = []
    seen_keys = set()
    static_pool = static_findings or []

    # Merge, normalize, and deduplicate by (line, title) or (line, rule)
    all_raw = list(security_findings) + list(bug_findings)

    for idx, raw_finding in enumerate(all_raw, 1):
        f = dict(raw_finding)

        # 1. Normalize line number
        try:
            line_val = int(f.get("line", 1))
            f["line"] = max(1, line_val)
        except (ValueError, TypeError):
            f["line"] = 1

        # 2. Normalize severity (Critical, High, Medium, Low, Informational)
        sev = str(f.get("severity", "medium")).lower().strip()
        f["severity"] = sev if sev in VALID_SEVERITIES else "medium"

        # 3. Normalize category (Security, Bug, Style, Performance, Reliability)
        cat = str(f.get("category", "bug")).lower().strip()
        if cat == "complexity":
            cat = "reliability"
        f["category"] = cat if cat in VALID_CATEGORIES else "bug"

        # 4. Target file
        f["file"] = f.get("file") or filename

        # 5. Normalize rule identifiers, CWE, and OWASP
        cwe_raw = str(f.get("cwe", "")).strip()
        if cwe_raw and not cwe_raw.upper().startswith("CWE-") and cwe_raw.isdigit():
            f["cwe"] = f"CWE-{cwe_raw}"
        else:
            f["cwe"] = cwe_raw or f.get("rule_id", "N/A")

        owasp_raw = str(f.get("owasp", "")).strip()
        f["owasp"] = owasp_raw or ("OWASP Top 10" if f["category"] == "security" else "N/A")

        if not f.get("rule_id"):
            f["rule_id"] = f.get("cwe") or f.get("tool") or f"{f['category'].upper()}-RULE"

        if not f.get("rule_citation"):
            if f.get("cwe") and f.get("owasp"):
                f["rule_citation"] = f"{f['owasp']} / {f['cwe']}"
            elif f.get("rule_id"):
                f["rule_citation"] = f"{f['rule_id']} Standard"
            else:
                f["rule_citation"] = "PR Agent Security Baseline"

        # 6. Detection Source & Verification Status
        # Check if corroborated by any deterministic static analyzer output
        is_static_corroborated = any(
            str(s.get("line")) == str(f["line"]) or 
            (f.get("cwe") and f["cwe"] == s.get("cwe")) or 
            (f.get("rule_id") and f["rule_id"] in str(s.get("rule_id", "")))
            for s in static_pool
        )

        existing_source = f.get("detection_source") or f.get("tool")
        if existing_source and existing_source not in ["security_agent", "bug_agent", "llm"]:
            f["detection_source"] = existing_source
            f["verification_status"] = "verified_static"
            f["verified"] = True
        elif is_static_corroborated:
            matched_tool = next(
                (s.get("tool") for s in static_pool if str(s.get("line")) == str(f["line"]) or f.get("cwe") == s.get("cwe")),
                "mcp_static_analyzer"
            )
            f["detection_source"] = matched_tool
            f["verification_status"] = "verified_static"
            f["verified"] = True
        else:
            f["detection_source"] = f.get("detection_source") or ("security_agent" if f["category"] == "security" else "bug_agent")
            f["verification_status"] = "unverified_llm_observation"
            f["verified"] = False

        if f.get("resolved"):
            f["verification_status"] = "remediated"

        # 7. Normalize Evidence
        if not f.get("evidence"):
            if f["verification_status"] == "verified_static":
                f["evidence"] = f.get("raw_linter_output") or f"Deterministic violation reported by {f['detection_source']} at line {f['line']}."
            else:
                f["evidence"] = f.get("triggering_condition") or "AI-generated heuristic observation; pending automated linter corroboration."

        # 8. Normalize Recommendation and Description
        if not f.get("recommendation"):
            f["recommendation"] = "Apply defensive programming practices and conform to language-specific security guidelines."
        if not f.get("description"):
            f["description"] = f.get("message", "Potential code quality, reliability, or security flaw flagged.")

        # 9. Unique Finding ID
        prefix = "SEC" if f["category"] == "security" else "BUG" if f["category"] == "bug" else "STY" if f["category"] == "style" else "PERF" if f["category"] == "performance" else "REL"
        f["id"] = f.get("id") or f"{prefix}-{str(f['line']).zfill(3)}-{idx:02d}"
        f["finding_id"] = f["id"]

        # Deduplication key: combination of line and title/cwe
        title_key = re.sub(r'[^a-zA-Z0-9]', '', str(f.get("title", "")).lower())[:30]
        cwe_key = str(f.get("cwe", f.get("rule_id", ""))).upper()
        key = f"{f['line']}_{title_key}_{cwe_key}"

        if key not in seen_keys:
            seen_keys.add(key)
            combined.append(f)

    # Sort combined issues: Critical first, then High, Medium, Low, Informational; then by line number
    sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}
    combined.sort(key=lambda x: (sev_rank.get(x.get("severity", "medium"), 2), int(x.get("line", 1))))

    unresolved_findings = [f for f in combined if not f.get("resolved", False)]
    resolved_findings = [f for f in combined if f.get("resolved", False)]
    verified_findings = [f for f in combined if f.get("verification_status") == "verified_static"]
    unverified_recommendations = [f for f in combined if f.get("verification_status") == "unverified_llm_observation"]

    # Compute severity counts on unresolved actionable findings
    counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "informational": 0
    }
    category_counts = {
        "security": 0,
        "bug": 0,
        "style": 0,
        "performance": 0,
        "reliability": 0
    }
    status_counts = {
        "verified_static": len(verified_findings),
        "unverified_llm_observation": len(unverified_recommendations),
        "remediated": len(resolved_findings),
        "failed_verification": len([f for f in unresolved_findings if f.get("remediation_attempted")])
    }

    for item in unresolved_findings:
        sev = item["severity"]
        if sev in counts:
            counts[sev] += 1
        cat = item["category"]
        if cat in category_counts:
            category_counts[cat] += 1

    # Health score reflects remaining unresolved defects
    health_score = calculate_health_score(
        unresolved_findings,
        criteria=criteria,
        pipeline_stages_failed=pipeline_stages_failed,
        pipeline_stages_skipped=pipeline_stages_skipped
    )
    is_assessed = not (pipeline_stages_failed or pipeline_stages_skipped)
    score_status = "FAILED" if pipeline_stages_failed else ("UNASSESSED" if pipeline_stages_skipped else "ASSESSED")

    # STRICT VERDICT:
    # Determined strictly from actual unresolved findings:
    # - 0 unresolved defects -> CLEAN
    # - only low or informational -> NEEDS REVIEW
    # - critical / high / medium -> FIX REQUIRED
    if len(unresolved_findings) == 0:
        verdict = "CLEAN"
    elif all(f.get("severity") in ["low", "informational"] for f in unresolved_findings):
        verdict = "NEEDS REVIEW"
    else:
        verdict = "FIX REQUIRED"

    # Generate executive summary with required mathematical disclaimer
    safety_disclaimer = "Scope is limited to the executed static linters and multi-agent checks; not a mathematical proof of absolute correctness."
    if verdict == "CLEAN":
        if resolved_findings:
            summary = (
                f"All {len(resolved_findings)} actionable finding(s) have been successfully remediated and verified. "
                f"Codebase meets clean architecture and security baseline standards. ({safety_disclaimer})"
            )
        else:
            summary = (
                f"Code meets clean architecture and security baseline standards. No blocking flaws detected. ({safety_disclaimer})"
            )
    elif verdict == "NEEDS REVIEW":
        summary = (
            f"Review identified {len(unresolved_findings)} non-blocking finding(s) "
            f"({counts['low']} low, {counts['informational']} informational) that warrant developer review."
        )
    else:
        crit_count = counts["critical"]
        high_count = counts["high"]
        med_count = counts["medium"]
        total_unresolved = len(unresolved_findings)
        summary = (
            f"Triage identified {total_unresolved} unresolved actionable defect(s) requiring remediation "
            f"({crit_count} critical, {high_count} high, {med_count} medium, {counts['low']} low, {counts['informational']} informational)."
        )

    return {
        "all_issues": combined,
        "unresolved_findings": unresolved_findings,
        "resolved_findings": resolved_findings,
        "verified_findings": verified_findings,
        "unverified_recommendations": unverified_recommendations,
        "unresolved_count": len(unresolved_findings),
        "resolved_count": len(resolved_findings),
        "health_score": health_score,
        "is_assessed": is_assessed,
        "score_status": score_status,
        "scoring_criteria": asdict(criteria or ScoringCriteria()),
        "verdict": verdict,
        "summary": summary,
        "counts": counts,
        "category_counts": category_counts,
        "status_counts": status_counts,
        "total_issues": len(combined),
        "safety_disclaimer": safety_disclaimer
    }
