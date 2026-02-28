#!/usr/bin/env python3
"""
setup_n8n_nodes.py
Scans all n8n workflow JSONs to find the npm packages they require,
then checks whether those packages are installed and (optionally) installs
any that are missing.

Usage:
    python setup_n8n_nodes.py                 # check only (default)
    python setup_n8n_nodes.py --install       # check and install missing packages
    python setup_n8n_nodes.py --api-url http://localhost:5678   # custom n8n URL

How package detection works:
    n8n node types follow the pattern  "package.NodeName" or "@scope/package.NodeName".
    We strip the node-class suffix to get the npm package name:
        n8n-nodes-base.code          → n8n-nodes-base
        @n8n/n8n-nodes-langchain.lm  → @n8n/n8n-nodes-langchain
        n8n-nodes-mypkg.myNode       → n8n-nodes-mypkg   ← community node

Built-in packages (shipped with n8n, never need installation):
    n8n-nodes-base
    @n8n/n8n-nodes-langchain
    @n8n/n8n-nodes-ai

Installation check strategy (tried in order):
    1. GET <api-url>/rest/nodes  — works when n8n is running
    2. Filesystem: ~/.n8n/nodes/node_modules/<package>/package.json

Installation:
    subprocess.run(["n8n", "install", "<package>"])   (requires n8n on PATH)
"""

import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────

WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), "n8n")
DEFAULT_API_URL = "http://localhost:5678"
N8N_NODES_DIR = Path.home() / ".n8n" / "nodes" / "node_modules"

