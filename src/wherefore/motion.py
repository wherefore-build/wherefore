"""Every feature, in motion: a short clip for each, compiled from the ledger.

A CLIP IS A PAGE. For each feature the engine ships, this writes one HTML page
whose motion is CSS: six scenes in order - the version, who asked, the
command typed, what it printed, the claim, the install line - every word of
which is a fact the engine already states (features.json, releases.json,
roadmap.json, the docs' examples). Nothing is written for the clip; the clip
is compiled, like the changelog. The page plays in any frame it is shown in,
portrait or landscape, because every size is a share of the frame; the
company's site plays it on the feature's card, and a renderer steps it frame
by frame into a video (corpus/motion_render.py) by setting `--t` on a page
marked `still`, which pauses every animation at that second.

WHAT HOLDS IT (tests/test_motion.py): every feature has a claim of at most
CLAIM_WORDS words; every storyboard runs MIN_SECONDS to MAX_SECONDS; no scene
asks more than WORDS_PER_SECOND; the command typed is one the CLI has; every
printed line is one the release picture or a docs example prints; and the page
carries every scene's words, so reach holds the clip as it holds a page.

    wherefore motion [ID ...] [--out DIR] [--storyboards DIR] [--show]
                                      write the clips (all, or the ids named),
                                      the storyboards beside them or in DIR;
                                      --show opens the first in a browser

`motion` in wherefore.json, all optional: `out` (default motion/),
`storyboards` (where the JSON goes, default beside the pages; a corpus whose
palette check reads the pages' folder keeps the storyboards, which quote
what a command printed, out of it), `css` (a
stylesheet the clip links for the brand's variables and fonts, relative to the
corpus root; without one the clip carries plain colours), `vars` (the
variable each role reads, when the stylesheet names them differently), `name`
(the product's, default Wherefore), `install` (the install line, {version}
for the version), `site` (where the feature's page is).
"""
import html
import json
import os
import pathlib
import re
import sys

from . import __version__

HERE = pathlib.Path(__file__).resolve().parent
ELIDED = "…"
CLAIM_WORDS = 12
WORDS_PER_SECOND = 3.0
MIN_SECONDS = 16.0
MAX_SECONDS = 30.0
LINE_WORDS = 14          # an output line longer than this is cut at a clause, with … to say so
ANSWER_LINES = 4
ANSWER_WORDS = 28
FIELDS = ("out", "storyboards", "css", "vars", "name", "install", "site")
ROLES = ("ground", "surface", "line", "ink", "muted", "accent", "font-display", "font-body", "font-mono")
DEFAULTS = {"out": "motion", "name": "Wherefore", "install": "pip install wherefore-build=={version}",
            "site": "https://wherefore.build/"}
# Without a brand stylesheet, the clip's own plain colours: a terminal's black,
# paper, and one green that means a passing build.
PLAIN = {"ground": "#000000", "surface": "#161616", "line": "#3A3A3A", "ink": "#F2F2F2",
         "muted": "#A8A8A8", "accent": "#7CFC00",
         "font-display": "Georgia, 'Times New Roman', serif",
         "font-body": "system-ui, -apple-system, 'Segoe UI', sans-serif",
         "font-mono": "ui-monospace, Menlo, Consolas, monospace"}


