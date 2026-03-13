# Lessons Learned

Hard-won knowledge from building and debugging the TarotCardProject. Each entry documents a real failure or insight, the root cause, and the fix — so no one has to rediscover these the hard way.

---

## ComfyUI

*Discovered by Claude Opus 4.6*

### WanImageToVideo does NOT accept an end image

**Symptom:** Interpolation workflow silently ignores the end frame; output is just forward extrapolation from the start image.

**Root cause:** `WanImageToVideo` only exposes a `start_image` input. There is no `end_image` parameter despite what the name might suggest.

**Fix:** Use `WanFirstLastFrameToVideo` instead. It accepts both `start_image` and `end_image` with the same interface and works with the same Wan 2.2 I2V model.

---

### DualCLIPLoader does not support type "wan"

**Symptom:** ComfyUI returns an error when loading a Wan workflow that uses DualCLIPLoader.

**Root cause:** DualCLIPLoader's valid types are: sdxl, sd3, flux, hunyuan_video, hidream, hunyuan_image, hunyuan_video_15, kandinsky5, kandinsky5_image, ltxv, newbie. The "wan" type is not among them.

**Fix:** Use `CLIPLoader` (single) with type "wan". Wan only needs one text encoder (umt5_xxl), not two.

---

### AnimateDiff is not installed — don't reference it

**Symptom:** Workflows referencing AnimateDiff nodes fail to load.

**Root cause:** The AnimateDiff custom node pack (ComfyUI-AnimateDiff-Evolved) was never installed. Any workflow using its nodes will break.

**Fix:** Never use AnimateDiff nodes. Use Wan 2.2 I2V pipelines for video generation instead.

---

### GUI JSON vs API JSON — two different formats

**Symptom:** Copying a workflow from the ComfyUI GUI and pasting it into an n8n HTTP Request body fails, or vice versa.

**Root cause:** ComfyUI has two JSON formats:
- **GUI format:** `nodes[]` array with integer IDs, `links[]` array with `[linkId, srcNodeId, srcSlot, dstNodeId, dstSlot, type]`, and `widgets_values` arrays.
- **API format:** A `prompt` object with string node IDs (`"1"`, `"2"`, ...), each containing `class_type` and `inputs` where connections are `["otherNodeId", slotIndex]`.

**Fix:** Know which format you need. n8n HTTP bodies use API format. Files in the `ComfyUI/` directory use GUI format. Converting between them requires mapping node IDs, wiring links, and extracting widget values into inputs.

---

### FramePack F1-T2V and FramePack HY are incompatible

**Symptom:** Trying to connect outputs from one FramePack variant to inputs of the other fails with type mismatch errors.

**Root cause:** F1-T2V produces `FramePackMODEL` type; HY uses `FP_DIFFUSERS_PIPELINE`. They are completely separate type systems.

**Fix:** Pick one and stick with it. Do not mix nodes from the two packs.

---

### Card back filename is IMAGE_Deck_Back.png

**Symptom:** Workflows can't find the card back image.

**Root cause:** The file is named `IMAGE_Deck_Back.png`, not `CardBack.png` or `card_back.png`.

**Fix:** Always reference `IMAGE_Deck_Back.png`. The bundled data directory includes this file.

---

### last_node_id and last_link_id must match actual content

**Symptom:** ComfyUI silently creates duplicate IDs or refuses to add new nodes/links in the GUI.

**Root cause:** The `last_node_id` and `last_link_id` fields in GUI workflow JSON must be >= the maximum ID actually used in the nodes and links arrays. If they're too low, ComfyUI may assign colliding IDs.

**Fix:** After editing workflow JSON by hand, verify with `validate_comfyui.py`. It checks that these counters are correct.

---

### Some nodes have null link arrays

**Symptom:** Validation scripts crash with `TypeError: 'NoneType' is not iterable` when iterating output links.

**Root cause:** ComfyUI stores unconnected outputs as `"links": null` rather than `"links": []`.

