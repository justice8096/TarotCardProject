"""
make_keyframes.py — Generate composite keyframe images for the dealer animation pipeline.

Reads IMAGE_Deck_Back.png and IMAGE_Deck_Front.png from the path in Deck.json and
produces 12 keyframe PNGs in the AnimationKeyframes directory. These are used by the
n8n "Generate Dealer Stop Motion" workflow as anchor frames for Wan I2V interpolation.

Usage:
    python make_keyframes.py [deck_json_path]

    deck_json_path defaults to D:/data/cards/Standard/Deck.json
"""

import json
import math
import os
import sys
from PIL import Image

# ── Load Deck.json ─────────────────────────────────────────────────────────────

DECK_JSON = sys.argv[1] if len(sys.argv) > 1 else 'D:/data/cards/Standard/Deck.json'

with open(DECK_JSON, 'r') as f:
    raw = json.load(f)
deck = raw.get('data', raw)   # handle both wrapped and unwrapped

assets    = deck['Assets']
geom      = deck['Geometries']['Animation']
KF_DIR    = assets['AnimationKeyframes']
BACK_PATH = assets['BackImage']
FRONT_PATH = assets['FrontImage']

W = geom['Width']    # 832
H = geom['Height']   # 480

os.makedirs(KF_DIR, exist_ok=True)

# ── Canvas background colour (dark green felt) ─────────────────────────────────

FELT = (15, 60, 20, 255)

# ── Helper functions ───────────────────────────────────────────────────────────

def scale_card(img, w):
    """Scale an image to width w, preserving aspect ratio."""
    h = int(img.height * w / img.width)
    return img.resize((w, h), Image.LANCZOS)


def make_canvas():
    return Image.new('RGBA', (W, H), FELT)


def clip_paste(canvas, img, cx, cy):
    """Alpha-composite img centred at (cx, cy), clipping to canvas bounds."""
    px, py = cx - img.width // 2, cy - img.height // 2
    sx0, sy0 = max(0, -px), max(0, -py)
    sx1, sy1 = min(img.width, W - px), min(img.height, H - py)
    dx, dy   = max(0, px), max(0, py)
    if sx0 < sx1 and sy0 < sy1:
        canvas.alpha_composite(img.crop((sx0, sy0, sx1, sy1)), (dx, dy))


def darken(img, factor):
    """Return a darkened copy of an RGBA image (factor 0.0–1.0)."""
    r, g, b, a = img.split()
    return Image.merge('RGBA', (
        r.point(lambda p: int(p * factor)),
        g.point(lambda p: int(p * factor)),
        b.point(lambda p: int(p * factor)),
        a
    ))


def draw_stack(canvas, card, cx, cy, n, dx=2, dy=-1):
    """
    Draw a stack of n cards.

    Top card is at (cx, cy); each deeper card is offset by (dx, dy).
    Cards are drawn bottom-to-top so the top card appears on top visually.
    Deeper cards are slightly darkened to suggest depth.

    Args:
        dx: horizontal offset per depth level (positive = right)
        dy: vertical offset per depth level (negative = up = stack recedes away)
    """
    for i in range(n - 1, -1, -1):     # i=0 → top card (drawn last)
        brightness = max(0.60, 1.0 - i * 0.038)
        clip_paste(canvas, darken(card, brightness), cx + i * dx, cy + i * dy)


def draw_fan(canvas, card, pivot_x, pivot_y, n, a0, a1, radius):
    """
    Draw n cards in an arc (fan).

    Each card's centre is placed at `radius` from (pivot_x, pivot_y) at the
    corresponding angle. pivot_y is typically set below the canvas bottom so
    that the fan opens upward naturally.

    Args:
        a0, a1: start and end angles in degrees (0 = straight up, +ve = right)
        radius: distance from pivot to card centre in pixels
    """
    for i in range(n):
        t     = i / max(n - 1, 1)
        angle = a0 + t * (a1 - a0)
        ar    = math.radians(angle)
        cx    = int(pivot_x + radius * math.sin(ar))
        cy    = int(pivot_y - radius * math.cos(ar))
        rot   = card.rotate(-angle, expand=True, resample=Image.BICUBIC)
        clip_paste(canvas, rot, cx, cy)


