"""
Cassandra — local smoke test
============================
Run this BEFORE deploying. It checks the three things that can go wrong,
in the order they'd bite you:

  1. Does it even import? (dependencies + Python version)
  2. Does the reasoning engine work? (offline — no internet needed)
  3. Do the LIVE on-chain calls work? (the part that could NOT be tested
     in the build sandbox — this is the one you actually need to confirm)

Usage:
    python test_local.py

Exit code 0 = safe to deploy. Anything else = read the output.
"""

import sys

GREEN, RED, YEL, DIM, BOLD, END = "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[1m", "\033[0m"
def ok(m):   print(f"{GREEN}  PASS{END}  {m}")
def bad(m):  print(f"{RED}  FAIL{END}  {m}")
def warn(m): print(f"{YEL}  WARN{END}  {m}")
def head(m): print(f"\n{BOLD}{m}{END}")

failures, warnings = [], []


# ---------------------------------------------------------------- 1. imports
head("1. Environment")

if sys.version_info < (3, 10):
    bad(f"Python {sys.version_info.major}.{sys.version_info.minor} — need 3.10 or newer.")
    print("\n    Install a newer Python, then re-run. Everything else is blocked on this.")
    sys.exit(1)
ok(f"Python {sys.version_info.major}.{sys.version_info.minor}")

try:
    import httpx  # noqa: F401
    ok("httpx installed")
except ImportError:
    bad("httpx missing  ->  pip install httpx")
    failures.append("httpx")

try:
    import fastmcp  # noqa: F401
    ok(f"fastmcp installed ({getattr(fastmcp, '__version__', 'unknown version')})")
except ImportError:
    bad("fastmcp missing  ->  pip install fastmcp")
    failures.append("fastmcp")

if failures:
    print(f"\n{RED}Install the missing packages first:{END}\n    pip install fastmcp httpx\n")
    sys.exit(1)

try:
    import server
    ok("server.py imports cleanly")
except Exception as e:
    bad(f"server.py failed to import: {e}")
    sys.exit(1)


# ------------------------------------------------------- 2. reasoning engine
head("2. Reasoning engine  (offline — no internet required)")

CASES = [
    # (label, plan, min_score, max_score, expected plan type)
    ("catches FOMO + savings",
     "Everyone says this token is guaranteed to 100x, putting my savings in right now before it's too late",
     70, 100, "acquire"),
    ("catches leverage",
     "I'm going to open a 10x leverage long on this",
     30, 100, "leverage"),
    ("catches sunk cost",
     "I'm down bad, already put in 5k, going to average down with my savings",
     40, 100, "acquire"),
    ("catches implausible yield",
     "I want to stake everything into this farm for the 900% APY",
     40, 100, "yield"),
    ("CONCEDES to a good plan",
     "I plan to allocate 200 dollars I can afford to lose into an index position and hold three years. "
     "I will exit if regulation changes.",
     0, 9, "acquire"),
    ("CONCEDES to disciplined DCA",
     "I will allocate a small fixed amount monthly regardless of price",
     0, 9, "acquire"),
]

for label, plan, lo, hi, want_type in CASES:
    try:
        r = server.challenge_plan(plan)
        score, kinds = r["case_against_strength"], r["plan_type"]
        if not (lo <= score <= hi):
            bad(f"{label}: score {score}, expected {lo}-{hi}")
            failures.append(label)
        elif want_type not in kinds:
            bad(f"{label}: classified {kinds}, expected '{want_type}'")
            failures.append(label)
        else:
            ok(f"{label}  {DIM}(score {score}, {kinds}){END}")
    except Exception as e:
        bad(f"{label}: raised {type(e).__name__}: {e}")
        failures.append(label)

# the other two tools
try:
    assert server.premortem("I want to launch a token")["failure_paths"]
    ok("premortem() returns failure paths")
except Exception as e:
    bad(f"premortem() broken: {e}")
    failures.append("premortem")

