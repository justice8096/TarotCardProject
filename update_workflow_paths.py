#!/usr/bin/env python3
"""
update_workflow_paths.py
Migrates all n8n workflow JSONs to read machine-specific paths from config.json.
Run once after cloning/moving the project to a new machine.
"""
import json, os, re

WORKTREE = "D:/TarotCardProject/n8n/.claude/worktrees/thirsty-austin/n8n"
CONFIG_EXPR = "process.env.TAROT_CONFIG || 'D:/TarotCardProject/config.json'"

# ── helpers ───────────────────────────────────────────────────────────────────

def load(filename):
    with open(os.path.join(WORKTREE, filename), encoding='utf-8') as f:
        return json.load(f)

def save(filename, wf):
    with open(os.path.join(WORKTREE, filename), 'w', encoding='utf-8') as f:
        json.dump(wf, f, indent=4, ensure_ascii=False)
    print("  OK " + filename)

def find_node(wf, name):
    return next((n for n in wf['nodes'] if n['name'] == name), None)

def config_header():
    lines = [
        "const fs = require('fs');",
        "// \u2500\u2500 Machine configuration \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
        "// Edit config.json to change paths for your machine. Do not edit this node.",
        "const CONFIG_PATH = " + CONFIG_EXPR + ";",
        "// \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
        "const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));",
        "",
    ]
    return "\n".join(lines) + "\n"

def set_to_code(node, js_code):
    node['type'] = 'n8n-nodes-base.code'
    node['typeVersion'] = 2
    node['parameters'] = {'jsCode': js_code}

def update_assignment(node, field_name, new_value):
    for a in node['parameters']['assignments']['assignments']:
        if a['name'] == field_name:
            a['value'] = new_value
            return True
    return False

def find_trigger(wf):
    """Find the manual trigger node regardless of its display name (handles curly quotes)."""
    return next((n for n in wf['nodes']
                 if n.get('type') == 'n8n-nodes-base.manualTrigger'), None)

def insert_sgp_node(wf, node_id, position, js_code):
    trigger = find_trigger(wf)
    actual_name = trigger['name']          # use the actual name (straight or curly quotes)
    trigger_conns = wf['connections'].get(actual_name, {})
    first_targets = trigger_conns.get('main', [[]])[0]

    new_node = {
        "parameters": {"jsCode": js_code},
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": list(position),
        "id": node_id,
        "name": "Set Global Parameters"
    }
    wf['nodes'].append(new_node)
    wf['connections'][actual_name]['main'][0] = [
        {"node": "Set Global Parameters", "type": "main", "index": 0}
    ]
    wf['connections']['Set Global Parameters'] = {"main": [first_targets]}
    return wf, actual_name

def shift_others(wf, dx, anchors):
    for n in wf['nodes']:
        if n['name'] not in anchors:
            n['position'][0] += dx

# ── 1. Generate Dealer Stop Motion ───────────────────────────────────────────

def update_dealer_stop_motion():
    wf = load("Generate Dealer Stop Motion.json")
    node = find_node(wf, "Set Global Parameters")
    js = config_header() + "\n".join([
        "return [{ json: {",
        "    // Machine-specific (from config.json)",
        "    DeckJsonPath:     config.DefaultDeckJsonPath,",
        "    ComfyUIAPI:       config.ComfyUIAPI,",
        "    ComfyUIInputDir:  config.ComfyUIInputDir  || (config.ComfyUIDir + '/input'),",
        "    ComfyUIOutputDir: config.ComfyUIOutputDir || (config.ComfyUIDir + '/output'),",
        "    // Workflow-specific",
        "    AnimationTypes: 'Cut,Fan,Merge,Rotate',",
        "} }];",
    ])
    set_to_code(node, js)
    save("Generate Dealer Stop Motion.json", wf)

# ── 2. Generate Card Narrations ───────────────────────────────────────────────

def update_card_narrations():
    wf = load("Generate Card Narrations.json")
    node = find_node(wf, "Set Global Parameters")
    js = config_header() + "\n".join([
        "return [{ json: {",
        "    // Machine-specific (from config.json)",
        "    DeckJsonPath:     config.DefaultDeckJsonPath,",
        "    ComfyUIAPI:       config.ComfyUIAPI,",
        "    ComfyUIOutputDir: config.ComfyUIOutputDir || (config.ComfyUIDir + '/output'),",
        "} }];",
    ])
    set_to_code(node, js)
    save("Generate Card Narrations.json", wf)

# ── 3. Generate Narration Styles ──────────────────────────────────────────────

