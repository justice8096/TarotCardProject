# Supply Chain Security Audit

## TarotCardProject

**Date**: 2026-03-29
**Commit**: f55bcb8
**Branch**: claude/focus-upright-blend-stills
**Repository**: https://github.com/justice8096/TarotCardProject.git (public)
**Auditor**: Automated (Claude Code)

---

## Executive Summary

The TarotCardProject is a tarot card generation system using ComfyUI (image/video generation), n8n (workflow orchestration), Python scripts, and local ML models. The project has **significant supply chain security gaps** typical of a single-developer creative/ML project. There are no lockfiles, no dependency pinning, no SBOM, no CI/CD pipelines, no branch protection, no model hash verification, and hardcoded API credentials in worktree configuration files. The project achieves **SLSA Level 0 (L0)**.

**Overall Risk Rating: HIGH**

---

## 1. Dependency Pinning

### Python Dependencies

| Finding | Severity |
|---------|----------|
| No `requirements.txt`, `Pipfile.lock`, `poetry.lock`, or any Python dependency manifest | HIGH |
| Python scripts use only stdlib modules (`json`, `os`, `re`, `subprocess`, `sys`, `urllib`, `pathlib`) | MITIGATING |
| No third-party Python packages are imported in committed scripts | LOW (current) |

**Analysis**: The three Python scripts (`setup_comfyui_nodes.py`, `setup_n8n_nodes.py`, `update_workflow_paths.py`) exclusively use Python standard library modules. This eliminates third-party Python supply chain risk for the committed code. However, the `setup_comfyui_nodes.py` script installs ComfyUI custom nodes via `git clone` from GitHub URLs found in ComfyUI Manager's `extension-node-map.json` -- these cloned packages have their own unaudited Python dependencies.

### Node.js / n8n Dependencies

| Finding | Severity |
|---------|----------|
| No `package-lock.json`, `yarn.lock`, or `pnpm-lock.yaml` in the project | HIGH |
| n8n is installed externally at `D:/n8n/` (not part of this repo) | INFO |
| n8n community packages installed via `n8n install <pkg>` without version pinning | MEDIUM |

### ComfyUI Dependencies

| Finding | Severity |
|---------|----------|
| Custom nodes installed via `git clone` without pinning to specific commits or tags | HIGH |
| No verification of cloned repository integrity | HIGH |
| `setup_comfyui_nodes.py` trusts `extension-node-map.json` from ComfyUI Manager as source of truth for GitHub URLs | MEDIUM |

---

## 2. Lockfile Integrity

| Check | Status |
|-------|--------|
| `package-lock.json` exists | NO |
| `yarn.lock` exists | NO |
| `pnpm-lock.yaml` exists | NO |
| `requirements.txt` exists | NO |
| `Pipfile.lock` exists | NO |
| `poetry.lock` exists | NO |
| Any lockfile committed to git | NO |

**Verdict**: No lockfiles exist anywhere in the project. Builds are not reproducible. Any installation of dependencies (ComfyUI custom nodes, n8n community packages) will pull the latest version at install time, which could include malicious or breaking changes.

---

## 3. CI/CD Secret Handling

| Check | Status |
|-------|--------|
| GitHub Actions workflows present | NO |
| Any CI/CD pipeline configured | NO |
| `.github/` directory contents | Only issue templates (`bug_report.md`, `feature_request.md`) |
| Branch protection on `main` | NO -- confirmed via GitHub API (404: Branch not protected) |

**Findings**:
- No CI/CD pipeline exists. All builds and deployments are manual/local.
- No automated security scanning, linting, or testing.
- No signed commits required.
- The `main` branch has no protection rules -- anyone with write access can force-push.

### Credential Exposure

| Finding | Severity |
|---------|----------|
| n8n API key (JWT) hardcoded in `.claude/worktrees/*/settings.local.json` files | CRITICAL |
| n8n Ollama credential ID exposed in `n8n/Add Meanings.json` (`trj8oFkLILUiN2Pd`) | LOW |
| Worktree settings files contain full `X-N8N-API-KEY` JWT tokens in plaintext | CRITICAL |
| No `.gitignore` file exists at project root | HIGH |

**Detail on API key exposure**: Multiple worktree `settings.local.json` files under `n8n/.claude/worktrees/` contain the full n8n API JWT token in curl command allowlists. While these are in `.claude/` worktree directories (which may not be intended for commit), the `n8n/.claude/` directory is shown as untracked in git status, meaning it could accidentally be committed. The JWT payload decodes to:
- Subject: `328e7f1b-2e82-4b71-bc49-cf0db0cd9322`
- Issuer: `n8n`
- Audience: `public-api`
- Issued: Dec 2024

