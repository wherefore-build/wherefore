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
marked `still`, which pauses every animation at that second. A viewer who
asks for less motion sees the claim, still.

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
(the product's, default Wherefore), `install` (the install line, with
{version} where the version goes if it should name one), `site` (where the
feature's page is), `roadmap` (the corpus's copy of the engine's ledger, so
the ask scene can say who asked), `icon` (the brand's mark, shown at the
close) and `tagline` (the line under the address at the close: a string, or
a fact out of the source, so the clip says what the site says).

THE MECHANISM SCENE (mechanism.py): what the feature does, drawn from the
corpus the clip is made in - its own file counts, pages, sources and ledger -
after the command's answer. Each feature names one of four in features.json.
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
WORDS_PER_SECOND = 3.0   # a headline
CAPTION_WORDS_PER_SECOND = 2.5   # a caption, or printed lines
TYPE_SECONDS = 0.055            # a character typed
MIN_SECONDS = 16.0
MAX_SECONDS = 34.0
LINE_WORDS = 14          # an output line longer than this is cut at a clause, with … to say so
ANSWER_LINES = 4
ANSWER_WORDS = 28
FIELDS = ("out", "storyboards", "css", "vars", "name", "install", "site", "roadmap", "icon", "tagline")
ROLES = ("ground", "surface", "line", "ink", "muted", "accent", "font-display", "font-body", "font-mono")
DEFAULTS = {"out": "motion", "name": "Wherefore", "install": "pip install wherefore-build",
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


def ledger_items(root=None, copy=None):
    """The roadmap's items: the corpus's copy when `motion.roadmap` names one,
    else the engine's own when run in its repository; [] otherwise."""
    paths = ([root / copy] if root and copy else []) + ([root / "roadmap.json"] if root else []) \
        + [HERE.parents[1] / "roadmap.json"]
    for path in paths:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))["items"]
    return []


def ledger(root=None, copy=None):
    """The roadmap's shipped items by feature."""
    return {it["feature"]: it for it in ledger_items(root, copy) if it.get("state") == "shipped" and it.get("feature")}


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


def _answer(lines, short=False):
    """At most ANSWER_LINES lines and ANSWER_WORDS words, the last line always,
    each cut at a clause: the result is the point. `short`, when a mechanism
    scene follows: the last line alone."""
    if not lines:
        return []
    last = cut(lines[-1])
    if short:
        return [last]
    kept, n = [last], words(last)
    for l in reversed(lines[:-1]):
        c = cut(l)
        if len(kept) >= ANSWER_LINES or n + words(c) > ANSWER_WORDS:
            break
        kept.insert(0, c)
        n += words(c)
    return kept


def _seconds(text_words, least, most, rate=WORDS_PER_SECOND):
    """Long enough to read at `rate` words a second, in half seconds, within bounds."""
    import math
    return max(least, min(most, math.ceil(text_words / rate * 2) / 2))


def storyboard(feature, release=None, item=None, examples=(), settings=None, mechanics=None):
    """The scenes of one feature's clip, in time: [{kind, start, end, ...}].
    `mechanics` is mechanism.gather()'s {kind: data} for the corpus the clip
    is made in; the feature's mechanism scene is drawn when its data is there."""
    s = dict(DEFAULTS, **(settings or {}))
    version = feature["since"]
    scenes = []

    def add(kind, least, most, **text):
        start = scenes[-1]["end"] if scenes else 0.0
        sc = dict(kind=kind, start=start, end=0.0, **text)
        rate = CAPTION_WORDS_PER_SECOND if kind in ("answer", "mechanism", "more") else WORDS_PER_SECOND
        sc["end"] = round(start + _seconds(sum(words(t) for t in texts(sc)), least, most, rate), 2)
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
        typing = math.ceil((0.6 + TYPE_SECONDS * len(typed) + 0.2 * (len(typed_lines(typed)) - 1) + 1.5) * 2) / 2
        add("command", max(4.0, typing), max(5.0, typing), eyebrow="the command", typed=typed)
    from . import mechanism
    kind = feature.get("mechanism")
    mech = (mechanics or {}).get(kind) if kind else None
    lines = _answer(printed, short=mech is not None)
    if lines:
        add("answer", 4.0, 10.0, eyebrow="the answer", lines=lines)
    elif mech is None:
        more = cut(feature.get("details", "").split(". ")[0].strip().rstrip("."), 24)
        if more:
            add("more", 4.0, 9.0, eyebrow="what it does", text=more)
    if mech is not None:
        add("mechanism", 5.0, 8.0, eyebrow=mechanism.eyebrow(kind), mechanism=kind, data=mech,
            caption=mechanism.caption(kind, mech))
    add("claim", 4.0, 4.0, text=feature["claim"])
    home = s["site"].replace("https://", "").replace("http://", "").rstrip("/")
    # The last frame is the one that stays: the mark, the address, the line
    # under it, then how to install and where this feature's page is.
    close = dict(home=home, install=s["install"].format(version=version), url=f"{home}/features/#{feature['id']}")
    if s.get("tagline"):
        close["tagline"] = s["tagline"]
    if s.get("icon"):
        close["icon"] = s["icon"]
    add("close", 4.0, 4.5, **close)
    return {"id": feature["id"], "name": feature["name"], "version": version,
            "duration": scenes[-1]["end"], "frames": ["portrait", "landscape"], "scenes": scenes}


