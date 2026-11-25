"""Draft the two Probate stack diagrams from the stack-diagram template, with Probate's tokens.

    python3 design/diagrams/make.py [path/to/stack-diagram/skills/stack-diagram]

Steps and rules: apps/site/content/docs/guides/diagrams.mdx.
"""
import os, pathlib, sys
SKILL = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("STACK_DIAGRAM", "stack-diagram/skills/stack-diagram"))
OUT = pathlib.Path(__file__).resolve().parent
T = (SKILL / "assets/template.html").read_text()
head, _ = T.split("<body>", 1)

def theme(h, w, ht):
    # Night Court dark tokens; light stays the template's paper. Fly.io violet for ga, Cloudflare orange for gc.
    h = h.replace('<html lang="en"><!-- set lang to the label language, e.g. "ja" for Japanese labels -->', '<html lang="en">')
    h = h.replace("""  --color-accent:  oklch(70% 0.16 256);
  --color-graphite:oklch(31% 0.020 260);
  --color-g1:      oklch(70% 0.14 55);
  --color-g1-soft: oklch(58% 0.11 55);
  --color-g1-ink:  oklch(78% 0.12 55);
  --color-g1-tint: oklch(26% 0.030 60 / .40);
  --color-accent-soft: oklch(70% 0.16 256 / .5);
  --color-accent-tint: oklch(28% 0.045 256 / .35);
  --color-veil: oklch(18% 0.012 255 / .78);""", """  --color-accent:  #d9b46a;
  --color-graphite:oklch(31% 0.006 260);
  --color-g1:      oklch(62% 0.13 295);
  --color-g1-soft: oklch(52% 0.10 295);
  --color-g1-ink:  oklch(80% 0.09 295);
  --color-g1-tint: oklch(24% 0.025 295 / .45);
  --color-g2:      oklch(68% 0.15 50);
  --color-g2-ink:  oklch(80% 0.11 55);
  --color-g2-tint: oklch(25% 0.030 55 / .40);
  --color-accent-soft: rgb(217 180 106 / .45);
  --color-accent-tint: rgb(217 180 106 / .05);
  --color-veil: rgb(14 16 20 / .82);""")
    h = h.replace("""  --color-paper:   oklch(18% 0.012 255);
  --color-paper-2: oklch(22% 0.014 255);
  --color-rule:    oklch(24% 0.013 255);
  --color-rule-2:  oklch(38% 0.018 255);
  --color-muted:   oklch(65% 0.014 255);
  --color-neutral: oklch(72% 0.012 255);
  --color-ink-2:   oklch(85% 0.010 255);
  --color-ink:     oklch(94% 0.008 255);""", """  --color-paper:   #0e1014;
  --color-paper-2: #14161b;
  --color-rule:    #15181d;
  --color-rule-2:  #2c3038;
  --color-muted:   #959ca8;
  --color-neutral: #a9afba;
  --color-ink-2:   #c3c8d1;
  --color-ink:     #edeff3;""")
    # light-theme accents for the two vendor groups
    h = h.replace("  --color-g1-tint: oklch(96.5% 0.015 60 / .5);", """  --color-g1-tint: oklch(96.5% 0.015 60 / .5);
  --color-g2:      oklch(68% 0.15 50);
  --color-g2-ink:  oklch(52% 0.14 45);
  --color-g2-tint: oklch(96.5% 0.02 50 / .5);""", 1)
    h = h.replace("  --color-g1:      oklch(68% 0.15 55);\n  --color-g1-soft: oklch(78% 0.12 55);\n  --color-g1-ink:  oklch(52% 0.14 50);",
                  "  --color-g1:      oklch(58% 0.15 295);\n  --color-g1-soft: oklch(72% 0.10 295);\n  --color-g1-ink:  oklch(46% 0.14 295);", 1)
    h = h.replace("  --color-accent:  oklch(58% 0.20 256);     /* primary-flow edges, one signal color */", "  --color-accent:  #9a7a35;     /* primary-flow edges: Probate gilt, darkened for paper */", 1)
    h = h.replace("  --color-accent-soft: oklch(58% 0.20 256 / .45);\n  --color-accent-tint: oklch(97% 0.012 256 / .5);", "  --color-accent-soft: rgb(154 122 53 / .45);\n  --color-accent-tint: rgb(154 122 53 / .05);", 1)
    h = h.replace(".group.gb > .g-label { color: var(--color-accent); }", ".group.gb > .g-label { color: var(--color-accent); }\n.group.gc { border:1.5px solid var(--color-g2); background: var(--color-g2-tint); }\n.group.gc > .g-label { color: var(--color-g2-ink); }")
    h = h.replace("h1 { font-family: var(--font-display); font-weight: 700;", "h1 { font-family: var(--font-display); font-weight: 500;")
    h = h.replace(".canvas { position: relative; width: 1000px; height: 540px;", f".canvas {{ position: relative; width: {w}px; height: {ht}px;")
    h = h.replace("svg.edges { position:absolute; inset:0; width:1000px; height:540px;", f"svg.edges {{ position:absolute; inset:0; width:{w}px; height:{ht}px;")
    h = h.replace('<title><!-- TITLE --></title>', '<title>%TITLE%</title>')
    return h

