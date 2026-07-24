"""
Try Cassandra from the terminal — over real MCP, the same way a buying agent
on OKX.AI would call it. Also the cleanest surface to screen-record.

    python try_cassandra.py                      # interactive, asks for plans
    python try_cassandra.py "I'm going all in"   # one shot
    python try_cassandra.py "..." --token 0xABC… --chain xlayer
    python try_cassandra.py "..." --url https://your-service.onrender.com/mcp

Ctrl-C or an empty line to quit.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import sys
import textwrap

from fastmcp import Client

DEFAULT_URL = "http://127.0.0.1:8000/mcp"

BOLD, DIM, IT, END = "\033[1m", "\033[2m", "\033[3m", "\033[0m"
RED, YEL, GRN, GLD, GRY = "\033[91m", "\033[93m", "\033[92m", "\033[33m", "\033[90m"
COLS = min(shutil.get_terminal_size((88, 24)).columns, 88)


def rule(ch: str = "─") -> str:
    return GRY + ch * COLS + END


def wrap(text: str, indent: str = "  ", width: int | None = None) -> str:
    return textwrap.fill(str(text), width=width or COLS,
                         initial_indent=indent, subsequent_indent=indent)


def heading(label: str) -> None:
    print(f"\n{DIM}{BOLD}{label.upper()}{END}")


def verdict_colour(score: int) -> str:
    return RED if score >= 70 else YEL if score >= 40 else GLD if score >= 18 else GRN


def payload(res):
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


def render(d: dict) -> None:
    if not isinstance(d, dict):
        print(f"{RED}unexpected response:{END} {str(d)[:300]}")
        return
    if d.get("error"):
        print(f"\n{RED}  {d['error']}{END}\n")
        return

    score = d.get("case_against_strength", 0)
    col = verdict_colour(score)

    print()
    print(rule("═"))
    print(f"{col}{BOLD}  {d.get('verdict', '?')}{END}{col}   {score}/100{END}")
    print(rule("═"))
    print(wrap(d.get("my_position", ""), "  "))

    steel = (d.get("steelman") or {}).get("argument")
    if steel:
        heading("first, your case at its strongest")
        print(f"{IT}{wrap(steel, '  ')}{END}")

    biases = d.get("biases_in_your_own_words") or []
    if biases:
        heading(f"{len(biases)} tell(s) in your own wording")
        for b in biases:
            print(f"\n  {col}▸ {b['bias']}{END}   {DIM}you said{END} {BOLD}“{b['you_said']}”{END}")
            print(wrap(b["objection"], "    "))
    elif d.get("framing_note"):
        heading("your framing")
        print(f"{GRN}{wrap(d['framing_note'], '  ')}{END}")

    ev = d.get("on_chain_evidence") or {}
    if ev.get("checked"):
        heading("on-chain evidence")
        facts = [
            ("token", f"{ev.get('name') or '?'} ({ev.get('symbol') or '?'})"),
            ("liquidity", f"${ev['liquidity_usd']:,.0f}" if isinstance(ev.get("liquidity_usd"), (int, float)) else None),
            ("price", f"${ev['price_usd']}" if ev.get("price_usd") else None),
            ("24h change", f"{ev['price_change_24h']}%" if ev.get("price_change_24h") is not None else None),
            ("pair age", f"{ev['pair_age_days']} days" if ev.get("pair_age_days") is not None else None),
            ("owner powers", ", ".join(ev["privileged_functions"]) if ev.get("privileged_functions") else None),
            ("renounced", str(ev["ownership_renounced"]) if ev.get("ownership_renounced") is not None else None),
            ("upgradeable", str(ev["is_upgradeable_proxy"]) if ev.get("is_upgradeable_proxy") is not None else None),
            ("sellable", str(not ev["is_honeypot"]) if ev.get("is_honeypot") is not None else None),
            ("sell tax", f"{ev['sell_tax']}%" if ev.get("sell_tax") is not None else None),
        ]
        for k, v in facts:
            if v:
                print(f"    {DIM}{k:<14}{END}{v}")
        print(f"    {DIM}{'source':<14}{END}{GRY}{ev.get('market_source') or '—'} · "
              f"{ev.get('rpc_endpoint') or '—'}{END}")

    strongest = d.get("strongest_objection")
    if strongest:
        heading("the objection that matters most")
        print(f"  {DIM}via {strongest.get('source')} — {strongest.get('label')}{END}")
        print(f"{col}{wrap(strongest.get('detail', ''), '  ')}{END}")

    paths = (d.get("premortem") or {}).get("failure_paths") or []
    if paths:
        heading("pre-mortem — assume it already failed")
        for p in paths:
            print(wrap(f"• {p}", "  "))

    gaps = d.get("what_i_could_not_verify")
    if gaps:
        heading("what i could not verify")
        for g in gaps:
            print(f"{GRY}{wrap('• ' + g, '  ')}{END}")

    changers = d.get("what_would_change_my_mind") or []
    if changers:
        heading("what would change my mind")
        for c in changers:
            print(wrap(f"• {c}", "  "))

    if d.get("smallest_reversible_test"):
        heading("smallest reversible test")
        print(f"{GRN}{wrap(d['smallest_reversible_test'], '  ')}{END}")

    print(f"\n{GRY}{wrap(d.get('disclaimer', ''), '  ')}{END}\n")


async def run(url: str, plan: str | None, token: str | None, chain: str) -> None:
    async with Client(url) as client:
        await client.ping()
        tools = sorted(t.name for t in await client.list_tools())
        print(f"{DIM}connected to {url}{END}")
        print(f"{DIM}tools: {', '.join(tools)}{END}")

        async def ask(p: str) -> None:
            args: dict[str, object] = {"plan": p}
            if token:
                args["token_address"] = token
                args["chain"] = chain
            render(payload(await client.call_tool("challenge_plan", args)))

        if plan:
            await ask(plan)
            return

        print(f"\n{BOLD}State a plan and Cassandra will argue against it.{END}")
        print(f"{DIM}Try:  Everyone says this token is guaranteed to 100x, I'm putting my "
              f"savings in right now\n      I'll allocate 200 dollars I can afford to lose "
              f"and exit if regulation changes{END}")
        while True:
            try:
                p = input(f"\n{GLD}your plan ›{END} ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not p:
                return
            await ask(p)


def main() -> None:
    argv = sys.argv[1:]
    url, token, chain, parts = DEFAULT_URL, None, "xlayer", []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--url", "--token", "--chain") and i + 1 < len(argv):
            val = argv[i + 1]
            url, token, chain = (val if a == "--url" else url), (val if a == "--token" else token), (val if a == "--chain" else chain)
            i += 2
            continue
        if a in ("-h", "--help"):
            print(__doc__)
            return
        parts.append(a)
        i += 1

    try:
        asyncio.run(run(url, " ".join(parts) or None, token, chain))
    except KeyboardInterrupt:
        print()
    except Exception as e:
        print(f"\n{RED}could not reach {url}{END}\n  {type(e).__name__}: {str(e)[:140]}")
        print(f"{DIM}  Is the server running?  python server.py{END}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