def texts(scene):
    """Every string a scene shows, in reading order."""
    out = []
    for k in ("name", "version", "eyebrow", "headline", "typed", "text", "caption", "home", "tagline", "install", "url"):
        if scene.get(k):
            out.append(scene[k])
    out += scene.get("lines", [])
    return out


def storyboards(ids=None, root=None, settings=None, cfg=None):
    """Every feature's storyboard, or those named; with `cfg`, the corpus the
    clips are made in, whose numbers fill each mechanism scene."""
    from . import mechanism
    copy = (settings or {}).get("roadmap")
    rel, items, ex = releases(), ledger(root, copy), docs_examples()
    mechanics = mechanism.gather(cfg, ledger_items(root, copy), list(rel.values()))
    feats = features()
    if ids:
        unknown = sorted(set(ids) - {f["id"] for f in feats})
        if unknown:
            raise SystemExit(f"::error::no feature called {', '.join(unknown)}: "
                             f"{', '.join(f['id'] for f in feats)}")
        feats = [f for f in feats if f["id"] in ids]
    return [storyboard(f, rel.get(f["since"]), items.get(f["id"]), ex, settings, mechanics) for f in feats]


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


def _window(name, start, end, total, fade_in=0.3, fade_out=0.3, rise=False):
    """A scene's window: in at `start`, out at `end`. A fade of 0 is a cut - a
    terminal does not fade. `rise` brings the scene up into place as it comes."""
    # A cut is a fade of a fiftieth: two keyframes at one instant make the
    # browser ramp from the clip's start instead, and the scene ghosts early.
    fade_in, fade_out = max(fade_in, 0.02), max(fade_out, 0.02)
    a, b = start + fade_in, max(start + fade_in, end - fade_out)
    up = ";transform:translateY(4cqmin)" if rise else ""
    flat = ";transform:none" if rise else ""
    return (f"@keyframes {name}{{0%,{_pct(start, total)}{{opacity:0{up}}}{_pct(a, total)}{{opacity:1{flat}}}"
            f"{_pct(b, total)}{{opacity:1{flat}}}{_pct(end, total)},100%{{opacity:0{flat}}}}}")