def _data(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def features():
    return _data("features.json")["features"]


def releases():
    return {r["version"]: r for r in _data("releases.json")["releases"]}


def ledger(root=None):
    """The roadmap's items by feature, from the engine's own repository when run
    there, else from the release's copy if one ships; empty otherwise."""
    for path in ([root / "roadmap.json"] if root else []) + [HERE.parents[1] / "roadmap.json"]:
        if path.exists():
            items = json.loads(path.read_text(encoding="utf-8"))["items"]
            return {it["feature"]: it for it in items if it.get("state") == "shipped" and it.get("feature")}
    return {}


def docs_examples():
    """[(command, [lines])] from every docs page, the examples the tests replay."""
    from . import docs
    out = []
    for _pid, _title, text in docs.pages():
        out += docs.examples(text)
    return out


def words(text):
    return len(text.split())


def head(usage):
    """The words of a command's usage a person always types: up to the first
    placeholder or flag. `wherefore gate [--keep]` -> `wherefore gate`."""
    out = []
    for tok in usage.split():
        if tok.startswith(("[", "-")) or tok.upper() == tok and any(c.isalpha() for c in tok):
            break
        out.append(tok)
    return " ".join(out)


def cut(line, limit=LINE_WORDS):
    """A line of at most `limit` words: whole clauses while they fit, then …"""
    if words(line) <= limit:
        return line
    parts = re.split(r"(?<=[.;:])\s+|\s+-\s+", line)
    kept, n = [], 0
    for p in parts:
        if n + words(p) > limit:
            break
        kept.append(p)
        n += words(p)
    text = " ".join(kept).rstrip(".;:") if kept else " ".join(line.split()[:limit])
    return text + ELIDED


def _picture(feature, release, examples):
    """(typed, lines): what the clip types and what it prints, from the release
    picture when it shows this feature's command, else from the docs' example of
    it; (None, []) when the feature has no command to show."""
    shows = (release or {}).get("shows") or {}
    run = shows.get("run", "")
    heads = [head(u) for u in feature.get("commands", [])]
    if run and run.split()[1:2] != ["--version"] and (not heads or any(run.startswith(h) for h in heads)):
        return run, [l for l in shows.get("output", []) if l.strip() and l != ELIDED]
    for h in heads:
        for cmd, lines in examples:
            if cmd == h or cmd.startswith(h + " "):
                return cmd, [l for l in lines if l != ELIDED]
    if heads:
        return heads[0], []
    return None, []


def _answer(lines):
    """At most ANSWER_LINES lines and ANSWER_WORDS words, the last line always,
    each cut at a clause: the result is the point."""
    if not lines:
        return []
    last = cut(lines[-1])
    kept, n = [last], words(last)
    for l in reversed(lines[:-1]):
        c = cut(l)
        if len(kept) >= ANSWER_LINES or n + words(c) > ANSWER_WORDS:
            break
        kept.insert(0, c)
        n += words(c)
    return kept


def _seconds(text_words, least, most):
    """Long enough to read at WORDS_PER_SECOND, in half seconds, within bounds."""
    import math
    return max(least, min(most, math.ceil(text_words / WORDS_PER_SECOND * 2) / 2))


def storyboard(feature, release=None, item=None, examples=(), settings=None):
    """The scenes of one feature's clip, in time: [{kind, start, end, ...}]."""
    s = dict(DEFAULTS, **(settings or {}))
    version = feature["since"]
    scenes = []

    def add(kind, least, most, **text):
        start = scenes[-1]["end"] if scenes else 0.0
        sc = dict(kind=kind, start=start, end=0.0, **text)
        sc["end"] = round(start + _seconds(sum(words(t) for t in texts(sc)), least, most), 2)
        scenes.append(sc)

    add("open", 2.0, 2.0, name=s["name"], version=version)
    if item and item.get("issues"):
        eyebrow = f"asked for by {item['asked_by']} · #{', #'.join(u.rsplit('/', 1)[1] for u in item['issues'])}"
    else:
        eyebrow = f"shipped in {version}"
    add("ask", 4.0, 5.5, eyebrow=eyebrow, headline=feature["name"])
    typed, printed = _picture(feature, release, examples)
    if typed:
        # Long enough to type it, a line at a time, and read it once typed.
        import math
        typing = math.ceil((0.6 + 0.07 * len(typed) + 0.2 * (len(typed_lines(typed)) - 1) + 1.5) * 2) / 2
        add("command", max(4.0, typing), max(5.0, typing), eyebrow="the command", typed=typed)
    lines = _answer(printed)
    if lines:
        add("answer", 4.0, 10.0, eyebrow="the answer", lines=lines)
    else:
        more = cut(feature.get("details", "").split(". ")[0].strip().rstrip("."), 24)
        if more:
            add("more", 4.0, 9.0, eyebrow="what it does", text=more)
    add("claim", 4.0, 4.0, text=feature["claim"])
    add("close", 3.5, 3.5, eyebrow="try it", install=s["install"].format(version=version),
        url=s["site"].replace("https://", "").replace("http://", "").rstrip("/") + f"/features/#{feature['id']}")
    return {"id": feature["id"], "name": feature["name"], "version": version,
            "duration": scenes[-1]["end"], "frames": ["portrait", "landscape"], "scenes": scenes}


def texts(scene):
    """Every string a scene shows, in reading order."""
    out = []
    for k in ("name", "version", "eyebrow", "headline", "typed", "text", "install", "url"):
        if scene.get(k):
            out.append(scene[k])
    out += scene.get("lines", [])
    return out


def storyboards(ids=None, root=None, settings=None):
    rel, items, ex = releases(), ledger(root), docs_examples()
    feats = features()
    if ids:
        unknown = sorted(set(ids) - {f["id"] for f in feats})
        if unknown:
            raise SystemExit(f"::error::no feature called {', '.join(unknown)}: "
                             f"{', '.join(f['id'] for f in feats)}")
        feats = [f for f in feats if f["id"] in ids]
    return [storyboard(f, rel.get(f["since"]), items.get(f["id"]), ex, settings) for f in feats]


# --- the page ---------------------------------------------------------------

TYPED_LINE = 28          # characters of a typed command per line, in a portrait frame


def typed_lines(typed):
    """A command in lines of at most TYPED_LINE characters, broken at spaces,
    every line but the last ending in the shell's backslash."""
    words, lines, cur = typed.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) + 2 > TYPED_LINE:
            lines.append(cur + " \\")
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w
    lines.append(cur)
    return lines


