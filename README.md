<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->

# Tarot Card Project

A tarot card layout, spread and reader system. Differs from Rider-Waite by having more cards, and compatible with both the I-Ching balance model and the Tarot action model.

## Licensing

| What | License |
|------|---------|
| **Source code** (workflows, scripts, configs) | [GNU AGPL v3](LICENSE) — free to use and modify; all derivatives must also be open source |
| **Generated assets** (card images, animations) | [CC BY 4.0](LICENSE-ASSETS) — free to use, sell, or build on; attribution required |

## Tools Used

- [n8n](https://n8n.io) — orchestration and automation
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) — image and video generation
- [Perplexity](https://www.perplexity.ai) — research
- [Claude](https://claude.ai) — code co-generation
- [huggingFace](https://huggingface.co) — repository of AI models and associated tools
- [Ollama](https://ollama.com) — local small language model runtime and model repository
- TypeScript

---

## Directory Structure

```
config.json        Machine-specific path configuration (edit this when setting up a new machine)
CLAUDE.md          Project conventions and architecture notes
n8n/               n8n workflow JSONs
ComfyUI/           ComfyUI workflow JSONs
data/              Spreadsheet source files
Perplexity/        Research documents
```

---

## Setting Up on a New Machine

All machine-specific paths are stored in one place: **`config.json`** at the project root.

### 1. Edit config.json

Open `config.json` and update each path to match your machine:

```json
{
    "DataDir":             "D:/data",
    "CardsDir":            "D:/data/cards",
    "DefaultDeckDir":      "D:/data/cards/Standard",
    "DefaultDeckJsonPath": "D:/data/cards/Standard/Deck.json",
    "LegacyDeckJsonPath":  "D:/data/cards/Deck.json",

    "FullImagesDir":       "D:/data/Full_Images",
    "CardPartImagesDir":   "D:/data/Card_Part_Images",
    "ErrorsDir":           "D:/data/errors",

    "SpreadsheetPath":       "D:/data/TarotSpreadsheet2.ods",
    "LegacySpreadsheetPath": "D:/data/CardImages.ods",

    "ComfyUIDir": "D:/ComfyUI_windows_portable/ComfyUI",
    "ComfyUIAPI": "http://127.0.0.1:8188",
    "OllamaAPI":  "http://127.0.0.1:11434"
}
```

> Do **not** edit path values inside the n8n workflow nodes themselves. All 10 workflows read their paths from this file at runtime.

### 2. (Optional) Override the config file location

By default every workflow looks for `config.json` at `D:/TarotCardProject/config.json`. If you store the project at a different path, set the `TAROT_CONFIG` environment variable to the full path of your `config.json` before starting n8n:

```cmd
set TAROT_CONFIG=E:/MyProject/config.json
set NODE_FUNCTION_ALLOW_BUILTIN=* && set NODE_FUNCTION_ALLOW_EXTERNAL=* && set N8N_RUNNERS_TASK_TIMEOUT=28800 && n8n start
```

### 3. Start n8n

n8n requires several environment flags to allow file access and long-running tasks:

```cmd
set NODE_FUNCTION_ALLOW_BUILTIN=* && set NODE_FUNCTION_ALLOW_EXTERNAL=* && set N8N_RUNNERS_TASK_TIMEOUT=28800 && n8n start
```

| Flag | Purpose |
|------|---------|
| `NODE_FUNCTION_ALLOW_BUILTIN=*` | Allows `fs`, `path`, `child_process` in Code nodes |
| `NODE_FUNCTION_ALLOW_EXTERNAL=*` | Allows `axios` and other npm packages in Code nodes |
| `N8N_RUNNERS_TASK_TIMEOUT=28800` | 8-hour timeout for long image/video generation batches |

### 4. Import workflows into n8n

Import each JSON file from the `n8n/` folder into n8n. No edits are needed — paths are read from `config.json` automatically.

---

## How Path Configuration Works

Each n8n workflow starts with a **Set Global Parameters** Code node that:

1. Reads `config.json` from the path in `TAROT_CONFIG` (or the default location)
2. Exposes all paths as named fields (`DeckJsonPath`, `ComfyUIAPI`, etc.)
3. All downstream nodes reference these fields via n8n expressions like `$('Set Global Parameters').first().json.ComfyUIAPI`

This means the only file you ever need to change for a new machine is `config.json`.

### Adding a New Workflow

Follow the same pattern. Start your workflow with a Code node named **"Set Global Parameters"**:

```javascript
const fs = require('fs');
// ── Machine configuration ──────────────────────────────────────────────────────
// Edit config.json to change paths for your machine. Do not edit this node.
const CONFIG_PATH = process.env.TAROT_CONFIG || 'D:/TarotCardProject/config.json';
// ──────────────────────────────────────────────────────────────────────────────
const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));

return [{ json: {
    // Machine-specific (from config.json)
    DeckJsonPath: config.DefaultDeckJsonPath,
    ComfyUIAPI:   config.ComfyUIAPI,
    // Workflow-specific (hardcode here — not machine-specific)
    MyWorkflowParam: 'some-value',
} }];
```

Then reference values downstream with `$('Set Global Parameters').first().json.DeckJsonPath`.

### Re-running the Migration Script

If you need to re-apply path migration to newly added workflows, use `update_workflow_paths.py`:

```cmd
python update_workflow_paths.py
```

> Note: The script is not idempotent for workflows that insert a new node (workflows 5–10). Run it only on fresh workflow JSON files.

---

## Checking and Installing n8n Node Packages

`setup_n8n_nodes.py` scans every workflow JSON, identifies which npm packages they require, and checks whether any community packages need to be installed.

### Check only (default)

```cmd
python setup_n8n_nodes.py
```

Reports which packages are built-in vs. community, then for community packages checks installation status via the n8n REST API (falling back to a filesystem check if n8n is not running).

### Check and install missing packages

```cmd
python setup_n8n_nodes.py --install
```

Calls `n8n install <package>` for any community package that is not yet installed. Requires `n8n` to be on the system PATH.

### Options

| Flag | Default | Purpose |
|------|---------|---------|
| `--install` | off | Install missing community packages automatically |
| `--api-url <url>` | `http://localhost:5678` | n8n base URL for the REST API check |

### How package names are resolved

n8n node types follow the pattern `package.NodeClass` or `@scope/package.NodeClass`. The script strips the node-class suffix:

| Node type | Resolved package |
|-----------|-----------------|
| `n8n-nodes-base.code` | `n8n-nodes-base` (built-in) |
| `@n8n/n8n-nodes-langchain.ollama` | `@n8n/n8n-nodes-langchain` (built-in) |
| `n8n-nodes-mypkg.myNode` | `n8n-nodes-mypkg` (community — checked/installed) |

Built-in packages (`n8n-nodes-base`, `@n8n/n8n-nodes-langchain`, `@n8n/n8n-nodes-ai`) are always skipped — they ship with n8n and cannot be installed separately.

---

## Checking and Installing ComfyUI Custom Nodes

`setup_comfyui_nodes.py` scans every ComfyUI workflow JSON, identifies which custom node packages they require, and checks whether those packages are installed in your ComfyUI `custom_nodes/` directory.

### Check only (default)

```cmd
python setup_comfyui_nodes.py
```

Reports each custom node type as one of:
- `[OK]` — installed (found by URL, folder name, or Python file scan)
- `[!!]` — missing, with the GitHub URL to install it
- `[??]` — unknown (not in ComfyUI Manager's registry; may need manual investigation)

### Check and install missing packages

```cmd
python setup_comfyui_nodes.py --install
```

Tries ComfyUI Manager REST API first, falls back to `git clone`. Requires ComfyUI to be running for the API path, or `git` on PATH for the fallback.

### Options

| Flag | Default | Purpose |
|------|---------|---------|
| `--install` | off | Install missing packages automatically |
| `--comfyui-dir <path>` | from `config.json` | Override the ComfyUI installation path |

### How node detection works

The script handles three ComfyUI workflow formats:
- **GUI format** (`.json` with `nodes[]` array) — uses the `type` field of each node
- **API format** (`.json` with `{nodeId: {class_type, inputs}}`) — uses the `class_type` field
- **n8n-embedded API format** (files containing `{{ $json... }}` n8n expressions) — preprocessed before parsing

Each detected `class_type` is classified as:

| Classification | Action |
|----------------|--------|
| UUID proxy widget (`xxxxxxxx-xxxx-...`) | Skipped — internal ComfyUI GUI state |
| Frontend-only (`MarkdownNote`) | Skipped — rendered by browser, no Python backend |
| Core ComfyUI node | Skipped — scanned dynamically from ComfyUI Python files |
| Custom node | Checked against ComfyUI Manager's `extension-node-map.json` |

### Custom nodes currently used by this project

| Node type | Package | GitHub |
|-----------|---------|--------|
| `VHS_VideoCombine` | ComfyUI-VideoHelperSuite | https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite |
| `RMBG`, `AILab_ImagePreview` | ComfyUI-RMBG | https://github.com/1038lab/ComfyUI-RMBG |
| `ColorPalette`, `PalleteTransferClustering` | ComfyUI-Color_Transfer | https://github.com/45uee/ComfyUI-Color_Transfer |
| `ImageBatchSaver` | ComfyUI-Batch-Process | https://github.com/Zar4X/ComfyUI-Batch-Process |
| `ImageConcanateOfUtils` | comfyui-utils-nodes | https://github.com/zhangp365/ComfyUI-utils-nodes |
| `LayerUtility: RoundedRectangle` | ComfyUI_LayerStyle | https://github.com/chflame163/ComfyUI_LayerStyle |
| `Basic data handling: PathSaveImageRGBA` | ComfyUI-basic_data_handling | https://github.com/StableLlama/ComfyUI-basic_data_handling |
| `chaosaiart_Number` | Chaosaiart-Nodes | https://github.com/chaosaiart/Chaosaiart-Nodes |
| `LoadImageFromPath_`, `MultilineText` | **Unknown** — in disabled pack `comfyui_realtimenodes_disabled` |

> **Note on `[??]` nodes:** `LoadImageFromPath_` and `MultilineText` exist only inside the disabled pack `comfyui_realtimenodes_disabled`. They are used by `Change_Card_To_Pallette.json`, `Make_Images_For_Card.json`, `Make_Deck_Front_Transparent.json`, and `Make_Symmetric_Card.json`. If those workflows fail to load, re-enable or reinstall that pack.

---

## Card Image Generation Pipeline

Generating a complete set of card images requires running **three n8n flows in order**, each building on the previous stage's output. Two optional ComfyUI workflows can be run manually in the ComfyUI browser UI for additional variants.

```
ODS Spreadsheet (card names + prompts)
  |
  |  [1] Generate Full Tarot Images  (n8n + ComfyUI: TarotFullImage.json)
  v
FullImagesDir/          <-- one full-size artwork image per card
  |
  |  [2] Generate Card Tarot Images  (n8n + ComfyUI: Make_Images_For_Card.json)
  v
CardPartImagesDir/      <-- three orientations per card (upright, reverse, between)
  |
  |  [3] Generate Pallette Tarot Images  (n8n + ComfyUI: Change_Card_To_Pallette.json)
  v
CardPartImagesDir/      <-- same files, overwritten with palette-harmonized colors
  |
  +--[opt] Make_Symmetric_Card.json   --> transparent symmetric card variant
  +--[opt] Make_Deck_Front_Transparent.json  --> transparent background PNG
```

---

### Stage 1 — Generate Full Artwork

**n8n flow:** `Generate Full Tarot Images`
**ComfyUI workflow (embedded):** equivalent to `ComfyUI/TarotFullImage.json`
**Model type:** Text-to-image (SD3 / FLUX-style, `QuadrupleCLIPLoader`)

**What it does:** Reads each card's name, orientation, and positive/negative prompts from the ODS spreadsheet and generates a full-size artwork image for each card.

**ComfyUI node chain:**
```
UNETLoader --> ModelSamplingSD3
QuadrupleCLIPLoader --> CLIPTextEncode (positive + negative)
EmptySD3LatentImage --> KSampler --> VAEDecode --> ImageBatchSaver
```

**Inputs:**
- `LegacySpreadsheetPath` — path to the ODS spreadsheet containing card names and prompts

**Outputs:**
- `FullImagesDir/` — one full-size PNG per card

**To run:** In n8n, open `Generate Full Tarot Images` and click **Execute Workflow**. The `Code in JavaScript` node near the top has `start` / `end` index variables you can edit to process a subset of cards.

---

### Stage 2 — Scale, Rotate, and Refine to Card Dimensions

**n8n flow:** `Generate Card Tarot Images`
**ComfyUI workflow (embedded):** equivalent to `ComfyUI/Make_Images_For_Card.json`
**Model type:** Image-to-image refinement (Qwen Vision, `TextEncodeQwenImageEditPlus`)

**What it does:** Takes each full-size artwork from Stage 1, scales it to card dimensions, and runs an img2img pass to refine details. Produces **three orientation variants** per card in a single ComfyUI call — upright (0 degrees), reverse (180 degrees), and between (90 degrees).

**ComfyUI node chain (repeated three times, one per orientation):**
```
LoadImageFromPath_ --> ImageScaleToTotalPixels --> VAEEncode
TextEncodeQwenImageEditPlus (positive + negative)
KSampler --> VAEDecode --> ImageRotate --> ImageBatchSaver
```

**Inputs:**
- `Deck.json` — card list and image file paths
- Images from `FullImagesDir/` (Stage 1 output)

**Outputs:**
- `CardPartImagesDir/` — upright, reverse, and between PNGs for each card

**To run:** Open `Generate Card Tarot Images` in n8n and click **Execute Workflow**. Edit `start` / `end` in the `Choose Which Cards to Send` node to process a subset.

---

### Stage 3 — Apply Color Palette

**n8n flow:** `Generate Pallette Tarot Images`
**ComfyUI workflow (embedded):** equivalent to `ComfyUI/Change_Card_To_Pallette.json`
**Model type:** None — pure algorithmic color palette transfer

**What it does:** Applies a unified color palette to all three orientation variants of each card, ensuring visual consistency across the deck. Uses clustering-based palette transfer — no ML inference required.

**ComfyUI node chain:**
```
LoadImageFromPath_ (x3, one per orientation)
ColorPalette --> PalleteTransferClustering (x3) --> ImageBatchSaver (x3)
```

**Inputs:**
- `Deck.json` — card list and image file paths
- Images from `CardPartImagesDir/` (Stage 2 output)

**Outputs:**
- `CardPartImagesDir/` — same files overwritten with palette-harmonized colors

**To run:** Open `Generate Pallette Tarot Images` in n8n and click **Execute Workflow**. Edit `start` / `end` in `Choose Which Cards to Send` to process a subset.

---

### Optional — Symmetric Card Variant

**ComfyUI workflow:** `ComfyUI/Make_Symmetric_Card.json`
**Run manually in the ComfyUI browser UI** (no n8n flow)

**What it does:** Takes a card image, removes its background (RMBG), flips it horizontally, concatenates the original and flipped versions side-by-side, and applies a rounded-rectangle mask to produce a symmetrical transparent card.

**ComfyUI node chain:**
```
LoadImage --> RMBG (background removal)
  --> flip copy --> ImageConcanateOfUtils
  --> LayerUtility: RoundedRectangle (mask)
  --> Basic data handling: PathSaveImageRGBA
```

---

### Optional — Transparent Background Variant

**ComfyUI workflow:** `ComfyUI/Make_Deck_Front_Transparent.json`
**Run manually in the ComfyUI browser UI** (no n8n flow)

**What it does:** Removes the background from a card image using RMBG to produce an RGBA transparent PNG — useful for overlaying cards on custom backgrounds in the reader UI.

---

### Relationship Between n8n Workflows and ComfyUI JSON Files

The ComfyUI workflow files in the `ComfyUI/` folder are **GUI format** — they can be loaded in the ComfyUI browser (`Load` button) for visual editing. Each n8n flow embeds the corresponding workflow in **API format** directly inside its HTTP request body. The two representations are equivalent but formatted differently:

| ComfyUI GUI JSON (`ComfyUI/*.json`) | n8n HTTP body (API JSON) |
|-------------------------------------|--------------------------|
| `nodes[]` array + `links[]` array | `{"prompt": {"1": {"class_type": ..., "inputs": {...}}, ...}}` |
| Numeric node IDs resolved via links | String node IDs with direct input references |
| Used for editing in the browser | Sent directly to `http://127.0.0.1:8188/prompt` |

To update the ComfyUI workflow used by an n8n flow: edit the GUI JSON in the browser, export it as API format (disable the GUI toggle in ComfyUI settings), then paste the result into the `jsonBody` field of the `Send to ComfyUI` HTTP node in n8n.
