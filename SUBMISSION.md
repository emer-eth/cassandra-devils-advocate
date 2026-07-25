# Submission write-up

Four lengths, because the form's fields are unknown — use whichever fits, they
say the same thing at different resolutions. Then the video description and a
copy-paste links block.

---

## Tagline — 15 words

Every agent on OKX.AI is built to say yes. Cassandra is built to say no.

---

## Short — 55 words

Cassandra argues against your plan before you act on it. State any decision and
it makes your own case better than you did, then takes it apart: the cognitive
bias in your own wording quoted back at you, a pre-mortem, live on-chain
evidence, and the smallest reversible test. It concedes when your plan is sound.

---

## Standard — 156 words

Every agent on this marketplace is built to say yes — find the data, make the
logo, confirm the thesis. All of them are optimised for agreement, because
agreement is what gets rated five stars. Nobody is selling friction.

Cassandra is the counterparty to your own conviction. You state a plan; it
states your plan back to you better than you did, then dismantles it: it names
the cognitive bias visible in your own phrasing and quotes your words back at
you, runs a pre-mortem, checks any on-chain claim against the chain itself,
tells you exactly what evidence would change its mind, and proposes the smallest
reversible version you could test instead.

And it concedes. Give it a sized, reversible, falsifiable plan and it says "I
cannot mount a case against this" and gets out of the way.

No language model. A deterministic engine — same plan in, same critique out,
every time. Nothing to hallucinate.

---

## Full — 437 words

**Every agent on this marketplace is built to say yes.** Find me the data, make
me a logo, generate the signal, confirm what I already think. Every one of them
is optimised for agreement, because agreement is what gets rated five stars.

Nobody is selling friction. And friction is the thing that actually protects
people, because the expensive mistakes in this industry are not caused by a lack
of information — they are caused by nobody in the room being paid to disagree.

**Cassandra is the counterparty to your own conviction.** You state a plan — a
trade, a token, a launch, a hire. It states your plan back to you better than
you did, then takes it apart: it names the cognitive bias visible in your own
wording and quotes your words back at you, runs a pre-mortem to enumerate
concrete failure paths, checks any on-chain claim against the chain itself, tells
you exactly what evidence would change its mind, and offers the smallest
reversible version you could test instead.

**And critically, it concedes.** Give it a sized, reversible, falsifiable plan
and it answers "I cannot mount a case against this" and gets out of the way. A
critic that objects to everything is just noise — the concession is what makes
the objection worth paying for, and it was the hardest part to build.

**There is no language model in it.** Cassandra is a deterministic reasoning
engine: pattern analysis over your own phrasing, a structured pre-mortem library
keyed to the type of plan, and live chain data. Same plan in, same critique out,
every time. No API key, no per-call token cost, nothing to hallucinate. On an
agent marketplace, that is unusual enough to say out loud — and the code is
public, so it is a claim you can check rather than trust.

**Because every objection cites the chain, the chain data has to be right.** The
evidence layer got the most scrutiny of anything here. Market data is filtered to
the chain actually being queried — an unfiltered lookup happily returns a
different chain's pool and reports $0.0007 for a dollar stablecoin. X Layer is
not indexed by the usual market source at all, so it falls back to one that
covers it rather than reporting "no market found", which would be a fabricated
objection on OKX's own chain. Owner-power detection uses keccak-verified
selectors. Every chain has multiple RPC endpoints with failover. And where a
check cannot run, Cassandra reports the gap instead of inferring a finding from
silence.

The grounding is decision science, not vibes: pre-mortem (Klein), steelmanning,
inversion, falsifiability, base-rate neglect.

---

## Video description (YouTube)

```
Every AI agent is built to help you do the thing you already decided to do.
This one tries to talk you out of it.

Cassandra is an A2MCP service on the OKX.AI marketplace. You give it a plan;
it argues against it — naming the cognitive bias in your own wording and
quoting your words back at you, running a pre-mortem, and checking any
on-chain claim against the chain itself.

And when your plan is actually sound, it says so and gets out of the way.

There is no language model in it. It's a deterministic engine: same plan in,
same critique out, every time. No API key, nothing to hallucinate.

Try it yourself (the demo on the site is the real engine):
https://cassandra-devils-advocate.vercel.app

Source:
https://github.com/emer-eth/cassandra-devils-advocate

Listed on OKX.AI as ASP #9030, on X Layer.
Decision hygiene, not financial advice.

--- Chapters (adjust to your final edit) ---
0:00  Every agent says yes
0:11  A plan, phrased the way people actually phrase them
0:21  The case against is strong — 100/100
0:33  Five biases, quoted from one sentence
0:45  The part nobody expects: it concedes
1:05  It checks the chain
1:25  No LLM. Nothing to hallucinate.
```

**Verify the chapter times against your finished cut before posting** — they
assume the 90-second version with the pauses in the shot sheet, and a slower
read moves every one of them.

---

## Links block — copy-paste into the form

```
Live service      https://cassandra-devils-advocate.vercel.app
MCP endpoint      https://cassandra-devils-advocate.vercel.app/mcp
Health check      https://cassandra-devils-advocate.vercel.app/health
Source code       https://github.com/emer-eth/cassandra-devils-advocate
OKX.AI listing    ASP #9030 (X Layer, chainIndex 196)
Registration tx   0x540cdb61e9e7f0142cb7bb693e15a7e409bbe96f25f4cb1682daf13816777fae
X / Twitter       @CassandraArgues
Demo video        <paste your link>
```

## What a judge can verify in two minutes

Worth stating explicitly if the form has room — every claim above is checkable,
which is the point of a service that refuses to hallucinate.

- **The demo on the site is the live engine**, not a recording. Type your own
  plan; it answers in about a second.
- **It concedes on demand.** Click "The good one" — a sized, reversible plan
  scores 0 and it stands down. That is the claim hardest to fake.
- **Determinism is testable.** Submit the same plan twice and the response is
  byte-identical — verified, 5,842 bytes both times. No temperature, no drift.
  (Pass a token address and the evidence tracks the chain as it moves, which is
  the point rather than an exception: the reasoning is fixed, the facts are live.)
- **The on-chain evidence cites its sources** — the RPC endpoint and market
  source appear in the output next to the numbers.
- **`test_local.py`** in the repo exercises the reasoning engine and live chain
  calls across all six supported chains, including regression tests for
  cross-chain price contamination and false "no market" objections.
- **`verify_mcp.py`** runs the full MCP protocol against the production endpoint:
  handshake, tool discovery, every tool, and error handling.

## Services as listed

| Service | Price |
| --- | --- |
| Adversarial Plan Review — the full argument | 0.02 USDT |
| Cognitive Bias Check — fast read on your framing | free |
| Pre-Mortem Analysis — assume it already failed | free |
