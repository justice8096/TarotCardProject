#!/usr/bin/env python3
"""
setup.py — Interactive setup for the TarotCardProject.

Prompts the user for their data directory and ComfyUI directory, then
rewrites config.json and all hardcoded paths in n8n and ComfyUI workflow
JSON files.  Also checks for required external tools, ComfyUI models,
and custom nodes.

Run once after cloning the project or moving it to a new machine:

    python setup.py

Or pass arguments non-interactively:

    python setup.py --data-dir E:/data --comfyui-dir E:/ComfyUI_windows_portable/ComfyUI

Skip prerequisite checks:

    python setup.py --skip-checks
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

# ── Defaults (current values) ────────────────────────────────────────────────

DEFAULTS = {
    "data_dir": "D:/data",
    "comfyui_dir": "D:/ComfyUI_windows_portable/ComfyUI",
}

# Paths that appear in workflow files, mapped to their config.json derivation.
# Order matters: longer prefixes first so replacements don't partially match.
OLD_PATH_PREFIXES = [
    "D:/ComfyUI_windows_portable/ComfyUI",
    "D:/data",
    # Backslash variants found in ComfyUI GUI JSONs
    "D:\\\\ComfyUI_windows_portable\\\\ComfyUI",
    "D:\\\\data",
    "D:\\data",
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
N8N_DIR = os.path.join(SCRIPT_DIR, "n8n")
COMFYUI_DIR = os.path.join(SCRIPT_DIR, "ComfyUI")


# ── Helpers ──────────────────────────────────────────────────────────────────

def normalize_path(p):
    """Normalize to forward slashes, strip trailing slash."""
    return p.replace("\\", "/").rstrip("/")


def prompt_path(label, default):
    """Prompt the user for a directory path with a default."""
    while True:
        raw = input(f"  {label} [{default}]: ").strip()
        value = normalize_path(raw) if raw else default
        if not os.path.isdir(value):
            print(f"    WARNING: '{value}' does not exist yet. Continue anyway? [Y/n] ", end="")
            confirm = input().strip().lower()
            if confirm and confirm != "y":
                continue
        return value


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")


def replace_in_text(text, old_data, new_data, old_comfyui, new_comfyui):
    """Replace all path prefixes in raw text, handling both slash styles."""
    # Forward slash replacements
    text = text.replace(old_comfyui, new_comfyui)
    text = text.replace(old_data, new_data)

    # Escaped backslash variants (JSON-encoded "D:\\data")
    old_data_bs = old_data.replace("/", "\\\\")
    new_data_bs = new_data.replace("/", "\\\\")
    old_comfyui_bs = old_comfyui.replace("/", "\\\\")
    new_comfyui_bs = new_comfyui.replace("/", "\\\\")
    text = text.replace(old_comfyui_bs, new_comfyui_bs)
    text = text.replace(old_data_bs, new_data_bs)

    # Single backslash variants (sometimes in raw widget_values)
    old_data_sb = old_data.replace("/", "\\")
    new_data_sb = new_data.replace("/", "\\")
    old_comfyui_sb = old_comfyui.replace("/", "\\")
    new_comfyui_sb = new_comfyui.replace("/", "\\")
    text = text.replace(old_comfyui_sb, new_comfyui_sb)
    text = text.replace(old_data_sb, new_data_sb)

    return text


def update_workflow_file(filepath, old_data, new_data, old_comfyui, new_comfyui):
    """Read a workflow JSON as raw text, replace paths, write back."""
    with open(filepath, "r", encoding="utf-8") as f:
        original = f.read()

    updated = replace_in_text(original, old_data, new_data, old_comfyui, new_comfyui)

    if updated != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(updated)
        return True
    return False


# ── Required ComfyUI Models ──────────────────────────────────────────────────
# Each entry: (subfolder under models/, filename)
# Extracted from all ComfyUI workflow JSONs and n8n Code nodes.

REQUIRED_MODELS = [
    # Checkpoints
    ("checkpoints", "dreamshaper_8.safetensors"),

    # Diffusion models (UNETLoader)
    ("diffusion_models", "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"),
    ("diffusion_models", "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"),
    ("diffusion_models", "qwen_image_edit_2509_fp8_e4m3fn.safetensors"),
    ("diffusion_models", "hidream_i1_full_fp8.safetensors"),

    # Text encoders / CLIP
    ("text_encoders", "umt5_xxl_fp8_e4m3fn_scaled.safetensors"),
    ("text_encoders", "qwen_2.5_vl_7b_fp8_scaled.safetensors"),
    ("text_encoders", "clip_l_hidream.safetensors"),
    ("text_encoders", "clip_g_hidream.safetensors"),
    ("text_encoders", "t5xxl_fp8_e4m3fn_scaled.safetensors"),
    ("text_encoders", "llama_3.1_8b_instruct_fp8_scaled.safetensors"),
    ("text_encoders", "qwen_3_4b.safetensors"),

    # VAE
    ("vae", "wan_2.1_vae.safetensors"),
    ("vae", "qwen_image_vae.safetensors"),
    ("vae", "ae.safetensors"),

    # LoRAs
    ("loras", "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors"),
    ("loras", "Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors"),
]

# GGUF models live under a custom node's models directory, not standard ComfyUI models/
REQUIRED_GGUF_MODELS = [
    "orpheus-3b-0.1-ft-Q4_K_M.gguf",
]


# ── Prerequisite Checks ─────────────────────────────────────────────────────

def check_command(name, test_args=None):
    """Check if a command-line tool is available. Returns (found, version_str)."""
    cmd = test_args or [name, "--version"]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10
        )
        version_line = (result.stdout or result.stderr).strip().split("\n")[0]
        return True, version_line
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, ""


def check_external_tools():
    """Check for required external tools. Returns (ok_count, warn_count, messages)."""
    tools = [
        ("n8n", None, "n8n workflow engine — install via: npm install -g n8n"),
        ("ffmpeg", None, "video concatenation — install from https://ffmpeg.org/download.html"),
        ("git", None, "custom node installation — install from https://git-scm.com/"),
        ("ollama", None, "LLM for narration scripts — install from https://ollama.com/download"),
    ]
    ok = 0
    warn = 0
    msgs = []

    for name, test_args, help_text in tools:
        found, version = check_command(name, test_args)
        if found:
            msgs.append(f"    [OK] {name}: {version[:80]}")
            ok += 1
        else:
            msgs.append(f"    [!!] {name}: NOT FOUND — {help_text}")
            warn += 1

    return ok, warn, msgs


def check_comfyui_models(comfyui_dir):
    """Check for required model files. Returns (found, missing, messages)."""
    models_dir = os.path.join(comfyui_dir, "models")
    found = []
    missing = []
    msgs = []

    for subfolder, filename in REQUIRED_MODELS:
        filepath = os.path.join(models_dir, subfolder, filename)
        if os.path.isfile(filepath):
            found.append(filename)
        else:
            missing.append(f"models/{subfolder}/{filename}")

    # Check GGUF models — these can be in various locations under custom_nodes
    # or in a models/gguf/ directory
    for filename in REQUIRED_GGUF_MODELS:
        # Check common locations
        candidates = [
            os.path.join(models_dir, "gguf", filename),
            os.path.join(models_dir, "LLM", filename),
            os.path.join(comfyui_dir, "custom_nodes", "ComfyUI-Orpheus-TTS",
                         "models", filename),
        ]
        if any(os.path.isfile(c) for c in candidates):
            found.append(filename)
        else:
            missing.append(f"models/gguf/{filename} (or custom_nodes/*/models/)")

    if missing:
        msgs.append(f"    Found {len(found)}/{len(found) + len(missing)} required models")
        msgs.append(f"    Missing {len(missing)} model(s):")
        for m in missing:
            msgs.append(f"      - {m}")
        msgs.append("")
        msgs.append("    Download missing models and place them in the paths above")
        msgs.append(f"    (relative to {comfyui_dir})")
    else:
        msgs.append(f"    [OK] All {len(found)} required models found")

    return found, missing, msgs


def check_custom_nodes(comfyui_dir):
    """Run setup_comfyui_nodes.py in check-only mode. Returns (ok, messages)."""
    script = os.path.join(SCRIPT_DIR, "setup_comfyui_nodes.py")
    if not os.path.isfile(script):
        return True, ["    [SKIP] setup_comfyui_nodes.py not found"]

    if not os.path.isdir(comfyui_dir):
        return True, ["    [SKIP] ComfyUI directory not found — cannot check custom nodes"]

    msgs = []
    try:
        result = subprocess.run(
            [sys.executable, script, "--comfyui-dir", comfyui_dir],
            capture_output=True, text=True, timeout=120,
            cwd=SCRIPT_DIR,
        )
        # Parse output for summary
        output = result.stdout + result.stderr
        lines = output.strip().split("\n")

        # Extract key lines
        missing_count = 0
        unknown_count = 0
        for line in lines:
            if "Missing package" in line:
                missing_count += 1
            if "UNKNOWN" in line or "[??]" in line:
                unknown_count += 1

        if result.returncode == 0:
            msgs.append("    [OK] All custom node packages installed")
        else:
            msgs.append("    [!!] Some custom node packages are missing")
            msgs.append(f"         Run: python setup_comfyui_nodes.py --install")
            # Include the last few relevant lines
            for line in lines[-10:]:
                line = line.strip()
                if line and not line.startswith("="):
                    msgs.append(f"         {line}")
        return result.returncode == 0, msgs
    except subprocess.TimeoutExpired:
        return False, ["    [!!] Custom node check timed out (ComfyUI dir too large?)"]
    except Exception as e:
        return False, [f"    [!!] Custom node check failed: {e}"]


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Configure TarotCardProject paths for your machine."
    )
    parser.add_argument("--data-dir", help="Root data directory (e.g. E:/data)")
    parser.add_argument("--comfyui-dir", help="ComfyUI directory (e.g. E:/ComfyUI_windows_portable/ComfyUI)")
    parser.add_argument("--skip-checks", action="store_true",
                        help="Skip prerequisite checks (tools, models, custom nodes)")
    args = parser.parse_args()

    print("=" * 60)
    print("  TarotCardProject Setup")
    print("=" * 60)
    print()

    # Load current config to detect existing values
    if os.path.isfile(CONFIG_PATH):
        config = read_json(CONFIG_PATH)
        cur_data = normalize_path(config.get("DataDir", DEFAULTS["data_dir"]))
        cur_comfyui = normalize_path(config.get("ComfyUIDir", DEFAULTS["comfyui_dir"]))
    else:
        cur_data = DEFAULTS["data_dir"]
        cur_comfyui = DEFAULTS["comfyui_dir"]

    # Get new paths from args or interactive prompts
    if args.data_dir and args.comfyui_dir:
        new_data = normalize_path(args.data_dir)
        new_comfyui = normalize_path(args.comfyui_dir)
    else:
        print("  Enter the paths for your machine.")
        print("  Press Enter to keep the current value.\n")
        new_data = args.data_dir and normalize_path(args.data_dir) or prompt_path(
            "Data directory", cur_data
        )
        new_comfyui = args.comfyui_dir and normalize_path(args.comfyui_dir) or prompt_path(
            "ComfyUI directory", cur_comfyui
        )

    print()
    print(f"  Data directory:    {new_data}")
    print(f"  ComfyUI directory: {new_comfyui}")
    print()

    paths_changed = not (new_data == cur_data and new_comfyui == cur_comfyui)

    changed_count = 0

    if paths_changed:
        # ── 1. Update config.json ────────────────────────────────────────

        print("  Updating config.json ...")
        config = read_json(CONFIG_PATH) if os.path.isfile(CONFIG_PATH) else {}

        config["DataDir"] = new_data
        config["CardsDir"] = new_data + "/cards"
        config["DefaultDeckDir"] = new_data + "/cards/Standard"
        config["DefaultDeckJsonPath"] = new_data + "/cards/Standard/Deck.json"
        config["LegacyDeckJsonPath"] = new_data + "/cards/Deck.json"
        config["FullImagesDir"] = new_data + "/Full_Images"
        config["CardPartImagesDir"] = new_data + "/Card_Part_Images"
        config["ErrorsDir"] = new_data + "/errors"
        config["SpreadsheetPath"] = new_data + "/TarotSpreadsheet2.ods"
        config["LegacySpreadsheetPath"] = new_data + "/CardImages.ods"
        config["ComfyUIDir"] = new_comfyui

        write_json(CONFIG_PATH, config)
        print("    OK config.json")

        # ── 2. Update n8n + ComfyUI workflow JSONs ───────────────────────

        for dirname in [N8N_DIR, COMFYUI_DIR]:
            if not os.path.isdir(dirname):
                print(f"    SKIP {dirname} (not found)")
                continue
            for fname in sorted(os.listdir(dirname)):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(dirname, fname)
                if update_workflow_file(fpath, cur_data, new_data, cur_comfyui, new_comfyui):
                    relpath = os.path.relpath(fpath, SCRIPT_DIR)
                    print(f"    OK {relpath}")
                    changed_count += 1

        # ── 3. Update launch.json ────────────────────────────────────────

        launch_path = os.path.join(SCRIPT_DIR, ".claude", "launch.json")
        if os.path.isfile(launch_path):
            if update_workflow_file(launch_path, cur_data, new_data, cur_comfyui, new_comfyui):
                print("    OK .claude/launch.json")
                changed_count += 1

        # ── 4. Update update_workflow_paths.py ───────────────────────────

        uwp_path = os.path.join(SCRIPT_DIR, "update_workflow_paths.py")
        if os.path.isfile(uwp_path):
            with open(uwp_path, "r", encoding="utf-8") as f:
                uwp_text = f.read()
            uwp_updated = replace_in_text(uwp_text, cur_data, new_data, cur_comfyui, new_comfyui)
            if uwp_updated != uwp_text:
                with open(uwp_path, "w", encoding="utf-8") as f:
                    f.write(uwp_updated)
                print("    OK update_workflow_paths.py")
                changed_count += 1

    else:
        print("  Paths unchanged — skipping workflow updates.")

    # ── 5. Seed data directory from bundled files ─────────────────────────

    print("  Seeding data directory ...")
    bundled_data = os.path.join(SCRIPT_DIR, "data")
    seeded = 0
    skipped = 0

    for root, dirs, files in os.walk(bundled_data):
        for fname in files:
            src = os.path.join(root, fname)
            # Mirror the relative path under the target data dir
            rel = os.path.relpath(src, bundled_data)
            dst = os.path.join(new_data, rel).replace("\\", "/")
            dst_dir = os.path.dirname(dst)

            if os.path.exists(dst):
                skipped += 1
                continue

            os.makedirs(dst_dir, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"    COPY {rel}")
            seeded += 1

    if seeded:
        print(f"    Copied {seeded} file(s) to {new_data}")
    if skipped:
        print(f"    Skipped {skipped} file(s) (already exist)")

    # ── 6. Create output directories ─────────────────────────────────────

    print("  Creating output directories ...")
    output_dirs = [
        new_data + "/Full_Images",
        new_data + "/Card_Part_Images",
        new_data + "/errors",
        new_data + "/temp/card_faces",
        new_data + "/cards/Standard/Keyframes",
        new_data + "/cards/Standard/Cards",
        new_data + "/cards/Standard/Narration",
        new_data + "/cards/Standard/Music",
    ]
    created_dirs = 0
    for d in output_dirs:
        if not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
            print(f"    MKDIR {os.path.relpath(d, new_data)}")
            created_dirs += 1
    if created_dirs:
        print(f"    Created {created_dirs} directory(s)")
    else:
        print("    All directories already exist")

    # ── 7. Check prerequisites ──────────────────────────────────────────

    tool_warnings = 0
    model_missing = []
    nodes_ok = True

    if not args.skip_checks:
        print()
        print("-" * 60)
        print("  Checking prerequisites ...")
        print("-" * 60)
        print()

        # 7a. External tools
        print("  External tools:")
        ok_count, warn_count, tool_msgs = check_external_tools()
        for msg in tool_msgs:
            print(msg)
        tool_warnings = warn_count
        print()

        # 7b. ComfyUI models
        comfyui_exists = os.path.isdir(new_comfyui)
        if comfyui_exists:
            print("  ComfyUI models:")
            found_models, model_missing, model_msgs = check_comfyui_models(new_comfyui)
            for msg in model_msgs:
                print(msg)
        else:
            print(f"  ComfyUI models: SKIP (directory '{new_comfyui}' not found)")
            model_missing = ["(cannot check — directory missing)"]
        print()

        # 7c. Custom nodes
        if comfyui_exists:
            print("  ComfyUI custom nodes:")
            nodes_ok, node_msgs = check_custom_nodes(new_comfyui)
            for msg in node_msgs:
                print(msg)
        else:
            print("  ComfyUI custom nodes: SKIP (directory not found)")
        print()

    # ── Done ─────────────────────────────────────────────────────────────

    print()
    print("=" * 60)
    print(f"  Setup complete.")
    print(f"    Paths updated : {changed_count} file(s)")
    print(f"    Data seeded   : {seeded} file(s)")
    print(f"    Dirs created  : {created_dirs}")

    if not args.skip_checks:
        issues = []
        if tool_warnings:
            issues.append(f"{tool_warnings} missing tool(s)")
        if model_missing:
            issues.append(f"{len(model_missing)} missing model(s)")
        if not nodes_ok:
            issues.append("missing custom node(s)")

        if issues:
            print()
            print("  Issues found: " + ", ".join(issues))
            print()
            print("  Next steps:")
            if tool_warnings:
                print("    - Install missing tools (see messages above)")
            if model_missing:
                print("    - Download missing ComfyUI models")
            if not nodes_ok:
                print("    - Run: python setup_comfyui_nodes.py --install")
            print("    - Start n8n with required flags:")
            print("        set NODE_FUNCTION_ALLOW_BUILTIN=* && "
                  "set NODE_FUNCTION_ALLOW_EXTERNAL=* && "
                  "set N8N_RUNNERS_TASK_TIMEOUT=28800 && n8n start")
        else:
            print()
            print("  All prerequisites satisfied!")
            print()
            print("  To start:")
            print("    set NODE_FUNCTION_ALLOW_BUILTIN=* && "
                  "set NODE_FUNCTION_ALLOW_EXTERNAL=* && "
                  "set N8N_RUNNERS_TASK_TIMEOUT=28800 && n8n start")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