def _pct(t, total):
    return f"{t / total * 100:.3f}%"


def _window(name, start, end, total, fade=0.3):
    a, b = start + fade, max(start + fade, end - fade)
    return (f"@keyframes {name}{{0%,{_pct(start, total)}{{opacity:0}}{_pct(a, total)}{{opacity:1}}"
            f"{_pct(b, total)}{{opacity:1}}{_pct(end, total)},100%{{opacity:0}}}}")


def page(board, css=None, vars=None):
    """One self-contained page: the clip, playing and looping; `html.still`
    with `--t` set pauses it at that second (the renderer's way in)."""
    total = board["duration"]
    v = dict(zip(ROLES, (f"--{r}" for r in ROLES)), **(vars or {}))
    var = {r: f"var({v[r]})" for r in ROLES}
    if css:
        root = ":root{--t:0}"
        link = f'<link rel="stylesheet" href="{html.escape(css)}">'
    else:
        root = ":root{--t:0;" + ";".join(f"{v[r]}:{PLAIN[r]}" for r in ROLES) + "}"
        link = ""
    rules, body = [], []
    for i, sc in enumerate(board["scenes"]):
        name = f"w{i}"
        rules.append(_window(name, sc["start"], sc["end"], total))
        inner = ""
        if sc["kind"] == "open":
            inner = (f'<div class="mark">{html.escape(sc["name"])}</div>'
                     f'<div class="ver">{html.escape(sc["version"])}</div>')
        elif sc["kind"] == "ask":
            inner = (f'<div class="eye">{html.escape(sc["eyebrow"])}</div>'
                     f'<div class="big">{html.escape(sc["headline"])}</div>')
        elif sc["kind"] == "command":
            # Typed a line at a time, a long command broken shell-style with a
            # trailing backslash, so no line outruns a portrait frame.
            parts = typed_lines(sc["typed"])
            t0, lines = sc["start"] + 0.6, []
            for k, part in enumerate(parts):
                n = len(part)
                t1 = t0 + n * 0.07
                rules.append(f"@keyframes type{i}_{k}{{0%,{_pct(t0, total)}{{width:0}}{_pct(t1, total)},100%{{width:{n}ch}}}}")
                prompt = '<span class="prompt">$ </span>' if k == 0 else '<span class="prompt">&gt; </span>'
                lines.append(f'<code class="ln">{prompt}<span class="typed" style="animation-name:type{i}_{k};'
                             f'animation-timing-function:steps({n})">{html.escape(part)}</span></code>')
                t0 = t1 + 0.2
            inner = f'<div class="eye">{html.escape(sc["eyebrow"])}</div><pre class="term">{"".join(lines)}</pre>'
        elif sc["kind"] == "answer":
            lines = []
            for j, l in enumerate(sc["lines"]):
                t0 = sc["start"] + 0.4 + 0.5 * j
                rules.append(f"@keyframes line{i}_{j}{{0%,{_pct(t0, total)}{{opacity:0}}{_pct(t0 + 0.2, total)},100%{{opacity:1}}}}")
                hi = " hi" if j == len(sc["lines"]) - 1 else ""
                lines.append(f'<code class="ln{hi}" style="animation-name:line{i}_{j}">{html.escape(l)}</code>')
            inner = f'<div class="eye">{html.escape(sc["eyebrow"])}</div><pre class="term">{"".join(lines)}</pre>'
        elif sc["kind"] == "more":
            inner = f'<div class="eye">{html.escape(sc["eyebrow"])}</div><div class="claim">{html.escape(sc["text"])}</div>'
        elif sc["kind"] == "claim":
            inner = f'<div class="claim">{html.escape(sc["text"])}</div>'
        elif sc["kind"] == "close":
            inner = (f'<div class="eye">{html.escape(sc["eyebrow"])}</div>'
                     f'<div class="install">{html.escape(sc["install"])}</div>'
                     f'<div class="url">{html.escape(sc["url"])}</div>')
        body.append(f'<div class="scene {sc["kind"]}" style="animation-name:{name}">{inner}</div>')
    style = f"""{root}
html,body{{margin:0;height:100%;overflow:hidden;background:{var['ground']};color:{var['ink']}}}
.frame{{position:relative;width:100%;height:100%;container-type:size;font-family:{var['font-body']}}}
.scene{{position:absolute;inset:0;padding:8cqmin 9cqmin;display:flex;flex-direction:column;justify-content:center;gap:3cqmin;opacity:0;animation:{total}s linear infinite;animation-delay:calc(var(--t) * -1s)}}
.scene>*{{max-width:120cqmin}}
.typed,.answer .ln{{animation:{total}s linear infinite;animation-delay:calc(var(--t) * -1s)}}
.typed{{font:inherit}}
html.still .scene,html.still .typed,html.still .answer .ln{{animation-play-state:paused}}
@media (prefers-reduced-motion:reduce){{.scene,.typed,.answer .ln{{animation-play-state:paused}}}}
.mark{{font:400 17cqmin/1 {var['font-display']};letter-spacing:-0.02em}}
.ver{{font:500 4cqmin/1 {var['font-mono']};color:{var['ground']};background:{var['accent']};padding:1.6cqmin 2.6cqmin;border-radius:999px;align-self:flex-start}}
.eye{{font:500 3.3cqmin/1.3 {var['font-mono']};letter-spacing:0.06em;text-transform:uppercase;color:{var['muted']}}}
.big{{font:400 11.5cqmin/1.05 {var['font-display']};text-wrap:balance}}
.term{{margin:0;font:400 4.2cqmin/1.6 {var['font-mono']};background:{var['surface']};border:1px solid {var['line']};border-radius:3cqmin;padding:4cqmin;display:grid;gap:1.2cqmin;white-space:normal}}
.term .ln{{display:block;font:inherit;white-space:pre-wrap;overflow-wrap:anywhere}}
.term .ln.hi{{color:{var['accent']}}}
.term .prompt{{color:{var['muted']}}}
.typed{{display:inline-block;white-space:nowrap;overflow:hidden;vertical-align:bottom;width:0;border-right:0.5cqmin solid {var['accent']}}}
.answer .ln{{opacity:0}}
.claim{{font:400 9.5cqmin/1.1 {var['font-display']};text-wrap:balance}}
.install{{font:400 4.2cqmin/1.6 {var['font-mono']}}}
.install b{{color:{var['accent']};font-weight:500}}
.url{{font:400 3.6cqmin/1.5 {var['font-mono']};color:{var['muted']}}}
{"".join(rules)}"""
    title = f"{board['name']} · {board['version']}"
    return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{html.escape(title)}</title><meta name="robots" content="noindex">{link}<style>{style}</style></head>\n'
            f'<body><div class="frame" data-duration="{total}">{"".join(body)}</div></body></html>\n')