try:
    assert server.bias_check("I'm going all in right now")["framing_risk"] > 0
    ok("bias_check() flags a bad framing")
except Exception as e:
    bad(f"bias_check() broken: {e}")
    failures.append("bias_check")

# input handling
try:
    assert "error" in server.challenge_plan("")
    assert "error" in server.challenge_plan("buy this", token_address="0xnope")
    ok("rejects empty plans and malformed addresses")
except Exception as e:
    bad(f"input validation broken: {e}")
    failures.append("validation")


# ------------------------------------------------- 3. live network (the gap)
head("3. Live on-chain calls  (needs internet — THIS is the part that was untested)")

# Canonical, permanently-deployed wrapped-native / stable tokens on every
# supported chain. Each is a contract, each has deep real liquidity. If any of
# these comes back empty the RPC or market source for that chain is broken —
# which is exactly the failure that shipped last time, so it FAILS, not warns.
PROBES = [
    ("xlayer",   "0xe538905cf8410324e03A5A23C1c177a474D59b2b", "Wrapped OKB"),
    ("ethereum", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "USDC"),
    ("bsc",      "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", "WBNB"),
    ("base",     "0x4200000000000000000000000000000000000006", "WETH"),
    ("arbitrum", "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1", "WETH"),
    ("polygon",  "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270", "WPOL"),
]

live = {}
for chain, addr, what in PROBES:
    try:
        ev = server._onchain_evidence(addr, chain)
        live[chain] = ev
        if ev.get("chain_error"):
            bad(f"{chain:9} RPC: every endpoint failed — {str(ev['chain_error'])[:60]}")
            failures.append(f"{chain} rpc")
            continue
        if not ev.get("is_contract"):
            bad(f"{chain:9} connected but reports no contract at {what} — decoder or chain is wrong")
            failures.append(f"{chain} contract")
            continue

        bits = [f"name={ev.get('name') or '?'}"]
        if ev.get("liquidity_usd") is not None:
            bits.append(f"liq=${ev['liquidity_usd']:,.0f}")
        if ev.get("price_usd") is not None:
            bits.append(f"px={ev['price_usd']}")
        bits.append(f"src={ev.get('market_source') or 'none'}")
        if ev.get("is_honeypot") is not None:
            bits.append(f"sellable={not ev['is_honeypot']}")

        # Market data must be REAL, not merely present. A canonical token with
        # deep liquidity must never come back as "no market found".
        if ev.get("no_market_found"):
            bad(f"{chain:9} market: reported NO MARKET for {what} — that is a false objection")
            failures.append(f"{chain} false no-market")
        elif ev.get("market_data_unavailable"):
            warn(f"{chain:9} market data unreachable ({str(ev.get('market_errors'))[:50]}) — degraded, not wrong")
            warnings.append(f"{chain} market")
        elif not isinstance(ev.get("liquidity_usd"), (int, float)) or ev["liquidity_usd"] < 50_000:
            bad(f"{chain:9} market: liquidity for {what} came back {ev.get('liquidity_usd')} — implausibly low")
            failures.append(f"{chain} liquidity")
        else:
            ok(f"{chain:9} {DIM}({', '.join(bits)}){END}")
    except Exception as e:
        bad(f"{chain:9} raised {type(e).__name__}: {str(e)[:60]}")
        failures.append(chain)

# ---- regression: the chain-filter bug -------------------------------------
# DexScreener returns pairs from EVERY chain it indexes. Sorting by liquidity
# without filtering handed back a PulseChain pool for Ethereum USDC and called
# it a fact: $6.1M liquidity at $0.00074 instead of $884k at $1.00.
eth = live.get("ethereum") or {}
price = eth.get("price_usd")
if price is None:
    warn("chain-filter regression: no ethereum price to check")
    warnings.append("chain filter")
elif not (0.90 <= (float(price) if str(price).replace('.', '', 1).isdigit() else 0) <= 1.10):
    bad(f"chain-filter regression: USDC on ethereum priced at {price} — that is another chain's pair")
    failures.append("chain filter")