**Fix:** Always use `(out.get('links') or [])` instead of `out.get('links', [])`. The latter still returns `null` when the key exists with a null value.

---

## n8n

*Discovered by Claude Opus 4.6*

### require('axios') crashes the task runner

**Symptom:** Any Code node that calls `require('axios')` fails with a generic "Node execution failed" error in ~150ms. No useful stack trace.

**Root cause:** n8n's task runner calls `preventPrototypePollution()` at startup, which freezes `FormData.prototype` via `Object.freeze()`. When axios loads its bundled `form-data` dependency, it tries to set `FormData.prototype.toString`, which throws a TypeError. This crashes the entire task runner process.

**Fix:** Use Node.js built-in `require('http')` / `require('https')` instead. They are unaffected by the frozen prototypes. See the `httpRequest` helper pattern in CLAUDE.md.

---

### fetch() and new URL() are not available in Code nodes

**Symptom:** `fetch is not defined` or `URL is not defined` errors.

**Root cause:** The n8n Code node sandbox does not expose `fetch()` as a global, and `URL` is not in the vm context's `getNativeVariables()`.

**Fix:** Use `require('http')` for HTTP calls. Parse URLs with regex or `require('url')` (requires `NODE_FUNCTION_ALLOW_BUILTIN=*`).

---

### SplitInBatches loses enriched data on the "done" output

**Symptom:** The stage after a SplitInBatches loop receives incomplete items — fields added during the loop (like `SavedFilename`, `SavedPath`) are missing.

**Root cause:** The "done" output of SplitInBatches sends the **original** input items, not the items that were enriched during each iteration of the loop.

**Fix:** Don't use SplitInBatches for ComfyUI submit-then-poll workflows. Use a single Code node that internally loops over all jobs, submits each, polls until complete, and returns all results at once.

---

### NODE_FUNCTION_ALLOW_BUILTIN must be set for require() to work

**Symptom:** `Module 'http' is disallowed` or `Module 'fs' is disallowed` errors in Code nodes.

**Root cause:** By default, n8n restricts which built-in modules Code nodes can import.

**Fix:** Start n8n with these environment variables:
```
NODE_FUNCTION_ALLOW_BUILTIN=*
NODE_FUNCTION_ALLOW_EXTERNAL=*
N8N_RUNNERS_TASK_TIMEOUT=28800
```

**Gotcha:** On Windows, `set FOO='bar'` includes the quotes in the value. Use `set FOO=bar` without quotes.

---

### Default task timeout is 300 seconds — far too short

**Symptom:** Long-running Code nodes (ComfyUI generation batches) are killed mid-execution with no clear error.

**Root cause:** `N8N_RUNNERS_TASK_TIMEOUT` defaults to 300 seconds. Wan 2.2 I2V (14B fp8) on 6 GB VRAM takes 10-30 minutes per clip. A batch of 8 clips can take 4+ hours.

**Fix:** Set `N8N_RUNNERS_TASK_TIMEOUT=28800` (8 hours) before starting n8n.

---

### Execute Command node is unavailable in n8n 2.7.5

**Symptom:** Importing a workflow with `n8n-nodes-base.executeCommand` fails with "unrecognized node type."

**Fix:** Replace with a Code node using `require('child_process')`. Requires `NODE_FUNCTION_ALLOW_BUILTIN=*`.

---

## Project Setup

*Discovered by Claude Opus 4.6*

### Three different slash conventions in workflow files

**Symptom:** Path replacement misses some occurrences, leaving stale paths in workflow files.

**Root cause:** Paths appear in three forms across n8n and ComfyUI JSON files:
1. Forward slashes: `D:/data`
2. Double-escaped backslashes (JSON-encoded): `D:\\\\data`
3. Single backslashes (raw widget values): `D:\\data`

**Fix:** `setup.py`'s `replace_in_text()` handles all three variants by generating the backslash forms from the forward-slash canonical path and replacing each independently.

---

### Bundled data files must be seeded, not just referenced

