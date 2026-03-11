#!/usr/bin/env node
// ============================================================
// Workflow Integration Tests
// ============================================================
// Validates n8n workflow logic by extracting Code node JS
// and running it against mock data. No n8n or ComfyUI needed.
//
// Usage:  node tests/test_workflows.js
// ============================================================

const fs = require('fs');
const path = require('path');
const os = require('os');
const vm = require('vm');

// ── Test framework ──────────────────────────────────────────
let passed = 0;
let failed = 0;
const failures = [];

function assert(condition, message) {
  if (condition) {
    passed++;
  } else {
    failed++;
    failures.push(message);
    console.log('  FAIL: ' + message);
  }
}

function assertEqual(actual, expected, message) {
  if (actual === expected) {
    passed++;
  } else {
    failed++;
    const detail = message + ' (expected ' + JSON.stringify(expected) + ', got ' + JSON.stringify(actual) + ')';
    failures.push(detail);
    console.log('  FAIL: ' + detail);
  }
}

function assertIncludes(arr, value, message) {
  assert(arr.includes(value), message + ' — missing: ' + value);
}

function section(name) {
  console.log('\n=== ' + name + ' ===');
}

// ── Load workflows ──────────────────────────────────────────
const ROOT = path.resolve(__dirname, '..');
const normWf = JSON.parse(fs.readFileSync(path.join(ROOT, 'n8n/Normalize Deck Structure.json'), 'utf8'));
const obj3dWf = JSON.parse(fs.readFileSync(path.join(ROOT, 'n8n/Generate Card 3D Objects.json'), 'utf8'));
const musicWf = JSON.parse(fs.readFileSync(path.join(ROOT, 'n8n/Generate Card Music.json'), 'utf8'));

function getCodeNode(wf, name) {
  const node = wf.nodes.find(n => n.name === name);
  if (!node) throw new Error('Node not found: ' + name);
  return node.parameters.jsCode;
}

// ============================================================
// TEST 1: Normalizer v0.4 — buildRecordAssets()
// ============================================================
section('Normalizer v0.4 — buildRecordAssets');

(function testBuildRecordAssets() {
  const code = getCodeNode(normWf, 'Normalize Deck Structure');

  // Extract buildRecordAssets function
  const funcMatch = code.match(/(function buildRecordAssets\([\s\S]*?\n\})/);
  assert(funcMatch !== null, 'buildRecordAssets function exists in normalizer');
  if (!funcMatch) return;

  // Run the function in isolation
  const testScript = funcMatch[1] + '\n' +
    'module.exports = { buildRecordAssets };';

  const tmpFile = path.join(os.tmpdir(), 'test_buildRecordAssets_' + Date.now() + '.js');
  fs.writeFileSync(tmpFile, testScript);
  const { buildRecordAssets } = require(tmpFile);

  // Test upright orientation
  const upright = buildRecordAssets('Ace_of_Cups', 'upright');
  assertEqual(upright.Image, 'IMG_Ace_of_Cups_upright.png', 'upright Image filename');
  assertEqual(upright.BackView, 'BACKVIEW_Ace_of_Cups_upright.png', 'upright BackView filename');
  assertEqual(upright.ObjectGLB, 'MODEL_Ace_of_Cups_upright.glb', 'upright ObjectGLB filename');
  assertEqual(upright.Object3DRef, '3DREF_Ace_of_Cups_upright.png', 'upright Object3DRef filename');
  assertEqual(upright.Object, 'MODEL_Ace_of_Cups_upright.obj', 'upright Object (OBJ) filename');
  assertEqual(upright.Music, 'MUSIC_Ace_of_Cups_upright.mp3', 'upright Music filename');
  assertEqual(upright.Narration, 'NARRATION_Ace_of_Cups_upright.mp3', 'upright Narration filename');

  // Upright-only fields
  assert(Array.isArray(upright.FocusUprightT), 'upright has FocusUprightT array');
  assert(Array.isArray(upright.FocusUprightBlend), 'upright has FocusUprightBlend array');
  assert(upright.FocusReversedT === undefined, 'upright does NOT have FocusReversedT');
  assert(upright.FocusReversedBlend === undefined, 'upright does NOT have FocusReversedBlend');
  assert(upright.CardImageUpright === undefined, 'upright does NOT have CardImageUpright');

  // Test reversed orientation
  const reversed = buildRecordAssets('Ace_of_Cups', 'reversed');
  assertEqual(reversed.BackView, 'BACKVIEW_Ace_of_Cups_reversed.png', 'reversed BackView filename');
  assertEqual(reversed.ObjectGLB, 'MODEL_Ace_of_Cups_reversed.glb', 'reversed ObjectGLB filename');
  assertEqual(reversed.CardImageUpright, 'CARDIMGUPRIGHT_Ace_of_Cups_reversed.png', 'reversed CardImageUpright filename');
  assert(Array.isArray(reversed.FocusReversedT), 'reversed has FocusReversedT array');
  assert(Array.isArray(reversed.FocusReversedBlend), 'reversed has FocusReversedBlend array');
  assert(reversed.FocusUprightT === undefined, 'reversed does NOT have FocusUprightT');

  // Test between orientation
  const between = buildRecordAssets('The_Fool', 'between');
  assertEqual(between.CardImageUpright, 'CARDIMGUPRIGHT_The_Fool_between.png', 'between CardImageUpright filename');
  assert(between.FocusUprightT === undefined, 'between does NOT have FocusUprightT');
  assert(between.FocusReversedT === undefined, 'between does NOT have FocusReversedT');

  fs.unlinkSync(tmpFile);
})();