def _staggered(prefix, i, parts, t0, step, total, rules, cls="w", tag="span"):
    """`parts` as elements, each arriving `step` after the last from `t0`."""
    out = []
    for j, part in enumerate(parts):
        rules.append(f"@keyframes {prefix}{i}_{j}{{0%,{_pct(t0 + step * j, total)}{{opacity:0}}"
                     f"{_pct(t0 + step * j + 0.25, total)},100%{{opacity:1}}}}")
        out.append(f'<{tag} class="{cls}" style="animation-name:{prefix}{i}_{j}">{html.escape(part)}</{tag}>')
    return out


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
    kinds = [sc["kind"] for sc in board["scenes"]]
    for i, sc in enumerate(board["scenes"]):
        name = f"w{i}"
        # CUTS BY TYPE: the command cuts to its answer, as a terminal does; the
        # mechanism rises into place as a result; everything else fades.
        after = kinds[i + 1] if i + 1 < len(kinds) else None
        rules.append(_window(name, sc["start"], sc["end"], total,
                             fade_in=0 if sc["kind"] == "answer" and kinds[i - 1] == "command" else 0.3,
                             fade_out=0 if sc["kind"] == "command" and after == "answer" else 0.3,
                             rise=sc["kind"] == "mechanism"))
        inner = ""
        if sc["kind"] == "open":
            # THE ONE FLOURISH: the wordmark sets itself, a letter at a time,
            # then the version chip stamps in, the way a build goes green.
            letters = _staggered("set", i, list(sc["name"]), sc["start"] + 0.2, 0.06, total, rules, cls="l")
            t1 = sc["start"] + 0.2 + 0.06 * len(sc["name"]) + 0.3
            rules.append(f"@keyframes stamp{i}{{0%,{_pct(t1, total)}{{opacity:0;transform:scale(1.2)}}"
                         f"{_pct(t1 + 0.25, total)},100%{{opacity:1;transform:none}}}}")
            inner = (f'<div class="mark" aria-label="{html.escape(sc["name"])}">{"".join(letters)}</div>'
                     f'<div class="ver" style="animation-name:stamp{i}">{html.escape(sc["version"])}</div>')
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
                t1 = t0 + n * TYPE_SECONDS
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
        elif sc["kind"] == "mechanism":
            from . import mechanism
            inner = (f'<div class="eye">{html.escape(sc["eyebrow"])}</div>{mechanism.render(sc, i, total, rules)}'
                     f'<p class="mech-cap">{html.escape(sc["caption"])}</p>')
        elif sc["kind"] == "claim":
            # Set word by word, a beat behind the last.
            inner = f'<div class="claim">{" ".join(_staggered("wd", i, sc["text"].split(), sc["start"] + 0.3, 0.08, total, rules))}</div>'
        elif sc["kind"] == "close":
            parts = []
            if sc.get("icon"):
                parts.append(f'<img class="icon" src="{html.escape(sc["icon"])}" alt="">')
            parts.append(f'<div class="home">{html.escape(sc["home"])}</div>')
            if sc.get("tagline"):
                parts.append(f'<div class="tag">{html.escape(sc["tagline"])}</div>')
            parts.append(f'<div class="install">{html.escape(sc["install"])}</div>'
                         f'<div class="url">{html.escape(sc["url"])}</div>')
            close = _staggered("cl", i, [""] * len(parts), sc["start"] + 0.2, 0.3, total, rules, tag="div")
            inner = "".join(c.replace('></div>', f'>{p}</div>') for c, p in zip(close, parts))
        body.append(f'<div class="scene {sc["kind"]}" style="animation-name:{name}">{inner}</div>')
    from . import mechanism
    style = f"""{root}
:root{{--d:{total}s}}
html,body{{margin:0;height:100%;overflow:hidden;background:{var['ground']};color:{var['ink']}}}
.frame{{position:relative;width:100%;height:100%;container-type:size;font-family:{var['font-body']}}}
.scene{{position:absolute;inset:0;padding:8cqmin 9cqmin;display:flex;flex-direction:column;justify-content:center;gap:3cqmin;opacity:0;animation:{total}s linear infinite;animation-delay:calc(var(--t) * -1s)}}
.scene>*{{max-width:120cqmin}}
.typed,.answer .ln{{animation:{total}s linear infinite;animation-delay:calc(var(--t) * -1s)}}
.typed{{font:inherit}}
html.still .scene,html.still .typed,html.still .answer .ln,html.still .mark .l,html.still .ver,html.still .claim .w,html.still .close .w{{animation-play-state:paused}}
@media (prefers-reduced-motion:reduce){{.scene,.typed,.answer .ln,.mark .l,.ver,.claim .w,.close .w{{animation:none}}.scene{{opacity:0}}.scene.claim,.mark .l,.ver,.claim .w,.close .w{{opacity:1}}}}
.mark{{font:400 17cqmin/1 {var['font-display']};letter-spacing:-0.02em}}
.mark .l,.claim .w,.close .w{{opacity:0;animation:{total}s linear infinite;animation-delay:calc(var(--t) * -1s)}}
.close .icon{{width:14cqmin;height:14cqmin;display:block;margin-bottom:2cqmin}}
.tag{{font:italic 400 5.2cqmin/1.2 {var['font-display']};color:{var['muted']}}}
.ver{{font:500 4cqmin/1 {var['font-mono']};color:{var['ground']};background:{var['accent']};padding:1.6cqmin 2.6cqmin;border-radius:999px;align-self:flex-start;opacity:0;animation:{total}s linear infinite;animation-delay:calc(var(--t) * -1s)}}
.eye{{font:500 3.3cqmin/1.3 {var['font-mono']};letter-spacing:0.06em;text-transform:uppercase;color:{var['muted']}}}
.big{{font:400 11.5cqmin/1.05 {var['font-display']};text-wrap:balance}}
.term{{margin:0;font:400 4.2cqmin/1.6 {var['font-mono']};background:{var['surface']};border:1px solid {var['line']};border-radius:3cqmin;padding:4cqmin;display:grid;gap:1.2cqmin;white-space:normal}}
.term .ln{{display:block;font:inherit;white-space:pre-wrap;overflow-wrap:anywhere}}
.term .ln.hi{{color:{var['accent']}}}
.term .prompt{{color:{var['muted']}}}
.typed{{display:inline-block;white-space:nowrap;overflow:hidden;vertical-align:bottom;width:0;border-right:0.5cqmin solid {var['accent']}}}
.answer .ln{{opacity:0}}
.claim{{font:400 9.5cqmin/1.1 {var['font-display']};text-wrap:balance}}
.install{{font:400 3.8cqmin/1.6 {var['font-mono']}}}
.install b{{color:{var['accent']};font-weight:500}}
.home{{font:400 12cqmin/1 {var['font-display']};letter-spacing:-0.02em}}
.mech-cap{{margin:0}}
{mechanism.CSS.replace("var(--font-mono)", var['font-mono']).replace("var(--font-display)", var['font-display']).replace("var(--font-body)", var['font-body']).replace("var(--muted)", var['muted']).replace("var(--ink)", var['ink']).replace("var(--accent)", var['accent']).replace("var(--surface)", var['surface']).replace("var(--line)", var['line'])}
.url{{font:400 3.6cqmin/1.5 {var['font-mono']};color:{var['muted']}}}
{"".join(rules)}"""
    title = f"{board['name']} · {board['version']}"
    return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{html.escape(title)}</title><meta name="robots" content="noindex">{link}<style>{style}</style></head>\n'
            f'<body><div class="frame" data-duration="{total}">{"".join(body)}</div></body></html>\n')