# Packages that ship with n8n — never need community installation
BUILTIN_PACKAGES = {
    "n8n-nodes-base",
    "@n8n/n8n-nodes-langchain",
    "@n8n/n8n-nodes-ai",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def type_to_package(node_type: str) -> str | None:
    """
    Convert an n8n node type string to its npm package name.
    Returns None for unknown / internal types.

    Examples:
        "n8n-nodes-base.code"          → "n8n-nodes-base"
        "@n8n/n8n-nodes-langchain.lm"  → "@n8n/n8n-nodes-langchain"
        "myOrg/myPkg.myNode"           → None  (unrecognised format, skip)
    """
    if not node_type or "." not in node_type:
        return None

    if node_type.startswith("@"):
        # Scoped package: @scope/pkg.NodeClass
        # Split on the LAST '.' to get @scope/pkg
        parts = node_type.rsplit(".", 1)
        return parts[0] if len(parts) == 2 else None
    else:
        # Unscoped: pkg.NodeClass
        return node_type.split(".")[0]


def scan_workflows(workflows_dir: str) -> dict[str, set[str]]:
    """
    Walk all .json files in workflows_dir and collect every unique node type
    grouped by npm package.

    Returns: {package_name: {node_type, ...}}
    """
    packages: dict[str, set[str]] = {}
    wf_dir = Path(workflows_dir)

    if not wf_dir.exists():
        print(f"  ERROR: workflows directory not found: {workflows_dir}")
        sys.exit(1)

    for json_file in sorted(wf_dir.glob("*.json")):
        try:
            wf = json.loads(json_file.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"  WARN: could not parse {json_file.name}: {exc}")
            continue

        for node in wf.get("nodes", []):
            ntype = node.get("type", "")
            pkg = type_to_package(ntype)
            if pkg:
                packages.setdefault(pkg, set()).add(ntype)

    return packages


def fetch_installed_via_api(api_url: str) -> set[str] | None:
    """
    Query the n8n REST API for installed community nodes.
    Returns a set of package names, or None if the API is unreachable.
    """
    url = api_url.rstrip("/") + "/rest/nodes"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            # Response shape: {"data": [{"name": "n8n-nodes-mypkg", ...}, ...]}
            nodes_list = data.get("data", data) if isinstance(data, dict) else data
            return {item["name"] for item in nodes_list if isinstance(item, dict) and "name" in item}
    except Exception:
        return None


def is_installed_on_filesystem(package: str) -> bool:
    """
    Check whether a community package exists in the n8n user nodes directory.
    """
    pkg_path = N8N_NODES_DIR / package / "package.json"
    return pkg_path.exists()


def check_installed(package: str, api_installed: set[str] | None) -> bool:
    """
    Return True if package is installed, using API result first, then filesystem.
    """
    if api_installed is not None:
        return package in api_installed
    return is_installed_on_filesystem(package)


def install_package(package: str) -> bool:
    """
    Run `n8n install <package>`. Returns True on success.
    """
    print(f"  Installing {package} ...", flush=True)
    result = subprocess.run(
        ["n8n", "install", package],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"    OK — {package} installed.")
        return True
    else:
        print(f"    FAILED — {package}")
        if result.stdout.strip():
            print(f"    stdout: {result.stdout.strip()}")
        if result.stderr.strip():
            print(f"    stderr: {result.stderr.strip()}")
        return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    # Parse simple args without argparse dependency
    do_install = "--install" in sys.argv
    api_url = DEFAULT_API_URL
    for i, arg in enumerate(sys.argv):
        if arg == "--api-url" and i + 1 < len(sys.argv):
            api_url = sys.argv[i + 1]

    print("=" * 60)
    print("n8n Node Package Checker")
    print("=" * 60)
    print(f"Workflows dir : {WORKFLOWS_DIR}")
    print(f"n8n API       : {api_url}")
    print(f"Mode          : {'CHECK + INSTALL' if do_install else 'CHECK ONLY'}")
    print()

    # ── Step 1: Scan workflows ─────────────────────────────────────────────────
    print("Scanning workflow JSONs ...")
    packages = scan_workflows(WORKFLOWS_DIR)

    if not packages:
        print("  No node types found — is the workflows directory empty?")
        sys.exit(0)

    community_packages = {
        pkg for pkg in packages if pkg not in BUILTIN_PACKAGES
    }

    print(f"  Found {len(packages)} package(s) total:")
    for pkg in sorted(packages):
        tag = "(built-in)" if pkg in BUILTIN_PACKAGES else "(community)"
        types_str = ", ".join(sorted(packages[pkg]))
        print(f"    {tag:12}  {pkg}")
        print(f"               node types: {types_str}")
    print()

    # ── Step 2: Short-circuit if nothing to check ──────────────────────────────
    if not community_packages:
        print("All packages are built-in to n8n — nothing to install.")
        print("(If you add community nodes to a workflow later, re-run this script.)")
        sys.exit(0)

    # ── Step 3: Check installation status ─────────────────────────────────────
    print(f"Checking {len(community_packages)} community package(s) ...")

    api_installed = fetch_installed_via_api(api_url)
    if api_installed is not None:
        print(f"  Used n8n REST API ({api_url})")
    else:
        print(f"  n8n API unreachable — falling back to filesystem check ({N8N_NODES_DIR})")

    missing = []
    for pkg in sorted(community_packages):
        installed = check_installed(pkg, api_installed)
        marker = "✓" if installed else "✗"
        print(f"  [{marker}] {pkg}")
        if not installed:
            missing.append(pkg)
    print()

    # ── Step 4: Install or report ──────────────────────────────────────────────
    if not missing:
        print("All community packages are installed.")
        sys.exit(0)

    print(f"Missing package(s): {', '.join(missing)}")

    if not do_install:
        print()
        print("Run with --install to install them automatically:")
        print(f"  python setup_n8n_nodes.py --install")
        sys.exit(1)

    print()
    print("Installing missing packages ...")
    failed = []
    for pkg in missing:
        ok = install_package(pkg)
        if not ok:
            failed.append(pkg)

    print()
    if failed:
        print(f"ERROR: {len(failed)} package(s) failed to install: {', '.join(failed)}")
        print("You may need to install them manually:")
        for pkg in failed:
            print(f"  n8n install {pkg}")
        sys.exit(1)
    else:
        print(f"Done — {len(missing)} package(s) installed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
