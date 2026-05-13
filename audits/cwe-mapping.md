# CWE Mapping Report

## TarotCardProject

**Date**: 2026-03-29
**Commit**: f55bcb8
**Branch**: claude/focus-upright-blend-stills
**Auditor**: Automated CWE Mapping (Claude)
**Scope**: All Python scripts, config.json, and embedded JavaScript in n8n workflow JSONs

---

## Executive Summary

This audit identified **14 unique CWE vulnerabilities** across the TarotCardProject codebase. The project is a local-only creative/media pipeline (tarot card image generation) with no public-facing services, no authentication layer, and no user input from untrusted sources. Most findings are low-to-medium severity given the local deployment context, but would become critical if the project were exposed to a network or multi-user environment.

**Total CWEs Found**: 14
**Critical**: 1
**High**: 3
**Medium**: 6
**Low**: 4

---

## Findings

### CWE-78: Improper Neutralization of Special Elements used in an OS Command (OS Command Injection)

**Severity**: High
**Files Affected**:
- `setup_comfyui_nodes.py` (line 276) -- subprocess.run with git clone and a URL from an external JSON map
- `n8n/Update Card JSONs from Spreadsheet.json` -- Read Spreadsheet node uses string-interpolated shell command
- `n8n/Generate Card Faces.json` -- Generate All Card Faces node uses child_process with dynamic arguments
- `n8n/Generate Between Upright Images.json` -- Rotate All Between Images node uses child_process with dynamic arguments
- `n8n/Generate FOCUST Reversed Stills - All Cards.json` -- Uses child_process with dynamic file paths

**Description**: Multiple locations run shell commands using values derived from JSON configuration files or workflow data. While some call sites use array-based argument passing (which avoids shell expansion), the Read Spreadsheet node uses string interpolation with file paths that could contain shell metacharacters. The git clone call passes URLs from an external JSON map directly to subprocess.

**Exploitation Context**: Requires attacker control over config.json, Deck.json, or extension-node-map.json -- realistic only in a supply-chain or shared-machine scenario.

| Framework | Mapping |
|-----------|---------|
| OWASP Top 10 2021 | A03:2021 - Injection |
| OWASP LLM Top 10 2025 | Not applicable (no LLM input pipeline) |
| NIST SP 800-53 | SI-10 (Information Input Validation) |
| EU AI Act | Not applicable |
| ISO 27001 | A.8.26 (Application security requirements) |
| SOC 2 | CC6.1 (Logical and Physical Access Controls) |
| MITRE ATT&CK | T1059.004 (Command and Scripting Interpreter: Unix Shell) |
| MITRE ATLAS | Not applicable |

---

### CWE-427: Uncontrolled Search Path Element

**Severity**: Medium
**Files Affected**:
- `n8n/Update Card JSONs from Spreadsheet.json` -- Read Spreadsheet node writes a Python script to a predictable temp path then runs it
- `n8n/Generate Card Faces.json` -- Embeds a Python PIL script, writes it to TempDir, and runs it

**Description**: Python scripts are written to predictable temporary file paths and then run. An attacker with write access to the temp directory could replace the script between the write and run calls (TOCTOU race condition). The python3 command is also resolved via PATH, which could be manipulated.

| Framework | Mapping |
|-----------|---------|
| OWASP Top 10 2021 | A08:2021 - Software and Data Integrity Failures |
| OWASP LLM Top 10 2025 | Not applicable |
| NIST SP 800-53 | SI-7 (Software, Firmware, and Information Integrity) |
| EU AI Act | Not applicable |
| ISO 27001 | A.8.9 (Configuration management) |
| SOC 2 | CC6.1 (Logical and Physical Access Controls) |
| MITRE ATT&CK | T1574.007 (Hijack Execution Flow: Path Interception by PATH Environment Variable) |
| MITRE ATLAS | Not applicable |

---

### CWE-94: Improper Control of Generation of Code (Code Injection)