**Symptom:** A fresh clone can't run any workflow because `Deck.json`, spreadsheets, and card images don't exist in the external data directory.

**Root cause:** The project git repo contains template/default data files, but workflows reference them in an external data directory (e.g., `D:/data/`). A new user's external directory is empty.

**Fix:** `setup.py` seeds the external data directory by copying bundled files from `data/` to the configured data path, skipping files that already exist (so manual edits aren't overwritten).

---

### Make_Deck_Front_Transparent.json contains n8n template expressions

**Symptom:** JSON parsers choke on `{{ $json.someField }}` inside what should be valid JSON.

**Root cause:** Some ComfyUI workflow JSONs in the project embed n8n template expressions (`{{ ... }}`) as placeholder values. These are valid in n8n's context but invalid JSON.

**Fix:** `setup_comfyui_nodes.py` preprocesses JSON by stripping `{{ ... }}` expressions before parsing. `validate_comfyui.py` gracefully skips files with invalid JSON. If you need to parse these files, strip templates first.

---

## General Principles

*Discovered by Claude Opus 4.6*

### Deck.json is the single source of truth

Every deck-specific value — prompts, negative prompts, model names, dimensions, sampler settings, output paths — belongs in `Deck.json`. Nothing deck-specific should be hardcoded in n8n workflows. This means any contributor can change the artistic direction by editing one JSON file without touching workflow logic.

### Safe defaults prevent hard failures

Optional Deck.json sections (`Models`, `Samplers`) have fallback values in Code nodes:
```javascript
const models = deck.Models || {};
const checkpoint = models.KeyframeCheckpoint || 'dreamshaper_8.safetensors';
```
A deck author only needs to fill in `Assets`, `Geometries`, and `Prompts`.

### Validate early, validate often

Run `python validate_comfyui.py` after any manual edit to ComfyUI workflow JSON. It catches link/node mismatches, stale IDs, and structural errors that ComfyUI would silently mishandle.

Run `python setup_comfyui_nodes.py` to verify all required custom node packages are installed before attempting to run workflows.

---

## Process & Methodology

*Contributed by Justice (project lead)*

### Decompose into smaller, focused projects

Large monolithic projects exhaust AI context windows quickly. Break work into smaller projects scoped to individual functionality — one for image generation, one for narration, one for video interpolation, etc. This gives the AI more room to think within each context and reduces the chance of losing important details to context compression.

### Create reusable skills for recurring patterns

When a design principle or workflow pattern proves useful, codify it as a Claude Code skill so it can be applied consistently across future projects. Examples: the Deck.json schema convention, the ComfyUI submit-then-poll Code node pattern, the safe-defaults fallback pattern. Skills compound — investing time to formalize them now saves multiples of that time later.

### Add attribution to every AI-generated artifact

Every artifact produced with AI assistance should carry attribution metadata — which model, which version, what role the AI played (generated, assisted, reviewed). This is not just good practice; it is preparation for evolving AI transparency regulations worldwide. Embed attribution in file headers, commit messages (Co-Authored-By), and metadata fields where formats support it. Start now while it's easy, not later when it's a retrofit.

### Research and create certification-readiness artifacts

As AI-generated content faces increasing regulatory scrutiny, proactively create the documentation artifacts needed for future certification. This includes provenance records, model cards for each AI model used, decision logs explaining why specific models were chosen, and audit trails of human review steps. Research what frameworks (EU AI Act, NIST AI RMF, ISO/IEC 42001) may apply and create skills that produce the required documentation as a natural byproduct of the workflow.

### Integrate AI-assisted coding with Obsidian for cross-project knowledge

Use Obsidian as a cross-project knowledge base that bridges what individual AI coding sessions learn. Lessons learned, architectural decisions, debugging breakthroughs, and design patterns should flow from project-specific files (like this one) into a shared Obsidian vault with bidirectional links. This creates a persistent, searchable knowledge graph that any future AI session can reference — turning isolated project insights into organizational memory that survives across tools, models, and team members.
