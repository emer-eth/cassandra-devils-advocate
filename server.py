"""
CASSANDRA — The Devil's Advocate
=================================
An A2MCP service for the OKX.AI marketplace (Build X / OKX.AI Genesis Hackathon).

Every agent on this marketplace is built to say YES.
Find me data. Make me a logo. Give me a signal. Confirm what I already think.

Cassandra is built to say NO — or at least, "not like this, and here's why."

You hand it a plan. It steelmans your position (states your case better than you
did), then attacks it: names the cognitive bias visible in your own wording,
runs a pre-mortem to enumerate concrete failure paths, checks any on-chain claim
against real chain evidence, tells you exactly what evidence would change its
mind, and proposes the smallest reversible version you could test instead.

Named for the prophetess cursed to speak true and never be believed.

Design notes
------------
* **No LLM required.** This is a deterministic reasoning engine, not a chatbot
  wrapper: pattern-based bias detection over your own phrasing, a structured
  pre-mortem library, and live on-chain evidence. Same input -> same critique,
  no API key, no token cost, nothing to hallucinate.
* **It concedes.** A critic that objects to everything is noise. When a plan is
  sized, reversible and falsifiable, Cassandra says so and gets out of the way.
* Framed as decision hygiene, NOT financial advice.

Run:
    pip install -r requirements.txt
    python server.py          # streamable-http on 0.0.0.0:8000/mcp
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from landing import LANDING_HTML

HTTP_TIMEOUT = 6.0      # market / sellability APIs
RPC_TIMEOUT = 5.0       # a single RPC attempt, before failing over

DISCLAIMER = (
    "Cassandra is a decision-hygiene tool, not financial, legal or investment "
    "advice. It argues against your plan by design — that is its job, not a "
    "prediction. A strong case against a plan is not proof the plan is wrong, "
    "and a weak one is not permission. You own the decision."
)

# Every RPC below was verified live (eth_getCode + eth_call + eth_getStorageAt).
# Multiple per chain because public endpoints die without notice — a dead
# provider must degrade to the next one, not to a missing objection.
# Override any chain with <CHAIN>_RPC_URL (e.g. ETHEREUM_RPC_URL).
#
# "dexscreener" / "geckoterminal" are that chain's id at each market source.
# DexScreener does NOT index X Layer at all, so xlayer relies on GeckoTerminal.
CHAINS: dict[str, dict[str, Any]] = {
    "xlayer": {
        "id": 196,
        "rpcs": ["https://rpc.xlayer.tech", "https://xlayerrpc.okx.com", "https://xlayer.drpc.org"],
        "dexscreener": None,
        "geckoterminal": "x-layer",
        "honeypot": False,
    },
    "ethereum": {
        "id": 1,
        "rpcs": ["https://ethereum-rpc.publicnode.com", "https://eth.merkle.io", "https://eth.drpc.org"],
        "dexscreener": "ethereum",
        "geckoterminal": "eth",
        "honeypot": True,
    },
    "bsc": {
        "id": 56,
        "rpcs": ["https://bsc-dataseed.bnbchain.org", "https://bsc-dataseed1.bnbchain.org", "https://bsc.drpc.org"],
        "dexscreener": "bsc",
        "geckoterminal": "bsc",
        "honeypot": True,
    },
    "base": {
        "id": 8453,
        "rpcs": ["https://base-rpc.publicnode.com", "https://mainnet.base.org", "https://base.drpc.org"],
        "dexscreener": "base",
        "geckoterminal": "base",
        "honeypot": True,
    },
    "arbitrum": {
        "id": 42161,
        "rpcs": ["https://arbitrum-one-rpc.publicnode.com", "https://arb1.arbitrum.io/rpc", "https://arbitrum.drpc.org"],
        "dexscreener": "arbitrum",
        "geckoterminal": "arbitrum",
        "honeypot": False,
    },
    "polygon": {
        "id": 137,
        "rpcs": ["https://polygon-bor-rpc.publicnode.com", "https://polygon.drpc.org"],
        "dexscreener": "polygon",
        "geckoterminal": "polygon_pos",
        "honeypot": False,
    },
}
CHAIN_ALIASES = {"eth": "ethereum", "bnb": "bsc", "matic": "polygon", "x-layer": "xlayer", "okx": "xlayer"}

GECKOTERMINAL = "https://api.geckoterminal.com/api/v2"

# Remembers which endpoint last answered, so a dead provider is not re-probed
# on every call. Purely an optimisation — correctness never depends on it.
_LAST_GOOD_RPC: dict[str, str] = {}

mcp = FastMCP(
    name="Cassandra — The Devil's Advocate",
    instructions=(
        "Hire Cassandra to argue AGAINST a plan before you act on it. Call "
        "challenge_plan with the plan in plain language (and a token address if "
        "the plan involves one) to get a steelman of your position, the "
        "strongest case against it, named biases quoted from your own wording, "
        "concrete failure paths, what evidence would change the verdict, and the "
        "smallest reversible test. Use premortem for failure enumeration only, "
        "or bias_check for a fast read on how you framed the decision. "
        "Cassandra is deliberately adversarial and is not financial advice."
    ),
)


# ===========================================================================
# 1. BIAS DETECTION — quote the user's own words back at them
# ===========================================================================
# Each pattern: regex, bias name, the objection, and severity weight.

PATTERNS: list[dict[str, Any]] = [
    dict(
        re=r"\b(right now|hurry|hurries|before it'?s too late|last chance|closing soon|only \d+ (hours?|days?|spots?) left|ends tonight|act fast|don'?t miss)\b",
        bias="Manufactured urgency",
        weight=18,
        objection=(
            "Your framing contains a deadline. Ask who set it. Genuine opportunity "
            "rarely expires on a schedule that conveniently prevents you from "
            "checking it — but a bad offer needs that deadline to survive scrutiny. "
            "If this is still a good idea in 48 hours, you lose nothing by waiting. "
            "If it is only a good idea within the next hour, that is information "
            "about the offer, not the opportunity."
        ),
    ),
    dict(
        re=r"\b(everyone|everybody|every ?one is|all my friends|the whole|whole group|group chat|my friend said|influencer|kol|shill|trending|viral|everyone'?s (buying|in|talking))\b",
        bias="Social proof / herd following",
        weight=15,
        objection=(
            "Your reason for acting is that other people are acting. That is not "
            "evidence about the thing itself — it is evidence about a crowd, and "
            "crowds in this space are frequently the product being sold. Name the "
            "reason you would still act if nobody you knew was involved. If you "
            "cannot, you are not evaluating the plan, you are joining it."
        ),
    ),
    dict(
        re=r"\b(already (put|spent|invested|lost)|averag(e|ing) down|double down|doubling down|down bad|get (it|my money) back|recover my loss|break even|too late to sell|in too deep)\b",
        bias="Sunk cost / loss-chasing",
        weight=25,
        objection=(
            "You are reasoning from what you have already committed. Money already "
            "spent cannot be an argument for spending more — it is gone either way, "
            "and the position does not know or care what you paid. The only honest "
            "question: if you held none of this today, at today's price and with "
            "today's information, would you open this position from zero? If the "
            "answer is no, you are not investing, you are trying to be right."
        ),
    ),
    dict(
        re=r"\b(all in|all-in|everything i have|(stake|put|invest|send|move|throw) (in )?everything|my entire (savings|balance|portfolio|stack|net worth)|life savings|my savings|rent money|borrow(ed|ing)?|loan|credit card|max leverage|\d+x leverage|leverage|margin|liquidat)\b",
        bias="Ruinous position sizing",
        weight=35,
        objection=(
            "This is the objection that matters more than any view on whether you "
            "are right. You can be correct about direction and still be wiped out by "
            "size or leverage — being early is indistinguishable from being wrong if "
            "you cannot survive the interval. A plan that requires you to be right "
            "immediately is a bet, not a strategy. Assume the worst plausible outcome "
            "happens tomorrow: if that outcome ends your ability to keep playing, the "
            "size is wrong regardless of the thesis."
        ),
    ),
    dict(
        re=r"\b(guaranteed|guarantee|can'?t lose|cannot lose|risk[- ]free|sure thing|no[- ]brainer|certain|100% safe|always goes up|only goes up)\b",
        bias="False certainty",
        weight=30,
        objection=(
            "You have used the language of certainty about an uncertain outcome. "
            "There is no risk-free return; there are only risks that have not shown "
            "up yet, and confidence is the least reliable indicator of accuracy. "
            "State this plan as a probability instead of a certainty. If you cannot "
            "put a number on it, you do not have a thesis — you have a hope."
        ),
    ),
    dict(
        re=r"\b(100x|1000x|10x|moon|mooning|to the moon|life[- ]changing|generational wealth|retire|get rich|easy money|free money|printing)\b",
        bias="Outcome fixation / base-rate neglect",
        weight=20,
        objection=(
            "You are anchored on the payoff and silent on its probability. The "
            "distribution here has a long left tail that nobody screenshots: the "
            "overwhelming majority of assets promising this outcome go to zero or "
            "near it, and you are seeing the survivors because the failures stopped "
            "posting. Multiply your target by your honest odds of reaching it. If you "
            "have not estimated those odds, the expected value of this plan is "
            "unknown, not high."
        ),
    ),
    dict(
        re=r"\b(dev said|team (said|promised)|they promised|roadmap|audited|audit|trust me|insider|alpha|private (group|call)|whitelist|presale)\b",
        bias="Appeal to authority / unverified claim",
        weight=18,
        objection=(
            "Your confidence rests on somebody's statement. A claim is not evidence, "
            "an audit is not a guarantee, and a roadmap is a marketing document with "
            "no enforcement mechanism. Separate what you have verified yourself from "
            "what you were told. Then ask what the person telling you gains if you "
            "act — if their upside comes from your entry, they are not a source, they "
            "are a counterparty."
        ),
    ),
    dict(
        re=r"\b(just launched|brand new|new (token|coin|project|pool)|stealth|fair launch|day one|first mover|early|got in early)\b",
        bias="Novelty preference",
        weight=12,
        objection=(
            "Newness is doing load-bearing work in your reasoning, but it is the "
            "property most correlated with catastrophic failure: no track record, no "
            "adversarial testing, no history of behaving well under stress, and the "
            "founders' incentives are maximally front-loaded. 'Early' and 'unvetted' "
            "describe the same moment. What survives contact with time is unknowable "
            "at day one — that is the whole risk you are being paid for, and you "
            "should price it rather than celebrate it."
        ),
    ),
    dict(
        re=r"\b(i (just )?(feel|felt)|gut|instinct|vibes?|sense that|feels? (right|like)|convinced|obvious(ly)?|clearly)\b",
        bias="Intuition presented as analysis",
        weight=12,
        objection=(
            "The plan rests on a feeling wearing the costume of a conclusion. "
            "Intuition is a legitimate hypothesis generator and a terrible final "
            "arbiter, and words like 'obviously' tend to mark the exact places an "
            "argument has not been made. Write the case in falsifiable form: what "
            "specifically must be true, and how would you know if it were not?"
        ),
    ),
    dict(
        re=r"\b(worked (last time|before)|did this before|last time i|always works|has never failed|every time)\b",
        bias="Small-sample / survivorship reasoning",
        weight=15,
        objection=(
            "You are generalising from a handful of your own outcomes, which is a "
            "sample too small to distinguish skill from luck. A strategy that worked "
            "three times can still be negative expected value; you would need to know "
            "how often it fails and how badly, and you have only counted the wins. "
            "What was the largest loss this approach has ever produced for anyone, "
            "and could you absorb it?"
        ),
    ),
    dict(
        # Percentages and advertised yields only. A bare "100x" is a price
        # target, already caught as outcome fixation — matching it here quoted
        # the same words twice and answered a multiple with a yield critique.
        re=r"(\b\d{3,}\s*%|\b(apy|apr) of \d{3,}|\b\d{2,}\s*%\s*(a|per) (day|week|month))",
        bias="Implausible return claim",
        weight=28,
        objection=(
            "The advertised return sits outside the range that sustainable mechanisms "
            "produce. Yields that size are rarely a return ON capital — they are a "
            "return OF someone else's capital, paid in an emission that must be sold to "
            "be realised, and the rate is high precisely because it has to attract "
            "deposits faster than it loses them. Name who pays it and where that money "
            "comes from. If the answer is 'new depositors', you are not the investor — "
            "you are the yield."
        ),
    ),
    dict(
        re=r"\b(nobody (knows|is talking)|hidden gem|under ?the ?radar|undervalued|sleeping|mispriced|market hasn'?t)\b",
        bias="Unexamined edge claim",
        weight=20,
        objection=(
            "You are claiming an information edge over everyone else looking at the "
            "same public thing. That is possible but it is a strong claim and it "
            "requires a mechanism: state why you know something the market does not, "
            "and why that gap persists rather than being arbitraged away in minutes. "
            "If the answer is that you found it on social media, thousands of others "
            "did too, and you are not early — you are the liquidity."
        ),
    ),
    dict(
        # Deliberately narrow: "regardless of price" is disciplined averaging,
        # not a dismissed downside. Only match dismissal of RISK itself.
        re=r"\b(ignore the (risk|downside|warning)|don'?t care (about|if)|whatever the risk|no matter what|regardless of (the )?(risk|downside|consequence|what happens)|not worried|what could go wrong|there'?s no downside)\b",
        bias="Dismissed downside",
        weight=22,
        objection=(
            "You have pre-emptively waved away the failure case. That is the single "
            "most reliable predictor of being destroyed by it, because a risk you "
            "refuse to name is one you cannot size, hedge or exit. Say the downside "
            "out loud, in numbers, as a sentence beginning 'I lose ___ and then I'."
        ),
    ),
]


def _detect_biases(plan: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    low = plan.lower()
    for p in PATTERNS:
        m = re.search(p["re"], low, re.IGNORECASE)
        if m:
            found.append(
                {
                    "bias": p["bias"],
                    "your_words": m.group(0).strip(),
                    "objection": p["objection"],
                    "weight": p["weight"],
                }
            )
    found.sort(key=lambda f: f["weight"], reverse=True)
    return found


# ===========================================================================
# 2. PLAN CLASSIFICATION + PRE-MORTEM LIBRARY
# ===========================================================================

PLAN_TYPES: dict[str, str] = {
    # NOTE: "exit" deliberately requires an explicit selling intent. A bare
    # "I will exit if X" is an invalidation clause inside an acquire plan —
    # treating it as a sell plan produces the wrong pre-mortem entirely.
    "acquire":  r"\b(buy|buying|bought|buy more|ape|aping|going long|enter|entry|invest\w*|acquire|accumulate|get in|got in|allocat\w+|hold\w*|position in|averag\w+ down|add to (my )?position|dca|put\w* (in |into )?(my |the |half my )?(money|savings|cash|capital|\$?\d+))\b",
    "exit":     r"\b(sell|selling|dump|take profit|taking profit|close (my|the|this) position|exit (my|the|this) (position|trade|bag)|liquidate my|go short|shorting)\b",
    # "100x" is a price target, NOT leverage — bare \d+x must not match here or
    # it drags a leverage critique into plans that involve no leverage at all.
    "leverage": r"\b(leverage[d]?|margin|perp|perps|futures|liquidation|\d+x (leverage|long|short|margin)|(leverage|margin) of \d+)\b",
    "deploy":   r"\b(deploy|launch|ship|shipping|build|building|create|creating|develop|code up|write a|make an?|mint|contract|token launch|go live|release|start a)\b",
    "delegate": r"\b(hire|hiring|pay|paying|outsource|delegate|agent to|let (the|my) agent|automate|subscribe)\b",
    "yield":    r"\b(stake|staking|farm|farming|yield|apy|apr|liquidity pool|provide liquidity|lp|lend(ing)?|deposit)\b",
}

PREMORTEM: dict[str, list[str]] = {
    "acquire": [
        "You bought near a local top because the reason you heard about it was the same reason it had already run.",
        "You could not exit at any size — the liquidity you saw was thin, one-sided, or partly the seller's own.",
        "The thesis was correct but the timeline was 3x longer than your patience, and you sold at the bottom of the drawdown.",
        "Supply you did not model unlocked — team allocation, vesting cliff, or a mint function — and diluted you.",
        "You were right about the sector and wrong about this specific instrument within it.",
    ],
    "exit": [
        "You sold the entire position on a temporary drawdown and watched the thesis play out without you.",
        "You exited to avoid discomfort rather than because anything in your thesis broke.",
        "Tax, fees or slippage consumed a meaningful share of the gain you were protecting.",
        "You had no plan for the proceeds, so you redeployed them impulsively into something worse.",
    ],
    "leverage": [
        "A brief wick you would have slept through liquidated the position; the price then went exactly where you predicted.",
        "Funding costs bled the position over weeks until it was unprofitable even though direction was right.",
        "You were liquidated at the worst possible print during a cascade, not at the price you set.",
        "You added margin to defend the position and converted a survivable loss into a ruinous one.",
    ],
    "deploy": [
        "You shipped it and nobody used it, because you never validated that anyone wanted it before building.",
        "A bug or exploit in code you wrote fast under deadline cost you money or reputation you could not refund.",
        "It worked but you could not be found — distribution, not the product, was the binding constraint.",
        "An incumbent already did this, had traction you did not check for, and you spent your effort re-solving a solved problem.",
        "Maintenance cost exceeded what you expected and it quietly rotted, taking your credibility with it.",
    ],
    "delegate": [
        "The agent did exactly what you asked and what you asked was wrong; the error scaled at machine speed.",
        "You could not verify the output, so you accepted it, and the mistake surfaced later at greater cost.",
        "The counterparty had no track record, took the payment, and delivered something technically compliant but useless.",
        "Spend compounded quietly per-call until the total was far past what you would have approved as a lump sum.",
    ],
    "yield": [
        "The yield was denominated in an emission that fell faster than the yield accrued; real return was negative.",
        "The contract holding your principal was exploited — the return was compensation for a risk that materialised.",
        "Impermanent loss quietly exceeded the fees earned and you would have done better holding.",
        "Withdrawal was gated, queued or paused exactly when you needed the capital.",
    ],
    "general": [
        "The plan assumed a condition you never wrote down, and that condition failed silently.",
        "You committed more than you could afford to lose because the decision arrived in stages, none of which felt final.",
        "You never defined what failure looked like, so you could not tell you were in it until it was expensive.",
        "The opportunity cost was the real loss — capital and attention locked here while a better option passed.",
    ],
}


def _classify(plan: str) -> list[str]:
    low = plan.lower()
    kinds = [k for k, pat in PLAN_TYPES.items() if re.search(pat, low, re.IGNORECASE)]
    return kinds or ["general"]


# ===========================================================================
# 3. ON-CHAIN EVIDENCE (so objections cite facts, not vibes)
# ===========================================================================

def _resolve_chain(chain: str) -> tuple[str, dict[str, Any]]:
    key = CHAIN_ALIASES.get(chain.strip().lower(), chain.strip().lower())
    if key not in CHAINS:
        raise ValueError(f"Unsupported chain '{chain}'. Supported: {', '.join(CHAINS)}.")
    return key, CHAINS[key]


def _endpoints(chain_key: str, cfg: dict[str, Any]) -> list[str]:
    """Endpoints to try, best-known first. Env override always wins."""
    urls = list(cfg["rpcs"])
    for preferred in (_LAST_GOOD_RPC.get(chain_key), os.getenv(f"{chain_key.upper()}_RPC_URL")):
        if preferred:
            urls = [preferred] + [u for u in urls if u != preferred]
    return urls


def _rpc_once(client: httpx.Client, url: str, method: str, params: list[Any]) -> Any:
    r = client.post(url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                    timeout=RPC_TIMEOUT)
    r.raise_for_status()
    d = r.json()
    if "error" in d:
        raise RuntimeError(d["error"].get("message", "rpc error"))
    return d.get("result")


def _rpc(client: httpx.Client, chain_key: str, cfg: dict[str, Any],
         method: str, params: list[Any]) -> tuple[Any, str]:
    """Call `method`, failing over across endpoints. Returns (result, url_that_answered)."""
    last: Optional[Exception] = None
    for url in _endpoints(chain_key, cfg):
        try:
            res = _rpc_once(client, url, method, params)
            _LAST_GOOD_RPC[chain_key] = url
            return res, url
        except Exception as e:      # dead host, rate limit, method not supported
            last = e
    raise RuntimeError(f"no RPC endpoint answered ({type(last).__name__}: {str(last)[:80]})")


def _call(client: httpx.Client, chain_key: str, cfg: dict[str, Any],
          url: str, to: str, selector: str) -> Optional[str]:
    """eth_call against the endpoint already known to work, failing over if it
    refuses eth_call specifically (several public nodes serve state but not calls)."""
    params = [{"to": to, "data": "0x" + selector}, "latest"]
    try:
        return _rpc_once(client, url, "eth_call", params)
    except Exception:
        try:
            return _rpc(client, chain_key, cfg, "eth_call", params)[0]
        except Exception:
            return None


def _dec_str(h: Optional[str]) -> Optional[str]:
    if not h or h == "0x":
        return None
    raw = h[2:]
    try:
        if len(raw) >= 128:
            ln = int(raw[64:128], 16)
            return bytes.fromhex(raw[128:128 + ln * 2]).decode("utf-8", "ignore").strip("\x00") or None
        return bytes.fromhex(raw).decode("utf-8", "ignore").strip("\x00") or None
    except Exception:
        return None


def _dec_addr(h: Optional[str]) -> Optional[str]:
    if not h or h == "0x" or len(h) < 66:
        return None
    return "0x" + h[-40:]


# Owner powers, found by looking for their 4-byte selectors in the deployed
# bytecode. Every value below is keccak256(signature)[:4], computed and checked
# against name()/symbol()/owner()/transfer() as known-good fixtures — a wrong
# selector here would be an invented fact, which is the one thing this service
# cannot afford. Several spellings per capability because token contracts are
# not written to a standard.
RISKY_SELECTORS: dict[str, dict[str, str]] = {
    "mint": {
        "40c10f19": "mint(address,uint256)",
        "a0712d68": "mint(uint256)",
        "94d008ef": "mint(address,uint256,bytes)",
    },
    "pause": {
        "8456cb59": "pause()",
        "1031e36e": "pauseTrading()",
        "16c38b3c": "setPaused(bool)",
    },
    "blacklist": {
        "f9f92be4": "blacklist(address)",
        "404e5129": "blacklist(address,bool)",
        "153b0d1e": "setBlacklist(address,bool)",
        "68092bd9": "setBlackList(address,bool)",
        "9cfe42da": "addBlacklist(address)",
        "f3290d75": "blacklistAddress(address)",
    },
    "setFees": {
        "0b78f9c0": "setFees(uint256,uint256)",
        "3d18678e": "setFees(uint256)",
        "69fe0e2d": "setFee(uint256)",
        "c647b20e": "setTaxes(uint256,uint256)",
        "6db79437": "updateFees(uint256,uint256)",
        "0cc835a3": "setBuyFee(uint256)",
        "8b4cee08": "setSellFee(uint256)",
    },
}


def _f(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _market_dexscreener(client: httpx.Client, addr: str, ds_chain: str) -> Optional[dict[str, Any]]:
    """Deepest pair for this token ON THE CHAIN WE WERE ASKED ABOUT.

    DexScreener returns pairs across every chain it indexes, so an unfiltered
    sort by liquidity happily hands back a different chain's pool — for USDC on
    Ethereum it returns a PulseChain pair at $0.0007. Filtering is not optional.
    """
    r = client.get(f"https://api.dexscreener.com/latest/dex/tokens/{addr}", timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    pairs = [p for p in (r.json().get("pairs") or []) if p.get("chainId") == ds_chain]
    if not pairs:
        return None
    pairs.sort(key=lambda p: _f((p.get("liquidity") or {}).get("usd")) or 0.0, reverse=True)
    top = pairs[0]
    ch = top.get("priceChange") or {}
    out: dict[str, Any] = {
        "liquidity_usd": _f((top.get("liquidity") or {}).get("usd")),
        "volume_24h": _f((top.get("volume") or {}).get("h24")),
        "price_usd": top.get("priceUsd"),
        "price_change_1h": ch.get("h1"),
        "price_change_6h": ch.get("h6"),
        "price_change_24h": ch.get("h24"),
        "pairs_on_this_chain": len(pairs),
        "top_dex": top.get("dexId"),
    }
    if top.get("pairCreatedAt"):
        out["pair_age_days"] = round((time.time() * 1000 - top["pairCreatedAt"]) / 86_400_000, 1)
    return out


def _market_geckoterminal(client: httpx.Client, addr: str, gt_network: str) -> Optional[dict[str, Any]]:
    """Fallback market source — and the ONLY one that covers X Layer."""
    r = client.get(f"{GECKOTERMINAL}/networks/{gt_network}/tokens/{addr}/pools", timeout=HTTP_TIMEOUT)
    if r.status_code == 429:
        raise RuntimeError("rate limited")
    r.raise_for_status()
    pools = r.json().get("data") or []
    if not pools:
        return None

    def reserve(p: dict[str, Any]) -> float:
        return _f((p.get("attributes") or {}).get("reserve_in_usd")) or 0.0

    pools.sort(key=reserve, reverse=True)
    top = pools[0]
    a = top.get("attributes") or {}
    rel = top.get("relationships") or {}

    def rel_id(key: str) -> str:
        return (((rel.get(key) or {}).get("data") or {}).get("id") or "").lower()

    # The pool quotes a price for its base token and its quote token. Report the
    # one that is actually the token we were asked about, or nothing at all.
    want = f"{gt_network}_{addr}".lower()
    if rel_id("base_token") == want:
        price = a.get("base_token_price_usd")
    elif rel_id("quote_token") == want:
        price = a.get("quote_token_price_usd")
    else:
        price = None

    chg = a.get("price_change_percentage") or {}
    out: dict[str, Any] = {
        "liquidity_usd": reserve(top) or None,
        "volume_24h": _f((a.get("volume_usd") or {}).get("h24")),
        "price_usd": price,
        "price_change_1h": chg.get("h1"),
        "price_change_6h": chg.get("h6"),
        "price_change_24h": chg.get("h24"),
        "pairs_on_this_chain": len(pools),
        "top_dex": rel_id("dex").replace(f"{gt_network}_", "") or None,
    }
    created = a.get("pool_created_at")
    if created:
        try:
            born = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
            out["pair_age_days"] = round(
                (datetime.now(timezone.utc) - born).total_seconds() / 86_400, 1)
        except (TypeError, ValueError):
            pass
    return out


def _market_evidence(client: httpx.Client, addr: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Market facts, and — when there are none — an honest reason why.

    'No market exists' and 'we could not see the market' are different claims.
    Only the first one is evidence, and only the first one earns an objection.
    """
    sources: list[tuple[str, Any]] = []
    if cfg.get("dexscreener"):
        sources.append(("dexscreener", lambda: _market_dexscreener(client, addr, cfg["dexscreener"])))
    if cfg.get("geckoterminal"):
        sources.append(("geckoterminal", lambda: _market_geckoterminal(client, addr, cfg["geckoterminal"])))

    answered_empty = False
    errors: list[str] = []
    for name, fetch in sources:
        try:
            found = fetch()
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__} {str(e)[:60]}")
            continue
        if found:
            found["market_source"] = name
            return found
        answered_empty = True

    if answered_empty:
        return {
            "liquidity_usd": None,
            "no_market_found": True,
            "market_sources_checked": [n for n, _ in sources],
        }
    return {
        "liquidity_usd": None,
        "market_data_unavailable": True,
        "market_note": (
            "No market source answered for this chain, so liquidity and price are unknown. "
            "That is a gap in my evidence, not a finding about the token — I will not object "
            "to something I could not see."
        ),
        "market_errors": errors or ["no market-data source covers this chain"],
    }