def update_narration_styles():
    wf = load("Generate Narration Styles.json")
    node = find_node(wf, "Set Global Parameters")
    js = config_header() + "\n".join([
        "return [{ json: {",
        "    // Machine-specific (from config.json)",
        "    CardsDir:  config.DefaultDeckDir + '/Cards',",
        "    OllamaAPI: config.OllamaAPI,",
        "    // Workflow-specific",
        "    OllamaModel:  'mistral:latest',",
        "    SkipExisting: false,",
        "} }];",
    ])
    set_to_code(node, js)
    save("Generate Narration Styles.json", wf)

# ── 4. Update Card JSONs from Spreadsheet ─────────────────────────────────────

def update_card_jsons_spreadsheet():
    wf = load("Update Card JSONs from Spreadsheet.json")
    node = find_node(wf, "Set Global Parameters")
    js = config_header() + "\n".join([
        "return [{ json: {",
        "    // Machine-specific (from config.json)",
        "    SpreadsheetPath: config.SpreadsheetPath,",
        "    CardsDir:        config.DefaultDeckDir + '/Cards',",
        "    // Workflow-specific",
        "    SheetName: 'Character Prompts',",
        "} }];",
    ])
    set_to_code(node, js)
    save("Update Card JSONs from Spreadsheet.json", wf)

# ── 5. Normalize Deck Structure ───────────────────────────────────────────────

def update_normalize_deck_structure():
    wf = load("Normalize Deck Structure.json")
    trigger = find_trigger(wf)
    tx, ty = trigger['position']

    js_sgp = config_header() + "\n".join([
        "return [{ json: {",
        "    DeckJsonPath:         config.LegacyDeckJsonPath || (config.CardsDir + '/Deck.json'),",
        "    CardsDir:             config.CardsDir,",
        "    NormalizedOutputPath: config.CardsDir + '/Deck_normalized.json',",
        "} }];",
    ])
    wf, tname = insert_sgp_node(wf, "a1b2c3d4-0000-4000-8000-000000000000",
                                [tx + 224, ty], js_sgp)
    shift_others(wf, 224, {tname, "Set Global Parameters"})

    rn = find_node(wf, "Read Deck JSON")
    rn['parameters']['fileSelector'] = \
        "={{ $('Set Global Parameters').first().json.DeckJsonPath }}"

    cn = find_node(wf, "Convert to JSON File")
    cn['parameters']['options']['fileName'] = \
        "={{ $('Set Global Parameters').first().json.NormalizedOutputPath }}"

    code_node = find_node(wf, "Normalize Deck Structure")
    code_node['parameters']['jsCode'] = re.sub(
        r"const BASE_DIR = '[^']*';",
        "const BASE_DIR = $('Set Global Parameters').first().json.CardsDir + '/';",
        code_node['parameters']['jsCode']
    )
    save("Normalize Deck Structure.json", wf)

# ── 6. Generate Deck Structure ────────────────────────────────────────────────

def update_generate_deck_structure():
    wf = load("Generate Deck Structure.json")
    trigger = find_trigger(wf)
    tx, ty = trigger['position']

    js_sgp = config_header() + "\n".join([
        "return [{ json: {",
        "    DataDir:               config.DataDir,",
        "    LegacySpreadsheetPath: config.LegacySpreadsheetPath || (config.DataDir + '/CardImages.ods'),",
        "} }];",
    ])
    wf, tname = insert_sgp_node(wf, "gds0000-0001-4000-8000-000000000000",
                                [tx + 192, ty], js_sgp)
    shift_others(wf, 192, {tname, "Set Global Parameters"})

    rn = find_node(wf, "Read Character Image Spreadsheet")
    rn['parameters']['fileSelector'] = \
        "={{ $('Set Global Parameters').first().json.LegacySpreadsheetPath }}"

    cn = find_node(wf, "Change Card Name and Extract Orientation")
    update_assignment(cn, "Directory",
                      "={{ $('Set Global Parameters').first().json.DataDir }}")

    save("Generate Deck Structure.json", wf)

# ── 7. Generate Full Tarot Images ─────────────────────────────────────────────