// ============================================================
// TEST 2: Normalizer v0.4 — normalizeRecord with existing data
// ============================================================
section('Normalizer v0.4 — normalizeRecord preserves existing data');

(function testNormalizeRecord() {
  const code = getCodeNode(normWf, 'Normalize Deck Structure');

  // Extract both functions needed
  const buildRecordMatch = code.match(/(function buildRecordAssets\([\s\S]*?\n\})/);
  const buildImageMatch = code.match(/(function buildImagePrompts\([\s\S]*?\n\})/);
  const buildNarrationMatch = code.match(/(function buildNarrationPrompts\([\s\S]*?\n\})/);
  const buildMusicMatch = code.match(/(function buildMusicPrompts\([\s\S]*?\n\})/);
  const normalizeMatch = code.match(/(function normalizeRecord\([\s\S]*?\n\})/);

  assert(normalizeMatch !== null, 'normalizeRecord function exists');
  if (!normalizeMatch || !buildRecordMatch) return;

  const testScript = [
    buildRecordMatch[1],
    buildImageMatch[1],
    buildNarrationMatch[1],
    buildMusicMatch[1],
    normalizeMatch[1],
    'module.exports = { normalizeRecord };'
  ].join('\n\n');

  const tmpFile = path.join(os.tmpdir(), 'test_normalizeRecord_' + Date.now() + '.js');
  fs.writeFileSync(tmpFile, testScript);
  const { normalizeRecord } = require(tmpFile);

  // Test: existing record with populated data
  const existingRecord = {
    Orientation: 'upright',
    Description: 'A golden cup overflowing',
    Meanings: ['love', 'joy'],
    Keywords: ['emotional', 'intuitive'],
    Assets: {
      Image: 'custom_image.png',
      FocusUprightT: ['still1.png', 'still2.png'],
      FocusUprightBlend: ['blend1.png']
    },
    Prompts: {
      Image: { Positive: 'custom positive', Negative: 'custom negative' },
      Narration: { Voice: 'Male', Tone: 'Deep' },
      Music: { Tags: 'ambient harp', BPM: 72, KeyScale: 'C Major' }
    }
  };

  const result = normalizeRecord(existingRecord, 'Ace of Cups', 'Ace_of_Cups', 'upright');

  // Should preserve existing values
  assertEqual(result.Assets.Image, 'custom_image.png', 'preserves existing Image asset');
  assertEqual(result.Assets.FocusUprightT.length, 2, 'preserves existing FocusUprightT array');
  assertEqual(result.Assets.FocusUprightT[0], 'still1.png', 'preserves FocusUprightT[0] value');
  assertEqual(result.Prompts.Image.Positive, 'custom positive', 'preserves existing Image prompt');
  assertEqual(result.Prompts.Music.Tags, 'ambient harp', 'preserves existing Music tags');

  // Should fill in missing fields with defaults
  assertEqual(result.Assets.BackView, 'BACKVIEW_Ace_of_Cups_upright.png', 'fills missing BackView with default');
  assertEqual(result.Assets.ObjectGLB, 'MODEL_Ace_of_Cups_upright.glb', 'fills missing ObjectGLB with default');
  assertEqual(result.Assets.Object3DRef, '3DREF_Ace_of_Cups_upright.png', 'fills missing Object3DRef with default');
  assertEqual(result.Description, 'A golden cup overflowing', 'preserves Description');

  // Test: empty record gets all defaults
  const emptyResult = normalizeRecord({}, 'The Fool', 'The_Fool', 'reversed');
  assertEqual(emptyResult.Assets.BackView, 'BACKVIEW_The_Fool_reversed.png', 'empty record gets BackView default');
  assertEqual(emptyResult.Assets.CardImageUpright, 'CARDIMGUPRIGHT_The_Fool_reversed.png', 'empty reversed gets CardImageUpright');
  assert(Array.isArray(emptyResult.Assets.FocusReversedT), 'empty reversed gets FocusReversedT array');
  assertEqual(emptyResult.Assets.FocusReversedT.length, 0, 'empty reversed FocusReversedT is empty array');
  assertEqual(emptyResult.Prompts.Music.Tags, '', 'empty record gets blank Music tags');

  fs.unlinkSync(tmpFile);
})();