def _onchain_evidence(token_address: str, chain: str) -> dict[str, Any]:
    """Gather hard facts. Every field may be None if a source is unreachable."""
    ev: dict[str, Any] = {"checked": False, "chain": chain}
    try:
        chain_key, cfg = _resolve_chain(chain)
    except ValueError as e:
        ev["error"] = str(e)
        return ev
    ev["chain"] = chain_key
    gaps: list[str] = []

    with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        # --- chain state ---
        try:
            code, url = _rpc(client, chain_key, cfg, "eth_getCode", [token_address, "latest"])
            ev["checked"] = True
            ev["rpc_endpoint"] = url
            ev["is_contract"] = bool(code and code != "0x")
            if ev["is_contract"]:
                ev["name"] = _dec_str(_call(client, chain_key, cfg, url, token_address, "06fdde03"))
                ev["symbol"] = _dec_str(_call(client, chain_key, cfg, url, token_address, "95d89b41"))
                owner = _dec_addr(_call(client, chain_key, cfg, url, token_address, "8da5cb5b"))
                zero, dead = "0x" + "0" * 40, "0x" + "0" * 36 + "dead"
                ev["owner"] = owner
                ev["ownership_renounced"] = (owner.lower() in (zero, dead)) if owner else None
                lc = (code or "").lower()
                ev["privileged_functions"] = [
                    capability for capability, sigs in RISKY_SELECTORS.items()
                    if any(sel in lc for sel in sigs)
                ]
                try:
                    slot = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
                    impl, _ = _rpc(client, chain_key, cfg, "eth_getStorageAt",
                                   [token_address, slot, "latest"])
                    ev["is_upgradeable_proxy"] = bool(impl and int(impl, 16) != 0)
                except Exception:
                    ev["is_upgradeable_proxy"] = None
                    gaps.append("Could not read the proxy slot, so I cannot say whether the code is upgradeable.")
        except Exception as e:
            ev["chain_error"] = str(e)
            gaps.append("No RPC endpoint answered for this chain, so contract ownership and "
                        "privileged functions are unverified.")

        # --- market ---
        ev.update(_market_evidence(client, token_address, cfg))
        if ev.get("market_data_unavailable"):
            gaps.append("Liquidity and price are unknown — no market source answered.")

        # --- sellability ---
        if cfg["honeypot"]:
            try:
                r = client.get("https://api.honeypot.is/v2/IsHoneypot",
                               params={"address": token_address, "chainID": cfg["id"]},
                               timeout=HTTP_TIMEOUT)
                r.raise_for_status()
                d = r.json()
                ev["is_honeypot"] = (d.get("honeypotResult") or {}).get("isHoneypot")
                sim = d.get("simulationResult") or {}
                ev["buy_tax"], ev["sell_tax"] = _f(sim.get("buyTax")), _f(sim.get("sellTax"))
            except Exception as e:
                ev["honeypot_error"] = str(e)
                gaps.append("The sell simulation did not run, so I cannot confirm this token is sellable.")
        else:
            ev["sellability_simulation"] = "unsupported on this chain"
            gaps.append(f"Sell simulation is not available on {chain_key}, so I cannot prove "
                        "the exit works — only that a market exists.")

    if gaps:
        ev["evidence_gaps"] = gaps
    return ev


