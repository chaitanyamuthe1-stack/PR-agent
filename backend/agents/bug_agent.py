"""
Bug-Detection Agent for PR Agent.
Flags logic bugs, resource leaks, edge-case failures, and style inconsistencies.
Runs in parallel with the Security Agent.
"""

import json
from typing import Dict, Any, List
from ..llm_gateway import gateway

SYSTEM_PROMPT = """You are the specialized pr_agent Bug-Detection Agent.
Your job is to analyze source code for logic errors, runtime risks, boundary errors, incorrect conditions, and resource-management issues.

Strict Responsibilities:
1. Identify logic errors, runtime risks, boundary errors, incorrect conditions, and resource-management issues.
2. Explain the triggering condition: state the exact operational inputs, boundary conditions, or state that causes failure.
3. Suggest a concrete correction in 'recommendation'.

For each finding, provide:
- line: integer line number
- severity: 'high', 'medium', or 'low'
- category: 'bug', 'style', or 'performance'
- title: concise title
- description: clear, plain-language explanation of the bug or edge case
- triggering_condition: specific input, boundary state, or execution condition that causes the fault
- recommendation: concrete, actionable correction
- rule_citation: formatted citation combining RAG rule and MCP tool (e.g. 'RAG: CWE-369 + MCP: Pylint:zero-division')
- evidence_level: 'confirmed' or 'suspected'

Return ONLY a valid JSON object matching this schema:
{
  "agent": "bug_agent",
  "findings": [
    {
      "line": 12,
      "severity": "high",
      "category": "bug",
      "title": "Division by Zero Exception",
      "description": "Division operation executed without validating if denominator is zero.",
      "triggering_condition": "Denominator variable evaluates to 0 (e.g. empty record set or zero count).",
      "recommendation": "Guard division with ternary validation: (num / denom) if denom > 0 else 0.0",
      "rule_citation": "RAG: CWE-369 + MCP: Pylint:zero-division",
      "evidence_level": "confirmed"
    }
  ]
}
"""

def run_bug_agent(
    code: str,
    language: str,
    static_findings: List[Dict[str, Any]],
    rag_context: List[Dict[str, Any]],
    provider: str = None
) -> List[Dict[str, Any]]:
    # Bounded prompt: limit code context to prevent LLM context overflow (max 50,000 characters)
    bounded_code = code if len(code) <= 50000 else code[:50000] + "\n... [TRUNCATED FOR CONTEXT BUDGET] ..."

    # Bound findings and RAG context to prevent prompt explosion on large scans
    bounded_static = [
        {
            'tool': sf.get('tool'),
            'rule_id': sf.get('rule_id'),
            'line': sf.get('line'),
            'message': str(sf.get('message', ''))[:200],
            'severity': sf.get('severity'),
            'cwe': sf.get('cwe')
        }
        for sf in static_findings[:25]
    ]
    bounded_rag = [
        {
            'rule_id': r.get('rule_id'),
            'cwe': r.get('cwe'),
            'title': str(r.get('title', ''))[:100],
            'remediation': str(r.get('remediation', ''))[:200]
        }
        for r in rag_context[:8]
    ]

    prompt = f"""Language: {language}

SOURCE CODE:
```{language}
{bounded_code}
```

DETERMINISTIC STATIC ANALYSIS FINDINGS (MCP Layer):
{json.dumps(bounded_static, indent=2)}

GROUNDED RAG RULES & STANDARDS:
{json.dumps(bounded_rag, indent=2)}

Analyze the code for logic errors, bounds, resource leaks, and style defects. Output JSON.
"""

    response_text = gateway.generate(
        prompt=prompt,
        system_instruction=SYSTEM_PROMPT,
        provider_preference=provider,
        temperature=0.1
    )

    try:
        cleaned = response_text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()
        
        data = json.loads(cleaned)
        findings = data.get("findings", [])
        if findings:
            return findings
    except Exception:
        pass

    # Resilient fallback synthesis
    fallback_findings = []
    for sf in static_findings:
        if sf.get("category") in ["bug", "style", "performance"]:
            rag_match = next((r for r in rag_context if r.get("cwe") == sf.get("cwe")), None)
            citation = f"RAG: {rag_match.get('citation', 'CWE-Logic')} + MCP: {sf.get('tool', 'linter').capitalize()} {sf.get('rule_id', '')}" if rag_match else f"MCP: {sf.get('tool', 'linter').capitalize()} {sf.get('rule_id', '')}"

            fallback_findings.append({
                "line": sf.get("line", 1),
                "severity": sf.get("severity", "medium"),
                "category": sf.get("category", "bug"),
                "title": f"Logic / Quality Issue ({sf.get('rule_id', 'Lint')})",
                "description": sf.get("message", "Logic bug or style flaw detected"),
                "triggering_condition": f"Triggered during static analysis rule check: {sf.get('rule_id', 'RuleViolation')}.",
                "recommendation": rag_match.get("remediation", "Apply defensive guards and conform to language style guidelines.") if rag_match else "Ensure resource cleanup and boundary verification.",
                "rule_citation": citation,
                "rule_id": sf.get("rule_id", "Lint"),
                "cwe": sf.get("cwe", "CWE-1078"),
                "evidence_level": "confirmed",
                "verified": True
            })
    return fallback_findings
