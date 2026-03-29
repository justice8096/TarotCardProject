# SAST/DAST Security Scan Report

## TarotCardProject

**Date**: 2026-03-29
**Commit**: f55bcb8
**Branch**: claude/focus-upright-blend-stills
**Scanner**: Manual SAST/DAST review (Python scripts, n8n workflow JSONs, ComfyUI workflow JSONs, config files)
**Scope**: 3 Python scripts, 1 config JSON, 17 n8n workflow JSONs (with embedded Code nodes), 6 ComfyUI workflow JSONs

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1     |
| HIGH     | 5     |
| MEDIUM   | 6     |
| LOW      | 4     |
| INFO     | 3     |
| **Total** | **19** |

---

## Findings by Severity

---

### CRITICAL

#### C-1: Hardcoded n8n API Key (JWT) Committed to Repository

- **CWE**: CWE-798 (Use of Hard-coded Credentials)
- **File**: `n8n/.claude/worktrees/festive-morse/.claude/settings.local.json` (lines 15, 26-29) and `n8n/.claude/worktrees/quirky-bassi/.claude/settings.local.json` (lines 5-13)
- **Also referenced**: `C:/Users/justi/.claude/projects/D--TarotCardProject/memory/n8n-api.md` (base64-encoded copy)
- **Snippet** (redacted):
  ```
  "X-N8N-API-KEY: eyJhbG...OJAc"
  ```
- **Impact**: A valid JWT for the n8n REST API (named `claude-temp`, never-expiring) is committed in multiple worktree settings files within the repository. Anyone with repository read access can authenticate as a full-privilege n8n user, import/export workflows, execute arbitrary workflows, and run arbitrary code on the host via Code nodes. The key also appears base64-encoded in the MEMORY.md file.
- **Remediation**:
  1. **Immediately rotate the API key** via n8n admin (delete `claude-temp`, create a new one).
  2. Add `n8n/.claude/` and `.claude/` directories to `.gitignore`.
  3. Store the API key in an environment variable (`N8N_API_KEY`) referenced at runtime, never in committed files.
  4. Run `git filter-branch` or `git-filter-repo` to scrub the key from git history, or treat the repo as compromised and force-rotate.

---

### HIGH

#### H-1: Command Injection via Unsanitized Shell Command Construction

- **CWE**: CWE-78 (OS Command Injection)
- **File**: `n8n/Generate Dealer Stop Motion.json`, node `sm0001-0012-4000-8000-000000000012` ("Copy Keyframes to ComfyUI Input") and node `sm0001-0019-4000-8000-000000000019` ("FFmpeg Concat Clips")
- **Snippet** (Copy node):
  ```
  copy "{{ ComfyUIOutputDir }}\\{{ $json.FrameAFilename }}" ...
  ```
- **Snippet** (FFmpeg node):
  ```
  mkdir "{{ ... }}" 2>nul & (for %f in ({{ $json.ClipPaths... }}) ...) > "{{ $json.ConcatListPath }}" && ffmpeg ...
  ```
- **Impact**: Filenames and paths from Deck.json (e.g., `FrameAFilename`, `ClipPaths`, `FinalOutput`) are interpolated directly into shell commands without sanitization. If a malicious Deck.json contains values with shell metacharacters, the commands execute arbitrary OS commands. The `executeCommand` node passes the entire string to the system shell.
- **Remediation**: Replace `executeCommand` nodes with Code nodes using `child_process.execFileSync()` (which does NOT invoke a shell) and pass arguments as an array. This is already the documented pattern in CLAUDE.md.

#### H-2: Command Injection in Python Fallback (Update Card JSONs from Spreadsheet)

- **CWE**: CWE-78 (OS Command Injection)
- **File**: `n8n/Update Card JSONs from Spreadsheet.json`, node `upd0001-0003-4000-8000-000000000003` ("Read Spreadsheet")
- **Snippet** (within jsCode):
  ```javascript
  const raw = execSync(
    `python3 "${tmpPy}" "${spreadsheetPath}" "${sheetName}"`,
    { encoding: 'utf8', maxBuffer: 20 * 1024 * 1024 }
  );
  ```