**Recommendation**: Immediately rotate the n8n API key. Add `.claude/` to `.gitignore`. Use environment variables for all credentials.

---

## 4. Software Bill of Materials (SBOM)

| Check | Status |
|-------|--------|
| SPDX SBOM file | NOT PRESENT |
| CycloneDX SBOM file | NOT PRESENT |
| Any SBOM format | NOT PRESENT |

**Inventory of known software components** (manual reconstruction):

| Component | Version | Source | Pinned? |
|-----------|---------|--------|---------|
| Python | System install | `C:/Users/justi/AppData/Local/Microsoft/WindowsApps/python.exe` | No (system) |
| Node.js | System install | `C:/Program Files/nodejs/node.exe` | No (system) |
| n8n | 2.7.5 (per CLAUDE.md) | npm | No |
| ComfyUI | Unknown | `D:/ComfyUI_windows_portable/ComfyUI/` | No |
| ffmpeg | 8.0.1 | `D:/ComfyUI_windows_portable/ffmpeg-8.0.1-full_build/` | Yes (local binary) |
| Wan 2.2 I2V model (14B fp8) | 2.2 | Local `.safetensors` files | No hash verification |
| LightX2V 4-step LoRA | v1 | Local `.safetensors` file | No hash verification |
| umt5_xxl text encoder (fp8) | Unknown | Local `.safetensors` file | No hash verification |
| CLIP-L | Unknown | Local `.safetensors` file | No hash verification |
| Wan 2.1 VAE | 2.1 | Local `.safetensors` file | No hash verification |
| ComfyUI-VideoHelperSuite | Unknown | git clone | No (HEAD of default branch) |

---

## 5. SLSA Level Assessment

| SLSA Requirement | Status | Notes |
|-----------------|--------|-------|
| **L0: No guarantees** | **CURRENT LEVEL** | -- |
| **L1: Documentation of build process** | NOT MET | No build system defined; no provenance generated |
| L1: Build exists | NOT MET | No automated build; manual local execution only |
| L1: Provenance generated automatically | NOT MET | No provenance attestation for any artifact |
| **L2: Hosted build** | NOT MET | No CI/CD; all execution is local |
| L2: Authenticated provenance | NOT MET | No signing of artifacts or provenance |
| **L3: Hardened builds** | NOT MET | No build isolation; scripts run with full user privileges |
| L3: Provenance non-falsifiable | NOT MET | -- |
| **L4: Two-party review** | NOT MET | No branch protection; no required reviews |
| L4: Hermetic, reproducible builds | NOT MET | -- |

**Assessment: SLSA Level 0 (L0)** -- The project has no supply chain security guarantees. Builds are entirely manual, unattested, and unreproducible.

---

## 6. Third-Party Model Supply Chain

### ML Model Files (referenced in CLAUDE.md)

| Model | Path (relative to ComfyUI dir) | Hash Verified? | Source Pinned? |
|-------|-------------------------------|----------------|----------------|
| wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors | `models/diffusion_models/` | NO | NO |
| wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors | `models/diffusion_models/` | NO | NO |
| wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors | `models/loras/` | NO | NO |
| umt5_xxl_fp8_e4m3fn_scaled.safetensors | `models/text_encoders/` | NO | NO |
| clip_l.safetensors | `models/text_encoders/` | NO | NO |
| wan_2.1_vae.safetensors | `models/vae/` | NO | NO |

**Risks**:
- No SHA-256 checksums recorded for any model file.
- No download URLs or Hugging Face model card references documented for provenance.
- Model files are referenced by filename only in CLAUDE.md and workflow JSONs -- a swapped file with the same name would be silently accepted.
- The `.safetensors` format does mitigate arbitrary code execution risk compared to legacy serialization formats, but does not prevent model poisoning or backdoor attacks.
- No model scanning tools (e.g., ModelScan) are used.

### ComfyUI Custom Node Supply Chain

| Risk | Severity |
|------|----------|
| `setup_comfyui_nodes.py` clones from any GitHub URL in `extension-node-map.json` | HIGH |
| No commit pinning -- always clones HEAD of default branch | HIGH |
| Cloned repos may contain `install.py` or `requirements.txt` that pip-install arbitrary packages | HIGH |
| ComfyUI Manager's `extension-node-map.json` is itself unverified | MEDIUM |
| `install_via_manager()` sends POST to local API without authentication | LOW |

---

## 7. n8n Workflow Integrity