**Severity**: Medium
**Files Affected**:
- `update_workflow_paths.py` (lines 38-41) -- set_to_code() function injects JavaScript code strings into n8n workflow JSON files
- `n8n/Update Card JSONs from Spreadsheet.json` -- Read Spreadsheet node dynamically generates and runs Python code

**Description**: update_workflow_paths.py programmatically constructs JavaScript code and embeds it into n8n workflow nodes. The Read Spreadsheet node writes a full Python script to a temp file and runs it. While the code is not derived from user input, the pattern of code generation and execution creates risk if any upstream data source is compromised.

| Framework | Mapping |
|-----------|---------|
| OWASP Top 10 2021 | A03:2021 - Injection |
| OWASP LLM Top 10 2025 | Not applicable |
| NIST SP 800-53 | SI-10 (Information Input Validation) |
| EU AI Act | Not applicable |
| ISO 27001 | A.8.26 (Application security requirements) |
| SOC 2 | CC6.1 (Logical and Physical Access Controls) |
| MITRE ATT&CK | T1059 (Command and Scripting Interpreter) |
| MITRE ATLAS | Not applicable |

---

### CWE-798: Use of Hard-coded Credentials / Paths

**Severity**: Medium
**Files Affected**:
- `config.json` (lines 5-21) -- All paths hardcoded to D:/data and D:/ComfyUI_windows_portable
- `update_workflow_paths.py` (line 9) -- WORKTREE hardcoded to a specific worktree path
- `update_workflow_paths.py` (line 10) -- CONFIG_EXPR hardcodes fallback path
- Multiple n8n workflow nodes -- Hardcoded fallback paths for D:/data/cards/Standard, D:/ComfyUI_windows_portable/ComfyUI/input
- `n8n/Generate Card Faces.json` -- Embedded Python has FONT_DIR = C:/Windows/Fonts
- `n8n/Update Card JSONs from Spreadsheet.json` -- tmpPy path hardcoded to C:/Windows/Temp

**Description**: Numerous hardcoded filesystem paths are scattered across config and workflow files. While config.json is the intended centralization mechanism, many Code nodes contain hardcoded fallback paths specific to the developer's Windows machine. This creates portability issues and implicitly trusts the filesystem layout.

| Framework | Mapping |
|-----------|---------|
| OWASP Top 10 2021 | A05:2021 - Security Misconfiguration |
| OWASP LLM Top 10 2025 | Not applicable |
| NIST SP 800-53 | CM-6 (Configuration Settings) |
| EU AI Act | Not applicable |
| ISO 27001 | A.8.9 (Configuration management) |
| SOC 2 | CC6.6 (System Boundaries) |
| MITRE ATT&CK | T1083 (File and Directory Discovery) |
| MITRE ATLAS | Not applicable |

---

### CWE-319: Cleartext Transmission of Sensitive Information

**Severity**: Medium
**Files Affected**:
- `config.json` (lines 19-20) -- ComfyUIAPI and OllamaAPI use HTTP
- `setup_comfyui_nodes.py` (lines 41-42) -- DEFAULT_API_URL and MANAGER_API_URL use HTTP
- `setup_n8n_nodes.py` (line 44) -- DEFAULT_API_URL uses HTTP
- All n8n workflow Code nodes that POST to ComfyUI API

**Description**: All API communications (ComfyUI, Ollama, n8n REST API) use plaintext HTTP. While currently all traffic is localhost, if any service were exposed beyond the loopback interface, prompt data, model parameters, and API responses would be transmitted unencrypted.

| Framework | Mapping |
|-----------|---------|
| OWASP Top 10 2021 | A02:2021 - Cryptographic Failures |
| OWASP LLM Top 10 2025 | LLM06:2025 - Excessive Agency |
| NIST SP 800-53 | SC-8 (Transmission Confidentiality and Integrity) |
| EU AI Act | Art. 15 (Accuracy, robustness and cybersecurity) |
| ISO 27001 | A.8.24 (Use of cryptography) |
| SOC 2 | CC6.7 (Transmission Security) |
| MITRE ATT&CK | T1040 (Network Sniffing) |
| MITRE ATLAS | AML.T0024 (Exfiltration via ML Inference API) |