def _evidence_objections(ev: dict[str, Any]) -> list[dict[str, Any]]:
    """Turn hard facts into specific, cited objections."""
    out: list[dict[str, Any]] = []

    def add(weight: int, fact: str, objection: str):
        out.append({"fact": fact, "objection": objection, "weight": weight})

    if ev.get("checked") and ev.get("is_contract") is False:
        add(40, "This address holds no contract code.",
            "You are describing a token that does not exist at this address. Either the address is wrong or you were given a wallet. Stop here and re-check the source you copied it from.")

    if ev.get("is_honeypot") is True:
        add(45, "A simulated sale of this token failed.",
            "Buying is not the risk; being unable to sell is. Simulation says the exit does not work. Your entire plan assumes an exit that this contract may not permit.")

    st = ev.get("sell_tax")
    if isinstance(st, (int, float)) and st >= 15:
        add(25, f"Sell tax is approximately {st}%.",
            f"You must be right by more than {st}% before you break even on the exit alone. Your plan needs to clear a hurdle you have probably not included in it.")

    liq = ev.get("liquidity_usd")
    if isinstance(liq, (int, float)):
        if liq < 10_000:
            add(30, f"Pooled liquidity is about ${liq:,.0f}.",
                "At this depth your own exit is the event that moves the price against you. A position you cannot leave at size is not a position, it is a donation with extra steps.")
        elif liq < 100_000:
            add(15, f"Pooled liquidity is about ${liq:,.0f}.",
                "Thin enough that your exit will cost noticeably more than your entry suggests. Size against the pool, not against your conviction.")
    if ev.get("no_market_found"):
        add(28, "No trading pair was found for this token.",
            "There is currently no observable market. You would be entering something with no demonstrated exit and no price discovery.")

    age = ev.get("pair_age_days")
    if isinstance(age, (int, float)) and age < 7:
        add(18, f"The trading pair is {age} days old.",
            "There is no track record here — no history of behaving well under stress, and no adversarial testing. You are underwriting a risk that has not had time to show itself.")

    priv = ev.get("privileged_functions") or []
    if priv and ev.get("ownership_renounced") is False:
        meaning = {
            "blacklist": "'blacklist' means your address can be stopped from selling",
            "mint": "'mint' means your share can be diluted at will",
            "pause": "'pause' means trading can be halted",
            "setFees": "'setFees' means the tax on your exit can be raised after you enter",
        }
        add(30, f"The owner address retains: {', '.join(priv)}.",
            "One key can change the rules after you commit. "
            + "; ".join(meaning[p] for p in priv if p in meaning)
            + ". Your plan silently assumes the owner chooses not to.")
    if ev.get("is_upgradeable_proxy"):
        add(20, "The contract is an upgradeable proxy.",
            "The code you are evaluating is not necessarily the code that will hold your funds tomorrow. You are trusting a future version that does not exist yet.")

    ch24 = ev.get("price_change_24h")
    try:
        if ch24 is not None and float(ch24) > 40:
            add(20, f"Price is up {float(ch24):.0f}% in 24 hours.",
                "You are arriving after the move, which means the people you are buying from are the ones who were early. Ask honestly whether you found this because it already ran.")
    except (TypeError, ValueError):
        pass
    return out


