#!/usr/bin/env python3
"""
setup_comfyui_nodes.py
Scans all ComfyUI workflow JSONs, identifies which custom node packages they
require, checks whether those packages are installed, and (optionally)
installs missing ones.

Usage:
    python setup_comfyui_nodes.py                        # check only (default)
    python setup_comfyui_nodes.py --install              # check + install missing
    python setup_comfyui_nodes.py --comfyui-dir "D:/x"  # override ComfyUI path

How class_type resolution works (in order):
  1. UUID proxy nodes  (xxxxxxxx-xxxx-4xxx-xxxx-xxxxxxxxxxxx) → skip, internal GUI
  2. Frontend-only nodes (MarkdownNote, etc.)                → skip, no Python needed
  3. Core ComfyUI nodes (scanned from ComfyUI Python files)  → skip, always present
  4. extension-node-map.json (from ComfyUI Manager)          → maps type → GitHub URL
  5. Filesystem scan of custom_nodes/*.py                    → fallback match
  6. Unknown                                                 → flagged for manual check

Installation:
  Tries ComfyUI Manager REST API (POST /customnode/install) first.
  Falls back to git clone into custom_nodes/.
  Requires git on PATH for the fallback.
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────

SCRIPT_DIR      = Path(__file__).parent
CONFIG_PATH     = SCRIPT_DIR / "config.json"
WORKFLOWS_DIR   = SCRIPT_DIR / "ComfyUI"
DEFAULT_API_URL = "http://127.0.0.1:8188"
MANAGER_API_URL = "http://127.0.0.1:8188"   # same host, Manager lives here

# Nodes whose class_type looks like a UUID (ComfyUI internal proxy widgets)
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)

# Pure-frontend nodes — they have no Python backend and cannot be "installed"
FRONTEND_ONLY_NODES = {
    "MarkdownNote",   # ComfyUI UI display node (rendered by the browser)
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"  ERROR: config.json not found at {CONFIG_PATH}")
        sys.exit(1)
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def preprocess_json(text: str) -> str:
    """
    Strip n8n template expressions ({{ ... }}) that are embedded in some
    ComfyUI API JSONs (e.g. Make_Deck_Front_Transparent.json).

    Two cases:
      "{{expression}}"  → "n8n_expr"   (quoted in JSON string — keep outer quotes)
      {{expression}}    → null          (bare JSON value — replace with null)
    """
    # Replace quoted template strings first: "{{...}}" → "n8n_expr"
    text = re.sub(r'"\{\{[^}]*\}\}"', '"n8n_expr"', text)
    # Replace bare template values: {{...}} → null
    text = re.sub(r'\{\{[^}]*\}\}', 'null', text)
    return text


def extract_node_types_gui(wf: dict) -> set[str]:
    """Extract class types from ComfyUI GUI format (has nodes[] array)."""
    types = set()
    for node in wf.get("nodes", []):
        ntype = node.get("type")
        if ntype:
            types.add(ntype)
    return types


def extract_node_types_api(wf: dict) -> set[str]:
    """Extract class types from ComfyUI API format ({nodeId: {class_type, inputs}})."""
    types = set()
    for val in wf.values():
        if isinstance(val, dict) and "class_type" in val:
            types.add(val["class_type"])
    return types


def scan_workflows(workflows_dir: Path) -> dict[str, list[str]]:
    """
    Scan all ComfyUI JSON workflows.
    Returns {class_type: [filename, ...]} for every unique class_type found.
    """
    type_to_files: dict[str, list[str]] = {}

    if not workflows_dir.exists():
        print(f"  ERROR: ComfyUI workflows directory not found: {workflows_dir}")
        sys.exit(1)

    for json_file in sorted(workflows_dir.glob("*.json")):
        raw = json_file.read_text(encoding="utf-8")
        try:
            wf = json.loads(raw)
        except json.JSONDecodeError:
            # Try stripping n8n template expressions
            try:
                wf = json.loads(preprocess_json(raw))
            except json.JSONDecodeError as exc:
                print(f"  WARN: could not parse {json_file.name}: {exc}")
                continue

        if "nodes" in wf:
            types = extract_node_types_gui(wf)
        else:
            types = extract_node_types_api(wf)

        for t in types:
            type_to_files.setdefault(t, []).append(json_file.name)

    return type_to_files


def scan_core_comfyui_nodes(comfyui_dir: Path) -> set[str]:
    """
    Dynamically find all class_types defined in core ComfyUI Python files
    (everything outside custom_nodes/).
    Handles both the old NODE_CLASS_MAPPINGS API and the new io.ComfyNode API.
    """
    core_types: set[str] = set()
    skip_dirs = {
        "custom_nodes", "__pycache__", ".git", "web",
        "output", "input", "temp", "models", "user",
    }

    old_pattern = re.compile(r'["\']([A-Za-z][\w: ]+)["\']\s*:')
    new_pattern  = re.compile(r'node_id\s*=\s*["\']([A-Za-z][\w: ]+)["\']')

    for root, dirs, files in os.walk(comfyui_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            try:
                content = open(fpath, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for m in old_pattern.finditer(content):
                core_types.add(m.group(1))
            for m in new_pattern.finditer(content):
                core_types.add(m.group(1))

    return core_types


def load_extension_node_map(comfyui_dir: Path) -> dict[str, str]:
    """
    Load ComfyUI Manager's extension-node-map.json if present.
    Returns {class_type: github_url}.
    """
    map_path = comfyui_dir / "custom_nodes" / "comfyui-manager" / "extension-node-map.json"
    if not map_path.exists():
        return {}

    data = json.loads(map_path.read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    for repo_url, val in data.items():
        if isinstance(val, list) and val and isinstance(val[0], list):
            for class_type in val[0]:
                if class_type not in result:
                    result[class_type] = repo_url
    return result


def get_installed_folders(comfyui_dir: Path) -> dict[str, str]:
    """
    Scan custom_nodes/ and return:
      {folder_name_lower: remote_url_lower}

    remote_url is read from .git/config when available; otherwise empty.
    Keys are lowercased for case-insensitive comparison.
    """
    cn_dir = comfyui_dir / "custom_nodes"
    installed: dict[str, str] = {}
    if not cn_dir.exists():
        return installed

    for folder in cn_dir.iterdir():
        if not folder.is_dir():
            continue
        git_config = folder / ".git" / "config"
        remote_url = ""
        if git_config.exists():
            cfg_text = git_config.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r'url\s*=\s*(.+)', cfg_text)
            if m:
                remote_url = m.group(1).strip().removesuffix(".git").rstrip("/")
        installed[folder.name.lower()] = remote_url.lower()

    return installed


def is_repo_installed(github_url: str, installed: dict[str, str]) -> bool:
    """
    Check if a GitHub repo is installed in custom_nodes/.
    Tries (in order):
      1. Remote URL match (case-insensitive, ignores .git suffix)
      2. Folder name derived from GitHub URL (case-insensitive)
    """
    url_norm = github_url.lower().removesuffix(".git").rstrip("/")

    # 1. Match by remote URL recorded in .git/config
    if url_norm in installed.values():
        return True

    # 2. Match by folder name (last path component of the URL)
    folder_guess = url_norm.split("/")[-1]
    return folder_guess in installed


def scan_custom_nodes_for_type(comfyui_dir: Path, class_type: str) -> str | None:
    """
    Fallback: scan Python files in custom_nodes/ to find which folder
    registers the given class_type. Returns folder name or None.
    """
    cn_dir = comfyui_dir / "custom_nodes"
    old_pat = re.compile(r'["\']' + re.escape(class_type) + r'["\']')
    new_pat  = re.compile(r'node_id\s*=\s*["\']' + re.escape(class_type) + r'["\']')

    for folder in sorted(cn_dir.iterdir()):
        if not folder.is_dir() or folder.name.startswith("__"):
            continue
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                try:
                    content = open(os.path.join(root, fname), encoding="utf-8", errors="ignore").read()
                except OSError:
                    continue
                if old_pat.search(content) or new_pat.search(content):
                    return folder.name
    return None


def install_via_manager(github_url: str, manager_url: str) -> bool:
    """Attempt to install a custom node via ComfyUI Manager REST API."""
    payload = json.dumps({"id": github_url}).encode("utf-8")
    req = urllib.request.Request(
        manager_url.rstrip("/") + "/customnode/install",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status < 300
    except Exception:
        return False


def install_via_git(github_url: str, comfyui_dir: Path) -> bool:
    """Clone a GitHub repo into custom_nodes/."""
    cn_dir = comfyui_dir / "custom_nodes"
    result = subprocess.run(
        ["git", "clone", github_url],
        cwd=str(cn_dir),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"    git clone succeeded.")
        return True
    print(f"    git clone failed: {(result.stderr or result.stdout).strip()[:200]}")
    return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    # Parse args
    do_install    = "--install" in sys.argv
    comfyui_dir_override: str | None = None
    for i, arg in enumerate(sys.argv):
        if arg == "--comfyui-dir" and i + 1 < len(sys.argv):
            comfyui_dir_override = sys.argv[i + 1]

    # ── Step 1: load config ────────────────────────────────────────────────────
    config = load_config()
    raw_comfyui_dir = comfyui_dir_override or config.get("ComfyUIDir", "")
    if not raw_comfyui_dir:
        print("ERROR: ComfyUIDir not set in config.json")
        sys.exit(1)
    comfyui_dir = Path(raw_comfyui_dir)
    if not comfyui_dir.exists():
        print(f"ERROR: ComfyUIDir does not exist: {comfyui_dir}")
        sys.exit(1)

    print("=" * 64)
    print("ComfyUI Custom Node Checker")
    print("=" * 64)
    print(f"Workflows dir : {WORKFLOWS_DIR}")
    print(f"ComfyUI dir   : {comfyui_dir}")
    print(f"Mode          : {'CHECK + INSTALL' if do_install else 'CHECK ONLY'}")
    print()

    # ── Step 2: scan workflows ─────────────────────────────────────────────────
    print("Scanning ComfyUI workflow JSONs ...")
    type_to_files = scan_workflows(WORKFLOWS_DIR)
    print(f"  Found {len(type_to_files)} unique class_type(s) across "
          f"{len(list(WORKFLOWS_DIR.glob('*.json')))} workflows.")
    print()

    # ── Step 3: classify nodes ─────────────────────────────────────────────────
    print("Scanning core ComfyUI node definitions ...")
    core_nodes = scan_core_comfyui_nodes(comfyui_dir)
    print(f"  Found {len(core_nodes)} core class_type(s).")
    print()

    uuid_types       : set[str] = set()
    frontend_types   : set[str] = set()
    core_types       : set[str] = set()
    custom_types     : set[str] = set()

    for t in type_to_files:
        if UUID_PATTERN.match(t):
            uuid_types.add(t)
        elif t in FRONTEND_ONLY_NODES:
            frontend_types.add(t)
        elif t in core_nodes:
            core_types.add(t)
        else:
            custom_types.add(t)

    if uuid_types:
        print(f"  Skipping {len(uuid_types)} UUID proxy widget node(s) (internal GUI, no install needed).")
    if frontend_types:
        print(f"  Skipping {len(frontend_types)} frontend-only node(s): {', '.join(sorted(frontend_types))}")
    print(f"  Core ComfyUI nodes : {len(core_types)}")
    print(f"  Custom nodes       : {len(custom_types)}")
    print()

    if not custom_types:
        print("All node types are built into ComfyUI — no custom packages needed.")
        sys.exit(0)

    # ── Step 4: load extension-node-map for GitHub URL lookup ─────────────────
    ext_map = load_extension_node_map(comfyui_dir)
    if ext_map:
        print(f"Loaded ComfyUI Manager extension map ({len(ext_map)} entries).")
    else:
        print("ComfyUI Manager not installed — falling back to filesystem scan only.")
    print()

    # ── Step 5: load installed repos ──────────────────────────────────────────
    installed = get_installed_folders(comfyui_dir)

    # ── Step 6: check each custom type ────────────────────────────────────────
    print(f"Checking {len(custom_types)} custom node type(s):\n")

    missing_urls: dict[str, str] = {}    # github_url -> first class_type that needs it
    unknown_types: list[str]     = []

    for class_type in sorted(custom_types):
        github_url = ext_map.get(class_type)

        if github_url:
            inst = is_repo_installed(github_url, installed)
            if not inst:
                # URL/folder name match failed — ComfyUI Manager sometimes uses
                # a different folder name. Scan Python files as the ground-truth.
                found_folder = scan_custom_nodes_for_type(comfyui_dir, class_type)
                if found_folder:
                    inst = True
            marker = "OK" if inst else "!!"
            print(f"  [{marker}] {class_type}")
            print(f"       package : {github_url}")
            print(f"       used in : {', '.join(sorted(type_to_files[class_type]))}")
            if not inst:
                missing_urls.setdefault(github_url, class_type)
        else:
            # Extension map didn't know it — try scanning filesystem
            found_folder = scan_custom_nodes_for_type(comfyui_dir, class_type)
            if found_folder:
                print(f"  [OK] {class_type}")
                print(f"       package : {found_folder} (local scan, no GitHub URL)")
            else:
                print(f"  [??] {class_type}")
                print(f"       package : UNKNOWN - not in ComfyUI Manager registry")
                print(f"       used in : {', '.join(sorted(type_to_files[class_type]))}")
                unknown_types.append(class_type)
        print()

    # ── Step 7: summary ───────────────────────────────────────────────────────
    if unknown_types:
        print(f"WARN: {len(unknown_types)} node type(s) not found anywhere:")
        for t in unknown_types:
            print(f"  - {t}")
        print("  These may be from a disabled pack or missing from ComfyUI Manager's registry.")
        print("  Check which custom node pack provides them and install it manually.")
        print()

    if not missing_urls:
        print("All identified custom packages are installed.")
        sys.exit(0 if not unknown_types else 2)

    print(f"Missing package(s) ({len(missing_urls)}):")
    for url in sorted(missing_urls):
        print(f"  - {url}")
    print()

    if not do_install:
        print("Run with --install to install them automatically:")
        print("  python setup_comfyui_nodes.py --install")
        print()
        print("Or install manually via ComfyUI Manager, or by running:")
        for url in sorted(missing_urls):
            print(f"  git clone {url} \"{comfyui_dir / 'custom_nodes'}\"")
        sys.exit(1)

    # ── Step 8: install ───────────────────────────────────────────────────────
    # Try ComfyUI Manager API first
    manager_api_reachable = False
    try:
        with urllib.request.urlopen(MANAGER_API_URL + "/manager/version", timeout=3):
            manager_api_reachable = True
    except Exception:
        pass

    if manager_api_reachable:
        print("ComfyUI Manager API is reachable — installing via Manager ...")
    else:
        print("ComfyUI Manager API not reachable — falling back to git clone ...")

    failed: list[str] = []
    for url in sorted(missing_urls):
        print(f"\n  Installing: {url}")
        ok = False
        if manager_api_reachable:
            ok = install_via_manager(url, MANAGER_API_URL)
            if ok:
                print(f"    Manager install queued.")
            else:
                print(f"    Manager install failed — trying git clone ...")
        if not ok:
            ok = install_via_git(url, comfyui_dir)
        if not ok:
            failed.append(url)

    print()
    if failed:
        print(f"ERROR: {len(failed)} package(s) failed to install:")
        for url in failed:
            print(f"  - {url}")
        print("\nInstall them manually via ComfyUI Manager or:")
        for url in failed:
            print(f"  git clone {url} \"{comfyui_dir / 'custom_nodes'}\"")
        sys.exit(1)
    else:
        if manager_api_reachable:
            print("Done. Restart ComfyUI to load the newly installed nodes.")
        else:
            print("Done. Restart ComfyUI to load the newly installed nodes.")
            print("Some nodes may require pip install of dependencies:")
            print("  Run install.py / requirements.txt inside each new custom_nodes folder.")
        sys.exit(0)


if __name__ == "__main__":
    main()
