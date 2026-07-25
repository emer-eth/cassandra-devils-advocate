# Demo video — narration script + shot list

For a screen recording of **https://cassandra-devils-advocate.vercel.app**
with TTS narration laid over it.

Everything narrated below is a real thing on the page. No slides, no mockups,
no edits that fake a result.

---

## Read this before you record

**Generate the audio as 7 separate clips, not one file.** The demo calls live
RPC and market APIs, so the response takes anywhere from 0.7s to 3.5s depending
on the chain. One long audio file will drift out of sync the first time a call
runs slow. Seven clips means each beat starts when *you* are ready and the drift
never accumulates. Clip boundaries are marked **▸ CLIP n** below.

**Click the example chips — never type.** Typing that first sentence on camera
takes eleven seconds and you will typo it. The chips fill the box instantly and
that is why they are there.

**Setup:**
- **Dark theme** (the ☾ toggle, top right). The gold-on-black reads far better
  on video than the light theme, and the animated meter pops.
- Browser zoom **125%**. The verdict, the quoted words and the facts table all
  need to be legible after compression.
- Clean window: no bookmarks bar, no other tabs, no notifications.
- Record 1920×1080. Capture the browser window only, not the whole desktop.
- Do one warm-up run before recording — the first call of the day pays a cold
  start, every one after is under a second.

**Rate limit:** 60 calls/min per IP. That is plenty for retakes, but if you ever
see a 429, wait sixty seconds — it clears itself.

---

## Shot list

Timings assume TTS at ~155 words/min. Word counts are per clip.

### ▸ CLIP 1 — the hook · 31 words · ≈12s

**ON SCREEN:** Hero, freshly loaded, dark theme. The strikethrough on "yes"
animates in by itself — let it land before you start. Do not scroll yet.

> Every AI agent you have ever used is built to help you do the thing you
> already decided to do. I built one that tries to talk you out of it.

---

### ▸ CLIP 2 — set up the demo · 25 words · ≈10s

**ON SCREEN:** Scroll smoothly to the demo box. Click the first chip —
**"The bad one"** — so the sentence fills the textarea. Let it sit for a beat so
the sentence is readable. Then click **Argue against it**.

> This is Cassandra. It is live on the OKX dot AI marketplace right now. Here is
> a plan, phrased the way people actually phrase them.

---

### ▸ CLIP 3 — the verdict · 28 words · ≈11s

**ON SCREEN:** The result renders. The meter fills to 100 in red. Do not scroll —
let the number sit on screen for two full seconds before the narration moves on.

> A hundred out of a hundred. The case against is strong. And it did not just
> disagree with me. It found five separate tells in that one sentence.

---

### ▸ CLIP 4 — the five quoted words · 33 words · ≈13s

**ON SCREEN:** Scroll slowly through the bias list. Pause on each gold-highlighted
quote as it is named. Five of them, in this order.

> Then it quoted them back at me. My savings. Guaranteed. A hundred X. Right now.
> Everyone. Ruinous position sizing, false certainty, base rate neglect,
> manufactured urgency, herd following. Named, in my own words.

---

### ▸ CLIP 5 — the pre-mortem · 31 words · ≈12s

**ON SCREEN:** Keep scrolling to **Pre-mortem — assume it already failed**. Rest
on the first line long enough to read it.

> And then it assumes I already failed, and works backwards. You bought near a
> local top, because the reason you heard about it was the same reason it had
> already run.

---

### ▸ CLIP 6 — the twist · 45 words · ≈17s

**ON SCREEN:** Scroll back up to the box. Click the second chip — **"The good
one"** — then **Argue against it**. When it renders, the verdict is green and the
meter barely registers.

> Now the part nobody expects. A sensible plan. Sized, reversible, and it says
> what would prove it wrong. I cannot mount a case against this. Zero. A critic
> that objects to everything is just noise. The concession is what makes the
> objection worth paying for.

---

### ▸ CLIP 7 — the receipts and the close · 66 words · ≈26s

**ON SCREEN:** Open **"Add a token address for on-chain evidence"**, click **use
WOKB**, re-click the first chip, then **Argue against it**. Scroll to the
**On-chain evidence** table. The `source` row showing `geckoterminal ·
rpc.xlayer.tech` is the proof it is live — make sure it is in frame.

> It also checks the chain. That is live X Layer data, pulled while you watched.
> One point eight million in liquidity. Six months of trading history. No mint
> function, no blacklist. It found nothing wrong with the token, and it says so.
> The problem was never the token. It was my sentence.
>
> No language model. Nothing to hallucinate. Cassandra, on OKX dot AI. Hashtag
> OKX AI.

---

**Narration: 259 words ≈ 100s of speech.** With the deliberate pauses — letting the score sit, scrolling the bias list, waiting on live chain calls — the finished video lands around **2:00–2:15**.

---

## The 90-second cut

Trimming the version above does not get you to 90 seconds — the three live calls
and the pauses eat ~25s on their own, so the narration has to come down to about
67s. Here it is rewritten to that budget. Same six beats, pre-mortem dropped,
same on-screen actions.

**▸ 1 · hook** — hero, let the strikethrough land · 26 words
> Every AI agent is built to help you do what you already decided to do. I built
> one that tries to talk you out of it.

**▸ 2 · setup** — click *"The bad one"*, then *Argue against it* · 21 words
> This is Cassandra, live on the OKX dot AI marketplace. Here is a plan, phrased
> the way people actually phrase them.

**▸ 3 · verdict** — let the red 100 sit for two seconds · 16 words
> A hundred out of a hundred. And it found five separate tells in that one
> sentence.

**▸ 4 · the words** — scroll the bias list, pause on each gold quote · 18 words
> Quoted back at me. My savings. Guaranteed. A hundred X. Right now. Everyone.
> Named, in my own words.

**▸ 5 · the twist** — click *"The good one"*, then *Argue against it* · 36 words
> Now the part nobody expects. A sensible, sized, reversible plan. I cannot mount
> a case against this. Zero. A critic that objects to everything is noise. The
> concession is what makes the objection worth paying for.

**▸ 6 · receipts and close** — *use WOKB*, re-click the first chip, argue, scroll
to the evidence table · 55 words
> It also checks the chain. Live X Layer data, pulled while you watched. One point
> eight million in liquidity, no mint function, no blacklist. It found nothing
> wrong with the token, and says so. The problem was never the token. It was my
> sentence. No language model. Nothing to hallucinate. Cassandra, on OKX dot AI.

**172 words ≈ 67s of speech → ~90s finished.**

Whichever version you use, do not cut the concession beat. It is the whole
argument — a critic that only ever objects is a doom machine, and the moment it
says *zero* is the moment the objections become worth paying for.

---

## TTS notes

Numbers and symbols are already written the way they should be spoken —
"a hundred X", not "100x"; "OKX dot AI", not "OKX.AI". Do not paste the
marketing copy in instead; it is full of em-dashes and symbols that TTS reads
badly.

- Pace: slightly slower than default. This is an argument, not an ad.
- Voice: something dry and level. The content is already dramatic; a hyped
  read fights it.
- Leave ~0.4s of silence at the head and tail of every clip so the cuts breathe.

## If you want on-screen text too

The three lines worth burning in as captions, timed to the narration:

- `THE CASE AGAINST IS STRONG — 100` (clip 3)
- `I CANNOT MOUNT A CASE AGAINST THIS — 0` (clip 6)
- `Deterministic. No LLM. Nothing to hallucinate.` (clip 7 close)

Nothing else. The page is already doing the work.