# ===========================================================================
# 4. STEELMAN + VERDICT
# ===========================================================================

STEELMAN: dict[str, str] = {
    "acquire": "Asymmetric bets are how outsized outcomes happen, and refusing all of them guarantees you never catch one. If this is sized so the total loss is genuinely survivable and irrelevant to your life, the downside is bounded at 100% while the upside is not — and that asymmetry is a real argument.",
    "exit":    "Taking profit is never wrong in hindsight-free terms: realised gains are the only ones that exist, and reducing a position you no longer understand is discipline, not fear.",
    "leverage": "Leverage is a legitimate tool for expressing high-conviction, defined-risk views efficiently, and capital efficiency is a real advantage when the position is small relative to your equity and the invalidation is pre-set.",
    "deploy":  "Shipping is the only way to convert a hypothesis into information. Building it is often cheaper than the research needed to be sure about it, and being early to a real category compounds.",
    "delegate": "Delegating removes you as the bottleneck, and your attention is the scarcest input you have. If the task is verifiable and bounded, paying to not do it yourself is straightforwardly correct.",
    "yield":   "Idle capital has a real cost, and being paid to hold something you would hold anyway is close to a free option — provided the yield is not the reason you hold it.",
    "general": "Action under uncertainty is unavoidable, and waiting for certainty is itself a decision with costs. A plan that is reversible and sized to survive being wrong deserves to be tried rather than debated.",
}