// ============================================================
// TEST 3: Normalizer v0.4 — deck-level assets
// ============================================================
section('Normalizer v0.4 — deck-level assets');

(function testDeckLevelAssets() {
  const code = getCodeNode(normWf, 'Normalize Deck Structure');

  // Check that deck-level asset keys are present in the code
  const deckAssetKeys = [
    'MusicDirectory', 'NarrationDirectory', 'AnimationKeyframes',
    'Directory', 'BackImage', 'FrontImage', 'Music', 'Narration',
    'Cut', 'Fan', 'Merge', 'Rotate'
  ];

  for (const key of deckAssetKeys) {
    assert(code.includes(key), 'deck-level asset key present: ' + key);
  }

  // Verify DECK_VERSION
  const versionMatch = code.match(/DECK_VERSION\s*=\s*([\d.]+)/);
  assert(versionMatch !== null, 'DECK_VERSION constant exists');
  if (versionMatch) {
    assertEqual(parseFloat(versionMatch[1]), 0.4, 'DECK_VERSION is 0.4');
  }
})();

// ============================================================
// TEST 4: Refine 3D Meshes — node logic
// ============================================================
section('Refine 3D Meshes — node logic');

(function testRefineMeshes() {
  const code = getCodeNode(obj3dWf, 'Refine 3D Meshes');

  // Check key logic branches
  assert(code.includes("item.Status !== 'generated'"), 'skips non-generated items');
  assert(code.includes("Status: 'refined'"), 'sets Status to refined on success');
  assert(code.includes("Status: 'generated'"), 'falls back to generated on refinement failure');
  assert(code.includes("Status: 'failed'"), 'sets Status to failed on critical error');
  assert(code.includes('GLBPath'), 'outputs GLBPath field');
  assert(code.includes('GLBSizeKB'), 'outputs GLBSizeKB field');
  assert(code.includes('RefinementStats'), 'outputs RefinementStats field');
  assert(code.includes('RefinementError'), 'outputs RefinementError on fallback');

  // Check Python trimesh operations
  assert(code.includes('remove_degenerate_faces'), 'Python: removes degenerate faces');
  assert(code.includes('remove_duplicate_faces'), 'Python: removes duplicate faces');
  assert(code.includes('fill_holes'), 'Python: fills holes');
  assert(code.includes('simplify_quadric_decimation'), 'Python: decimation to target faces');
  assert(code.includes('target_faces = 50000'), 'Python: target is 50k faces');
  assert(code.includes('filter_laplacian'), 'Python: Laplacian smoothing');
  assert(code.includes('iterations=5'), 'Python: 5 smoothing iterations');
  assert(code.includes('fix_normals'), 'Python: fixes normals');

  // Check file operations
  assert(code.includes('copyFileSync'), 'copies GLB from ComfyUI output');
  assert(code.includes("comfyOutputDir = 'D:/ComfyUI_windows_portable/ComfyUI/output'"), 'correct ComfyUI output dir');

  // Check 3D reference image copy
  assert(code.includes('3DREF_'), 'copies 3D reference images');
})();

// ============================================================
// TEST 5: Upscale Textures — node logic
// ============================================================
section('Upscale Textures — node logic');

(function testUpscaleTextures() {
  const code = getCodeNode(obj3dWf, 'Upscale Textures');

  // Check it accepts both statuses
  assert(code.includes("item.Status !== 'refined'"), 'checks for refined status');
  assert(code.includes("item.Status !== 'generated'"), 'checks for generated status');

  // Check graceful fallbacks
  assert(code.includes('no_pillow'), 'handles missing Pillow gracefully');
  assert(code.includes('no_textures'), 'handles no textures gracefully');
  assert(code.includes('TextureUpscaled'), 'sets TextureUpscaled flag on success');

  // Check Python Pillow operations
  assert(code.includes('from PIL import Image'), 'Python: imports Pillow');
  assert(code.includes('Image.LANCZOS'), 'Python: uses LANCZOS resampling');
  assert(code.includes('w * 2, h * 2'), 'Python: 2x upscale');
  assert(code.includes('>= 2048'), 'Python: skips already large textures (2048+)');
  assert(code.includes('.export(glb_path)'), 'Python: re-exports GLB in place');

  // Check item passthrough
  assert(code.includes('results.push(item)'), 'passes through items even on skip/failure');
})();

