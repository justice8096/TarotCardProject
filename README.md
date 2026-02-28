
This project will attempt to create a Tarot Card layout, spread and reader. It will differ from the Rider-Waite version by having more cards, and it will be compatible with the I-Ching balance model as well as the Tarot action model.

Tools Used:
* n8n
* comfyUI
* Perplexity
* TypeScript

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