### Workflow Tampering Risks

| Finding | Severity |
|---------|----------|
| n8n workflow JSONs stored as plain JSON in git -- no signing or integrity verification | MEDIUM |
| Workflows contain Code nodes with arbitrary JavaScript that executes with `NODE_FUNCTION_ALLOW_BUILTIN=*` | HIGH |
| n8n startup flags grant Code nodes access to `fs`, `child_process`, `http`, `https` -- full system access | HIGH |
| No workflow review process -- workflows are committed directly to main | MEDIUM |
| `update_workflow_paths.py` programmatically rewrites workflow JSONs -- a compromised script could inject malicious code nodes | HIGH |

### n8n Runtime Security Posture

| Setting | Value | Risk |
|---------|-------|------|
| `NODE_FUNCTION_ALLOW_BUILTIN` | `*` (all) | HIGH -- Code nodes can read/write filesystem, spawn processes |
| `NODE_FUNCTION_ALLOW_EXTERNAL` | `*` (all) | HIGH -- Code nodes can load any npm package |
| `N8N_RUNNERS_TASK_TIMEOUT` | `28800` (8 hrs) | MEDIUM -- Long-running tasks harder to detect if compromised |
| ComfyUI API | `http://127.0.0.1:8188` (no auth) | MEDIUM -- Any local process can submit prompts |
| Ollama API | `http://127.0.0.1:11434` (no auth) | LOW -- Local LLM, no sensitive data |

---

## Risk Matrix

| ID | Risk | Likelihood | Impact | Severity | Mitigation Status |
|----|------|-----------|--------|----------|-------------------|
| R1 | n8n API key leaked via committed worktree files | HIGH | HIGH | **CRITICAL** | NONE -- key is in plaintext in multiple files |
| R2 | Dependency confusion / malicious ComfyUI node install | MEDIUM | HIGH | **HIGH** | NONE -- no pinning, no verification |
| R3 | Model file substitution (poisoned weights) | LOW | HIGH | **HIGH** | NONE -- no hash verification |
| R4 | Malicious code injection via workflow JSON tampering | MEDIUM | HIGH | **HIGH** | NONE -- no signing, no review gates |
| R5 | Unreproducible builds due to missing lockfiles | HIGH | MEDIUM | **HIGH** | NONE -- no lockfiles of any kind |
| R6 | Force-push to main destroying history | MEDIUM | MEDIUM | **MEDIUM** | NONE -- no branch protection |
| R7 | n8n Code nodes with unrestricted system access | LOW | HIGH | **MEDIUM** | PARTIAL -- local-only deployment mitigates remote exploitation |
| R8 | No automated security scanning | HIGH | MEDIUM | **MEDIUM** | NONE -- no CI/CD |
| R9 | Missing .gitignore causes accidental secret commits | HIGH | HIGH | **HIGH** | NONE -- no .gitignore at root |
| R10 | ComfyUI custom node post-install scripts run arbitrary code | MEDIUM | HIGH | **HIGH** | NONE -- no sandboxing |

---

## Framework Compliance

### SLSA (Supply-chain Levels for Software Artifacts) v1.0

| Requirement | Level | Status |
|-------------|-------|--------|
| Source version controlled | L1 | MET (git + GitHub) |
| Build scripted (not manual) | L1 | NOT MET |
| Provenance generated automatically | L1 | NOT MET |
| Build service (hosted, not local) | L2 | NOT MET |
| Provenance authenticated | L2 | NOT MET |
| Build isolated / hermetic | L3 | NOT MET |
| Provenance non-falsifiable | L3 | NOT MET |
| Two-party source review | L4 | NOT MET |
| Hermetic, reproducible builds | L4 | NOT MET |

**Achieved Level: L0**

### NIST SP 800-218A (Secure Software Development Framework)

| Practice | Status | Gap |
|----------|--------|-----|
| PO.1: Define security requirements | NOT MET | No security policy or requirements documented |
| PS.1: Protect all forms of code | PARTIAL | Code in git, but no branch protection, no signing |
| PS.2: Verify third-party components | NOT MET | No dependency verification, no SBOM |
| PS.3: Configure build environments securely | NOT MET | n8n runs with `ALLOW_BUILTIN=*`, no build isolation |
| PW.4: Reuse existing well-secured components | PARTIAL | Uses established tools (ComfyUI, n8n) but without pinning |
| PW.6: Configure compilation/build/packaging | NOT MET | No build process defined |
| PW.7: Review and analyze human-readable code | NOT MET | No code review requirement |
| PW.9: Test executable code | NOT MET | No test suite or test automation |
| RV.1: Identify and confirm vulnerabilities | NOT MET | No vulnerability scanning |
| RV.3: Analyze vulnerabilities to determine root cause | NOT MET | No incident response process |