def node(cx, top, icon, name, role, tile=""):
    return f'''    <div class="node" style="left:{cx-66}px;top:{top}px">
      <div class="tile {tile}"><img src="%%ICON_{icon}%%" alt=""></div>
      <div class="name"><span>{name}</span></div><div class="role"><span>{role}</span></div>
    </div>'''

def page(title, kicker, lede, w, h, groups, edges, nodes, legend, credits):
    return theme(head, w, h).replace("%TITLE%", title) + f'''<body>
<div class="page">
  <header class="head">
    <div>
      <div class="kicker">{kicker}</div>
      <h1>{title}</h1>
    </div>
    <p class="lede">{lede}</p>
  </header>
  <div class="scroller">
  <div class="canvas">
{groups}
    <svg class="edges" viewBox="0 0 {w} {h}" aria-hidden="true">
      <defs>
        <marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 z" fill="context-stroke"/>
        </marker>
      </defs>
{edges}
    </svg>
{nodes}
  </div>
  </div>
  <div class="legend">
{legend}
  </div>
  <div class="foot">
    <span>Probate, Fly.io Hacksgiving 2026</span>
    <span>icons: {credits} · made with <a href="https://github.com/caru-ini/stack-diagram" target="_blank" rel="noopener">stack-diagram</a></span>
  </div>
</div>
</body>
</html>
'''

# ---------------------------------------------------------------- overview
c1, c2, c3, c4, c5 = 100, 330, 520, 740, 890
r1, r2, r3 = 120, 290, 430
groups = f'''    <div class="group gc" style="left:{c1-90}px; top:{r1-60}px; width:180px; height:210px;">
      <div class="g-label"><img src="%%ICON_cloudflare%%" alt="">Cloudflare</div>
    </div>
    <div class="group ga" style="left:{c2-90}px; top:{r1-60}px; width:{c3-c2+180}px; height:{r2+150-(r1-60)}px;">
      <div class="g-label"><img src="%%ICON_flyio%%" alt="">Fly.io Sprites</div>
    </div>
    <div class="group gb" style="left:{c4-90}px; top:{r1-60}px; width:{c5-c4+180}px; height:{r3+150-(r1-60)}px;">
      <div class="g-label">Reached only through the gateway</div>
    </div>'''
edges = f'''      <path class="n" d="M{c1} {r2-4} V{r1+106}" marker-end="url(#ar)"/>
      <text class="el" x="{c1+10}" y="{(r2+r1+100)//2+4}">docs</text>
      <path class="e" d="M{c1+36} {r2+30} H210 V{r1+30} H{c2-36}" marker-end="url(#ar)"/>
      <text class="el a" x="268" y="{r1+22}" text-anchor="middle">HTTPS</text>
      <path class="n" d="M{c2} {r1+106} V{r2-4}" marker-end="url(#ar)"/>
      <text class="el" x="{c2+10}" y="{(r1+100+r2)//2+4}">Sprites API</text>
      <path class="n" d="M{c2+36} {r1+30} H{c3} V{r2-4}" marker-end="url(#ar)"/>
      <text class="el" x="{(c2+c3)//2+10}" y="{r1+22}" text-anchor="middle">the court</text>
      <path class="e" d="M{c2+36} {r2+30} H{c3-36}" marker-end="url(#ar)"/>
      <text class="el a" x="{(c2+c3)//2}" y="{r2+22}" text-anchor="middle">no keys</text>
      <path class="e" d="M{c3+36} {r2+30} H{c4-36}" marker-end="url(#ar)"/>
      <text class="el a" x="600" y="{r2+22}" text-anchor="middle">adds key</text>
      <path class="n" d="M{c1+36} {r3+30} H{c4-36}" marker-end="url(#ar)"/>
      <text class="el" x="{(c1+c4)//2}" y="{r3+22}" text-anchor="middle">approve or refuse, by email</text>'''
