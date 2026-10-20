"""
Security Agent for PR Agent.
Flags security vulnerabilities, citing specific CWE and OWASP rule IDs.
Grounded in MCP static analysis findings and RAG vector store context.
"""

import json
import re
from typing import Dict, Any, List
from ..llm_gateway import gateway

SYSTEM_PROMPT = """You are the specialized pr_agent Security Agent.
Your job is to analyze source code along with deterministic MCP static analysis findings and RAG security standards.
Identify potentially exploitable vulnerabilities (SQL Injection, Command Injection, XSS, Buffer Overflows, Hardcoded Secrets, Insecure Deserialization, etc.).

Strict Responsibilities:
1. Identify potentially exploitable vulnerabilities.
2. Explain the vulnerable operation and likely exploit impact in 'description'.
3. Reference a real rule, CWE, or OWASP category when justified.
4. Avoid declaring a vulnerability confirmed when evidence is insufficient:
   - If backed by deterministic tool output or direct code proof, set 'evidence_level' to 'confirmed'.
   - If circumstantial or inconclusive, set 'evidence_level' to 'suspected' and state the need for additional evidence.
5. Provide a concrete, grounded remediation instruction in 'recommendation'.

For each vulnerability, you MUST provide:
- line: integer line number where the issue occurs
- severity: 'critical', 'high', 'medium', or 'low'
- category: 'security'
- title: concise title
- description: clear, plain-language explanation of the vulnerable operation and likely impact
- recommendation: concrete, grounded remediation instruction
- cwe: specific CWE ID (e.g. 'CWE-89')
- owasp: specific OWASP category (e.g. 'OWASP:A03:2021')
- rule_citation: formatted citation combining RAG rule and MCP tool (e.g. 'RAG: OWASP A03:2021 + MCP: Bandit B608')
- evidence_level: 'confirmed' or 'suspected'

Return ONLY a valid JSON object matching this schema:
{
  "agent": "security_agent",
  "findings": [
    {
      "line": 10,
      "severity": "critical",
      "category": "security",
      "title": "SQL Injection in User Query",
      "description": "Vulnerable operation: string-concatenated SQL query. Likely impact: arbitrary query manipulation and unauthorized database data extraction.",
      "recommendation": "Use parameterized query placeholders instead of raw string concatenation.",
      "cwe": "CWE-89",
      "owasp": "OWASP:A03:2021",
      "rule_citation": "RAG: OWASP A03:2021 + MCP: Bandit B608",
      "evidence_level": "confirmed"
    }
  ]
}
"""

def run_security_agent(
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
            'remediation': str(r.get('remediation', ''))[:200],
            'citation': r.get('citation')
        }
        for r in rag_context[:8]
    ]

    # Format user prompt
    prompt = f"""Language: {language}

SOURCE CODE:
```{language}
{bounded_code}
```

DETERMINISTIC STATIC ANALYSIS FINDINGS (MCP Layer):
{json.dumps(bounded_static, indent=2)}

GROUNDED RAG RULES & STANDARDS:
{json.dumps(bounded_rag, indent=2)}

Analyze the code and output the security findings in JSON format. Every finding MUST cite a real rule ID.
"""

    response_text = gateway.generate(
        prompt=prompt,
        system_instruction=SYSTEM_PROMPT,
        provider_preference=provider,
        temperature=0.1
    )

    # Parse JSON output
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

    # Resilient fallback synthesis from static findings + RAG
    fallback_findings = []
    for sf in static_findings:
        if sf.get("category") == "security":
            # Match with RAG rule
            rag_match = next((r for r in rag_context if r.get("cwe") == sf.get("cwe")), None)
            citation = f"RAG: {rag_match.get('citation', 'OWASP:A03:2021')} + MCP: {sf.get('tool', 'linter').capitalize()} {sf.get('rule_id', '')}" if rag_match else f"MCP: {sf.get('tool', 'linter').capitalize()} {sf.get('rule_id', '')}"
            
            fallback_findings.append({
                "line": sf.get("line", 1),
                "severity": sf.get("severity", "high"),
                "category": "security",
                "title": f"Security Vulnerability ({sf.get('cwe', 'CWE-Unknown')})",
                "description": f"Vulnerable operation flagged by {sf.get('tool', 'linter')}: {sf.get('message', 'Security vulnerability detected')}. Likely impact: unauthorized access or execution risk.",
                "recommendation": rag_match.get("remediation", "Apply defensive validation and parameterized controls.") if rag_match else "Review and remediate according to secure coding standards.",
                "cwe": sf.get("cwe", "CWE-Unknown"),
                "rule_id": sf.get("rule_id", "SecRule"),
                "owasp": rag_match.get("rule_id", "OWASP:A03:2021") if rag_match else "OWASP:General",
                "rule_citation": citation,
                "evidence_level": "confirmed",
                "verified": True
            })
    return fallback_findings