else:
    ok(f"chain-filtered market data  {DIM}(USDC/ethereum = ${price}, not a PulseChain pair){END}")

# ---- regression: false 'no market' on the default chain -------------------
# X Layer is the DEFAULT chain and DexScreener does not index it at all, so the
# unfiltered path invented a 28-point "no observable market" objection on OKX's
# own chain. GeckoTerminal covers it; the objection must not fire.
xl = live.get("xlayer") or {}
if xl.get("no_market_found"):
    bad("X Layer still reports 'no market found' — the false-objection bug is back")
    failures.append("xlayer false no-market")
elif isinstance(xl.get("liquidity_usd"), (int, float)):
    ok(f"X Layer market data present  {DIM}(liq=${xl['liquidity_usd']:,.0f} via {xl.get('market_source')}){END}")
else:
    warn("X Layer market data unavailable — degraded but not asserting a false finding")
    warnings.append("xlayer market")

# ---- regression: no invented owner powers on a known-clean contract -------
# USDC is upgradeable and pausable but has no blacklist(address) / setFees.
# A selector that does not exist must never appear here.
priv = set((eth.get("privileged_functions") or []))
if "setFees" in priv:
    bad("USDC reports a 'setFees' owner power it does not have — selector is wrong again")
    failures.append("selectors")
else:
    ok(f"owner-power detection is sober  {DIM}(USDC -> {sorted(priv) or 'none'}){END}")

# ---- end-to-end: an evidence-backed critique -------------------------------
try:
    r = server.challenge_plan(
        "I'm putting my savings into this right now, everyone says it's guaranteed",
        token_address=PROBES[1][1], chain="ethereum")
    if not r["on_chain_evidence"].get("checked"):
        bad("end-to-end ran but no evidence was attached")
        failures.append("end-to-end")
    else:
        cited = [o for o in [r.get("strongest_objection")] if o]
        ok(f"end-to-end critique with live evidence  {DIM}(verdict: {r['verdict']}, "
           f"score {r['case_against_strength']}){END}")
        if r.get("what_i_could_not_verify"):
            print(f"{DIM}        discloses {len(r['what_i_could_not_verify'])} evidence gap(s){END}")
except Exception as e:
    bad(f"end-to-end critique failed: {type(e).__name__}: {e}")
    failures.append("end-to-end")

# ---- a token that genuinely does not exist should say so -------------------
try:
    ev = server._onchain_evidence("0x" + "1234" * 10, "ethereum")
    objs = server._evidence_objections(ev)
    if ev.get("is_contract") is False and any("no contract code" in o["fact"] for o in objs):
        ok("nonexistent contract is correctly called out")
    else:
        bad(f"nonexistent address not flagged (is_contract={ev.get('is_contract')})")
        failures.append("nonexistent")
except Exception as e:
    bad(f"nonexistent-address check raised {type(e).__name__}: {e}")
    failures.append("nonexistent")


# ------------------------------------------------------------------ verdict
head("Result")

if failures:
    print(f"{RED}  {len(failures)} real failure(s): {', '.join(failures)}{END}")
    print("  Do not deploy yet.\n")
    sys.exit(1)

if warnings:
    print(f"{YEL}  Logic is sound, but {len(warnings)} live call(s) did not come back.{END}")
    print(f"{DIM}  Usually a firewall, VPN, corporate network, or a rate-limited public RPC.")
    print("  Cassandra degrades gracefully — it still critiques your reasoning without")
    print(f"  chain data — but retry on another network before relying on the evidence features.{END}\n")
    sys.exit(0)

print(f"{GREEN}  Everything passed, including live on-chain calls.{END}")
print("  Safe to deploy.\n")
print(f"{DIM}  Next: python server.py     then     npx @modelcontextprotocol/inspector")
print(f"  In the Inspector: Streamable HTTP -> http://localhost:8000/mcp{END}\n")
sys.exit(0)
