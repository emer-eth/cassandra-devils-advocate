"""Cassandra avatar — 1:1 square, gold serif monogram on near-black.
Matches the landing page palette so the listing and the endpoint look like
one product. Rendered at 4x then downsampled for clean edges.
"""
from PIL import Image, ImageDraw, ImageFont

S = 1024          # final size
X = 4             # supersample factor
W = S * X

BG    = (18, 16, 13)
GOLD  = (201, 165, 92)
GOLD_D= (138, 109, 47)
CREAM = (236, 231, 221)

img = Image.new("RGB", (W, W), BG)
d = ImageDraw.Draw(img)

# --- soft centre glow ------------------------------------------------------
# Drawn tiny and scaled up: stepped rectangles produced visible concentric
# banding, which reads as a rendering artifact rather than depth.
GLOW = 96
glow = Image.new("L", (GLOW, GLOW), 0)
gd = ImageDraw.Draw(glow)
for i in range(GLOW // 2, 0, -1):
    t = i / (GLOW / 2)
    gd.ellipse([GLOW / 2 - i, GLOW / 2 - i, GLOW / 2 + i, GLOW / 2 + i],
               fill=int(38 * (1 - t) ** 1.6))
img = Image.composite(
    Image.new("RGB", (W, W), (38, 33, 26)), img, glow.resize((W, W), Image.LANCZOS))
d = ImageDraw.Draw(img)

# --- outer hairline frame (editorial, not techy) ---------------------------
m = int(W * 0.055)
d.rectangle([m, m, W - m, W - m], outline=GOLD_D, width=max(2, W // 340))

# --- the ring the monogram sits in ----------------------------------------
cx = cy = W // 2
r = int(W * 0.315)
d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GOLD, width=max(3, W // 150))

# --- monogram ------------------------------------------------------------
def load(size):
    for path, idx in (("/System/Library/Fonts/Palatino.ttc", 0),
                      ("/System/Library/Fonts/Times.ttc", 0),
                      ("/Library/Fonts/Georgia.ttf", None)):
        try:
            return (ImageFont.truetype(path, size, index=idx) if idx is not None
                    else ImageFont.truetype(path, size))
        except (OSError, ValueError):
            continue
    return ImageFont.load_default()

font = load(int(W * 0.42))
letter = "C"
box = d.textbbox((0, 0), letter, font=font)
d.text((cx - (box[0] + box[2]) / 2, cy - (box[1] + box[3]) / 2 - W * 0.012),
       letter, font=font, fill=CREAM)

# --- two ticks on the ring: the argument has two sides --------------------
tick = int(W * 0.052)
for side in (-1, 1):
    d.line([cx + side * r - side * tick // 2, cy, cx + side * r + side * tick // 2, cy],
           fill=BG, width=max(4, W // 110))
    d.line([cx + side * r - side * tick // 2, cy, cx + side * r + side * tick // 2, cy],
           fill=GOLD, width=max(2, W // 300))

img = img.resize((S, S), Image.LANCZOS)
out = "/private/tmp/claude-501/-Users-emer/169de1c3-4070-4ad9-8593-e16498130868/scratchpad/cassandra-avatar.png"
img.save(out, "PNG", optimize=True)

import os
print(f"{out}  {img.size[0]}x{img.size[1]}  {os.path.getsize(out) / 1024:.0f} KB")