# --- the command -------------------------------------------------------------

def settings_from(cfg):
    """The `motion` section, checked, with a tagline named as a fact read out of
    the source; {} when there is none."""
    doc = cfg.doc if cfg else {}
    m = doc.get("motion")
    if m is None:
        return {}
    m = _checked(m)
    if isinstance(m.get("tagline"), dict):
        from . import sources
        name, src = cfg.source(m["tagline"].get("source"))
        d = json.loads((cfg.root / src["path"]).read_text(encoding="utf-8"))
        m = dict(m, tagline=str(sources.value(d, m["tagline"]["fact"], src.get("adapter", "leaves"))))
    return m


def _checked(m):
    from .config import ConfigError
    if not isinstance(m, dict):
        raise ConfigError("`motion` is an object: out, css, vars, name, install, site - all optional")
    unknown = set(m) - set(FIELDS)
    if unknown:
        raise ConfigError(f"`motion` has {', '.join(sorted(unknown))}, which it does not take: {', '.join(FIELDS)}")
    for k in FIELDS:
        if k in ("vars", "tagline"):
            continue
        if k in m and not (isinstance(m[k], str) and m[k].strip()):
            raise ConfigError(f"`motion.{k}` is a string")
    if "vars" in m:
        if not isinstance(m["vars"], dict) or set(m["vars"]) - set(ROLES) or \
                not all(isinstance(x, str) and x.startswith("--") for x in m["vars"].values()):
            raise ConfigError(f"`motion.vars` maps a role to the CSS variable the stylesheet names it by: "
                              f"{', '.join(ROLES)}")
    if "tagline" in m and not (isinstance(m["tagline"], str) or
                               (isinstance(m["tagline"], dict) and isinstance(m["tagline"].get("fact"), str))):
        raise ConfigError("`motion.tagline` is the line under the address at the close: a string, or "
                          "{\"fact\": a dotted path into the source, \"source\": its name if not the first}")
    return m


def validate(doc):
    if doc.get("motion") is not None:
        _checked(doc["motion"])


def write(boards, out, css=None, vars=None, storyboards=None, root=None):
    """out/<id>/index.html for each, and <id>/storyboard.json beside it or
    under `storyboards`; [paths written]. `root` is what the stylesheet and
    the icon are relative to - the corpus - so the page links them from
    where it is."""
    paths = []
    for b in boards:
        d = out / b["id"]
        d.mkdir(parents=True, exist_ok=True)
        rel = css and os.path.relpath(css, d).replace(os.sep, "/")
        for sc in b["scenes"]:
            if sc["kind"] == "close" and sc.get("icon") and root is not None:
                sc["icon"] = os.path.relpath(root / sc["icon"], d).replace(os.sep, "/")
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
    boards = storyboards(ids or None, root, s, cfg)
    for b in boards:
        print(f"  {b['id']:<12} {len(b['scenes'])} scenes  {b['duration']:>4.1f} s  {b['name']}")
    write(boards, out, css, s.get("vars"), boards_dir, root)
    shown = typed_out.rstrip("/") if typed_out else os.path.relpath(out, pathlib.Path.cwd()).replace(os.sep, "/")
    print(f"wrote {shown}/: {len(boards)} clip{'s' if len(boards) != 1 else ''}, "
          f"{'each ' if len(boards) != 1 else ''}a page in motion, played by the frame it is shown in")
    if show:
        import webbrowser
        first = out / boards[0]["id"] / "index.html"
        webbrowser.open(first.resolve().as_uri())
        print(f"opened {first}")
    return 0