---

### CWE-306: Missing Authentication for Critical Function

**Severity**: High
**Files Affected**:
- `setup_comfyui_nodes.py` (line 259) -- install_via_manager() POSTs to ComfyUI Manager API without authentication
- `setup_n8n_nodes.py` (line 114) -- fetch_installed_via_api() queries n8n REST API without authentication
- All n8n Code nodes that POST prompts to ComfyUI API /prompt endpoint
- `n8n/Generate Narration Styles.json` -- Generate Narration Styles node POSTs to Ollama API unauthenticated

**Description**: All local API endpoints (ComfyUI, Ollama, n8n) are accessed without any authentication tokens, API keys, or authorization headers. ComfyUI Manager's install endpoint allows installing arbitrary GitHub repositories, and the ComfyUI prompt endpoint allows running arbitrary generation workflows -- both without authentication.

| Framework | Mapping |
|-----------|---------|
| OWASP Top 10 2021 | A07:2021 - Identification and Authentication Failures |
| OWASP LLM Top 10 2025 | LLM06:2025 - Excessive Agency |
| NIST SP 800-53 | IA-2 (Identification and Authentication), AC-3 (Access Enforcement) |
| EU AI Act | Art. 15 (Accuracy, robustness and cybersecurity) |
| ISO 27001 | A.8.5 (Secure authentication) |
| SOC 2 | CC6.1 (Logical and Physical Access Controls) |
| MITRE ATT&CK | T1190 (Exploit Public-Facing Application) |
| MITRE ATLAS | AML.T0040 (ML Model Inference API Access) |

---

### CWE-22: Improper Limitation of a Pathname to a Restricted Directory (Path Traversal)

**Severity**: High
**Files Affected**:
- Multiple n8n Code nodes that construct file paths from Deck.json data:
  - `n8n/Generate Card Narrations.json` -- Build Narration Job List
  - `n8n/Generate Card Faces.json` -- Build Card Face Job List
  - `n8n/Generate Between Upright Images.json` -- Build Rotation Job List
  - `n8n/Generate Focus Upright Stills.json`
  - `n8n/Generate FOCUST Upright Stills.json` and All Cards variant
  - `n8n/Generate FOCUST Reversed Stills - All Cards.json`
  - `n8n/Update Card JSONs from Spreadsheet.json` -- Update Card JSONs node

**Description**: File paths are constructed by joining a base directory with filenames from Deck.json card references (e.g., cardRef.File). None of the Code nodes validate that the resulting path stays within the intended directory. A malicious Deck.json entry with path traversal sequences would allow reading or writing arbitrary files. The writeFileSync calls in multiple nodes also write to paths derived from Deck.json without validation.

| Framework | Mapping |
|-----------|---------|
| OWASP Top 10 2021 | A01:2021 - Broken Access Control |
| OWASP LLM Top 10 2025 | Not applicable |
| NIST SP 800-53 | AC-6 (Least Privilege), SI-10 (Information Input Validation) |
| EU AI Act | Not applicable |
| ISO 27001 | A.8.3 (Information access restriction) |
| SOC 2 | CC6.1 (Logical and Physical Access Controls) |
| MITRE ATT&CK | T1083 (File and Directory Discovery) |
| MITRE ATLAS | Not applicable |

---

### CWE-502: Deserialization of Untrusted Data

**Severity**: Medium
**Files Affected**:
- `setup_comfyui_nodes.py` (line 175) -- json.loads on ComfyUI Manager extension-node-map.json
- All n8n Code nodes that parse Deck.json and card JSON files via JSON.parse(fs.readFileSync(...))
- `n8n/Generate Dealer Stop Motion.json` -- Read Deck.json node

