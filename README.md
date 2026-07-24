# Cassandra — The Devil's Advocate

> Every agent on OKX.AI is built to say yes. Cassandra is built to say no.

An A2MCP service for the OKX.AI marketplace. You give it a plan; it argues
against it — states your case better than you did, names the cognitive bias in
your own wording (and quotes it back), runs a pre-mortem, checks any on-chain
claim against the chain, tells you what would change its mind, and proposes the
smallest reversible test. **It concedes when your plan is sound.**

Named for the prophetess cursed to speak true and never be believed.

## Tools

| Tool | Purpose |
| --- | --- |
| `challenge_plan(plan, token_address=None, chain="xlayer")` | The main event: steelman → case against → biases → pre-mortem → on-chain evidence → what would change my mind → smallest test |
| `premortem(plan)` | "It's a year from now and this failed. Why?" Failure paths only |
| `bias_check(plan)` | Fast read on *how* you framed the decision, ignoring its merits |
| `supported_chains()` | Chains it can pull evidence from |

Chains: `xlayer` (default), `ethereum`, `bsc`, `base`, `arbitrum`, `polygon`.

## Why it's not a chatbot wrapper

Deterministic. No LLM, no API key, no per-call token cost, nothing to
hallucinate — pattern analysis over your phrasing, a structured pre-mortem
library, and live chain data. Same input, same critique, every time.

## Run locally

```bash
pip install -r requirements.txt
python server.py        # http://localhost:8000/mcp
```

Test with the MCP Inspector (`npx @modelcontextprotocol/inspector`) →
Transport: **Streamable HTTP** → URL: `http://localhost:8000/mcp`.

Try:
```
challenge_plan(plan="Everyone says this token is guaranteed to 100x,
                     I'm putting my savings in right now before it's too late")
```
→ `THE CASE AGAINST IS STRONG` (100), five biases quoted from your own sentence.

Then try a good plan:
```
challenge_plan(plan="I'll allocate 200 dollars I can afford to lose and exit if regulation changes")
```
→ `I CANNOT MOUNT A CASE AGAINST THIS` (0).

## Live endpoint

```
MCP    https://cassandra-devils-advocate.vercel.app/mcp     (Streamable HTTP)
Health https://cassandra-devils-advocate.vercel.app/health
```

A browser GET on `/mcp` answers `406` on purpose — MCP needs an SSE `Accept`
header. That is the protocol working. Point a client at it instead:

```bash
python try_cassandra.py --url https://cassandra-devils-advocate.vercel.app/mcp
```

## Deploy (HTTPS required by OKX)

Deployed on Vercel — `api/index.py` serves the same app as `server.py`, and
`vercel.json` routes every path to it:

```bash
vercel deploy --prod
```

Two things that will bite you:
- **Use the clean production domain.** Per-deployment and per-team URLs
  (`…-emer-eths-projects.vercel.app`) sit behind Vercel SSO and `302` everyone.
- **FastMCP needs its ASGI lifespan.** Serverless adapters may not emit it, and
  without it `/mcp` returns 500 while `/health` still returns 200 — a green
  health check in front of a dead service. `api/index.py` enters the lifespan
  lazily to cover that.

`Dockerfile` and `render.yaml` are still here if you'd rather run it on Render,
Railway, Fly.io or any VPS + Caddy.

## List on OKX.AI

See **PITCH-AND-LAUNCH.md** for the listing copy, pricing, demo script, X post
and the day-by-day submission timeline.

## Files
- `server.py` — the MCP server + reasoning engine
- `PITCH-AND-LAUNCH.md` — positioning, listing copy, demo script, X post, timeline
- `requirements.txt` / `Dockerfile` / `render.yaml` — deploy

---
Cassandra is a decision-hygiene tool, **not financial advice**. It argues against
your plan by design — that is its job, not a prediction.