- **Impact**: `spreadsheetPath` and `sheetName` originate from `config.json` and the workflow's `Set Global Parameters` node. If an attacker can modify config.json or inject n8n parameters, they can inject shell metacharacters. The function invokes a shell to run the command.
- **Remediation**: Use `execFileSync('python3', [tmpPy, spreadsheetPath, sheetName], ...)` instead, which avoids shell interpretation entirely.

#### H-3: Command Injection in Generate Card Faces (Controllable Executable Path)

- **CWE**: CWE-78 (OS Command Injection)
- **File**: `n8n/Generate Card Faces.json`, node `gcf0001-0006-4000-8000-000000000006` ("Generate All Card Faces")
- **Snippet**:
  ```javascript
  const out = execFileSync(
    job.PythonExe,
    [scriptPath, dataPath],
    { encoding: 'utf8', timeout: 30000 }
  );
  ```
- **Impact**: The `PythonExe` path comes from the n8n Set node parameter. While `execFileSync` does not invoke a shell (mitigating metacharacter injection), the executable path itself (`job.PythonExe`) is user-controlled. An attacker who modifies the n8n workflow parameters could point `PythonExe` to a malicious binary.
- **Remediation**: Validate that `PythonExe` points to a known Python executable. Consider hardcoding or reading from config.json with allowlist validation.

#### H-4: Generate Between Upright Images -- Shell Command via ffmpeg

- **CWE**: CWE-78 (OS Command Injection)
- **File**: `n8n/Generate Between Upright Images.json`, Code node "Rotate All Images" (contains child_process usage with ffmpeg)
- **Snippet pattern**:
  ```javascript
  execSync(`"${job.FfmpegExe}" -i "${job.SourcePath}" -vf "transpose=1" "${job.OutputPath}"`)
  ```
- **Impact**: `FfmpegExe`, `SourcePath`, and `OutputPath` are interpolated into a shell command string. Malicious card names or paths with shell metacharacters could lead to arbitrary command execution.
- **Remediation**: Use `execFileSync(job.FfmpegExe, ['-i', job.SourcePath, '-vf', 'transpose=1', job.OutputPath])` to avoid shell interpretation.

#### H-5: Path Traversal via Unsanitized File Path Construction

- **CWE**: CWE-22 (Path Traversal)
- **File**: Multiple n8n workflows (Generate Card Faces, Generate Card Narrations, Update Card JSONs from Spreadsheet, Generate Narration Styles, FOCUST Upright Stills, FOCUS Upright Blend Stills)
- **Example** (Generate Card Faces, node `gcf0001-0005`):
  ```javascript
  const cardJsonPath = path.join(deckDir, cardRef.File).replace(/\\/g, '/');
  ```
- **Example** (Update Card JSONs, node `upd0001-0004`):
  ```javascript
  const filename = cardName.replace(/[ \/\\]+/g, '_') + '.json';
  const jsonPath = path.join(cardsDir, filename);
  ```
- **Impact**: Card file references from Deck.json (e.g., `cardRef.File`) are joined to directory paths without validating that the result stays within the expected directory tree. A Deck.json entry like `"File": "../../etc/passwd"` would read arbitrary files. Write operations (`fs.writeFileSync`) in Update Card JSONs and Narration Styles could overwrite arbitrary files.
- **Remediation**: After constructing the full path, validate it starts with the expected base directory:
  ```javascript
  const resolved = path.resolve(cardsDir, filename);
  if (!resolved.startsWith(path.resolve(cardsDir))) {
    throw new Error('Path traversal detected: ' + filename);
  }
  ```

---

### MEDIUM

#### M-1: Hardcoded Absolute Paths as Default Fallbacks

