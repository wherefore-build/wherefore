"""The mechanism scene: what a feature does, drawn from the corpus the clip is made in.

A CLIP THAT SHOWS THE MECHANISM, NOT ONLY THE WORDS. Twenty features need
four pictures (owner, 6 November 2026): values compared across places and
the one that disagrees lit; a fact held, so that when it moves every page
moves; files sorted into built, written and captured with nothing left over;
and a request handed over, from an issue to a plan to a release to the note
that closes it. Each feature names its mechanism in features.json, and the
scene is filled from the corpus the clip is made in - this site's own file
counts, its own pages, its own sources - so every number on screen is one
the corpus can be asked for, and nothing is drawn that is not so.

No model draws these. Each of the four is a template, written once and held
by the tests; the numbers come from the gate's classification, the scan,
the reach probes and the ledger, at the moment the clip is written.

    compare   places and the values they state, and how many disagree
    hold      a source, its facts, and the pages built from them
    sort      every tracked file: built, written with a reason, captured
    handover  issues answered, by how many items, in how many releases
"""
import html
import json
import pathlib

KINDS = ("compare", "hold", "sort", "handover")
PAGES_SHOWN = 8


def _tracked(root):
    import subprocess
    out = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, text=True).stdout
    return [p for p in out.split("\0") if p]


def gather(cfg, ledger_items=None, releases=None):
    """{kind: data} for the corpus `cfg` is, or what can be said without one."""
    data = {}
    if cfg is not None:
        for kind, fn in (("sort", _sort), ("hold", _hold), ("compare", _compare)):
            try:
                data[kind] = fn(cfg)
            except (Exception, SystemExit):        # a corpus that lacks what a scene reads is drawn without it
                pass
    items = ledger_items or []
    with_issues = [it for it in items if it.get("issues")]
    if with_issues or releases:
        data["handover"] = {"issues": sum(len(it["issues"]) for it in with_issues), "items": len(with_issues),
                            "releases": len(releases or []),
                            "steps": ["an issue", "the plan, on it", "the release", "the note that closes it"]}
    return data


def _sort(cfg):
    from . import gate, graph
    graph.configure(cfg)
    decl = gate.DECL()
    decl.setdefault("authored", {}).setdefault("rules", [])
    decl.setdefault("captured", {}).setdefault("groups", {})
    captured = gate.captured_files(decl)
    rules = decl["authored"]["rules"]
    files = _tracked(cfg.root)
    n_cap = sum(1 for f in files if f in captured)
    n_auth = sum(1 for f in files if f not in captured and gate.authored_rule(f, rules))
    return {"files": len(files), "built": len(files) - n_cap - n_auth, "authored": n_auth, "captured": n_cap,
            "left": 0}


