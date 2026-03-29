# LLM Compliance & Transparency Report
## TarotCardProject

**Report Date**: 2026-03-29
**Auditor**: LLM Governance & Compliance Team
**Project**: TarotCardProject (Claude-assisted development)
**Framework**: EU AI Act Art. 25, OWASP LLM Top 10 2025, NIST SP 800-218A
**Audit Type**: INITIAL

---

## Executive Summary

**Overall LLM Compliance Score: 52/100 (DEVELOPING)**

The TarotCardProject demonstrates strong transparency around AI involvement in development (Co-Authored-By tags, CLAUDE.md documentation) but has significant gaps in supply chain security, sensitive data handling, and incident response processes. The project uses AI (Claude) as a development assistant and LLMs (Ollama) as a runtime component for narration generation. Neither use case falls under EU AI Act "high-risk" classification, but the project would benefit from hardening in several compliance dimensions.

| Dimension | Score | Status |
|-----------|-------|--------|
| System Transparency | 82 | GOOD |
| Training Data Disclosure | 55 | DEVELOPING |
| Risk Classification | 60 | DEVELOPING |
| Supply Chain Security | 25 | NEEDS IMPROVEMENT |
| Consent & Authorization | 75 | GOOD |
| Sensitive Data Handling | 40 | NEEDS IMPROVEMENT |
| Incident Response | 45 | NEEDS IMPROVEMENT |
| Bias Assessment | 35 | NEEDS IMPROVEMENT |

---

## Dimension Scores

### Dimension 1: System Transparency (82/100)

The project has strong AI disclosure practices:

- **Co-Authored-By tags**: Every commit generated with Claude includes `Co-Authored-By: Claude` in the commit message. Git log confirms this across multiple commits.
- **CLAUDE.md**: Comprehensive project instructions file explicitly describes the human-AI collaboration model, including tool stack, workflow design philosophy, and Claude's role.
- **Branch naming**: Claude-generated branches use `claude/` prefix convention (e.g., `claude/focus-upright-blend-stills`).
- **Limitation documentation**: CLAUDE.md documents known limitations (e.g., "AnimateDiff is NOT installed", "require('axios') CRASHES the task runner") discovered through AI-assisted debugging.

**Gap**: No per-file attribution indicating which files were AI-generated vs human-written. No README disclosure for end users about AI involvement in the project.

**Regulatory mapping**: EU AI Act Art. 52 -- partial compliance (developer-facing disclosure exists; end-user disclosure missing).

### Dimension 2: Training Data Disclosure (55/100)

- **Model identification**: CLAUDE.md identifies Claude as the AI assistant (though not the specific model version). Ollama is identified as the runtime LLM for narrations.
- **Framework sources**: CLAUDE.md references ComfyUI, n8n, and Wan 2.2 model documentation, but does not cite specific versions of security frameworks (OWASP, CWE, NIST) used in audit generation.
- **No model cards**: The ML models (Wan 2.2, CLIP-L, umt5_xxl) are referenced by filename only with no Hugging Face model card links or data provenance documentation.

**Gap**: No documentation of which knowledge sources (OWASP version, CWE database version, NIST publication dates) inform AI-generated security assessments.

**Regulatory mapping**: EU AI Act Art. 53 -- not met (no formal technical documentation of AI system capabilities and limitations).

### Dimension 3: Risk Classification (60/100)

- **CWE Mapping Report** (Phase 1): Successfully identified 14 CWEs with accurate severity classifications aligned to CVSS conventions.
- **Multi-framework mapping**: Each finding is mapped to 8 compliance frameworks with consistent cross-referencing.
- **Contextual severity**: The reports correctly contextualize findings for a local-only deployment (e.g., cleartext HTTP on localhost rated MEDIUM, not HIGH).

**Gap**: No formal false positive analysis. No validation against known vulnerability databases or test suites. Severity ratings are analyst judgment, not CVSS-calculated scores.

**Regulatory mapping**: EU AI Act Art. 25 -- partial (risk identification exists but lacks formal methodology documentation).

### Dimension 4: Supply Chain Security (25/100)

This is the weakest dimension. The Supply Chain Audit (Phase 1) found:

- **SLSA Level 0**: No build automation, no provenance, no reproducibility.
- **No lockfiles**: Zero dependency pinning across Python, Node.js, or ComfyUI custom nodes.
- **No SBOM**: No Software Bill of Materials in any format.
- **No model hash verification**: 6 ML model files referenced by filename only.
- **Unverified code inclusion**: `setup_comfyui_nodes.py` clones arbitrary GitHub repos without integrity checks. Embedded Python runs `pip install` at runtime.
- **No branch protection** on `main`.
- **No CI/CD**: No automated scanning or testing pipeline.