nodes = "\n".join([
    node(c1, r1, "nextjs", "Landing and docs", "static next.js"),
    node(c1, r2, "browser", "Visitors", "browser"),
    node(c1, r3, "harsh", "Harsh", "the owner"),
    node(c2, r1, "probate", "Courthouse", "lives forever"),
    node(c2, r2, "python", "Generation", "one sprite a day"),
    node(c3, r2, "gateway", "Connector gateway", "api.sprites.dev"),
    node(c4, r1, "jev", "TypeSafe Jev", "the judge"),
    node(c5, r1, "ollama", "Ollama Cloud", "the brain"),
    node(c4, r2, "box", "Box", "the archive"),
    node(c5, r2, "pinecone", "Pinecone", "inherited memory"),
    node(c4, r3, "agentmail", "AgentMail", "the inboxes"),
    node(c5, r3, "elevenlabs", "ElevenLabs", "eulogies"),
])
legend = '''    <span><span class="sw"></span>a generation's work</span>
    <span><span class="sw n"></span>control and reading</span>'''
(OUT / "overview.html").write_text(page(
    "How Probate fits together", "probate / architecture",
    "Two kinds of Sprite, one connector gateway, and a website on each side. No Sprite holds a key.",
    1000, 620, groups, edges, nodes, legend, "svgl / gilbarbara logos / Lucide"))

# ---------------------------------------------------------------- deploy
cA, cB, cC = 100, 400, 600
rA, rB, rC = 100, 280, 500
groups = f'''    <div class="group ga" style="left:{cB-90}px; top:{rB-60}px; width:{cC-cB+180}px; height:210px;">
      <div class="g-label"><img src="%%ICON_flyio%%" alt="">Fly.io Sprites</div>
    </div>
    <div class="group gc" style="left:{cB-90}px; top:{rC-60}px; width:180px; height:210px;">
      <div class="g-label"><img src="%%ICON_cloudflare%%" alt="">Cloudflare Workers</div>
    </div>'''
edges = f'''      <path class="n dash" d="M{cA} {rB-4} V{rA+30} H{cB-36}" marker-end="url(#ar)"/>
      <text class="el" x="{(cA+cB)//2}" y="{rA+22}" text-anchor="middle">git push</text>
      <path class="n dash" d="M{cA+36} {rB+30} H{cB-36}" marker-end="url(#ar)"/>
      <text class="el" x="210" y="{rB+22}" text-anchor="middle">scripts/deploy.py</text>
      <path class="n dash" d="M{cA} {rB+106} V{rC+30} H{cB-36}" marker-end="url(#ar)"/>
      <text class="el" x="225" y="{rC+22}" text-anchor="middle">wrangler deploy</text>
      <path class="e" d="M{cB+36} {rB+30} H{cC-36}" marker-end="url(#ar)"/>
      <text class="el a" x="{(cB+cC)//2}" y="{rB+22}" text-anchor="middle">one a day</text>'''
nodes = "\n".join([
    node(cA, rB, "laptop", "make ship", "harsh's laptop"),
    node(cB, rA, "github", "GitHub", "the repo"),
    node(cB, rB, "probate", "Courthouse", "deployed once"),
    node(cC, rB, "python", "Generation", "born by the clock"),
    node(cB, rC, "nextjs", "Landing and docs", "static export"),
])
legend = '''    <span><span class="sw n dash"></span>make ship, once</span>
    <span><span class="sw"></span>after that, every day</span>'''
(OUT / "deploy.html").write_text(page(
    "What make ship deploys", "probate / deploy",
    "One command checks, pushes and deploys both sites. After that the Courthouse runs the family by itself.",
    760, 660, groups, edges, nodes, legend, "svgl / Lucide"))
print("ok")