**Description**: Multiple locations parse JSON from files on disk without schema validation. The parsed data controls file paths, command arguments, and API request bodies. While JSON.parse itself is safe from code execution (unlike binary serialization formats like Python's marshalling or Java object streams), the parsed structure is trusted implicitly -- no field type checking, no schema enforcement, no bounds validation on numeric fields.

| Framework | Mapping |
|-----------|---------|
| OWASP Top 10 2021 | A08:2021 - Software and Data Integrity Failures |
| OWASP LLM Top 10 2025 | Not applicable |
| NIST SP 800-53 | SI-10 (Information Input Validation) |
| EU AI Act | Not applicable |
| ISO 27001 | A.8.26 (Application security requirements) |
| SOC 2 | CC7.2 (System Monitoring) |
| MITRE ATT&CK | T1059.007 (Command and Scripting Interpreter: JavaScript) |
| MITRE ATLAS | Not applicable |

---

### CWE-377: Insecure Temporary File

**Severity**: Low
**Files Affected**:
- `n8n/Update Card JSONs from Spreadsheet.json` -- Read Spreadsheet node writes to a fixed temp path
- `n8n/Generate Card Faces.json` -- Generate All Card Faces node writes Python script to TempDir

**Description**: Temporary files are created at fixed, predictable paths without unique naming (no mktemp equivalent). This allows TOCTOU race conditions and symlink attacks on multi-user systems.

| Framework | Mapping |
|-----------|---------|
| OWASP Top 10 2021 | A05:2021 - Security Misconfiguration |
| OWASP LLM Top 10 2025 | Not applicable |
| NIST SP 800-53 | SI-7 (Software, Firmware, and Information Integrity) |
| EU AI Act | Not applicable |
| ISO 27001 | A.8.10 (Information deletion) |
| SOC 2 | CC6.1 (Logical and Physical Access Controls) |
| MITRE ATT&CK | T1036.005 (Masquerading: Match Legitimate Name or Location) |
| MITRE ATLAS | Not applicable |

---

### CWE-209: Generation of Error Message Containing Sensitive Information

**Severity**: Low
**Files Affected**:
- `setup_comfyui_nodes.py` (line 285) -- Prints stderr from git clone (may contain credentials in URL)
- `n8n/Generate Card Narrations.json` -- Generate All Narrations node logs API response data which may contain server internals
- `n8n/Generate Narration Styles.json` -- Generate Narration Styles node logs raw Ollama response on parse failure
- Multiple n8n Code nodes -- Error messages include full filesystem paths

**Description**: Error handlers throughout the codebase include raw exception messages, filesystem paths, and API response bodies in log output. These could expose internal system structure to anyone viewing n8n execution logs.

| Framework | Mapping |
|-----------|---------|
| OWASP Top 10 2021 | A05:2021 - Security Misconfiguration |
| OWASP LLM Top 10 2025 | Not applicable |
| NIST SP 800-53 | SI-11 (Error Handling) |
| EU AI Act | Not applicable |
| ISO 27001 | A.8.15 (Logging) |
| SOC 2 | CC7.2 (System Monitoring) |
| MITRE ATT&CK | T1005 (Data from Local System) |
| MITRE ATLAS | Not applicable |

---

### CWE-400: Uncontrolled Resource Consumption

**Severity**: Low
**Files Affected**:
- `n8n/Generate Card Narrations.json` -- Generate All Narrations node polls for up to 240 attempts at 5 seconds each = 20 minutes per card
- `n8n/Generate Focus Upright Stills.json` -- Processes all cards in a single long-running Code node
- `n8n/Generate Dealer Stop Motion.json` -- Long polling loops in interpolation generation

**Description**: Multiple Code nodes run unbounded loops processing all cards sequentially in a single task. The n8n task timeout is set to 28800 seconds (8 hours). A deck with many cards or a stuck ComfyUI process could consume the n8n worker indefinitely. No circuit breaker or per-job timeout enforcement exists within the loops.

| Framework | Mapping |
|-----------|---------|
| OWASP Top 10 2021 | A05:2021 - Security Misconfiguration |
| OWASP LLM Top 10 2025 | LLM04:2025 - Data and Model Poisoning (resource exhaustion vector) |
| NIST SP 800-53 | SC-5 (Denial-of-Service Protection) |
| EU AI Act | Art. 15 (Accuracy, robustness and cybersecurity) |
| ISO 27001 | A.8.6 (Capacity management) |
| SOC 2 | CC7.2 (System Monitoring) |
| MITRE ATT&CK | T1499 (Endpoint Denial of Service) |
| MITRE ATLAS | AML.T0029 (Denial of ML Service) |

---

### CWE-732: Incorrect Permission Assignment for Critical Resource

**Severity**: Medium
**Files Affected**:
- `n8n/Generate Card Narrations.json` -- Build Narration Job List uses fs.mkdirSync with recursive: true
- `n8n/Generate FOCUST Upright Stills.json` -- writeFileSync updates card JSON files
- `n8n/Generate FOCUST Reversed Stills - All Cards.json` -- writeFileSync updates card JSON files
- `n8n/Generate Card Faces.json` -- fs.mkdirSync for temp directory

**Description**: Directories and files are created using default permissions (inheriting from parent or process umask). No explicit permission settings are applied to created directories or written files. Card JSON files containing deck metadata are written with default permissions, potentially allowing other local users to modify them.

| Framework | Mapping |
|-----------|---------|
| OWASP Top 10 2021 | A01:2021 - Broken Access Control |
| OWASP LLM Top 10 2025 | Not applicable |
| NIST SP 800-53 | AC-6 (Least Privilege) |
| EU AI Act | Not applicable |
| ISO 27001 | A.8.3 (Information access restriction) |
| SOC 2 | CC6.1 (Logical and Physical Access Controls) |
| MITRE ATT&CK | T1222 (File and Directory Permissions Modification) |
| MITRE ATLAS | Not applicable |

---

### CWE-1188: Initialization with Hard-Coded Network Resource Configuration

**Severity**: Low
**Files Affected**:
- `config.json` -- ComfyUIAPI and OllamaAPI use fixed localhost addresses with fixed ports
- `setup_comfyui_nodes.py` (line 41) -- DEFAULT_API_URL hardcoded
- `setup_n8n_nodes.py` (line 44) -- DEFAULT_API_URL hardcoded

**Description**: All network endpoints are hardcoded to localhost addresses with fixed ports. If port bindings change or services are containerized, the project fails silently. No service discovery, health checks, or configurable retry logic exists.

| Framework | Mapping |
|-----------|---------|
| OWASP Top 10 2021 | A05:2021 - Security Misconfiguration |
| OWASP LLM Top 10 2025 | Not applicable |
| NIST SP 800-53 | CM-6 (Configuration Settings) |
| EU AI Act | Not applicable |
| ISO 27001 | A.8.9 (Configuration management) |
| SOC 2 | CC6.6 (System Boundaries) |
| MITRE ATT&CK | T1571 (Non-Standard Port) |
| MITRE ATLAS | Not applicable |

---

### CWE-829: Inclusion of Functionality from Untrusted Control Sphere

**Severity**: Critical
**Files Affected**:
- `setup_comfyui_nodes.py` (lines 273-286) -- install_via_git() clones arbitrary GitHub repos into custom_nodes/
- `setup_comfyui_nodes.py` (lines 257-270) -- install_via_manager() triggers installation of arbitrary packages via ComfyUI Manager
- `n8n/Update Card JSONs from Spreadsheet.json` -- Read Spreadsheet node fallback runs pip install at runtime from within generated Python code

**Description**: The setup_comfyui_nodes.py script clones Git repositories listed in ComfyUI Manager's extension-node-map.json directly into the executable custom_nodes directory. The embedded Python in Read Spreadsheet runs pip install odfpy at runtime if the package is missing. Both patterns pull and run code from external sources (GitHub, PyPI) without integrity verification (no hash pinning, no signature checks).

| Framework | Mapping |
|-----------|---------|
| OWASP Top 10 2021 | A08:2021 - Software and Data Integrity Failures |
| OWASP LLM Top 10 2025 | LLM05:2025 - Improper Output Handling |
| NIST SP 800-53 | SA-12 (Supply Chain Protection), SI-7 (Software Integrity) |
| EU AI Act | Art. 15 (Accuracy, robustness and cybersecurity) |
| ISO 27001 | A.8.19 (Installation of software on operational systems) |
| SOC 2 | CC8.1 (Change Management) |
| MITRE ATT&CK | T1195.002 (Supply Chain Compromise: Compromise Software Supply Chain) |
| MITRE ATLAS | AML.T0010 (ML Supply Chain Compromise) |

---

## Aggregate CWE-to-Framework Mapping Table

| CWE | Name | OWASP 2021 | OWASP LLM 2025 | NIST 800-53 | EU AI Act | ISO 27001 | SOC 2 | ATT&CK | ATLAS |
|-----|------|------------|----------------|-------------|-----------|-----------|-------|--------|-------|
| CWE-78 | OS Command Injection | A03 | -- | SI-10 | -- | A.8.26 | CC6.1 | T1059.004 | -- |
| CWE-427 | Uncontrolled Search Path | A08 | -- | SI-7 | -- | A.8.9 | CC6.1 | T1574.007 | -- |
| CWE-94 | Code Injection | A03 | -- | SI-10 | -- | A.8.26 | CC6.1 | T1059 | -- |
| CWE-798 | Hard-coded Paths/Creds | A05 | -- | CM-6 | -- | A.8.9 | CC6.6 | T1083 | -- |
| CWE-319 | Cleartext Transmission | A02 | LLM06 | SC-8 | Art.15 | A.8.24 | CC6.7 | T1040 | AML.T0024 |
| CWE-306 | Missing Authentication | A07 | LLM06 | IA-2, AC-3 | Art.15 | A.8.5 | CC6.1 | T1190 | AML.T0040 |
| CWE-22 | Path Traversal | A01 | -- | AC-6, SI-10 | -- | A.8.3 | CC6.1 | T1083 | -- |
| CWE-502 | Untrusted Deserialization | A08 | -- | SI-10 | -- | A.8.26 | CC7.2 | T1059.007 | -- |
| CWE-377 | Insecure Temp File | A05 | -- | SI-7 | -- | A.8.10 | CC6.1 | T1036.005 | -- |
| CWE-209 | Sensitive Error Messages | A05 | -- | SI-11 | -- | A.8.15 | CC7.2 | T1005 | -- |
| CWE-400 | Resource Exhaustion | A05 | LLM04 | SC-5 | Art.15 | A.8.6 | CC7.2 | T1499 | AML.T0029 |
| CWE-732 | Incorrect Permissions | A01 | -- | AC-6 | -- | A.8.3 | CC6.1 | T1222 | -- |
| CWE-1188 | Hard-coded Network Config | A05 | -- | CM-6 | -- | A.8.9 | CC6.6 | T1571 | -- |
| CWE-829 | Untrusted Code Inclusion | A08 | LLM05 | SA-12, SI-7 | Art.15 | A.8.19 | CC8.1 | T1195.002 | AML.T0010 |

---

## Framework Coverage Matrix

| Framework | CWEs Mapped | Coverage | Key Controls Triggered |
|-----------|-------------|----------|----------------------|
| **OWASP Top 10 2021** | 14/14 | 100% | A01 (2), A02 (1), A03 (2), A05 (5), A07 (1), A08 (3) |
| **OWASP LLM Top 10 2025** | 4/14 | 29% | LLM04 (1), LLM05 (1), LLM06 (2) |
| **NIST SP 800-53** | 14/14 | 100% | SI-10 (4), SI-7 (3), AC-6 (2), CM-6 (2), SC-8 (1), SC-5 (1), SA-12 (1), IA-2 (1), AC-3 (1), SI-11 (1) |
| **EU AI Act** | 4/14 | 29% | Art. 15 (4) -- cybersecurity requirements |
| **ISO 27001** | 14/14 | 100% | A.8.x controls across 10 distinct sub-controls |
| **SOC 2** | 14/14 | 100% | CC6.1 (8), CC6.6 (2), CC6.7 (1), CC7.2 (3), CC8.1 (1) |
| **MITRE ATT&CK** | 14/14 | 100% | 12 distinct techniques across Execution, Persistence, Discovery, and Impact |
| **MITRE ATLAS** | 3/14 | 21% | AML.T0010 (1), AML.T0024 (1), AML.T0029 (1), AML.T0040 (1) |

---

## Framework-Specific Notes

### OWASP Top 10 2021
The most triggered category is **A05: Security Misconfiguration** (5 CWEs), consistent with a project that prioritizes rapid iteration over hardening. **A08: Software and Data Integrity Failures** (3 CWEs) reflects the supply-chain risks from untrusted code inclusion and unvalidated JSON deserialization.

### OWASP LLM Top 10 2025
Low mapping (29%) because this project uses LLMs (Ollama) only for metadata generation (narration styles), not as a core application logic layer. The LLM06 (Excessive Agency) findings relate to unauthenticated API access to AI inference endpoints.

### NIST SP 800-53
Full coverage. The most-cited control family is **SI (System and Information Integrity)** with 8 mappings, followed by **AC (Access Control)** with 3. This indicates the primary gap is input validation and integrity verification.

### EU AI Act
Only 4 CWEs map to the EU AI Act, all under **Article 15** (cybersecurity requirements for high-risk AI systems). The low mapping reflects that this project is a creative tool, not a high-risk AI system under the Act's classification. However, if the tarot reading system were used for decision-making affecting individuals, more articles would apply.

### ISO 27001
Full coverage across **Annex A.8** (Technology controls). The most triggered controls are A.8.26 (Application security requirements), A.8.9 (Configuration management), and A.8.3 (Information access restriction).

### SOC 2
Full coverage. **CC6.1 (Logical and Physical Access Controls)** is triggered by 8 CWEs, making access control the dominant gap area for SOC 2 readiness.

### MITRE ATT&CK
Full coverage across 12 distinct techniques. The most concerning technique is **T1195.002 (Supply Chain Compromise)** from the untrusted code inclusion pattern. The project's attack surface is primarily local execution rather than network exploitation.

### MITRE ATLAS
Low mapping (21%) with 3 CWEs, reflecting that while the project uses ML models (Wan 2.2, Orpheus TTS, Ollama), it does not expose ML inference as a service. The ML supply chain risk (AML.T0010) from ComfyUI custom node installation is the most significant ATLAS finding.

---

## Recommendations (Priority Order)

1. **[Critical]** Add integrity verification (hash pinning or GPG signatures) for git clone operations in setup_comfyui_nodes.py and remove runtime pip install from embedded Python scripts
2. **[High]** Replace string-interpolated shell command in Read Spreadsheet node with array-based argument passing
3. **[High]** Add path validation (canonicalize and verify prefix) for all path.join operations that use Deck.json data
4. **[High]** Add authentication headers or API keys to ComfyUI, Ollama, and n8n API calls
5. **[Medium]** Use unique temporary file names instead of fixed paths
6. **[Medium]** Add JSON schema validation for Deck.json and card JSON parsing
7. **[Medium]** Sanitize error messages to exclude full filesystem paths in production logging
8. **[Low]** Add per-job timeout enforcement within long-running Code node loops
9. **[Low]** Consider HTTPS for API endpoints if services may be exposed beyond localhost