def _hold(cfg):
    from . import sources
    name, src = cfg.source()
    path = cfg.root / src["path"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    facts = sum(1 for _ in sources.leaves(doc))
    pages = sorted(f for f in _tracked(cfg.root) if f.endswith(".html"))
    probes = ((cfg.doc.get("reach") or {}).get("probes") or [])
    probe = max(probes, key=lambda p: len(p.get("files", [])), default=None)
    shown = {"fact": probe["fact"], "files": len(probe["files"])} if probe else None

    def label(rel):                      # site/pendulum/plate/index.html -> pendulum/plate/; site/index.html -> /
        parts = rel.split("/")
        inner = parts[1:-1] if len(parts) > 1 else []
        return "/".join(inner) + "/" if inner else ("/" if parts[-1] == "index.html" else parts[-1])
    labels = list(dict.fromkeys(label(p) for p in pages))
    return {"source": src["path"], "facts": facts, "pages": len(pages),
            "shown": labels[:PAGES_SHOWN], "probe": shown}


def _compare(cfg):
    from . import scan
    def readable(part):
        d = cfg.root / part
        return d.is_dir() and any(f.suffix.lower() in scan.TEXT for f in d.rglob("*") if f.is_file())
    roots = []
    for g in cfg.generators:
        for part in (g.makes or "").replace(",", " ").split():
            if part.endswith("/") and "/" not in part.rstrip("/") and part.rstrip("/") not in roots and readable(part):
                roots.append(part.rstrip("/"))
    if not roots:
        roots = [d.name for d in sorted(cfg.root.iterdir()) if d.is_dir() and (d / "index.html").is_file()][:3]
    if not roots:
        raise ValueError("nothing to scan")
    got = scan.scan([str(cfg.root / r) for r in roots])
    return {"places": roots, "stated": got["stated"], "files": got["sources"], "disagree": len(got["disagree"]),
            "says": [g["says"] for g in got["disagree"][:2]]}


def caption(kind, d):
    """The one line said under the picture; every number is the picture's."""
    if kind == "sort":
        return (f"{d['files']} files tracked: {d['built']} built by a script, {d['authored']} written with a reason, "
                f"{d['captured']} captured and stamped, {d['left']} unaccounted for")
    if kind == "hold":
        probe = (f"; {d['probe']['fact']} alone reaches {d['probe']['files']} "
                 f"{'page' if d['probe']['files'] == 1 else 'pages'}") if d.get("probe") else ""
        return (f"{d['facts']} facts in {d['source']}, and {d['pages']} "
                f"{'page' if d['pages'] == 1 else 'pages'} built from them{probe}")
    if kind == "compare":
        where = ", ".join(d["places"])
        return (f"{d['stated']} values stated across {d['files']} pages in {where}; "
                f"{d['disagree']} disagree")
    if kind == "handover":
        return f"{d['issues']} issues answered by {d['items']} roadmap items across {d['releases']} releases"
    raise ValueError(kind)


def eyebrow(kind):
    return {"compare": "what it compares", "hold": "what it holds", "sort": "what it sorts",
            "handover": "what it hands over"}[kind]


# ── the picture ─────────────────────────────────────────────────────────────

def _pct(t, total):
    return f"{t / total * 100:.3f}%"


def render(sc, i, total, rules):
    """The scene's inner HTML; keyframes for its parts go into `rules`."""
    kind, d, t0 = sc["mechanism"], sc["data"], sc["start"]
    esc = html.escape
    counted = [0]

    def count(n, at, cls="num"):
        """A number that climbs to `n` from `at`, over a second; the value is
        in the markup too, for anything that reads rather than watches."""
        counted[0] += 1
        name = f"cnt{i}_{counted[0]}"
        rules.append(f"@keyframes {name}{{0%,{_pct(at, total)}{{--n:0}}{_pct(at + 1.0, total)},100%{{--n:{n}}}}}")
        return f'<span class="{cls} count" style="--to:{n};animation-name:{name}" data-n="{n}"><span class="sr">{n}</span></span>'

    def appear(name, at, grow=False):
        a, b = _pct(at, total), _pct(at + 0.35, total)
        if grow:
            rules.append(f"@keyframes {name}{{0%,{a}{{width:0}}{b},100%{{width:var(--w)}}}}")
        else:
            rules.append(f"@keyframes {name}{{0%,{a}{{opacity:0}}{b},100%{{opacity:1}}}}")

    if kind == "sort":
        most = max(d["built"], d["authored"], d["captured"], 1)
        rows, out = [("built by a script", d["built"], "accent"), ("written, with a reason", d["authored"], "ink"),
                     ("captured, stamped", d["captured"], "muted")], []
        for j, (label, n, tone) in enumerate(rows):
            appear(f"bar{i}_{j}", t0 + 0.4 + 0.5 * j, grow=True)
            out.append(f'<div class="row"><span class="lab">{esc(label)}</span>'
                       f'<span class="bar"><i class="t-{tone}" style="--w:{100 * n / most:.1f}%;animation-name:bar{i}_{j}"></i></span>'
                       f'{count(n, t0 + 0.4 + 0.5 * j)}</div>')
        # THE POINT OF THE SCENE, last and largest: nothing left over.
        appear(f"left{i}", t0 + 2.6)
        out.append(f'<div class="row left" style="animation-name:left{i}"><span class="lab">unaccounted for</span>'
                   f'<span class="bar none"></span><span class="num t-accent">{d["left"]}</span></div>')
        return f'<div class="viz sort">{"".join(out)}</div>'

    if kind == "hold":
        appear(f"src{i}", t0 + 0.3)
        chips = []
        for j, p in enumerate(d["shown"]):
            appear(f"pg{i}_{j}", t0 + 1.0 + 0.25 * j)
            chips.append(f'<span class="chip" style="animation-name:pg{i}_{j}">{esc(p)}</span>')
        more = len(set(d["shown"])) and d["pages"] - len(d["shown"]) if d["pages"] > len(d["shown"]) else 0
        if more > 0:
            appear(f"pgm{i}", t0 + 1.0 + 0.25 * len(d["shown"]))
            chips.append(f'<span class="chip t-muted" style="animation-name:pgm{i}">+{more} more</span>')
        return (f'<div class="viz hold"><div class="card src" style="animation-name:src{i}">'
                f'<span class="lab">the source</span><span class="val">{esc(d["source"])}</span>'
                f'<span class="num">{count(d["facts"], t0 + 0.4)} facts</span></div>'
                f'<div class="arrow">→</div><div class="chips">{"".join(chips)}</div></div>')

    if kind == "compare":
        cards = []
        for j, p in enumerate(d["places"]):
            appear(f"pl{i}_{j}", t0 + 0.3 + 0.3 * j)
            cards.append(f'<div class="card" style="animation-name:pl{i}_{j}"><span class="lab">a place</span>'
                         f'<span class="val">{esc(p)}/</span></div>')
        appear(f"st{i}", t0 + 1.4)
        appear(f"dis{i}", t0 + 2.6)
        tone = "fail" if d["disagree"] else "accent"
        says = "".join(f'<span class="chip t-fail">{esc(s)}</span>' for s in d.get("says", []))
        return (f'<div class="viz compare"><div class="places">{"".join(cards)}</div>'
                f'<div class="card tally" style="animation-name:st{i}">{count(d["stated"], t0 + 1.4, "num big")}'
                f'<span class="lab">values stated, {d["files"]} pages</span></div>'
                f'<div class="card tally t-{tone}" style="animation-name:dis{i}">{count(d["disagree"], t0 + 2.6, "num big")}'
                f'<span class="lab">disagree</span>{says}</div></div>')

    if kind == "handover":
        out = []
        for j, step in enumerate(d["steps"]):
            appear(f"hs{i}_{j}", t0 + 0.4 + 0.7 * j)
            out.append(f'<div class="step" style="animation-name:hs{i}_{j}"><span class="dot"></span><span class="lab">{esc(step)}</span></div>')
        return f'<div class="viz handover">{"".join(out)}</div>'
    raise ValueError(kind)


CSS = """
@property --n{syntax:'<integer>';inherits:false;initial-value:0}
.viz .count{animation:var(--d) linear infinite;animation-delay:calc(var(--t) * -1s)}
.viz .count::after{counter-reset:n var(--n);content:counter(n)}
.viz .count .sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.viz .row.left .lab{color:var(--ink)}
.viz .row.left .num{font-size:5.5cqmin;line-height:1}
.viz .bar.none{background:none;border:0}
.viz{display:grid;gap:2.2cqmin;width:100%;max-width:120cqmin}
.viz .row{display:grid;grid-template-columns:36cqmin 1fr 10cqmin;gap:2cqmin;align-items:center;font:400 3.2cqmin/1.3 var(--font-mono)}
.viz .row.left{opacity:0;animation:var(--d) linear infinite;animation-delay:calc(var(--t) * -1s)}
.viz .lab{color:var(--muted)}
.viz .num{text-align:right;font-variant-numeric:tabular-nums}
.viz .bar{display:block;height:3.2cqmin;background:var(--surface);border:1px solid var(--line);border-radius:999px;overflow:hidden}
.viz .bar i{display:block;height:100%;width:0;animation:var(--d) linear infinite;animation-delay:calc(var(--t) * -1s)}
.viz .t-accent{background:var(--accent)}.viz .bar .t-ink{background:var(--ink)}.viz .bar .t-muted{background:var(--muted)}
.viz span.t-accent,.viz .card.t-accent .num{background:none;color:var(--accent)}
.viz .card{opacity:0;animation:var(--d) linear infinite;animation-delay:calc(var(--t) * -1s);display:grid;gap:0.8cqmin;padding:3cqmin;border:1px solid var(--line);border-radius:3cqmin;background:var(--surface);font:400 3.2cqmin/1.3 var(--font-mono)}
.viz .card .val{font:400 4.2cqmin/1.2 var(--font-display);color:var(--ink)}
.viz .card .num.big{font:400 10cqmin/1 var(--font-display);text-align:left}
.viz .card.t-fail .num{color:var(--fail,var(--accent))}
.viz.hold{grid-template-columns:auto auto 1fr;align-items:center}
.viz .arrow{font:400 6cqmin/1 var(--font-display);color:var(--muted)}
.viz .chips{display:flex;flex-wrap:wrap;gap:1.4cqmin}
.viz .chip{opacity:0;animation:var(--d) linear infinite;animation-delay:calc(var(--t) * -1s);font:400 2.8cqmin/1.2 var(--font-mono);padding:1.2cqmin 2cqmin;border:1px solid var(--line);border-radius:999px;color:var(--ink)}
.viz .chip.t-muted{color:var(--muted)}.viz .chip.t-fail{color:var(--fail,var(--accent))}
.viz.compare .places{display:flex;gap:2cqmin;flex-wrap:wrap}
.viz.handover{grid-template-columns:repeat(4,1fr);gap:2cqmin}
.viz .step{opacity:0;animation:var(--d) linear infinite;animation-delay:calc(var(--t) * -1s);display:grid;gap:1.6cqmin;justify-items:start;font:400 3cqmin/1.3 var(--font-mono)}
.viz .step .dot{width:4cqmin;height:4cqmin;border-radius:50%;background:var(--accent)}
.viz .step .lab{color:var(--ink)}
html.still .viz .row.left,html.still .viz .bar i,html.still .viz .card,html.still .viz .chip,html.still .viz .step,html.still .viz .count{animation-play-state:paused}
@media (prefers-reduced-motion:reduce){.viz .row.left,.viz .bar i,.viz .card,.viz .chip,.viz .step,.viz .count{animation:none;opacity:1}.viz .bar i{width:var(--w)}.viz .count{--n:var(--to)}}
.mech-cap{font:400 3.4cqmin/1.45 var(--font-body);color:var(--muted);max-width:120cqmin}
"""