# --- the command -------------------------------------------------------------

def settings_from(cfg):
    """The `motion` section, checked; {} when there is none."""
    doc = cfg.doc if cfg else {}
    m = doc.get("motion")
    if m is None:
        return {}
    from .config import ConfigError
    if not isinstance(m, dict):
        raise ConfigError("`motion` is an object: out, css, vars, name, install, site - all optional")
    unknown = set(m) - set(FIELDS)
    if unknown:
        raise ConfigError(f"`motion` has {', '.join(sorted(unknown))}, which it does not take: {', '.join(FIELDS)}")
    for k in FIELDS:
        if k == "vars":
            continue
        if k in m and not (isinstance(m[k], str) and m[k].strip()):
            raise ConfigError(f"`motion.{k}` is a string")
    if "vars" in m:
        if not isinstance(m["vars"], dict) or set(m["vars"]) - set(ROLES) or \
                not all(isinstance(x, str) and x.startswith("--") for x in m["vars"].values()):
            raise ConfigError(f"`motion.vars` maps a role to the CSS variable the stylesheet names it by: "
                              f"{', '.join(ROLES)}")
    if "install" in m and "{version}" not in m["install"]:
        raise ConfigError("`motion.install` says the install line with {version} where the version goes")
    return m


def validate(doc):
    class _C:
        pass
    c = _C()
    c.doc = doc
    settings_from(c)


