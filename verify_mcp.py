"""
Verify Cassandra over the MCP protocol itself — real client, real handshake,
real streamable-HTTP transport. Not a direct Python function call.

    python verify_mcp.py [url]        default http://127.0.0.1:8000/mcp
"""
import asyncio
import json
import sys

import httpx
from fastmcp import Client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/mcp"
G, R, Y, D, B, E = "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[1m", "\033[0m"
fails = []


def ok(m):
    print(f"{G}  PASS{E}  {m}")


def bad(m):
    print(f"{R}  FAIL{E}  {m}")
    fails.append(m)


def head(m):
    print(f"\n{B}{m}{E}")


def payload(res):
    """Structured result if the server sent one, else parsed text content."""
    if getattr(res, "structured_content", None):
        sc = res.structured_content
        return sc.get("result", sc) if isinstance(sc, dict) else sc
    if getattr(res, "data", None) is not None:
        return res.data
    txt = "".join(getattr(c, "text", "") for c in (res.content or []))
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        return txt


async def main():
    base = URL.rsplit("/mcp", 1)[0]

    head(f"0. Health endpoint  {D}{base}/health{E}")
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            r = await c.get(f"{base}/health")
            if r.status_code == 200 and r.json().get("status") == "ok":
                ok(f"GET /health -> 200 {D}{json.dumps(r.json())[:90]}{E}")
            else:
                bad(f"GET /health -> {r.status_code} (platform health checks will fail)")
    except Exception as e:
        bad(f"GET /health raised {type(e).__name__}: {e}")

    head(f"1. MCP handshake over streamable HTTP  {D}{URL}{E}")
    async with Client(URL) as client:
        await client.ping()
        ok("initialize + ping")

        tools = await client.list_tools()
        names = sorted(t.name for t in tools)
        want = ["bias_check", "challenge_plan", "premortem", "supported_chains"]
        if names == want:
            ok(f"tools/list -> {names}")
        else:
            bad(f"tools/list -> {names}, expected {want}")

        # Schemas are what an OKX agent reads to decide whether to hire this.
        head("2. Tool contracts (what a buying agent sees)")
        for t in tools:
            schema = t.inputSchema or {}
            props = list((schema.get("properties") or {}).keys())
            desc = (t.description or "").strip()
            if not desc:
                bad(f"{t.name}: no description — unhireable on a marketplace")
            else:
                ok(f"{t.name}({', '.join(props) or '—'})  {D}{desc.splitlines()[0][:62]}{E}")
        cp = next((t for t in tools if t.name == "challenge_plan"), None)
        if cp:
            props = (cp.inputSchema or {}).get("properties") or {}
            req = (cp.inputSchema or {}).get("required") or []
            if set(props) >= {"plan", "token_address", "chain"} and req == ["plan"]:
                ok(f"challenge_plan schema correct {D}(required={req}, optional token_address/chain){E}")
            else:
                bad(f"challenge_plan schema off: props={list(props)} required={req}")

        head("3. The demo path — the brutal one")
        res = await client.call_tool("challenge_plan", {
            "plan": "Everyone in my group chat says this token is guaranteed to 100x, "
                    "I'm putting my savings in right now before it's too late",
        })
        d = payload(res)
        if not isinstance(d, dict):
            bad(f"challenge_plan returned {type(d).__name__}, not an object")
            return
        score, verdict = d.get("case_against_strength"), d.get("verdict")
        if verdict == "THE CASE AGAINST IS STRONG" and score == 100:
            ok(f"verdict over the wire: {verdict} — {score}")
        else:
            bad(f"expected STRONG/100, got {verdict}/{score}")

        biases = d.get("biases_in_your_own_words") or []
        quoted = [b.get("you_said") for b in biases]
        if len(biases) >= 5:
            ok(f"{len(biases)} biases, quoting the user's own words {D}{quoted}{E}")
        else:
            bad(f"only {len(biases)} biases detected: {quoted}")
        for key in ("steelman", "premortem", "what_would_change_my_mind",
                    "smallest_reversible_test", "strongest_objection", "disclaimer"):
            if not d.get(key):
                bad(f"missing report section: {key}")
        if all(d.get(k) for k in ("steelman", "premortem", "what_would_change_my_mind",
                                  "smallest_reversible_test", "strongest_objection", "disclaimer")):
            ok("full report shape: steelman, premortem, mind-changers, smallest test, disclaimer")
        st = (d.get("steelman") or {}).get("argument") or ""
        pm = (d.get("premortem") or {}).get("failure_paths") or []
        print(f"{D}        steelman: {st[:96]}...{E}")
        print(f"{D}        premortem[0]: {pm[0][:96] if pm else '—'}{E}")

        head("4. The twist — it concedes")
        res = await client.call_tool("challenge_plan", {
            "plan": "I'll allocate 200 dollars I can afford to lose and exit if regulation changes",
        })
        d = payload(res)
        if d.get("verdict") == "I CANNOT MOUNT A CASE AGAINST THIS" and d.get("case_against_strength") == 0:
            ok(f"concession over the wire: {d['verdict']} — 0")
        else:
            bad(f"expected concession, got {d.get('verdict')}/{d.get('case_against_strength')}")

        head("5. Evidence-backed critique — live chain data over MCP")
        for label, addr, chain in [
            ("X Layer (default chain, WOKB)", "0xe538905cf8410324e03A5A23C1c177a474D59b2b", "xlayer"),
            ("Ethereum (USDC)", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "ethereum"),
        ]:
            res = await client.call_tool("challenge_plan", {
                "plan": "I'm putting my savings into this right now, everyone says it's guaranteed",
                "token_address": addr, "chain": chain,
            })
            d = payload(res)
            ev = d.get("on_chain_evidence") or {}
            if not ev.get("checked"):
                bad(f"{label}: no evidence attached ({str(ev)[:80]})")
                continue
            if ev.get("no_market_found"):
                bad(f"{label}: claims NO MARKET for a canonical token — false objection over the wire")
                continue
            ok(f"{label}: {D}name={ev.get('name')} liq=${ev.get('liquidity_usd') or 0:,.0f} "
               f"px={ev.get('price_usd')} src={ev.get('market_source')} rpc={ev.get('rpc_endpoint')}{E}")
            if d.get("what_i_could_not_verify"):
                print(f"{D}        discloses gaps: {d['what_i_could_not_verify'][0][:88]}{E}")

        head("6. The other three tools")
        res = await client.call_tool("premortem", {"plan": "I want to launch a token next week"})
        d = payload(res)
        if (d.get("failure_paths") or []) and d.get("plan_type"):
            ok(f"premortem -> {len(d['failure_paths'])} failure paths, type={d['plan_type']}")
        else:
            bad(f"premortem returned {str(d)[:80]}")

        res = await client.call_tool("bias_check", {"plan": "I'm going all in right now, it's a sure thing"})
        d = payload(res)
        if (d.get("framing_risk") or 0) > 0 and d.get("detected"):
            ok(f"bias_check -> framing_risk={d['framing_risk']}, "
               f"{len(d['detected'])} tells {D}{[x['you_said'] for x in d['detected']]}{E}")
        else:
            bad(f"bias_check returned {str(d)[:80]}")

        res = await client.call_tool("supported_chains", {})
        d = payload(res)
        chains = list((d.get("chains") or {}).keys())
        if len(chains) == 6 and d.get("default") == "xlayer":
            ok(f"supported_chains -> {chains}, default={d['default']}")
        else:
            bad(f"supported_chains returned {str(d)[:100]}")

        head("7. Error handling over the wire")
        d = payload(await client.call_tool("challenge_plan", {"plan": "   "}))
        if isinstance(d, dict) and d.get("error"):
            ok(f"empty plan -> graceful error {D}{d['error'][:56]}{E}")
        else:
            bad(f"empty plan returned {str(d)[:80]}")

        d = payload(await client.call_tool("challenge_plan",
                                          {"plan": "buy this", "token_address": "0xnope"}))
        if isinstance(d, dict) and d.get("error"):
            ok(f"bad address -> graceful error {D}{d['error'][:56]}{E}")
        else:
            bad(f"bad address returned {str(d)[:80]}")

        d = payload(await client.call_tool("challenge_plan", {
            "plan": "buy this", "token_address": "0x" + "11" * 20, "chain": "dogechain"}))
        ev = d.get("on_chain_evidence") or {}
        if ev.get("error") and "Unsupported chain" in ev["error"]:
            ok("unsupported chain -> named error, critique still returned")
        else:
            bad(f"unsupported chain returned {str(ev)[:80]}")

    print(f"\n{B}Result{E}")
    if fails:
        print(f"{R}  {len(fails)} failure(s) over MCP{E}\n")
        sys.exit(1)
    print(f"{G}  Verified over the MCP protocol end to end.{E}\n")


asyncio.run(main())
