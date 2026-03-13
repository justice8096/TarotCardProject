#!/usr/bin/env python3
"""
setup.py — Interactive setup for the TarotCardProject.

Prompts the user for their data directory and ComfyUI directory, then
rewrites config.json and all hardcoded paths in n8n and ComfyUI workflow
JSON files.

Run once after cloning the project or moving it to a new machine:

    python setup.py

Or pass arguments non-interactively:

    python setup.py --data-dir E:/data --comfyui-dir E:/ComfyUI_windows_portable/ComfyUI
"""
import argparse
import json
import os
import re
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


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Configure TarotCardProject paths for your machine."
    )
    parser.add_argument("--data-dir", help="Root data directory (e.g. E:/data)")
    parser.add_argument("--comfyui-dir", help="ComfyUI directory (e.g. E:/ComfyUI_windows_portable/ComfyUI)")
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

    if new_data == cur_data and new_comfyui == cur_comfyui:
        print("  No changes needed — paths already match.")
        return

    # ── 1. Update config.json ────────────────────────────────────────────────

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

    # ── 2. Update n8n workflow JSONs ─────────────────────────────────────────

    changed_count = 0
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

    # ── 3. Update launch.json ────────────────────────────────────────────────

    launch_path = os.path.join(SCRIPT_DIR, ".claude", "launch.json")
    if os.path.isfile(launch_path):
        if update_workflow_file(launch_path, cur_data, new_data, cur_comfyui, new_comfyui):
            print("    OK .claude/launch.json")
            changed_count += 1

    # ── 4. Update update_workflow_paths.py itself ────────────────────────────

    uwp_path = os.path.join(SCRIPT_DIR, "update_workflow_paths.py")
    if os.path.isfile(uwp_path):
        with open(uwp_path, "r", encoding="utf-8") as f:
            uwp_text = f.read()
        # Update the CONFIG_EXPR fallback path
        project_dir = normalize_path(os.path.dirname(SCRIPT_DIR)) if os.path.basename(SCRIPT_DIR) != "n8n" else normalize_path(os.path.dirname(os.path.dirname(SCRIPT_DIR)))
        # Actually, just update any D:/ paths found
        uwp_updated = replace_in_text(uwp_text, cur_data, new_data, cur_comfyui, new_comfyui)
        if uwp_updated != uwp_text:
            with open(uwp_path, "w", encoding="utf-8") as f:
                f.write(uwp_updated)
            print("    OK update_workflow_paths.py")
            changed_count += 1

    # ── Done ─────────────────────────────────────────────────────────────────

    print()
    print(f"  Done. Updated {changed_count} file(s).")
    print()
    print("  Next steps:")
    print(f"    1. Ensure '{new_data}' exists with your card data")
    print(f"    2. Ensure '{new_comfyui}' has ComfyUI installed")
    print("    3. Start n8n with the required flags (see CLAUDE.md)")
    print()


if __name__ == "__main__":
    main()