- **CWE**: CWE-1188 (Insecure Default Initialization of Resource)
- **Files**:
  - `update_workflow_paths.py`, line 9: `WORKTREE = "D:/TarotCardProject/n8n/.claude/worktrees/thirsty-austin/n8n"`
  - `config.json`: All paths hardcoded to `D:/` drives
  - Multiple n8n Set Global Parameters nodes: `D:/data/cards/Standard/Deck.json`, `D:/ComfyUI_windows_portable/...`
  - n8n Code nodes: `COMFYUI_INPUT = 'D:/ComfyUI_windows_portable/ComfyUI/input'` (Generate FOCUS Upright Blend Stills)
  - `n8n/Generate Full Tarot Images.json`, node `105`: `"value": "D:\\\\data\\\\Full_Images"`
- **Impact**: Paths are bound to a single machine's layout. On a different machine, workflows silently read/write wrong locations. The `update_workflow_paths.py` script itself has a hardcoded worktree path that won't work outside that specific worktree.
- **Remediation**: All machine-specific paths should come from `config.json` exclusively. The older workflows (Generate Card Tarot Images, Generate Full Tarot Images, Generate Pallette Tarot Images) still have hardcoded paths in HTTP body templates and should be migrated like the newer workflows.

#### M-2: Ollama Credential ID Committed in Workflow JSON

- **CWE**: CWE-200 (Exposure of Sensitive Information)
- **File**: `n8n/Add Meanings.json`, line 184-189
- **Snippet**:
  ```json
  "credentials": {
      "ollamaApi": {
          "id": "trj8oFkLILUiN2Pd",
          "name": "Ollama account"
      }
  }
  ```
- **Impact**: The n8n credential reference ID is exposed. While the actual secret is stored in n8n's encrypted credential store (not in this file), the ID leaks the existence and name of the credential, and could be used in API calls if the n8n API is accessible.
- **Remediation**: This is standard n8n workflow export behavior. Ensure the n8n API is not exposed beyond localhost. Consider using credential environment variable references instead.

#### M-3: Webhook IDs Committed in Workflow JSONs

- **CWE**: CWE-200 (Exposure of Sensitive Information)
- **Files**: `n8n/Generate Card Tarot Images.json` (line 75), `n8n/Generate Pallette Tarot Images.json` (line 75), `n8n/Generate Full Tarot Images.json` (line 182)
- **Snippet**:
  ```json
  "webhookId": "35b62bd1-5f8e-4077-9b4e-dcf43194cb40"
  ```
- **Impact**: Webhook IDs, if the n8n instance has webhook triggers exposed, could allow unauthorized workflow execution by external parties.
- **Remediation**: These Wait nodes generate webhook endpoints for internal callback. Ensure n8n is not exposed to the public internet. If it must be, add authentication to webhook triggers.

#### M-4: No TLS on Local Service Communication

- **CWE**: CWE-319 (Cleartext Transmission of Sensitive Information)
- **Files**: `config.json` (lines 19-20), all n8n workflows referencing `ComfyUIAPI` and `OllamaAPI`
- **Snippet**:
  ```json
  "ComfyUIAPI": "http://127.0.0.1:8188",
  "OllamaAPI":  "http://127.0.0.1:11434"
  ```
- **Impact**: All communication between n8n, ComfyUI, and Ollama uses plaintext HTTP. On a single machine (localhost), this is low risk. However, if services are moved to separate hosts or containers on a shared network, traffic (including prompts, images, and API responses) could be intercepted.
- **Remediation**: For localhost-only deployment, this is acceptable. Document that if services are split across machines, TLS must be enabled.

#### M-5: Temporary File Written to World-Readable Location

- **CWE**: CWE-377 (Insecure Temporary File)
- **File**: `n8n/Update Card JSONs from Spreadsheet.json`, node `upd0001-0003` ("Read Spreadsheet")
- **Snippet**:
  ```javascript
  const tmpPy = 'C:/Windows/Temp/_n8n_read_ods.py';
  fs.writeFileSync(tmpPy, pyScript, 'utf8');
  ```