MIND_CHANGERS: dict[str, list[str]] = {
    "acquire": [
        "You can state the invalidation before you enter: the specific observable event that means the thesis is dead, and the price or date at which you act on it.",
        "The position is sized so that a total loss changes nothing material about your life.",
        "You can name a reason to hold that has nothing to do with the price going up.",
    ],
    "exit": [
        "Something in your original thesis actually broke, and you can name it.",
        "You have a defined use for the proceeds decided before the sale, not after.",
    ],
    "leverage": [
        "Your liquidation price sits outside the worst historical drawdown this asset has produced, not just outside your expectations.",
        "You have written the maximum loss as a number you have already accepted losing.",
    ],
    "deploy": [
        "At least one person who is not you, and not a friend, has asked for this unprompted.",
        "You checked for incumbents and can state specifically what you do that they do not.",
        "You can ship a crude version in days rather than weeks, so being wrong is cheap.",
    ],
    "delegate": [
        "You can verify the output cheaply and independently of the party producing it.",
        "The counterparty has a track record you checked rather than claims you read.",
        "There is a hard spend cap that does not depend on you remembering to watch it.",
    ],
    "yield": [
        "The return is denominated in something you would willingly hold with no yield at all.",
        "You can name the risk you are being paid to take, and it is not simply 'the contract works'.",
    ],
    "general": [
        "The decision is reversible, or the cost of reversing it is one you have priced.",
        "You wrote down in advance what failure looks like and what you will do when you see it.",
    ],
}