**Regulatory mapping**: NIST SP 800-218A -- largely non-compliant. SLSA v1.0 -- L0. EU AI Act Art. 25 -- gaps in risk management for third-party components.

### Dimension 5: Consent & Authorization (75/100)

- **Opt-in model**: All n8n workflows require manual trigger to execute. No background or automatic execution.
- **Destructive action gating**: The post-commit audit skill requires user confirmation before git push. The CLAUDE.md documents that git push requires explicit user approval.
- **User override capability**: All workflow parameters are configurable via Set Global Parameters nodes and Deck.json. Users can override any AI-generated value.
- **n8n permission model**: n8n startup flags (`NODE_FUNCTION_ALLOW_BUILTIN=*`) are a conscious, documented tradeoff.

**Gap**: ComfyUI API accepts unauthenticated requests from any local process -- no per-request authorization. Ollama API similarly unauthenticated.

**Regulatory mapping**: EU AI Act Art. 14 -- substantially met for human oversight. NIST AI RMF GOVERN 1.2 -- met.

### Dimension 6: Sensitive Data Handling (40/100)

The SAST/DAST Scan (Phase 1) revealed:

- **CRITICAL**: n8n API key (JWT, never-expiring) hardcoded in multiple worktree settings files. The same key referenced in memory files.
- **Credential IDs exposed**: Ollama credential ID and webhook IDs committed in workflow JSONs.
- **No .gitignore**: No root-level .gitignore to prevent accidental secret commits.
- **Error messages expose paths**: Error handlers include full filesystem paths and API response bodies.
- **No PII in outputs**: Card images and narrations do not contain personal information. Audit reports appropriately redact the full JWT value.

**Gap**: Critical credential exposure outweighs positive findings. No secret scanning in place.

**Regulatory mapping**: GDPR Art. 5 -- N/A (no PII processed). NIST SP 800-53 SC-28 -- not met for credential protection. ISO 27001 A.8.11 -- not met.

### Dimension 7: Incident Response (45/100)

- **Remediation guidance exists**: Each SAST/DAST finding includes specific remediation steps with code examples.
- **Fix-then-reaudit workflow**: The post-commit-audit skill includes a documented remediation loop (find -> fix -> re-audit -> verify).
- **Error surfacing**: n8n Code nodes throw descriptive errors per CLAUDE.md's design principle #5 ("Informative errors, not silent failures").

**Gap**: No formal incident response plan or SECURITY.md in the repository. No vulnerability disclosure process. No monitoring or alerting for runtime failures. The `require('axios')` bug in two workflows (M-6) silently breaks those workflows with a generic error.

**Regulatory mapping**: NIST SP 800-53 IR-4 -- partially met (remediation exists, no formal IR plan). ISO 27001 A.16 -- not met.

### Dimension 8: Bias Assessment (35/100)

- **Framework coverage documented**: The CWE Mapping Report acknowledges that OWASP LLM Top 10 and MITRE ATLAS have lower coverage (21-29%) because the project uses ML models as tools, not services.
- **Detection gap acknowledgment**: Reports note that findings are based on manual analysis, not automated scanner benchmarks.

**Gap**: No measurement of false positive or false negative rates. No multi-language/framework equity analysis (the project is JavaScript/Python/JSON only, so this is a limited concern). No formal methodology documentation for how findings were identified. No validation against known test suites (e.g., OWASP WebGoat, Juice Shop).

**Regulatory mapping**: EU AI Act Art. 10 -- not applicable (not a data-driven AI system). NIST AI RMF MEASURE 2.11 -- not met.

---

## Recommendations

1. **Create SECURITY.md** with vulnerability reporting instructions, supported versions, and expected response timeline.
2. **Add a .gitignore** immediately to prevent credential leakage (`.claude/`, `*.env`, `node_modules/`).
3. **Document model provenance**: Add Hugging Face model card links and SHA-256 hashes for all `.safetensors` files.
4. **Generate an SBOM** (CycloneDX 1.4 format) listing all software components.
5. **Enable branch protection** on `main` with required reviews.

## Regulatory Roadmap

| Milestone | Target | Dimension Impact |
|-----------|--------|-----------------|
| Rotate API key + add .gitignore | Immediate | D6: +20pts |
| Create SECURITY.md | 1 week | D7: +15pts |
| Add model provenance docs | 2 weeks | D2: +20pts, D4: +10pts |
| Enable branch protection + CI | 1 month | D4: +15pts, D7: +10pts |
| Generate SBOM + pin dependencies | 1 month | D4: +20pts |

**Next audit recommended**: After remediation of critical findings (estimated 2 weeks).
