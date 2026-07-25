"""
The public front door for Cassandra.

Kept in a module rather than a .html file so it is always importable wherever a
serverless bundler unpacks the app — a missing template would take the whole
page down. `__ORIGIN__` is substituted with the live origin at request time, so
the page always prints its own real endpoints.

The centrepiece is the live demo: the reasoning engine is deterministic and
fast, so a visitor can be argued with in the page instead of reading a feature
list about being argued with. It calls /api/challenge — the same engine as /mcp.
"""

LANDING_HTML = r"""<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cassandra — The Devil's Advocate</title>
<meta name="description" content="Every agent on OKX.AI is built to say yes. Cassandra is built to say no. State a plan; it argues against it — naming the bias in your own words, running a pre-mortem, and checking the chain. It concedes when your plan is sound.">
<meta property="og:title" content="Cassandra — The Devil's Advocate">
<meta property="og:description" content="Every AI agent is built to say yes. I built one that says no.">
<meta property="og:type" content="website">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' fill='%2314120f'/><text y='74' x='50' text-anchor='middle' font-size='68' font-family='Georgia,serif' fill='%23ece7dd'>C</text></svg>">
<style>
  :root{
    --bg:#faf8f4; --panel:#fffefb; --fg:#191713; --dim:#6b6558; --faint:#918a7c;
    --rule:#e2dbcc; --acc:#8a6d2f; --acc-soft:#b99a55;
    --red:#a3342a; --amber:#9a6b1f; --green:#3f6b46;
    --shadow:0 1px 2px rgba(25,23,19,.05),0 12px 32px -12px rgba(25,23,19,.14);
  }
  /* The toggle script stamps data-theme on <html> before first paint, so the
     explicit blocks own every value — no prefers-color-scheme duplication to
     drift out of sync. */
  :root[data-theme="dark"]{
    --bg:#100e0c; --panel:#181511; --fg:#ece7dd; --dim:#9a9284; --faint:#736c60;
    --rule:#2c2822; --acc:#c9a55c; --acc-soft:#8a7440;
    --red:#e0725f; --amber:#d7a54a; --green:#7fb489;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 16px 40px -16px rgba(0,0,0,.7);
  }
  *,*::before,*::after{box-sizing:border-box}
  html{scroll-behavior:smooth; -webkit-text-size-adjust:100%}
  body{
    margin:0; background:var(--bg); color:var(--fg);
    font:17px/1.68 Georgia,"Iowan Old Style","Palatino Linotype",Palatino,serif;
    transition:background .35s ease,color .35s ease;
  }
  .wrap{max-width:60rem; margin:0 auto; padding:0 clamp(1.1rem,4vw,2.5rem)}
  .mono{font-family:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace}
  a{color:var(--acc); text-decoration:none; border-bottom:1px solid transparent}
  a:hover{border-bottom-color:var(--acc)}

  /* ---------- nav ---------- */
  nav{
    position:sticky; top:0; z-index:50; backdrop-filter:blur(14px);
    background:color-mix(in srgb,var(--bg) 88%,transparent);
    border-bottom:1px solid var(--rule);
  }
  nav .wrap{display:flex; align-items:center; gap:1.6rem; height:3.9rem}
  .brand{font-size:1.16rem; letter-spacing:.02em; border:0; color:var(--fg); font-weight:400}
  .brand b{color:var(--acc); font-weight:400}
  nav .links{display:flex; gap:1.35rem; margin-left:auto; align-items:center}
  nav .links a{
    font:600 .69rem/1 ui-sans-serif,system-ui,sans-serif; letter-spacing:.13em;
    text-transform:uppercase; color:var(--dim); border:0;
  }
  nav .links a:hover{color:var(--fg)}
  @media(max-width:760px){ nav .links a.hide-sm{display:none} }
  .pill{
    display:inline-flex; align-items:center; gap:.45rem; padding:.42rem .8rem;
    border:1px solid var(--rule); border-radius:2rem; background:var(--panel);
    font:600 .67rem/1 ui-sans-serif,system-ui,sans-serif; letter-spacing:.1em;
    text-transform:uppercase; color:var(--dim);
  }
  .dot{width:.44rem; height:.44rem; border-radius:50%; background:var(--green);
       box-shadow:0 0 0 3px color-mix(in srgb,var(--green) 22%,transparent);
       animation:pulse 2.6s ease-in-out infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
  .tog{
    background:none; border:1px solid var(--rule); color:var(--dim); cursor:pointer;
    width:2rem; height:2rem; border-radius:50%; font-size:.9rem; line-height:1;
    display:grid; place-items:center; transition:.2s;
  }
  .tog:hover{color:var(--acc); border-color:var(--acc)}

  /* ---------- hero ---------- */
  header{padding:clamp(3.6rem,10vw,7rem) 0 clamp(2.4rem,6vw,4rem)}
  .kicker{
    font:600 .7rem/1 ui-sans-serif,system-ui,sans-serif; letter-spacing:.2em;
    text-transform:uppercase; color:var(--acc); margin-bottom:1.5rem;
  }
  h1{
    font-size:clamp(2.3rem,7.2vw,4.35rem); line-height:1.04; font-weight:400;
    letter-spacing:-.028em; margin:0 0 1.5rem; max-width:34ch;
  }
  h1 .strike{position:relative; color:var(--faint); white-space:nowrap}
  h1 .strike::after{
    content:""; position:absolute; left:-.04em; right:-.04em; top:.53em; height:.055em;
    background:var(--red); transform:scaleX(0); transform-origin:left;
    animation:strike .75s .55s cubic-bezier(.6,0,.2,1) forwards;
  }
  @keyframes strike{to{transform:scaleX(1)}}
  h1 .yes{color:var(--acc); font-style:italic}
  .lede{font-size:clamp(1.06rem,2.2vw,1.24rem); color:var(--dim); max-width:60ch; margin:0 0 2.2rem}
  .lede strong{color:var(--fg); font-weight:400}
  .cta{display:flex; flex-wrap:wrap; gap:.8rem; align-items:center}
  .btn{
    display:inline-flex; align-items:center; gap:.5rem; padding:.82rem 1.5rem;
    border-radius:.35rem; border:1px solid var(--acc); cursor:pointer;
    font:600 .78rem/1 ui-sans-serif,system-ui,sans-serif; letter-spacing:.07em;
    text-transform:uppercase; transition:.22s; background:var(--acc); color:var(--bg);
  }
  .btn:hover{filter:brightness(1.1); transform:translateY(-1px)}
  .btn.ghost{background:none; color:var(--acc)}
  .btn.ghost:hover{background:color-mix(in srgb,var(--acc) 11%,transparent)}
  .btn:disabled{opacity:.5; cursor:not-allowed; transform:none}

  /* ---------- sections ---------- */
  section{padding:clamp(2.8rem,7vw,4.6rem) 0; border-top:1px solid var(--rule)}
  .snum{
    font:600 .69rem/1 ui-sans-serif,system-ui,sans-serif; letter-spacing:.19em;
    text-transform:uppercase; color:var(--acc); margin-bottom:.85rem;
    display:flex; align-items:center; gap:.7rem;
  }
  .snum::after{content:""; height:1px; flex:1; background:var(--rule)}
  h2{font-size:clamp(1.6rem,3.7vw,2.3rem); font-weight:400; letter-spacing:-.02em;
     margin:0 0 1rem; max-width:30ch}
  .sub{color:var(--dim); max-width:62ch; margin:0 0 2rem}

  /* ---------- demo ---------- */
  .demo{background:var(--panel); border:1px solid var(--rule); border-radius:.6rem;
        box-shadow:var(--shadow); overflow:hidden}
  .demo-in{padding:clamp(1.1rem,3vw,1.7rem)}
  label.lbl{display:block; font:600 .69rem/1 ui-sans-serif,system-ui,sans-serif;
            letter-spacing:.13em; text-transform:uppercase; color:var(--dim); margin-bottom:.7rem}
  textarea{
    width:100%; min-height:6.2rem; resize:vertical; padding:.9rem 1rem;
    background:var(--bg); color:var(--fg); border:1px solid var(--rule);
    border-radius:.35rem; font:inherit; font-size:1rem; line-height:1.6;
  }
  textarea:focus{outline:none; border-color:var(--acc);
    box-shadow:0 0 0 3px color-mix(in srgb,var(--acc) 16%,transparent)}
  .chips{display:flex; flex-wrap:wrap; gap:.45rem; margin:.85rem 0 0}
  .chip{
    background:none; border:1px dashed var(--rule); color:var(--dim); cursor:pointer;
    padding:.42rem .75rem; border-radius:2rem; transition:.18s;
    font:.76rem/1.3 ui-sans-serif,system-ui,sans-serif; text-align:left;
  }
  .chip:hover{border-style:solid; border-color:var(--acc); color:var(--fg)}
  .chip b{font-weight:600; color:var(--acc)}
  .adv{margin-top:.9rem}
  .adv summary{cursor:pointer; color:var(--dim); font:.8rem/1 ui-sans-serif,system-ui,sans-serif; list-style:none}
  .adv summary::-webkit-details-marker{display:none}
  .adv summary::before{content:"+ "; color:var(--acc)}
  .adv[open] summary::before{content:"– "}
  .adv .row{display:flex; flex-wrap:wrap; gap:.6rem; margin-top:.8rem}
  .adv input,.adv select{
    padding:.6rem .7rem; background:var(--bg); color:var(--fg);
    border:1px solid var(--rule); border-radius:.3rem; font:inherit; font-size:.86rem;
  }
  .adv input{flex:1; min-width:15rem}
  .demo-bar{display:flex; align-items:center; gap:1rem; flex-wrap:wrap; margin-top:1.1rem}
  .hint{color:var(--faint); font-size:.8rem; font-family:ui-sans-serif,system-ui,sans-serif}

  /* ---------- verdict ---------- */
  #out{display:none; border-top:1px solid var(--rule)}
  #out.on{display:block; animation:rise .45s ease both}
  @keyframes rise{from{opacity:0; transform:translateY(9px)}to{opacity:1; transform:none}}
  .vhead{padding:clamp(1.1rem,3vw,1.7rem); border-bottom:1px solid var(--rule)}
  .vtop{display:flex; align-items:baseline; gap:1rem; flex-wrap:wrap}
  .verdict{font-size:clamp(1.22rem,3.1vw,1.72rem); letter-spacing:-.015em; flex:1; min-width:14rem}
  .score{font-size:clamp(2rem,5.5vw,2.9rem); line-height:1; letter-spacing:-.03em}
  .score small{font-size:.42em; color:var(--faint); letter-spacing:0}
  .meter{height:.4rem; background:color-mix(in srgb,var(--fg) 9%,transparent);
         border-radius:2rem; margin:1.1rem 0 .5rem; overflow:hidden}
  .meter i{display:block; height:100%; width:0; border-radius:2rem; transition:width 1s cubic-bezier(.2,.8,.2,1)}
  .bands{display:flex; justify-content:space-between; font:.63rem/1 ui-sans-serif,system-ui,sans-serif;
         letter-spacing:.08em; text-transform:uppercase; color:var(--faint)}
  .stance{color:var(--dim); margin:1rem 0 0}
  .block{padding:clamp(1.1rem,3vw,1.7rem); border-bottom:1px solid var(--rule)}
  .block:last-child{border-bottom:0}
  .btitle{font:600 .69rem/1 ui-sans-serif,system-ui,sans-serif; letter-spacing:.15em;
          text-transform:uppercase; color:var(--dim); margin-bottom:.9rem}
  .steel{font-style:italic; color:var(--dim); border-left:2px solid var(--acc-soft); padding-left:1rem; margin:0}
  .bias{padding:1rem 0; border-top:1px dotted var(--rule)}
  .bias:first-of-type{border-top:0; padding-top:0}
  .bias h4{margin:0 0 .45rem; font-size:1.02rem; font-weight:400; color:var(--red);
           display:flex; gap:.6rem; align-items:baseline; flex-wrap:wrap}
  .quote{
    font-family:ui-monospace,Menlo,monospace; font-size:.8rem; color:var(--fg);
    background:color-mix(in srgb,var(--acc) 17%,transparent);
    padding:.13rem .45rem; border-radius:.2rem; white-space:nowrap;
  }
  .bias p{margin:0; color:var(--dim); font-size:.96rem}
  .call{background:color-mix(in srgb,var(--red) 9%,transparent);
        border-left:2px solid var(--red); padding:1rem 1.15rem; border-radius:.25rem}
  .call.good{background:color-mix(in srgb,var(--green) 11%,transparent); border-left-color:var(--green)}
  ul.clean{margin:0; padding-left:1.15rem; color:var(--dim)}
  ul.clean li{margin:.5rem 0}
  ul.clean li::marker{color:var(--acc-soft)}
  .facts{display:grid; grid-template-columns:auto 1fr; gap:.5rem 1.2rem; font-size:.92rem}
  .facts dt{color:var(--faint); font:.68rem/1.5 ui-sans-serif,system-ui,sans-serif;
            letter-spacing:.1em; text-transform:uppercase; padding-top:.18rem}
  .facts dd{margin:0; font-family:ui-monospace,Menlo,monospace; font-size:.85rem; word-break:break-word}
  .gaps{color:var(--faint); font-size:.9rem}
  .disc{color:var(--faint); font-size:.82rem; font-style:italic}
  .err{color:var(--red)}
  .spin{display:inline-block; width:.85rem; height:.85rem; border:2px solid currentColor;
        border-right-color:transparent; border-radius:50%; animation:sp .7s linear infinite}
  @keyframes sp{to{transform:rotate(360deg)}}

  /* ---------- grids ---------- */
  .three{display:grid; gap:1.6rem; grid-template-columns:repeat(auto-fit,minmax(15rem,1fr))}
  .card{background:var(--panel); border:1px solid var(--rule); border-radius:.5rem;
        padding:1.5rem; transition:.25s}
  .card:hover{border-color:var(--acc-soft); transform:translateY(-2px); box-shadow:var(--shadow)}
  .card .n{font:600 .69rem/1 ui-sans-serif,system-ui,sans-serif; letter-spacing:.16em; color:var(--acc); margin-bottom:.8rem}
  .card h3{margin:0 0 .55rem; font-size:1.12rem; font-weight:400}
  .card p{margin:0; color:var(--dim); font-size:.94rem}
  .price{display:flex; align-items:baseline; gap:.4rem; margin:.9rem 0 0;
         padding-top:.9rem; border-top:1px solid var(--rule)}
  .price b{font-size:1.35rem; font-weight:400; color:var(--acc); letter-spacing:-.02em}
  .price span{font:.68rem/1 ui-sans-serif,system-ui,sans-serif; letter-spacing:.1em;
              text-transform:uppercase; color:var(--faint)}
  ol.steps{counter-reset:s; list-style:none; margin:0; padding:0}
  ol.steps li{counter-increment:s; position:relative; padding:0 0 1.5rem 3.2rem;
              border-left:1px solid var(--rule); margin-left:1rem}
  ol.steps li:last-child{border-left-color:transparent; padding-bottom:0}
  ol.steps li::before{
    content:counter(s,decimal-leading-zero); position:absolute; left:-1rem; top:-.1rem;
    width:2rem; height:2rem; border-radius:50%; background:var(--bg);
    border:1px solid var(--acc-soft); color:var(--acc); display:grid; place-items:center;
    font:600 .68rem/1 ui-sans-serif,system-ui,sans-serif;
  }
  ol.steps h3{margin:.25rem 0 .35rem; font-size:1.06rem; font-weight:400}
  ol.steps p{margin:0; color:var(--dim); font-size:.94rem}
  details.faq{border-bottom:1px solid var(--rule); padding:1.05rem 0}
  details.faq summary{cursor:pointer; list-style:none; font-size:1.04rem;
                      display:flex; gap:1rem; align-items:baseline}
  details.faq summary::-webkit-details-marker{display:none}
  details.faq summary::after{content:"+"; margin-left:auto; color:var(--acc); font-size:1.15rem}
  details.faq[open] summary::after{content:"–"}
  details.faq p{color:var(--dim); margin:.75rem 0 0; font-size:.95rem; max-width:66ch}
  pre.ep{background:var(--panel); border:1px solid var(--rule); border-left:2px solid var(--acc);
         padding:1rem 1.15rem; border-radius:.3rem; overflow-x:auto; font-size:.82rem; margin:0}
  footer{border-top:1px solid var(--rule); padding:2.6rem 0 3.4rem; color:var(--faint); font-size:.87rem}
  footer .fl{display:flex; gap:1.4rem; flex-wrap:wrap; margin-bottom:1.4rem}
  .reveal{opacity:0; transform:translateY(14px)}
  .reveal.in{opacity:1; transform:none; transition:opacity .6s ease,transform .6s ease}
  @media (prefers-reduced-motion:reduce){
    *{animation-duration:.01ms !important; transition-duration:.01ms !important}
    .reveal{opacity:1; transform:none}
  }
</style>

<script>
  /* Runs before first paint so dark-mode visitors never see a white flash. */
  (function(){
    var t;
    try { t = localStorage.getItem("cassandra-theme"); } catch(e){}
    if (!t) t = (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches)
                ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", t);
  })();
</script>

<nav>
  <div class="wrap">
    <a href="#top" class="brand">Cassandra<b>.</b></a>
    <div class="links">
      <a href="#try">Try it</a>
      <a href="#why" class="hide-sm">Why</a>
      <a href="#services" class="hide-sm">Services</a>
      <a href="#how" class="hide-sm">How</a>
      <a href="#faq" class="hide-sm">FAQ</a>
      <button class="tog" id="tog" title="Toggle theme" aria-label="Toggle theme">☾</button>
    </div>
  </div>
</nav>

<a id="top"></a>
<header>
  <div class="wrap">
    <div class="kicker">An A2MCP service on OKX.AI · ASP #9030</div>
    <h1>Every agent is built to say <span class="strike">yes</span>.<br>
        Cassandra is built to say <span class="yes">no</span>.</h1>
    <p class="lede">You give it a plan. It states your own case <strong>better than you
      did</strong> — then takes it apart: the cognitive bias in your own wording, quoted
      back at you. A pre-mortem of how this actually fails. Hard on-chain evidence when a
      token is involved. Exactly what would change its mind. And the smallest reversible
      test to run instead. <strong>It concedes when your plan is sound.</strong></p>
    <div class="cta">
      <a href="#try" class="btn">Argue with me →</a>
      <a href="https://github.com/emer-eth/cassandra-devils-advocate" class="btn ghost" target="_blank" rel="noopener">Read the code</a>
      <span class="pill"><span class="dot"></span>Endpoint live</span>
    </div>
  </div>
</header>

<section id="try">
  <div class="wrap">
    <div class="snum">I. The live demo</div>
    <h2>State a plan. Get argued with.</h2>
    <p class="sub">This is the real engine — the same one an agent hires over MCP, running
      now. Not a recording, not a script. Try something you actually intend to do, then
      try something sensible and watch it concede.</p>

    <div class="demo">
      <div class="demo-in">
        <label class="lbl" for="plan">Your plan</label>
        <textarea id="plan" placeholder="I'm going to put half my savings into this token everyone in my group chat is buying…"></textarea>
        <div class="chips">
          <button class="chip" data-p="Everyone in my group chat says this token is guaranteed to 100x, I'm putting my savings in right now before it's too late"><b>The bad one →</b> guaranteed 100x, my savings, right now</button>
          <button class="chip" data-p="I'll allocate 200 dollars I can afford to lose and exit if regulation changes"><b>The good one →</b> sized, reversible, falsifiable</button>
          <button class="chip" data-p="I'm down bad, already put in 5k, going to average down with my savings"><b>Sunk cost →</b> already put in 5k</button>
          <button class="chip" data-p="I want to launch a token next week and airdrop it to my followers"><b>A launch →</b> not just trades</button>
        </div>

        <details class="adv">
          <summary>Add a token address for on-chain evidence</summary>
          <div class="row">
            <input id="tok" class="mono" placeholder="0x… (42 chars)" spellcheck="false">
            <select id="chain">
              <option value="xlayer">X Layer</option>
              <option value="ethereum">Ethereum</option>
              <option value="bsc">BSC</option>
              <option value="base">Base</option>
              <option value="arbitrum">Arbitrum</option>
              <option value="polygon">Polygon</option>
            </select>
            <button class="chip" id="wokb" type="button">use WOKB</button>
          </div>
        </details>

        <div class="demo-bar">
          <button class="btn" id="go">Argue against it</button>
          <span class="hint" id="hint">⌘/Ctrl + Enter</span>
        </div>
      </div>
      <div id="out"></div>
    </div>
  </div>
</section>

<section id="why">
  <div class="wrap">
    <div class="snum">II. Why it can't hallucinate an objection</div>
    <h2>A critic you can audit.</h2>
    <p class="sub">Adversarial output is worthless if you can't trust it. So there is no
      model in the loop to invent one.</p>
    <div class="three">
      <div class="card reveal">
        <div class="n">01</div>
        <h3>No LLM. No API key.</h3>
        <p>A deterministic engine: pattern analysis over your own phrasing, a structured
          pre-mortem library, live chain data. Same plan in, same critique out, every
          time — and no per-call token cost to pass on to you.</p>
      </div>
      <div class="card reveal">
        <div class="n">02</div>
        <h3>Objections cite the chain.</h3>
        <p>Liquidity, owner privileges, sellability and pair age come from live RPC and
          market data across six chains. Where a check can't run, it says so rather than
          inferring a finding from silence.</p>
      </div>
      <div class="card reveal">
        <div class="n">03</div>
        <h3>It concedes.</h3>
        <p>A critic that objects to everything is noise. Give it a sized, reversible,
          falsifiable plan and it says <em>I cannot mount a case against this</em> and
          gets out of the way. The concession is what makes the objection worth paying for.</p>
      </div>
    </div>
  </div>
</section>

<section id="services">
  <div class="wrap">
    <div class="snum">III. Services</div>
    <h2>Hire it from your own agent.</h2>
    <p class="sub">Listed on the OKX.AI marketplace as ASP #9030. One A2MCP endpoint
      serves all of it — priced in USDT, per call.</p>
    <div class="three">
      <div class="card reveal">
        <div class="n">A2MCP</div>
        <h3>Adversarial Plan Review</h3>
        <p>The full argument: steelman, the case against, biases quoted from your wording,
          pre-mortem, on-chain evidence, what would change its mind, smallest test.</p>
        <div class="price"><b>0.02</b><span>USDT / call</span></div>
      </div>
      <div class="card reveal">
        <div class="n">A2MCP</div>
        <h3>Cognitive Bias Check</h3>
        <p>A fast read on <em>how</em> you framed the decision, ignoring its merits —
          urgency, social proof, sunk cost, false certainty — with your words quoted back.</p>
        <div class="price"><b>Free</b><span>USDT / call</span></div>
      </div>
      <div class="card reveal">
        <div class="n">A2MCP</div>
        <h3>Pre-Mortem Analysis</h3>
        <p>It's a year from now and this failed. Working backwards to the concrete ways it
          happened, for the failure path your plan doesn't currently defend against.</p>
        <div class="price"><b>Free</b><span>USDT / call</span></div>
      </div>
    </div>
  </div>
</section>

<section id="how">
  <div class="wrap">
    <div class="snum">IV. How it works</div>
    <h2>Four steps, no integration work.</h2>
    <ol class="steps">
      <li class="reveal"><h3>Find it on OKX.AI</h3>
        <p>Cassandra is registered on X Layer as an Agent Service Provider. Your agent
          discovers it in the marketplace and pays per call — no account, no key.</p></li>
      <li class="reveal"><h3>Your agent calls <code class="mono">challenge_plan</code></h3>
        <p>Over MCP, streamable HTTP. Pass the plan in plain language, plus a token
          address and chain if one is involved. More context, sharper critique.</p></li>
      <li class="reveal"><h3>It reads your wording, then the chain</h3>
        <p>Bias patterns are matched against your own phrasing and quoted back verbatim.
          If you passed a token, liquidity, owner powers and sellability are pulled live.</p></li>
      <li class="reveal"><h3>You get a verdict you can act on</h3>
        <p>A scored case against, the single strongest objection, concrete failure paths,
          the evidence that would change the verdict, and the smallest reversible test.</p></li>
    </ol>
  </div>
</section>

<section id="connect">
  <div class="wrap">
    <div class="snum">V. Connect</div>
    <h2>Endpoints.</h2>
    <pre class="ep mono">MCP      POST  __ORIGIN__/mcp        Streamable HTTP
Health   GET   __ORIGIN__/health
Demo API POST  __ORIGIN__/api/challenge   {"plan": "..."}

npx @modelcontextprotocol/inspector
  → Streamable HTTP → __ORIGIN__/mcp</pre>
    <p class="sub" style="margin-top:1.2rem">A browser <code class="mono">GET</code> on
      <code class="mono">/mcp</code> is refused by design — MCP is
      <code class="mono">POST</code> plus SSE, so a plain browser request gets
      <code class="mono">405</code> here (or <code class="mono">406</code> against a
      stateful host). That is the protocol working, not an outage — point an MCP client
      at it instead.</p>
  </div>
</section>

<section id="faq">
  <div class="wrap">
    <div class="snum">VI. Questions</div>
    <h2>Reasonable objections to a service that objects.</h2>
    <details class="faq"><summary>Is this financial advice?</summary>
      <p>No. Cassandra is a decision-hygiene tool. It argues against your plan by design —
        that is its job, not a prediction. A strong case against a plan is not proof the
        plan is wrong, and a weak one is not permission. You own the decision.</p></details>
    <details class="faq"><summary>Isn't this just a prompt wrapped around an LLM?</summary>
      <p>There is no LLM. The objections come from pattern analysis over your own phrasing,
        a structured pre-mortem library keyed to the type of plan, and live on-chain data.
        That is why it is deterministic, why it costs a fraction of a cent, and why it
        cannot invent an objection. The code is public if you'd rather check than trust.</p></details>
    <details class="faq"><summary>What stops it from objecting to everything?</summary>
      <p>Every objection carries a weight, and the total is scored 0–100. Below 18 it says
        the case against is weak; at zero it concedes outright. Try the sensible plan in the
        demo above — it scores 0 and tells you to proceed.</p></details>
    <details class="faq"><summary>Which chains can it pull evidence from?</summary>
      <p>X Layer (default), Ethereum, BSC, Base, Arbitrum and Polygon. Contract ownership,
        privileged functions and proxy checks work on all six. Sell simulation is
        unavailable on X Layer, Arbitrum and Polygon — where a check can't run, Cassandra
        reports the gap instead of inferring a finding from it.</p></details>
    <details class="faq"><summary>Why is the demo free if the service costs 0.02?</summary>
      <p>Because an argument you haven't experienced is just a claim. The demo is rate
        limited; the marketplace listing is the supported path, and it's where your agent
        gets a stable, metered endpoint.</p></details>
    <details class="faq"><summary>Who is Cassandra?</summary>
      <p>A Trojan princess given the gift of true prophecy and cursed so that nobody would
        ever believe her. Every warning she gave was correct and ignored. It seemed like the
        right name for a service that tells you what you don't want to hear.</p></details>
  </div>
</section>

<footer>
  <div class="wrap">
    <div class="fl">
      <a href="https://github.com/emer-eth/cassandra-devils-advocate" target="_blank" rel="noopener">Source</a>
      <a href="__ORIGIN__/health">Health</a>
      <a href="#try">Demo</a>
      <a href="#faq">FAQ</a>
    </div>
    <p style="margin:0 0 .5rem"><em>Named for the prophetess cursed to speak true and never
      be believed.</em></p>
    <p style="margin:0">Decision hygiene, not financial advice. Cassandra argues against
      your plan by design — that is its job, not a prediction.</p>
  </div>
</footer>

<script>
(function(){
  "use strict";
  var $ = function(s){ return document.querySelector(s); };
  var esc = function(s){
    return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){
      return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];
    });
  };

  /* ---- theme ---- */
  var root = document.documentElement, tog = $("#tog");
  function paint(t){
    root.setAttribute("data-theme", t);
    tog.textContent = t === "dark" ? "☀" : "☾";
  }
  var saved = null;
  try { saved = localStorage.getItem("cassandra-theme"); } catch(e){}
  paint(saved || (window.matchMedia &&
        window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
  tog.addEventListener("click", function(){
    var t = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    paint(t);
    try { localStorage.setItem("cassandra-theme", t); } catch(e){}
  });

  /* ---- reveal on scroll ---- */
  if (window.IntersectionObserver) {
    var io = new IntersectionObserver(function(es){
      es.forEach(function(e){
        if (e.isIntersecting){ e.target.classList.add("in"); io.unobserve(e.target); }
      });
    }, { threshold: .12 });
    document.querySelectorAll(".reveal").forEach(function(el, i){
      el.style.transitionDelay = (i % 4) * 70 + "ms";
      io.observe(el);
    });
  } else {
    document.querySelectorAll(".reveal").forEach(function(el){ el.classList.add("in"); });
  }

  /* ---- demo ---- */
  var plan = $("#plan"), out = $("#out"), go = $("#go"), hint = $("#hint");
  document.querySelectorAll(".chip[data-p]").forEach(function(c){
    c.addEventListener("click", function(){
      plan.value = c.getAttribute("data-p");
      plan.focus();
    });
  });
  $("#wokb").addEventListener("click", function(){
    $("#tok").value = "0xe538905cf8410324e03A5A23C1c177a474D59b2b";
    $("#chain").value = "xlayer";
  });

  var BANDS = [
    { min: 70, tone: "var(--red)"   },
    { min: 40, tone: "var(--amber)" },
    { min: 18, tone: "var(--acc)"   },
    { min:  1, tone: "var(--acc)"   },
    { min:  0, tone: "var(--green)" }
  ];
  function tone(n){
    for (var i = 0; i < BANDS.length; i++) if (n >= BANDS[i].min) return BANDS[i].tone;
    return "var(--green)";
  }

  function facts(ev){
    if (!ev || !ev.checked) return "";
    var rows = [], add = function(k, v){ if (v || v === 0) rows.push([k, v]); };
    add("token", (ev.name || "?") + (ev.symbol ? " (" + ev.symbol + ")" : ""));
    if (typeof ev.liquidity_usd === "number")
      add("liquidity", "$" + Math.round(ev.liquidity_usd).toLocaleString());
    add("price", ev.price_usd ? "$" + ev.price_usd : null);
    if (ev.price_change_24h != null) add("24h", ev.price_change_24h + "%");
    if (ev.pair_age_days != null) add("pair age", ev.pair_age_days + " days");
    if (ev.privileged_functions && ev.privileged_functions.length)
      add("owner powers", ev.privileged_functions.join(", "));
    if (ev.ownership_renounced != null) add("renounced", String(ev.ownership_renounced));
    if (ev.is_upgradeable_proxy != null) add("upgradeable", String(ev.is_upgradeable_proxy));
    if (ev.is_honeypot != null) add("sellable", String(!ev.is_honeypot));
    if (ev.sell_tax != null) add("sell tax", ev.sell_tax + "%");
    add("source", [ev.market_source, ev.rpc_endpoint].filter(Boolean).join(" · "));
    if (!rows.length) return "";
    return '<div class="block"><div class="btitle">On-chain evidence</div><dl class="facts">' +
      rows.map(function(r){ return "<dt>" + esc(r[0]) + "</dt><dd>" + esc(r[1]) + "</dd>"; }).join("") +
      "</dl></div>";
  }

  function render(d){
    var n = d.case_against_strength || 0, col = tone(n), conceded = n === 0;
    var biases = d.biases_in_your_own_words || [];
    var pm = (d.premortem && d.premortem.failure_paths) || [];
    var mc = d.what_would_change_my_mind || [];
    var so = d.strongest_objection;
    var gaps = d.what_i_could_not_verify || [];
    var h = "";

    h += '<div class="vhead"><div class="vtop">' +
           '<div class="verdict" style="color:' + col + '">' + esc(d.verdict) + "</div>" +
           '<div class="score" style="color:' + col + '">' + n + "<small>/100</small></div>" +
         '</div><div class="meter"><i id="mfill" style="background:' + col + '"></i></div>' +
         '<div class="bands"><span>concede</span><span>moderate</span><span>substantial</span><span>strong</span></div>' +
         '<p class="stance">' + esc(d.my_position) + "</p></div>";

    if (d.steelman && d.steelman.argument)
      h += '<div class="block"><div class="btitle">First, your case at its strongest</div>' +
           '<p class="steel">' + esc(d.steelman.argument) + "</p></div>";

    if (biases.length) {
      h += '<div class="block"><div class="btitle">' + biases.length +
           " tell" + (biases.length > 1 ? "s" : "") + ' in your own wording</div>';
      biases.forEach(function(b){
        h += '<div class="bias"><h4>' + esc(b.bias) +
             '<span class="quote">&ldquo;' + esc(b.you_said) + '&rdquo;</span></h4><p>' +
             esc(b.objection) + "</p></div>";
      });
      h += "</div>";
    } else if (d.framing_note) {
      h += '<div class="block"><div class="btitle">Your framing</div>' +
           '<div class="call good">' + esc(d.framing_note) + "</div></div>";
    }

    h += facts(d.on_chain_evidence);

    if (so)
      h += '<div class="block"><div class="btitle">The objection that matters most</div>' +
           '<div class="call' + (conceded ? " good" : "") + '"><p style="margin:0 0 .5rem;color:var(--faint);font-size:.8rem">via ' +
           esc(so.source) + " — " + esc(so.label) + "</p>" + esc(so.detail) + "</div></div>";

    if (pm.length)
      h += '<div class="block"><div class="btitle">Pre-mortem — assume it already failed</div><ul class="clean">' +
           pm.map(function(p){ return "<li>" + esc(p) + "</li>"; }).join("") + "</ul></div>";

    if (gaps.length)
      h += '<div class="block"><div class="btitle">What I could not verify</div><ul class="clean gaps">' +
           gaps.map(function(g){ return "<li>" + esc(g) + "</li>"; }).join("") + "</ul></div>";

    if (mc.length)
      h += '<div class="block"><div class="btitle">What would change my mind</div><ul class="clean">' +
           mc.map(function(c){ return "<li>" + esc(c) + "</li>"; }).join("") + "</ul></div>";

    if (d.smallest_reversible_test)
      h += '<div class="block"><div class="btitle">Smallest reversible test</div>' +
           '<div class="call good">' + esc(d.smallest_reversible_test) + "</div></div>";

    if (d.disclaimer)
      h += '<div class="block"><p class="disc">' + esc(d.disclaimer) + "</p></div>";

    out.innerHTML = h;
    out.classList.add("on");
    requestAnimationFrame(function(){
      var f = document.getElementById("mfill");
      if (f) f.style.width = Math.max(n, 1.5) + "%";
    });
  }

  var PHASES = ["Reading your wording…", "Matching bias patterns…",
                "Checking the chain…", "Building the case against…"];
  var timer = null;

  function ask(){
    var p = (plan.value || "").trim();
    if (!p) { plan.focus(); return; }
    var tok = ($("#tok").value || "").trim();
    var body = { plan: p };
    if (tok) { body.token_address = tok; body.chain = $("#chain").value; }

    go.disabled = true;
    var i = 0;
    hint.innerHTML = '<span class="spin"></span> ' + PHASES[0];
    timer = setInterval(function(){
      i = (i + 1) % PHASES.length;
      hint.innerHTML = '<span class="spin"></span> ' + PHASES[i];
    }, 1400);

    fetch("/api/challenge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    })
    .then(function(r){ return r.json().then(function(j){ return { ok: r.ok, j: j }; }); })
    .then(function(res){
      if (!res.ok || res.j.error) throw new Error(res.j.error || "request failed");
      render(res.j);
    })
    .catch(function(e){
      out.innerHTML = '<div class="block"><p class="err">' + esc(e.message) + "</p></div>";
      out.classList.add("on");
    })
    .then(function(){
      clearInterval(timer);
      go.disabled = false;
      hint.textContent = "⌘/Ctrl + Enter";
    });
  }

  go.addEventListener("click", ask);
  plan.addEventListener("keydown", function(e){
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") { e.preventDefault(); ask(); }
  });
})();
</script>
"""