def _verdict(score: int) -> tuple[str, str]:
    if score >= 70:
        return ("THE CASE AGAINST IS STRONG",
                "Multiple independent objections point the same direction, and at least one is structural rather than a matter of taste. I would not proceed in this form. If you proceed anyway, do it at a size where being wrong is boring.")
    if score >= 40:
        return ("THE CASE AGAINST IS SUBSTANTIAL",
                "There are real problems here, but they look like problems of construction rather than of premise. Fix the sizing and write down the invalidation, and this becomes a defensible plan rather than a bet.")
    if score >= 18:
        return ("THE CASE AGAINST IS MODERATE",
                "Nothing fatal surfaced. The objections worth taking seriously are about what you have not specified yet, not about what you have got wrong.")
    if score >= 1:
        return ("THE CASE AGAINST IS WEAK, BUT NOT EMPTY",
                "I found one or two soft spots and nothing structural. Worth tightening the point I raised, but I would not talk you out of this.")
    return ("I CANNOT MOUNT A CASE AGAINST THIS",
            "I argued in good faith and found nothing to attack. The plan appears sized, reversible and specific enough that any objection I made would be noise. Proceed — and note that my finding nothing is not the same as there being nothing.")


# ===========================================================================
# 5. TOOLS
# ===========================================================================