### OWASP Top 10 CI/CD Security Risks (2023)

| Risk | Applicability | Status |
|------|--------------|--------|
| CICD-SEC-1: Insufficient Flow Control | HIGH | No branch protection, no required reviews |
| CICD-SEC-2: Inadequate Identity and Access Management | MEDIUM | Public repo, no contributor access controls documented |
| CICD-SEC-3: Dependency Chain Abuse | HIGH | No lockfiles, no pinning, no SBOM |
| CICD-SEC-4: Poisoned Pipeline Execution | N/A | No CI/CD pipeline exists |
| CICD-SEC-5: Insufficient PBAC | N/A | No pipeline exists |
| CICD-SEC-6: Insufficient Credential Hygiene | HIGH | API keys in plaintext in worktree files |
| CICD-SEC-7: Insecure System Configuration | HIGH | n8n `ALLOW_BUILTIN=*`, ComfyUI API unauthenticated |
| CICD-SEC-8: Ungoverned Usage of 3rd Party Services | MEDIUM | ComfyUI Manager, custom node repos unverified |
| CICD-SEC-9: Improper Artifact Integrity Validation | HIGH | No artifact signing, no model hash verification |
| CICD-SEC-10: Insufficient Logging and Visibility | MEDIUM | No centralized logging or audit trail |

---

## Recommendations (Prioritized)

### Immediate (P0 -- this week)

1. **Rotate the n8n API key** -- the JWT is exposed in multiple worktree settings files.
2. **Create a `.gitignore`** at project root that excludes:
   - `.claude/` (worktree settings with credentials)
   - `*.env`
   - `node_modules/`
   - Any credential files
3. **Audit untracked files** before any commit -- `n8n/.claude/` directory contains credentials.

### Short-term (P1 -- next 2 weeks)

4. **Enable branch protection** on `main` -- require PR reviews, prevent force-push.
5. **Create `requirements.txt`** for Python dependencies (even if empty, documents the intent).
6. **Record model file SHA-256 hashes** in a `models.sha256` or `Deck.json` manifest.
7. **Pin ComfyUI custom node versions** to specific git commits in a manifest file.

### Medium-term (P2 -- next month)

8. **Add a basic GitHub Actions workflow** for JSON linting and Python syntax checking.
9. **Generate an SBOM** (CycloneDX or SPDX format) listing all components.
10. **Add commit signing** (GPG or SSH) for all contributors.
11. **Restrict n8n Code node permissions** -- replace `NODE_FUNCTION_ALLOW_BUILTIN=*` with an explicit allowlist of needed modules.

### Long-term (P3 -- next quarter)

12. **Implement SLSA L1** -- automated build with provenance generation.
13. **Add model scanning** (e.g., ModelScan) to verify `.safetensors` files before use.
14. **Create a security policy** (`SECURITY.md`) with vulnerability reporting instructions.
15. **Implement workflow signing** for n8n JSONs to detect tampering.

---

## Appendix A: Files Examined

| File | Purpose |
|------|---------|
| `config.json` | Machine-specific configuration (paths, API endpoints) |
| `setup_comfyui_nodes.py` | ComfyUI custom node dependency checker/installer |
| `setup_n8n_nodes.py` | n8n community package checker/installer |
| `update_workflow_paths.py` | Migrates n8n workflows to use config.json |
| `.github/ISSUE_TEMPLATE/bug_report.md` | GitHub issue template |
| `.github/ISSUE_TEMPLATE/feature_request.md` | GitHub issue template |
| `CLAUDE.md` | Project instructions and architecture documentation |
| `n8n/*.json` (18 files) | n8n workflow definitions |
| `ComfyUI/*.json` (8 files) | ComfyUI workflow definitions |
| `n8n/.claude/worktrees/*/settings.local.json` | Worktree settings (contain credentials) |

## Appendix B: Positive Findings

- Python scripts use **only stdlib modules** -- no third-party Python dependency risk in committed code.
- Model files use `.safetensors` format, which prevents arbitrary code execution on load.
- `config.json` centralizes machine-specific paths, reducing hardcoded path sprawl.
- The project has clear documentation (`CLAUDE.md`) of its architecture and dependencies.
- Dual licensing (AGPL v3 + CC BY 4.0) is properly documented.
- Local-only deployment model (ComfyUI and n8n on localhost) limits network attack surface.