def update_generate_full_tarot_images():
    wf = load("Generate Full Tarot Images.json")
    trigger = find_trigger(wf)
    tx, ty = trigger['position']

    js_sgp = config_header() + "\n".join([
        "return [{ json: {",
        "    FullImagesDir:         config.FullImagesDir         || (config.DataDir + '/Full_Images'),",
        "    ErrorsDir:             config.ErrorsDir             || (config.DataDir + '/errors'),",
        "    LegacySpreadsheetPath: config.LegacySpreadsheetPath || (config.DataDir + '/CardImages.ods'),",
        "    ComfyUIAPI:            config.ComfyUIAPI,",
        "} }];",
    ])
    wf, tname = insert_sgp_node(wf, "gfti0000-0001-4000-8000-000000000000",
                                [tx + 192, ty], js_sgp)
    shift_others(wf, 192, {tname, "Set Global Parameters"})

    rn = find_node(wf, "Read Character Image Spreadsheet")
    rn['parameters']['fileSelector'] = \
        "={{ $('Set Global Parameters').first().json.LegacySpreadsheetPath }}"

    cn = find_node(wf, "Change Card Name and Extract Orientation")
    update_assignment(cn, "Directory",
                      "={{ $('Set Global Parameters').first().json.FullImagesDir }}")

    en = find_node(wf, "Read/Write Files from Disk")
    if en:
        en['parameters']['fileName'] = \
            "={{ $('Set Global Parameters').first().json.ErrorsDir }}"

    save("Generate Full Tarot Images.json", wf)

# ── 8 & 9. Generate Card Tarot Images / Generate Pallette Tarot Images ────────

def update_card_or_pallette(filename, node_id):
    wf = load(filename)
    trigger = find_trigger(wf)
    tx, ty = trigger['position']

    js_sgp = config_header() + "\n".join([
        "return [{ json: {",
        "    FullImagesDir:     config.FullImagesDir     || (config.DataDir + '/Full_Images'),",
        "    CardPartImagesDir: config.CardPartImagesDir || (config.DataDir + '/Card_Part_Images'),",
        "} }];",
    ])
    wf, tname = insert_sgp_node(wf, node_id, [tx + 192, ty], js_sgp)
    shift_others(wf, 192, {tname, "Set Global Parameters"})

    # Try both exact node name variants (one has a double space)
    for node_name in ("Get Each Tarot Image on  Card", "Get Each Tarot Image on Card"):
        gn = find_node(wf, node_name)
        if gn:
            update_assignment(gn, "inputDirectory",
                              "={{ $('Set Global Parameters').first().json.FullImagesDir }}")
            update_assignment(gn, "OutputDirectory",
                              "={{ $('Set Global Parameters').first().json.CardPartImagesDir }}")

    fn = find_node(wf, "Filter to Only What is Needed")
    if fn:
        update_assignment(fn, "InputDirectory",
                          "={{ $('Set Global Parameters').first().json.FullImagesDir }}")
        update_assignment(fn, "OutputDirectory",
                          "={{ $('Set Global Parameters').first().json.CardPartImagesDir }}")

    save(filename, wf)

# ── 10. Add Meanings ──────────────────────────────────────────────────────────

def update_add_meanings():
    wf = load("Add Meanings.json")
    trigger = find_trigger(wf)
    tx, ty = trigger['position']

    js_sgp = config_header() + "\n".join([
        "return [{ json: {",
        "    DeckJsonPath: config.LegacyDeckJsonPath || (config.CardsDir + '/Deck.json'),",
        "    CardsDir:     config.CardsDir,",
        "} }];",
    ])
    wf, tname = insert_sgp_node(wf, "am0000-0001-4000-8000-000000000000",
                                [tx + 192, ty], js_sgp)
    shift_others(wf, 192, {tname, "Set Global Parameters"})

    rn = find_node(wf, "Read/Write Files from Disk")
    if rn:
        rn['parameters']['fileSelector'] = \
            "={{ $('Set Global Parameters').first().json.DeckJsonPath }}"

    wdn = find_node(wf, "Write the Deck to Disk")
    if wdn:
        # Rebuild: ={{ SGP.CardsDir }}{{ "\\" + $binary.data.fileName }}
        # The \\\\ in Python string = two backslash chars, which JSON.stringify → \\\\
        # which n8n sees as JS string "\\" = one backslash (path separator). Correct.
        wdn['parameters']['fileName'] = (
            "={{ $('Set Global Parameters').first().json.CardsDir }}"
            + '{{ "\\\\" + $binary.data.fileName }}'
        )

    save("Add Meanings.json", wf)

# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("Updating n8n workflows to use config.json...\n")
    update_dealer_stop_motion()
    update_card_narrations()
    update_narration_styles()
    update_card_jsons_spreadsheet()
    update_normalize_deck_structure()
    update_generate_deck_structure()
    update_generate_full_tarot_images()
    update_card_or_pallette("Generate Card Tarot Images.json",
                            "cti0000-0001-4000-8000-000000000000")
    update_card_or_pallette("Generate Pallette Tarot Images.json",
                            "cti0000-0002-4000-8000-000000000000")
    update_add_meanings()
    print("\nDone. All 10 workflows updated.")