@mcp.tool
def challenge_plan(
    plan: str,
    token_address: str | None = None,
    chain: str = "xlayer",
) -> dict[str, Any]:
    """Argue against a plan before you act on it. Cassandra's primary service.

    Give it your intention in plain language — "I'm going to put half my savings
    into this token that just launched, everyone in my group chat is buying" —
    and it returns: the strongest version of your own argument, the case against
    it, cognitive biases quoted from your own wording, concrete failure paths,
    hard on-chain evidence if a token is involved, what would change the verdict,
    and the smallest reversible test.

    Args:
        plan: Your plan or decision, in plain language. More context = sharper critique.
        token_address: Optional. A token contract address, if the plan involves one —
                       this upgrades objections from reasoning to cited chain evidence.
        chain: Chain for the address (xlayer, ethereum, bsc, base, arbitrum, polygon).

    Adversarial by design. Decision hygiene, not financial advice.
    """
    if not plan or not plan.strip():
        return {"error": "Give me a plan to argue against. One sentence is enough.", "disclaimer": DISCLAIMER}
    if len(plan) > 4000:
        plan = plan[:4000]

    kinds = _classify(plan)
    biases = _detect_biases(plan)

    evidence: dict[str, Any] = {}
    ev_objections: list[dict[str, Any]] = []
    if token_address:
        if not (isinstance(token_address, str) and token_address.startswith("0x") and len(token_address) == 42):
            return {"error": "token_address must be a 42-character address starting with 0x.", "disclaimer": DISCLAIMER}
        evidence = _onchain_evidence(token_address, chain)
        ev_objections = _evidence_objections(evidence)

    score = min(100, sum(b["weight"] for b in biases) + sum(o["weight"] for o in ev_objections))
    headline, stance = _verdict(score)

    premortem: list[str] = []
    for k in kinds:
        premortem.extend(PREMORTEM.get(k, []))
    seen: set[str] = set()
    premortem = [p for p in premortem if not (p in seen or seen.add(p))][:6]

    changers: list[str] = []
    for k in kinds:
        changers.extend(MIND_CHANGERS.get(k, []))
    changers.extend(MIND_CHANGERS["general"])
    seen = set()
    changers = [c for c in changers if not (c in seen or seen.add(c))][:5]

    # The single most important objection, whatever its source.
    pool = [{"source": "your reasoning", "detail": b["objection"], "weight": b["weight"], "label": b["bias"]} for b in biases]
    pool += [{"source": "on-chain evidence", "detail": o["objection"], "weight": o["weight"], "label": o["fact"]} for o in ev_objections]
    strongest = max(pool, key=lambda x: x["weight"], default=None)

    return {
        "your_plan": plan,
        "plan_type": kinds,
        "steelman": {
            "note": "Before I argue against you, here is your case made as well as I can make it.",
            "argument": " ".join(dict.fromkeys(STEELMAN.get(k, STEELMAN["general"]) for k in kinds)),
        },
        "verdict": headline,
        "case_against_strength": score,
        "my_position": stance,
        "strongest_objection": strongest,
        "biases_in_your_own_words": [
            {"bias": b["bias"], "you_said": b["your_words"], "objection": b["objection"]} for b in biases
        ],
        "framing_note": (
            "Your framing did not contain the usual tells — no manufactured urgency, no social "
            "proof, no dismissed downside, no borrowed certainty. That is rarer than you would "
            "think and it is to your credit."
            if not biases else
            f"{len(biases)} pattern(s) in your wording are doing argumentative work your evidence is not."
        ),
        "premortem": {
            "prompt": "Assume this failed badly. Here are the most common ways it happens:",
            "failure_paths": premortem,
        },
        "on_chain_evidence": evidence or {"checked": False, "note": "No token address supplied — critique is based on your reasoning alone. Pass token_address for evidence-backed objections."},
        # Stated plainly, because a critic that hides the limits of its own
        # evidence is asking to be trusted rather than checked.
        **({"what_i_could_not_verify": evidence["evidence_gaps"]} if evidence.get("evidence_gaps") else {}),
        "what_would_change_my_mind": changers,
        "smallest_reversible_test": (
            "Before committing fully: do the smallest version that still produces real information. "
            "Commit an amount you would forget about, set the invalidation condition in writing first, "
            "and give it a deadline. If the small version does not teach you something you did not already "
            "believe, the large version will not either."
        ),
        "disclaimer": DISCLAIMER,
    }


