"""X/Twitter header for Cassandra — 1500x500, same palette as the site.

Layout respects X's crop behaviour: the avatar overlaps the lower-left, and
mobile crops the sides, so the composition stays in the middle band and keeps
the bottom-left ~320px clear.
"""
from PIL import Image, ImageDraw, ImageFont

W, H, X = 1500, 500, 3          # X = supersample factor
CW, CH = W * X, H * X

BG    = (16, 14, 12)
GOLD  = (201, 165, 92)
GOLD_D= (120, 96, 44)
CREAM = (236, 231, 221)
DIM   = (150, 142, 128)
RED   = (196, 84, 68)

img = Image.new("RGB", (CW, CH), BG)
d = ImageDraw.Draw(img)


def font(size, mono=False):
    paths = (["/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Courier.ttc"]
             if mono else
             ["/System/Library/Fonts/Palatino.ttc", "/System/Library/Fonts/Times.ttc"])
    for p in paths:
        try:
            return ImageFont.truetype(p, size, index=0)
        except (OSError, ValueError):
            continue
    return ImageFont.load_default()


# soft centre glow, drawn small and scaled so there is no banding
G = 110
glow = Image.new("L", (G, G), 0)
gd = ImageDraw.Draw(glow)
for i in range(G // 2, 0, -1):
    t = i / (G / 2)
    gd.ellipse([G/2 - i, G/2 - i, G/2 + i, G/2 + i], fill=int(34 * (1 - t) ** 1.7))
img = Image.composite(Image.new("RGB", (CW, CH), (40, 35, 27)), img,
                      glow.resize((CW, CH), Image.LANCZOS).crop((0, 0, CW, CH)))
d = ImageDraw.Draw(img)

# hairline frame
m = 26 * X
d.rectangle([m, m, CW - m, CH - m], outline=GOLD_D, width=max(2, X))

# ---- the line, left-aligned but clear of the avatar ----
left = 118 * X
f_big = font(52 * X)
f_sm = font(21 * X)
f_mono = font(17 * X, mono=True)

y = 150 * X
l1a, l1b, l1c = "Every agent is built to say ", "yes", "."
w_a = d.textlength(l1a, font=f_big)
w_b = d.textlength(l1b, font=f_big)
d.text((left, y), l1a, font=f_big, fill=DIM)
d.text((left + w_a, y), l1b, font=f_big, fill=DIM)
d.text((left + w_a + w_b, y), l1c, font=f_big, fill=DIM)
# strike through "yes"
sy = y + int(34 * X)
d.line([left + w_a - 3 * X, sy, left + w_a + w_b + 3 * X, sy], fill=RED, width=max(3, X * 2))

y2 = y + int(74 * X)
l2a, l2b, l2c = "Cassandra is built to say ", "no", "."
w2a = d.textlength(l2a, font=f_big)
w2b = d.textlength(l2b, font=f_big)
d.text((left, y2), l2a, font=f_big, fill=CREAM)
d.text((left + w2a, y2), l2b, font=f_big, fill=GOLD)
d.text((left + w2a + w2b, y2), l2c, font=f_big, fill=CREAM)

# strap + endpoint, kept above the avatar zone
y3 = y2 + int(88 * X)
d.text((left, y3), "State a plan. It argues against it — and concedes when you are right.",
       font=f_sm, fill=DIM)
d.text((left, y3 + int(34 * X)), "cassandra-devils-advocate.vercel.app  ·  an A2MCP service on OKX AI",
       font=f_mono, fill=GOLD_D)

# ---- monogram, right side ----
cx, cy, r = CW - 170 * X, CH // 2, 92 * X
d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GOLD, width=max(3, X * 2))
fc = font(118 * X)
box = d.textbbox((0, 0), "C", font=fc)
d.text((cx - (box[0] + box[2]) / 2, cy - (box[1] + box[3]) / 2 - 4 * X),
       "C", font=fc, fill=CREAM)
tick = 15 * X
for side in (-1, 1):
    d.line([cx + side * r - side * tick // 2, cy, cx + side * r + side * tick // 2, cy],
           fill=BG, width=max(4, X * 3))
    d.line([cx + side * r - side * tick // 2, cy, cx + side * r + side * tick // 2, cy],
           fill=GOLD, width=max(2, X))

img = img.resize((W, H), Image.LANCZOS)
out = "banner.png"
img.save(out, "PNG", optimize=True)

import os
print(f"{out}  {img.size[0]}x{img.size[1]}  {os.path.getsize(out)/1024:.0f} KB")