- **Impact**: A Python script is written to `C:\Windows\Temp\` with a predictable filename. Another user or process on the same machine could replace the file between write and execution (TOCTOU race condition), achieving code execution as the n8n service user.
- **Remediation**: Use `os.tmpdir()` with `fs.mkdtempSync()` to create a unique temporary directory, or use `crypto.randomUUID()` in the filename.

#### M-6: require('axios') Used in Code Nodes Despite Known Incompatibility

- **CWE**: CWE-754 (Improper Check for Exceptional Conditions)
- **File**: `n8n/Generate Card Narrations.json`, node `nar0001-0006` ("Generate All Narrations") and `n8n/Generate Narration Styles.json`, node `gns0001-0004` ("Generate Narration Styles")
- **Snippet**:
  ```javascript
  const axios = require('axios');
  ```
- **Impact**: Per CLAUDE.md documentation, `require('axios')` crashes the n8n task runner due to `preventPrototypePollution()` freezing `FormData.prototype`. These nodes will fail at runtime with a generic "Node execution failed" error. While not a security vulnerability per se, it causes denial of service for these workflows and masks actual errors.
- **Remediation**: Replace `require('axios')` with the `require('http')`/`require('https')` pattern documented in CLAUDE.md.

---

### LOW

#### L-1: Predictable Random Seed in ComfyUI Submissions

- **CWE**: CWE-330 (Use of Insufficiently Random Values)
- **Files**: `n8n/Generate Dealer Stop Motion.json`, nodes `sm0001-0005` and `sm0001-0013`
- **Snippet**:
  ```
  "seed": {{ Math.floor(Math.random() * 999999999) }}
  ```
- **Impact**: `Math.random()` is not cryptographically secure. For image generation seeds this is acceptable (reproducibility is often desired), but the range is limited to ~30 bits of entropy.
- **Remediation**: No action needed for image generation seeds. If seed confidentiality matters, use `crypto.randomInt()`.

#### L-2: Git Clone of Arbitrary URLs

- **CWE**: CWE-829 (Inclusion of Functionality from Untrusted Control Sphere)
- **File**: `setup_comfyui_nodes.py`, line 273-287 (`install_via_git`)
- **Snippet**:
  ```python
  result = subprocess.run(
      ["git", "clone", github_url],
      cwd=str(cn_dir),
      capture_output=True,
      text=True,
  )
  ```
- **Impact**: The `github_url` comes from `extension-node-map.json` (ComfyUI Manager registry). If that registry is compromised or contains a malicious URL, arbitrary code could be cloned and potentially executed.
- **Remediation**: Validate that URLs match `https://github.com/` pattern before cloning. Consider pinning known-good commits.

#### L-3: File Overwrite Without Backup

- **CWE**: CWE-367 (TOCTOU Race Condition)
- **Files**: Multiple n8n Code nodes that do `fs.writeFileSync(cardFilePath, ...)` -- Generate Narration Styles, Update Card JSONs, FOCUST Upright Stills, FOCUS Upright Blend Stills
- **Impact**: Card JSON files are read, modified in memory, and written back without creating a backup or using atomic write (write-to-temp + rename). A crash during write could corrupt the file. Concurrent workflow executions could cause lost updates.
- **Remediation**: Write to a temporary file first, then rename:
  ```javascript
  const tmpPath = jsonPath + '.tmp';
  fs.writeFileSync(tmpPath, content);
  fs.renameSync(tmpPath, jsonPath);
  ```

#### L-4: HTTP Request to ComfyUI Manager Without Authentication

- **CWE**: CWE-306 (Missing Authentication for Critical Function)
- **File**: `setup_comfyui_nodes.py`, line 257-270 (`install_via_manager`)
- **Snippet**:
  ```python
  req = urllib.request.Request(
      manager_url.rstrip("/") + "/customnode/install",
      data=payload,
      headers={"Content-Type": "application/json"},
      method="POST",
  )
  ```
