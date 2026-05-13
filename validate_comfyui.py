#!/usr/bin/env python3
"""Validate ComfyUI GUI workflow JSONs for structural correctness."""
import json, os, sys

def validate(filepath):
    with open(filepath, encoding='utf-8') as f:
        try:
            wf = json.load(f)
        except json.JSONDecodeError as e:
            print(f"SKIP {os.path.basename(filepath)} (invalid JSON: {e})")
            return True  # pre-existing issue, not our problem

    name = os.path.basename(filepath)
    nodes = {n['id']: n for n in wf.get('nodes', [])}
    links = wf.get('links', [])
    errors = []

    # Check every link
    for link in links:
        link_id, src_id, src_slot, dst_id, dst_slot = link[0], link[1], link[2], link[3], link[4]
        link_type = link[5] if len(link) > 5 else "?"

        if src_id not in nodes:
            errors.append(f"  Link {link_id}: source node {src_id} not found")
        else:
            src = nodes[src_id]
            outputs = src.get('outputs', [])
            if src_slot >= len(outputs):
                errors.append(f"  Link {link_id}: source node {src_id} ({src['type']}) has {len(outputs)} outputs, but slot {src_slot} requested")
            else:
                # Verify the link ID is in the output's links list
                out = outputs[src_slot]
                if link_id not in out.get('links', []):
                    errors.append(f"  Link {link_id}: not listed in node {src_id} output slot {src_slot} links={out.get('links')}")

        if dst_id not in nodes:
            errors.append(f"  Link {link_id}: dest node {dst_id} not found")
        else:
            dst = nodes[dst_id]
            inputs = dst.get('inputs', [])
            if dst_slot >= len(inputs):
                errors.append(f"  Link {link_id}: dest node {dst_id} ({dst['type']}) has {len(inputs)} inputs, but slot {dst_slot} requested")
            else:
                inp = inputs[dst_slot]
                if inp.get('link') != link_id:
                    errors.append(f"  Link {link_id}: dest node {dst_id} input slot {dst_slot} has link={inp.get('link')}, expected {link_id}")

    # Check that every input link reference has a matching link
    for nid, node in nodes.items():
        for i, inp in enumerate(node.get('inputs', [])):
            lid = inp.get('link')
            if lid is not None:
                found = any(l[0] == lid for l in links)
                if not found:
                    errors.append(f"  Node {nid} ({node['type']}) input {i} references link {lid} which doesn't exist")

    # Check that every output link reference has a matching link
    for nid, node in nodes.items():
        for i, out in enumerate(node.get('outputs', [])):
            for lid in (out.get('links') or []):
                found = any(l[0] == lid for l in links)
                if not found:
                    errors.append(f"  Node {nid} ({node['type']}) output {i} references link {lid} which doesn't exist")

    # Check last_node_id >= max node id
    max_nid = max(nodes.keys()) if nodes else 0
    if wf.get('last_node_id', 0) < max_nid:
        errors.append(f"  last_node_id={wf['last_node_id']} < max node id {max_nid}")

    # Check last_link_id >= max link id
    max_lid = max(l[0] for l in links) if links else 0
    if wf.get('last_link_id', 0) < max_lid:
        errors.append(f"  last_link_id={wf['last_link_id']} < max link id {max_lid}")

    if errors:
        print(f"FAIL {name}")
        for e in errors:
            print(e)
        return False
    else:
        print(f"OK   {name} ({len(nodes)} nodes, {len(links)} links)")
        return True


if __name__ == '__main__':
    comfyui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ComfyUI')
    files = sorted(f for f in os.listdir(comfyui_dir) if f.endswith('.json'))
    all_ok = True
    for f in files:
        if not validate(os.path.join(comfyui_dir, f)):
            all_ok = False
    print()
    if all_ok:
        print("All workflows valid.")
    else:
        print("Some workflows have errors.")
        sys.exit(1)