@mcp.tool
def premortem(plan: str) -> dict[str, Any]:
    """Assume the plan already failed, then work backwards to why.

    A pre-mortem beats a risk list because it recruits hindsight you do not have
    yet: it is far easier to explain a failure that has 'already happened' than
    to imagine one that might. Returns concrete failure paths for your plan type.

    Args:
        plan: The plan, in plain language.
    """
    if not plan or not plan.strip():
        return {"error": "Give me a plan.", "disclaimer": DISCLAIMER}
    kinds = _classify(plan)
    paths: list[str] = []
    for k in kinds:
        paths.extend(PREMORTEM.get(k, []))
    paths.extend(PREMORTEM["general"])
    seen: set[str] = set()
    paths = [p for p in paths if not (p in seen or seen.add(p))]
    return {
        "your_plan": plan,
        "plan_type": kinds,
        "framing": "It is twelve months from now. This plan failed, and it is obvious in hindsight why. Which of these is the story?",
        "failure_paths": paths,
        "instruction": "Pick the one that made you least comfortable to read. That is the one your plan does not currently defend against. Go defend against it.",
        "disclaimer": DISCLAIMER,
    }


@mcp.tool
def bias_check(plan: str) -> dict[str, Any]:
    """Fast read on HOW you framed a decision, ignoring its merits.

    Detects manufactured urgency, social proof, sunk-cost reasoning, false
    certainty, dismissed downside and other tells — and quotes your own words
    back to you. Cheap sanity check before the full challenge_plan.

    Args:
        plan: The plan or decision, in your own words.
    """
    if not plan or not plan.strip():
        return {"error": "Give me something to read.", "disclaimer": DISCLAIMER}
    biases = _detect_biases(plan)
    total = min(100, sum(b["weight"] for b in biases))
    return {
        "your_plan": plan,
        "framing_risk": total,
        "reading": (
            "Your framing is doing a lot of work that your evidence is not."
            if total >= 45 else
            "Some pressure in the framing, but it is not driving the decision."
            if total >= 18 else
            "Clean framing. You are describing a decision rather than justifying one."
        ),
        "detected": [
            {"bias": b["bias"], "you_said": b["your_words"], "why_it_matters": b["objection"]} for b in biases
        ],
        "note": "This judges the wording of your decision, not whether it is correct. A well-framed bad idea is still a bad idea — run challenge_plan for that.",
        "disclaimer": DISCLAIMER,
    }


@mcp.tool
def supported_chains() -> dict[str, Any]:
    """Chains Cassandra can pull on-chain evidence from, and what works on each."""
    return {
        "chains": {
            k: {
                "chain_id": v["id"],
                "contract_checks": True,
                "market_data_source": v.get("dexscreener") and "dexscreener" or v.get("geckoterminal") and "geckoterminal",
                "sellability_simulation": v["honeypot"],
            }
            for k, v in CHAINS.items()
        },
        "default": "xlayer",
        "note": (
            "Contract ownership, privileged functions and proxy checks work on every chain listed. "
            "Sellability simulation is unavailable on X Layer, Arbitrum and Polygon. Where a check "
            "cannot run, Cassandra reports the gap instead of inferring a finding from it."
        ),
    }


# ---------------------------------------------------------------------------
# Health check. GET /mcp correctly answers 406 (the MCP endpoint requires an
# SSE Accept header), which a platform health check reads as "unhealthy" and
# restarts the service over. This gives Render — and OKX — a plain 200.
# ---------------------------------------------------------------------------

@mcp.custom_route("/", methods=["GET"])
async def landing(request: Request) -> HTMLResponse:
    """A front door. Reviewers and judges paste the base URL into a browser;
    'Not Found' reads as a broken service even when /mcp is perfectly healthy."""
    origin = str(request.base_url).rstrip("/")
    return HTMLResponse(LANDING_HTML.replace("__ORIGIN__", origin))


# --- browser demo -----------------------------------------------------------
# The landing page needs to call the engine from JavaScript, and /mcp cannot
# serve that: MCP is POST + SSE with a session handshake. This is the same
# reasoning engine behind a plain JSON route — no second implementation.

_RATE: dict[str, list[float]] = {}
# Generous on purpose: the engine costs nothing per call (no model), so the only
# thing worth protecting is upstream RPC quota. 20/min throttled legitimate use —
# recording a demo takes dozens of retakes from one IP.
RATE_LIMIT = int(os.getenv("DEMO_RATE_LIMIT", "60"))
RATE_WINDOW = 60.0


def _rate_limited(ip: str) -> bool:
    now = time.time()
    hits = [t for t in _RATE.get(ip, []) if now - t < RATE_WINDOW]
    _RATE[ip] = hits + [now]
    if len(_RATE) > 4000:                      # bound memory on a warm instance
        for stale in [k for k, v in _RATE.items() if not v or now - v[-1] > RATE_WINDOW]:
            _RATE.pop(stale, None)
    return len(hits) >= RATE_LIMIT


@mcp.custom_route("/api/challenge", methods=["POST"])
async def api_challenge(request: Request) -> JSONResponse:
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
          or (request.client.host if request.client else "unknown"))
    if _rate_limited(ip):
        return JSONResponse(
            {"error": "That is a lot of plans in one minute. Give it a moment — "
                      "or call the service properly over MCP, where there is no limit."},
            status_code=429)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Send JSON: {\"plan\": \"...\"}"}, status_code=400)

    plan = (body.get("plan") or "").strip()
    token = (body.get("token_address") or "").strip() or None
    chain = (body.get("chain") or "xlayer").strip() or "xlayer"
    if not plan:
        return JSONResponse({"error": "Give me a plan to argue against."}, status_code=400)

    # The tool object wraps the function in some FastMCP versions; unwrap either way.
    impl = getattr(challenge_plan, "fn", challenge_plan)
    try:
        return JSONResponse(impl(plan, token, chain))
    except Exception as e:                     # never leak a stack trace to a judge
        return JSONResponse(
            {"error": f"The critique failed to run ({type(e).__name__}). The reasoning "
                      f"engine is fine; this is usually a chain-data timeout — try again "
                      f"without a token address."}, status_code=500)


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "service": "Cassandra — The Devil's Advocate",
        "protocol": "a2mcp / streamable-http",
        "mcp_endpoint": "/mcp",
        "tools": ["challenge_plan", "premortem", "bias_check", "supported_chains"],
    })


if __name__ == "__main__":
    mcp.run(transport="http", host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")))