// ============================================================
// TEST 6: Music seamless loop crossfade
// ============================================================
section('Music seamless loop crossfade');

(function testMusicCrossfade() {
  const code = getCodeNode(musicWf, 'Generate All Music');

  // Check CROSSFADE_DURATION constant
  const xfadeMatch = code.match(/CROSSFADE_DURATION\s*=\s*(\d+)/);
  assert(xfadeMatch !== null, 'CROSSFADE_DURATION constant exists');
  if (xfadeMatch) {
    assertEqual(parseInt(xfadeMatch[1]), 2, 'CROSSFADE_DURATION is 2 seconds');
  }

  // Check makeSeamlessLoop function exists
  assert(code.includes('function makeSeamlessLoop('), 'makeSeamlessLoop function exists');

  // Check ffmpeg filter chain components
  assert(code.includes('asplit=3'), 'splits audio into 3 streams');
  assert(code.includes('atrim=start='), 'trims main body start');
  assert(code.includes('atrim=end='), 'trims head section');
  assert(code.includes('acrossfade'), 'uses acrossfade filter');
  assert(code.includes('c1=tri:c2=tri'), 'uses triangular crossfade curves');
  assert(code.includes('concat=n=2:v=0:a=1'), 'concatenates main + crossfade');

  // Check safe rename/restore pattern
  assert(code.includes('_preloop.mp3'), 'renames to _preloop.mp3 before processing');
  assert(code.includes('renameSync'), 'uses renameSync for safe swap');
  assert(code.includes('unlinkSync'), 'cleans up temp file on success');

  // Check fallback behavior
  assert(code.includes('return false'), 'returns false on failure');
  assert(code.includes('return true'), 'returns true on success');
  // Verify it restores original on failure
  assert(code.match(/catch.*\{[\s\S]*?renameSync\(tmpPath, inputPath\)/), 'restores original file on failure');

  // Check call order: postProcessAudio before makeSeamlessLoop
  const postProcessIdx = code.indexOf('postProcessAudio');
  const loopCallIdx = code.indexOf('makeSeamlessLoop(targetPath');
  assert(loopCallIdx > postProcessIdx, 'makeSeamlessLoop called after postProcessAudio');

  // Check DECK_DURATION is used (from Deck.json)
  assert(code.includes('DECK_DURATION'), 'uses DECK_DURATION for calculating crossfade points');
})();

// ============================================================
// TEST 7: Artist override / SkipExisting logic
// ============================================================
section('Artist override / SkipExisting logic');

(function testSkipExisting() {
  const code = getCodeNode(obj3dWf, 'Build 3D Job List');

  // Check SkipExisting parameter
  assert(code.includes("params.SkipExisting !== 'false'"), 'SkipExisting defaults to true');
  assert(code.includes('skipExisting && fs.existsSync(glbPath)'), 'checks GLB existence when SkipExisting=true');
  assert(code.includes('GLB exists, skipping'), 'logs skip message for existing GLBs');

  // Check BackView insertable asset support
  assert(code.includes('BackViewExists'), 'passes BackViewExists flag in job');
  assert(code.includes('fs.existsSync(backViewPath)'), 'checks for existing back-view image');

  // Verify back-view generation node respects BackViewExists
  const backViewCode = getCodeNode(obj3dWf, 'Generate Back-View Images');
  assert(backViewCode.includes('BackViewExists'), 'back-view generator checks BackViewExists');

  // Check file naming convention matches insertable asset pattern
  assert(code.includes("'BACKVIEW_' + cardSlug"), 'back-view uses BACKVIEW_ prefix convention');
  assert(code.includes("'MODEL_' + cardSlug"), 'GLB uses MODEL_ prefix convention');
  assert(code.includes("'3DREF_' + cardSlug"), '3D ref uses 3DREF_ prefix convention');

  // Check that error messages are informative
  assert(code.includes('Set SkipExisting=false to regenerate'), 'error message suggests SkipExisting=false');
  assert(code.includes('Missing images:'), 'error reports missing images');
})();

// ============================================================
// TEST 8: Workflow structure integrity
// ============================================================
section('Workflow structure integrity');

(function testWorkflowStructure() {
  const workflows = {
    'Generate Card 3D Objects': obj3dWf,
    'Generate Card Music': musicWf,
    'Normalize Deck Structure': normWf
  };

  for (const [name, wf] of Object.entries(workflows)) {
    // Valid top-level structure
    assert(Array.isArray(wf.nodes) && wf.nodes.length > 0, name + ': has nodes array');
    assert(typeof wf.connections === 'object', name + ': has connections object');

    // No duplicate IDs
    const ids = wf.nodes.map(n => n.id);
    const uniqueIds = new Set(ids);
    assertEqual(ids.length, uniqueIds.size, name + ': no duplicate node IDs');

    // No duplicate names
    const names = wf.nodes.map(n => n.name);
    const uniqueNames = new Set(names);
    assertEqual(names.length, uniqueNames.size, name + ': no duplicate node names');

    // All nodes have required fields
    for (const node of wf.nodes) {
      assert(node.id !== undefined, name + '/' + node.name + ': has id');
      assert(node.type !== undefined, name + '/' + node.name + ': has type');
      assert(node.position !== undefined, name + '/' + node.name + ': has position');
    }

    // All connection targets reference existing nodes
    const nodeNameSet = new Set(wf.nodes.map(n => n.name));
    for (const [src, outputs] of Object.entries(wf.connections)) {
      assert(nodeNameSet.has(src), name + ': connection source exists: ' + src);
      if (outputs.main) {
        for (const targets of outputs.main) {
          for (const t of targets) {
            assert(nodeNameSet.has(t.node), name + ': connection target exists: ' + t.node + ' (from ' + src + ')');
          }
        }
      }
    }
  }
})();

// ============================================================
// TEST 9: 3D pipeline node chain order
// ============================================================
section('3D pipeline node chain order');

(function testPipelineOrder() {
  const expectedOrder = [
    "When clicking 'Execute workflow'",
    'Set Global Parameters',
    'Read Deck.json',
    'Extract from File',
    'Build 3D Job List',
    'Generate Back-View Images',
    'Generate All 3D Models',
    'Refine 3D Meshes',
    'Upscale Textures',
    'Convert GLB to OBJ',
    'Report Results'
  ];

  // Walk the connection chain from the trigger
  const chain = [expectedOrder[0]];
  let current = expectedOrder[0];
  for (let i = 0; i < 20; i++) {
    const conn = obj3dWf.connections[current];
    if (!conn || !conn.main || !conn.main[0] || conn.main[0].length === 0) break;
    current = conn.main[0][0].node;
    chain.push(current);
  }

  assertEqual(chain.length, expectedOrder.length, '3D pipeline has ' + expectedOrder.length + ' nodes in chain');

  for (let i = 0; i < expectedOrder.length; i++) {
    assertEqual(chain[i], expectedOrder[i], 'pipeline step ' + (i + 1) + ': ' + expectedOrder[i]);
  }
})();

// ============================================================
// TEST 10: Code node JS syntax validation
// ============================================================
section('Code node JS syntax validation');

(function testJSSyntax() {
  const allCodeNodes = [
    { wf: normWf, wfName: 'Normalizer' },
    { wf: obj3dWf, wfName: '3D Objects' },
    { wf: musicWf, wfName: 'Music' }
  ];

  for (const { wf, wfName } of allCodeNodes) {
    const codeNodes = wf.nodes.filter(n => n.type === 'n8n-nodes-base.code');
    for (const node of codeNodes) {
      const code = node.parameters.jsCode;
      const wrapped = '(async () => {\n' + code + '\n})';
      try {
        vm.compileFunction(wrapped);
        passed++;
      } catch (e) {
        failed++;
        const msg = wfName + '/' + node.name + ': JS syntax error — ' + e.message;
        failures.push(msg);
        console.log('  FAIL: ' + msg);
      }
    }
  }
  // Report count
  const totalCodeNodes = allCodeNodes.reduce((sum, x) => sum + x.wf.nodes.filter(n => n.type === 'n8n-nodes-base.code').length, 0);
  console.log('  Checked ' + totalCodeNodes + ' code nodes across all workflows');
})();

// ── Summary ─────────────────────────────────────────────────
console.log('\n' + '='.repeat(50));
console.log('Results: ' + passed + ' passed, ' + failed + ' failed');
if (failures.length > 0) {
  console.log('\nFailures:');
  failures.forEach((f, i) => console.log('  ' + (i + 1) + '. ' + f));
  process.exit(1);
} else {
  console.log('All tests passed!');
  process.exit(0);
}