- **Impact**: The ComfyUI Manager install endpoint is called without authentication. If ComfyUI is exposed beyond localhost, anyone could install arbitrary custom nodes.
- **Remediation**: Ensure ComfyUI and its Manager API are bound to 127.0.0.1 only.

---

### INFO

#### I-1: n8n Startup Requires Permissive Environment Flags

- **File**: CLAUDE.md (documented), runtime configuration
- **Detail**: `NODE_FUNCTION_ALLOW_BUILTIN=*` and `NODE_FUNCTION_ALLOW_EXTERNAL=*` disable n8n's sandbox restrictions for Code nodes. This is required for the project to function but removes a layer of defense-in-depth.
- **Note**: This is a conscious design tradeoff documented in CLAUDE.md. Ensure n8n is not exposed to untrusted users.

#### I-2: update_workflow_paths.py Targets a Specific Worktree

- **File**: `update_workflow_paths.py`, line 9
- **Detail**: `WORKTREE = "D:/TarotCardProject/n8n/.claude/worktrees/thirsty-austin/n8n"` is hardcoded to a specific Claude Code worktree that may no longer exist. Running the script will fail or modify the wrong files.
- **Note**: This appears to be a one-shot migration script. Consider parameterizing the target directory.

#### I-3: Static KSampler Seeds in ComfyUI Workflows

- **Files**: `ComfyUI/Card_Dealer_Interpolate.json`, `ComfyUI/Card_Dealer_Keyframe.json`, `n8n/Generate Card Tarot Images.json`, `n8n/Generate Full Tarot Images.json`
- **Detail**: Several ComfyUI workflow templates contain fixed seed values (e.g., `1118877715456453`, `281470000745471`). These produce deterministic outputs, which may be intentional for reproducibility but limits output diversity.
- **Note**: Informational only. Use random seeds if output variation is desired.

---

## Files Reviewed (No Findings)

The following files were reviewed and contained no security issues:

- `ComfyUI/Card_Dealer_Interpolate.json` -- pure ComfyUI node graph, no code execution
- `ComfyUI/Card_Dealer_Keyframe.json` -- pure ComfyUI node graph
- `ComfyUI/Make_Images_For_Card.json` -- pure ComfyUI node graph
- `ComfyUI/Change_Card_To_Pallette.json` -- pure ComfyUI node graph
- `ComfyUI/Make_Deck_Front_Transparent.json` -- ComfyUI API format with n8n template expressions (no code execution)
- `ComfyUI/Make_Symmetric_Card.json` -- pure ComfyUI node graph
- `n8n/Generate Focus Upright Stills.json` -- uses Set node parameters only, no Code nodes with shell access
- `n8n/Generate FOCUST Reversed Stills - All Cards.json` -- sharp-based image processing, no shell commands

---

## Recommendations Summary

### Immediate Actions (Critical/High)

1. **Rotate the n8n API key** and scrub it from git history.
2. **Add `.claude/` to `.gitignore`** to prevent worktree settings (which may contain secrets) from being committed.
3. **Replace all `executeCommand` nodes** with Code nodes using `execFileSync()` (array arguments, no shell).
4. **Add path traversal guards** to all file read/write operations that construct paths from Deck.json data.
5. **Fix shell-invoking calls** in Update Card JSONs to use `execFileSync` instead of `execSync`.

### Short-Term Actions (Medium)

6. Migrate remaining hardcoded-path workflows to use `config.json`.
7. Replace `C:\Windows\Temp` temp file usage with secure temp directory creation.
8. Replace `require('axios')` with `require('http')` pattern in narration workflows.

### Long-Term Actions (Low/Info)

9. Implement atomic file writes (write-to-temp + rename) for card JSON updates.
10. Add URL validation for git clone operations in `setup_comfyui_nodes.py`.
11. Document network security requirements if services are ever split across hosts.