def write(boards, out, css=None, vars=None, storyboards=None):
    """out/<id>/index.html for each, and <id>/storyboard.json beside it or
    under `storyboards`; [paths written]."""
    paths = []
    for b in boards:
        d = out / b["id"]
        d.mkdir(parents=True, exist_ok=True)
        rel = css and os.path.relpath(css, d).replace(os.sep, "/")
        (d / "index.html").write_text(page(b, rel, vars), encoding="utf-8")
        j = (storyboards or out) / b["id"]
        j.mkdir(parents=True, exist_ok=True)
        (j / "storyboard.json").write_text(json.dumps(b, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        paths += [d / "index.html", j / "storyboard.json"]
    return paths


USAGE = "usage: wherefore motion [ID ...] [--out DIR] [--storyboards DIR] [--show]"


def main(cfg, args):
    if any(a in ("-h", "--help") for a in args):
        print(USAGE)
        return 0
    show, out, ids, boards_dir = False, None, [], None
    typed_out = None
    it = iter(args)
    for a in it:
        if a == "--show":
            show = True
        elif a == "--out":
            out = typed_out = next(it, None)
            if not out:
                print(USAGE)
                return 2
        elif a == "--storyboards":
            boards_dir = next(it, None)
            if not boards_dir:
                print(USAGE)
                return 2
        elif a.startswith("-"):
            print(f"::error::wherefore motion does not take {a}\n{USAGE}")
            return 2
        else:
            ids.append(a)
    s = settings_from(cfg)
    root = cfg.root if cfg else pathlib.Path.cwd()
    out = pathlib.Path(out) if out else root / s.get("out", DEFAULTS["out"])
    css = root / s["css"] if s.get("css") else None
    if boards_dir or s.get("storyboards"):
        boards_dir = pathlib.Path(boards_dir) if boards_dir else root / s["storyboards"]
    boards = storyboards(ids or None, root, s)
    for b in boards:
        print(f"  {b['id']:<12} {len(b['scenes'])} scenes  {b['duration']:>4.1f} s  {b['name']}")
    write(boards, out, css, s.get("vars"), boards_dir)
    shown = typed_out.rstrip("/") if typed_out else os.path.relpath(out, pathlib.Path.cwd()).replace(os.sep, "/")
    print(f"wrote {shown}/: {len(boards)} clip{'s' if len(boards) != 1 else ''}, "
          f"{'each ' if len(boards) != 1 else ''}a page in motion, played by the frame it is shown in")
    if show:
        import webbrowser
        first = out / boards[0]["id"] / "index.html"
        webbrowser.open(first.resolve().as_uri())
        print(f"opened {first}")
    return 0
