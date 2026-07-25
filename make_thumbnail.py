"""Video thumbnail — 1280x720, same palette as the site, avatar and banner.

Typeset rather than AI-generated, because a thumbnail's whole job is two legible
words and image models cannot render text. Everything here stays sharp at the
210x118 size a feed actually shows.

The verdict panel on the right is the real output — the verdict string, the score
and the quoted phrases are exactly what the live engine returns for the demo
sentence. It is re-typeset, not a screen capture; drop a real screenshot in if
you prefer.
"""
from PIL import Image, ImageDraw, ImageFont

W, H, S = 1280, 720, 2          # S = supersample factor
CW, CH = W * S, H * S

BG    = (16, 14, 12)
PANEL = (24, 21, 17)
GOLD  = (201, 165, 92)
GOLD_D= (122, 98, 46)
CREAM = (236, 231, 221)
DIM   = (154, 146, 132)
FAINT = (115, 108, 96)
RED   = (224, 114, 95)
RULE  = (44, 40, 34)


def font(px, mono=False):
    for p in (["/System/Library/Fonts/Menlo.ttc"] if mono else
              ["/System/Library/Fonts/Palatino.ttc", "/System/Library/Fonts/Times.ttc"]):
        try:
            return ImageFont.truetype(p, px, index=0)
        except (OSError, ValueError):
            continue
    return ImageFont.load_default()


img = Image.new("RGB", (CW, CH), BG)
d = ImageDraw.Draw(img)

# --- soft glow behind the left block, drawn small and scaled up ------------
G = 100
glow = Image.new("L", (G, G), 0)
gd = ImageDraw.Draw(glow)
for i in range(G // 2, 0, -1):
    t = i / (G / 2)
    gd.ellipse([G/2 - i, G/2 - i, G/2 + i, G/2 + i], fill=int(30 * (1 - t) ** 1.7))
img = Image.composite(Image.new("RGB", (CW, CH), (38, 33, 26)), img,
                      glow.resize((CW, CH), Image.LANCZOS))
d = ImageDraw.Draw(img)

# --- hairline frame -------------------------------------------------------
m = 26 * S
d.rectangle([m, m, CW - m, CH - m], outline=GOLD_D, width=max(2, S))


def tracked(xy, text, f, fill, track):
    """Letter-spaced text — PIL has no tracking, so step per glyph."""
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + track
    return x


# =========================================================================
# LEFT — the two words that have to read at thumbnail size
# =========================================================================
LX = 74 * S
f_eyebrow = font(19 * S, mono=True)
f_huge = font(132 * S)
f_huger = font(158 * S)

y = 128 * S
tracked((LX, y), "EVERY AGENT IS BUILT TO SAY", f_eyebrow, FAINT, 3.2 * S)

y2 = y + 30 * S
d.text((LX, y2), "YES", font=f_huge, fill=DIM)
w_yes = d.textlength("YES", font=f_huge)
sy = y2 + int(85 * S)
d.line([LX - 6 * S, sy, LX + w_yes + 6 * S, sy], fill=RED, width=max(4, 5 * S))

y3 = y2 + 150 * S
tracked((LX, y3), "I BUILT ONE THAT SAYS", f_eyebrow, GOLD, 3.2 * S)

y4 = y3 + 30 * S
d.text((LX, y4), "NO", font=f_huger, fill=GOLD)

# strap under the words
f_strap = font(23 * S)
d.text((LX + 4 * S, y4 + 190 * S),
       "It argues against your plan — and concedes when you're right.",
       font=f_strap, fill=DIM)

# =========================================================================
# RIGHT — the verdict panel, real output re-typeset
# =========================================================================
PX0, PY0, PX1, PY1 = 748 * S, 150 * S, CW - 74 * S, 524 * S
d.rounded_rectangle([PX0, PY0, PX1, PY1], radius=10 * S, fill=PANEL, outline=RULE, width=max(1, S))
d.line([PX0, PY0 + 5 * S, PX0, PY1 - 5 * S], fill=RED, width=max(3, 3 * S))

ix = PX0 + 34 * S
f_lab = font(16 * S, mono=True)
tracked((ix, PY0 + 34 * S), "VERDICT", f_lab, FAINT, 2.6 * S)

f_verdict = font(30 * S)
d.text((ix, PY0 + 66 * S), "THE CASE", font=f_verdict, fill=RED)
d.text((ix, PY0 + 104 * S), "AGAINST IS STRONG", font=f_verdict, fill=RED)

# score
f_score = font(112 * S)
f_over = font(34 * S)
d.text((ix, PY0 + 156 * S), "100", font=f_score, fill=RED)
w100 = d.textlength("100", font=f_score)
d.text((ix + w100 + 8 * S, PY0 + 216 * S), "/100", font=f_over, fill=FAINT)

# meter, full
mx0, mx1 = ix, PX1 - 34 * S
my = PY0 + 282 * S
d.rounded_rectangle([mx0, my, mx1, my + 9 * S], radius=5 * S, fill=(46, 34, 30))
d.rounded_rectangle([mx0, my, mx1, my + 9 * S], radius=5 * S, fill=RED)

# the quoted phrases — its own words, gold-highlighted like the live UI
f_q = font(19 * S, mono=True)
qx, qy = ix, PY0 + 310 * S
for q in ('"my savings"', '"guaranteed"', '"right now"'):
    tw = d.textlength(q, font=f_q)
    d.rounded_rectangle([qx - 7 * S, qy - 5 * S, qx + tw + 7 * S, qy + 27 * S],
                        radius=4 * S, fill=(58, 47, 28))
    d.text((qx, qy), q, font=f_q, fill=CREAM)
    qx += tw + 24 * S

f_note = font(17 * S, mono=True)
d.text((ix, PY0 + 350 * S), "5 biases, quoted from one sentence", font=f_note, fill=FAINT)

# guard: nothing may sit outside the panel it belongs to
assert PY0 + 350 * S + 20 * S < PY1, "note overflows the verdict panel"

# =========================================================================
# FOOTER — monogram, wordmark, url
# =========================================================================
cx, cy, r = LX + 22 * S, CH - 78 * S, 25 * S
d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GOLD, width=max(2, S))
fc = font(32 * S)
bb = d.textbbox((0, 0), "C", font=fc)
d.text((cx - (bb[0] + bb[2]) / 2, cy - (bb[1] + bb[3]) / 2 - S), "C", font=fc, fill=CREAM)

f_mark = font(30 * S)
d.text((cx + r + 20 * S, cy - 21 * S), "Cassandra", font=f_mark, fill=CREAM)
f_url = font(17 * S, mono=True)
d.text((cx + r + 21 * S, cy + 8 * S),
       "cassandra-devils-advocate.vercel.app  ·  an A2MCP service on OKX AI",
       font=f_url, fill=GOLD_D)

img = img.resize((W, H), Image.LANCZOS)
img.save("thumbnail.png", "PNG", optimize=True)

# the size a feed actually shows — if it fails here, it has failed
img.resize((210, 118), Image.LANCZOS).save("thumbnail-210.png", "PNG", optimize=True)

import os
print(f"thumbnail.png      {W}x{H}  {os.path.getsize('thumbnail.png')/1024:.0f} KB")
print(f"thumbnail-210.png  210x118  (legibility check)")