def save(img, filename):
    path = os.path.join(KF_DIR, filename)
    img.convert('RGB').save(path)
    print(f'  {filename}')


# ── Load and scale card images ─────────────────────────────────────────────────

print(f'Loading card images from {os.path.dirname(BACK_PATH)}...')
back  = Image.open(BACK_PATH).convert('RGBA')
front = Image.open(FRONT_PATH).convert('RGBA')

# Card variants at different sizes
sc = scale_card(back,  95)    # stack card  (95 × ~152 px)
fc = scale_card(back,  60)    # fan card    (60 × ~96 px)
sb = scale_card(back, 255)    # single large back  (255 × ~408 px)
sf = scale_card(front, 255)   # single large front

# Fan pivot — far below canvas so cards open upward
FPX, FPY, FR = W // 2, H + 280, 340

print(f'\nWriting keyframes to {KF_DIR}...')

# ── CUT ────────────────────────────────────────────────────────────────────────
# Frame 0: complete deck stacked at centre
img = make_canvas()
draw_stack(img, sc, W // 2, H // 2, 10)
save(img, 'KF_Cut_0.png')

# Frame 1: deck split — top half raised on left, bottom half lower on right
img = make_canvas()
draw_stack(img, sc, W // 3,     H // 2 - 32, 5)   # top half, lifted
draw_stack(img, sc, 2 * W // 3, H // 2 + 14, 5)   # bottom half, resting
save(img, 'KF_Cut_1.png')

# Frame 2: deck reassembled
img = make_canvas()
draw_stack(img, sc, W // 2, H // 2, 10)
save(img, 'KF_Cut_2.png')

# ── FAN ────────────────────────────────────────────────────────────────────────
# Frame 0: deck as a square stack
img = make_canvas()
draw_stack(img, fc, W // 2, H // 2, 10)
save(img, 'KF_Fan_0.png')

# Frame 1: partial fan (12 cards, ±28°)
img = make_canvas()
draw_fan(img, fc, FPX, FPY, 12, -28, 28, FR)
save(img, 'KF_Fan_1.png')

# Frame 2: full fan (22 cards, ±58°)
img = make_canvas()
draw_fan(img, fc, FPX, FPY, 22, -58, 58, FR)
save(img, 'KF_Fan_2.png')

# ── MERGE ──────────────────────────────────────────────────────────────────────
# Frame 0: two separate half-stacks, far apart
img = make_canvas()
draw_stack(img, sc, W // 4,     H // 2, 5)
draw_stack(img, sc, 3 * W // 4, H // 2, 5)
save(img, 'KF_Merge_0.png')

# Frame 1: halves brought close (about to interleave)
img = make_canvas()
draw_stack(img, sc, W // 2 - 80, H // 2, 5)
draw_stack(img, sc, W // 2 + 80, H // 2, 5)
save(img, 'KF_Merge_1.png')

# Frame 2: merged single deck
img = make_canvas()
draw_stack(img, sc, W // 2, H // 2, 10)
save(img, 'KF_Merge_2.png')

# ── ROTATE ─────────────────────────────────────────────────────────────────────
# Frame 0: single card face-down (card back)
img = make_canvas()
clip_paste(img, sb, W // 2, H // 2)
save(img, 'KF_Rotate_0.png')

# Frame 1: card edge-on (mid-flip) — squished to ~12% width
edge_w = max(6, int(sb.width * 0.12))
edge   = sb.resize((edge_w, sb.height), Image.LANCZOS)
img    = make_canvas()
clip_paste(img, edge, W // 2, H // 2)
save(img, 'KF_Rotate_1.png')

# Frame 2: single card face-up (card front)
img = make_canvas()
clip_paste(img, sf, W // 2, H // 2)
save(img, 'KF_Rotate_2.png')

# ── Done ───────────────────────────────────────────────────────────────────────
print(f'\nAll 12 keyframes written to {KF_DIR}')
print()
print('Tip: delete any KF_*.png file to let the AI regenerate that frame.')
print('Tip: replace any KF_*.png with your own 832×480 image to use custom art.')
