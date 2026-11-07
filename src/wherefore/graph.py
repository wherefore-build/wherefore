"""`wherefore graph` - what builds what, drawn from a real run.

The gate answers one question about every tracked file: generated, authored or
captured, and is it current. This answers the one a person asks next: WHICH
script made it, from WHAT. It runs every generator once, the way the gate does
- the observer recording what each wrote and, through its read log, what each
read - classifies every tracked file exactly as the gate does, and writes the
chain down twice: as JSON, for anything that wants to read it, and as one
self-contained page that draws it.

IT CHANGES NOTHING. Every tracked file is snapshotted before the run and put
back after it, byte for byte, and a file a generator created that was not
there before is removed again. A graph that left regenerated files behind
would be a build nobody asked for - and on a machine whose renders differ from
the one that committed them, a working tree full of changes nobody made.

WHO MADE A FILE is its FIRST writer. Later generators sometimes re-save an
earlier one's output - a pack builder that rewrites the sheets it embeds - and
crediting the last writer made the script that actually drew them look as if it
made nothing. The later writers are kept, as `also`.

WHAT A SCRIPT READ comes from its own read log, one per generator, so whose
read it was never rests on matching a script's name. Writes, the generator's
own outputs and untracked files are not reads of anything the corpus holds;
`.py` files it read are its code, said apart from its sources. A `run`
generator (any command, not Python) loads no observer: its writes are seen and
its reads are NOT, so it says `reads: null` - not observed - and never claims
it reads nothing.

Exit status: 0, or 1 when a generator failed - and the page is written either
way, with the failures on it, because a failure is the thing worth seeing.
"""
import html
import importlib
import json
import os
import re
import pathlib
import shutil
import subprocess
import sys
import tempfile

from . import __version__

SCHEMA = 1
USAGE = "usage: wherefore graph [--html PATH] [--json PATH|-] [--theme CSS ...] [--home URL [WORDS]]"
DEFAULT_HTML = "wherefore-graph.html"
WRITING = set("wax+")


# ── whose corpus ────────────────────────────────────────────────────────────

def configure(cfg):
    """Configure the runner and the gate for this corpus, the way its own gate
    is configured. A corpus that hands its gate to a script of its own (`entry`)
    configures the engine in that script, so the scripts it names for `list`
    and `gate` are imported - not run - and what they configure is used."""
    from . import gate
    scripts = [cfg.entry(c) for c in ("list", "gate") if cfg.entry(c)]
    if not scripts:
        gate.configure_from(cfg)
        return
    os.environ["WHEREFORE_ROOT"] = str(cfg.root)
    for argv in scripts:
        path = (cfg.root / argv[0]).resolve()
        if str(path.parent) not in sys.path:
            sys.path.insert(0, str(path.parent))
        importlib.import_module(path.stem)


def inventory(cfg):
    """The inventory as the gate sees it: wherefore.json's own, or - for a corpus
    that configures the engine in its scripts (`entry`) - what they configure."""
    if not any(cfg.entry(c) for c in ("list", "gate")):
        return cfg.doc.get("inventory") or {}
    from . import gate
    configure(cfg)
    return (gate.DECL() if gate.DECL else None) or {}


# ── the map's own generator ─────────────────────────────────────────────────
#
# A corpus may publish its own map: a `run` generator that is this command -
# `wherefore graph --html site/map/index.html`, say - so the page is built and
# judged like any other generated file. Under the gate it runs as any command
# does. Under this command it is NOT run: the map runs every generator, and
# that one would run the map, without end. It is credited instead with the
# files its arguments name, and the gate holds those files to what it writes.

def maps_itself(g):
    """The paths, relative to the root, that a `run` generator which is this
    command would write; None for any other generator."""
    if not g.run:
        return None
    words = list(g.run)
    if len(words) >= 3 and words[1] == "-m" and words[2] == "wherefore":
        words = words[3:]
    elif words and pathlib.PurePath(words[0]).name in ("wherefore", "wherefore.exe"):
        words = words[1:]
    else:
        return None
    if words[:1] != ["graph"]:
        return None
    out, rest = [], words[1:]
    while rest:
        a, rest = rest[0], rest[1:]
        if a not in ("--html", "--json", "--theme", "--home"):
            return None               # not a call this command would take: let it run, and fail in words
        if not rest:
            return None
        dest, rest = rest[0], rest[1:]
        if a == "--theme":
            continue                  # a stylesheet it reads, not a file it writes
        if a == "--home":             # an address, and maybe the words for it: nothing written
            if rest and not rest[0].startswith("--"):
                rest = rest[1:]
            continue
        if dest != "-":
            out.append(os.path.normpath(os.path.join(g.cwd, dest)))
    if not out and "--html" not in words:
        out.append(os.path.normpath(os.path.join(g.cwd, DEFAULT_HTML)))
    return out


# ── the run, and putting the tree back ──────────────────────────────────────

def _untracked(root):
    """Every file under root git does not track, ignored ones included."""
    r = subprocess.run(["git", "ls-files", "-z", "--others"], cwd=root,
                       capture_output=True, text=True)
    return {os.path.realpath(root / f) for f in r.stdout.split("\0") if f}


def _dirs(root):
    out = set()
    for d, dirs, _files in os.walk(root):
        dirs[:] = [x for x in dirs if x != ".git"]
        out.add(os.path.realpath(d))
    return out


def observe():
    """Run every generator once, watched, and put the tree back.

    Returns (tracked, wrote, reads, failures) - tracked as {realpath: rel},
    the rest as generators.run_all gives them."""
    from . import gate, generators as G
    from ._observe.sitecustomize import copying
    names = sorted(G.tracked().values())
    before_untracked, before_dirs = _untracked(G.ROOT), _dirs(G.ROOT)
    wrote, reads, failures, tracked = {}, {}, [], {}
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"{G.TEMP_PREFIX}graph-"))
    try:
        with copying():
            gate.snapshot(names, tmp / "before")
        every = list(G.GENERATORS)
        G.GENERATORS[:] = [g for g in every if maps_itself(g) is None]
        try:
            wrote, failures = G.run_all(quiet=True, reads=reads)
        finally:
            G.GENERATORS[:] = every
        for g in every:
            for rel in maps_itself(g) or ():
                wrote.setdefault(os.path.realpath(G.ROOT / rel), []).append(G.name(g))
        tracked = G.tracked()
    finally:
        with copying():
            for rel in names:
                was, now = tmp / "before" / rel, G.ROOT / rel
                if was.is_file() and (not now.is_file() or was.read_bytes() != now.read_bytes()):
                    now.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(was, now)
                elif not was.is_file() and now.is_file():
                    now.unlink()          # tracked, missing before, made by the run
            # What the run made that was not there before goes too, ignored or
            # not: every file a generator was seen writing, and the bytecode its
            # imports left - and then any directory the run created that is
            # empty again. Only what the run demonstrably made: a file that
            # appeared for any other reason is not this command's to delete.
            keep = {os.path.realpath(G.ROOT / rel) for rel in names} | before_untracked
            made = set(wrote) | {p for p in _untracked(G.ROOT)
                                 if p.endswith(".pyc") and os.sep + "__pycache__" + os.sep in p}
            for p in made:
                if p not in keep and os.path.isfile(p):
                    os.unlink(p)
            for d in sorted(_dirs(G.ROOT) - before_dirs, key=len, reverse=True):
                try:
                    os.rmdir(d)
                except OSError:
                    pass                  # not empty: something else is in it
        shutil.rmtree(tmp, ignore_errors=True)
    return tracked, wrote, reads, failures


# ── the model ───────────────────────────────────────────────────────────────

def model(name, tracked, wrote, reads, failures):
    """The chain, as data: what the JSON says and the page draws."""
    from . import gate, generators as G
    decl = gate.DECL()
    decl.setdefault("authored", {}).setdefault("rules", [])
    decl.setdefault("captured", {}).setdefault("groups", {})
    rules = decl["authored"]["rules"]
    captured = gate.captured_files(decl)
    failed = dict(failures)

    gens = [{"name": G.name(g), "cwd": g.cwd, "makes": g.makes,
             "kind": "run" if g.run else "script",
             "writes": [], "rewrites": [], "reads": None, "code": None,
             "failure": failed.get(G.name(g))} for g in G.GENERATORS]
    by_name = {g["name"]: g for g in gens}

    files = {}
    for real, rel in sorted(tracked.items(), key=lambda kv: kv[1]):
        if real in wrote:
            writers = list(dict.fromkeys(wrote[real]))
            files[rel] = {"kind": "generated", "by": writers[0], "also": writers[1:]}
            if writers[0] in by_name:
                by_name[writers[0]]["writes"].append(rel)
            for w in writers[1:]:
                if w in by_name:
                    by_name[w]["rewrites"].append(rel)
        elif rel in captured:
            files[rel] = {"kind": "captured", "group": captured[rel][0]}
        else:
            rule = gate.authored_rule(rel, rules)
            files[rel] = ({"kind": "authored", "rule": rule[0]} if rule
                          else {"kind": "unknown"})

    traced = 0
    for g in gens:
        got = reads.get(g["name"])
        if got is None:
            continue                      # a command: its reads are not observed
        mine = set(g["writes"]) | set(g["rewrites"])
        srcs, code = set(), set()
        for mode, real in got:
            if WRITING & set(mode):
                continue
            rel = tracked.get(os.path.realpath(real))
            if rel is None or rel in mine:
                continue
            (code if rel.endswith(".py") else srcs).add(rel)
        g["reads"], g["code"] = sorted(srcs), sorted(code)
        traced += len(srcs)

    groups = decl["captured"]["groups"]
    capt = [{"name": n, "why": grp.get("why", ""), "files": sorted(r for r, (gn, _) in captured.items() if gn == n),
             "stamp": grp.get("stamp"), "no_stamp": grp.get("no_stamp"),
             "upstream": (grp.get("upstream") or {}).get("url") if isinstance(grp.get("upstream"), dict) else None}
            for n, grp in groups.items()]
    authored = []
    for rule in rules:
        mine = sorted(r for r, f in files.items() if f["kind"] == "authored" and f["rule"] == rule[0])
        authored.append({"rule": rule[0], "why": rule[1], "files": mine})

    # DRIFT, ON THE MAP: what the scan finds in the hand-written files - a
    # value said in two or more of them that no source holds - drawn beside
    # the files that say it, with the count in the legend (drift.py).
    from . import config as cfgmod, drift as driftmod
    try:
        found = driftmod.find(cfgmod.load(os.environ.get("WHEREFORE_ROOT") or None))
    except Exception as e:                           # the map is drawn either way; the check says why
        found = {"values": [], "read": 0, "held": 0, "error": f"{type(e).__name__}: {e}"}
    kinds = [f["kind"] for f in files.values()]
    counts = {"files": len(files), "generated": kinds.count("generated"),
              "authored": kinds.count("authored"), "captured": kinds.count("captured"),
              "unknown": kinds.count("unknown"), "generators": len(gens),
              "code": sum(1 for r, f in files.items() if f["kind"] == "authored" and r.endswith(".py")),
              "reads": traced, "failed": len(failures), "drifting": len(found["values"])}
    allow = (cfgmod.load(os.environ.get("WHEREFORE_ROOT") or None).doc.get("drift") or {}).get("allow") \
        if "error" not in found else None
    return {"schema": SCHEMA, "engine": __version__, "repository": name, "counts": counts,
            "generators": gens, "files": files, "captured": capt, "authored": authored,
            "drift": {"values": found["values"], "read": found["read"], "held": found["held"],
                      "allow": allow, "error": found.get("error")}}


def summary(m, wrote_to=None):
    c = m["counts"]
    s = (f"{c['files']} files: {c['generated']} generated by {c['generators']} "
         f"{'script' if c['generators'] == 1 else 'scripts'}, {c['authored']} written, not built, "
         f"{c['captured']} captured")
    if c["unknown"]:
        s += f", {c['unknown']} unclassified"
    s += f"; {c['reads']} {'read' if c['reads'] == 1 else 'reads'} traced"
    if c["failed"]:
        s += f"; {c['failed']} {'generator' if c['failed'] == 1 else 'generators'} FAILED"
    if c.get("drifting"):
        s += f"; {c['drifting']} {'value drifts' if c['drifting'] == 1 else 'values drift'}"
    if wrote_to:
        s += f"; wrote {wrote_to}"
    return s


# ── the page ────────────────────────────────────────────────────────────────

THEME_BLOCKS = re.compile(r":root \{.*?\n\}\n@media \(prefers-color-scheme: dark\) \{\n  :root \{.*?\n  \}\n\}\n", re.S)


def themed(page, theme):
    """The page with its own light and dark palettes replaced by `theme`, a stylesheet's text.

    THE MAP IN A CORPUS'S OWN COLOURS. A corpus that holds its brand in one
    place - every colour and face a custom property the site builds from its
    tokens - should not carry a second palette typed into the engine. `--theme`
    takes one or more stylesheets and puts them where the page's palettes were,
    so the page's rules read the corpus's properties: --ground, --surface,
    --line, --ink, --muted, --accent, --accent-ink, --lit, --gen, --capt,
    --hand, --unk, --bad, --mark, --em, --em-mark, --sans, --serif, --mono
    and --r. A theme that leaves one out leaves that rule with no value, so set
    them all, by value or as var() of what the corpus already has.

    WHAT WRITES AND WHAT MARKS. --accent is what the page writes with: the
    traced lines, a chosen card's border, links, focus. --mark is what it marks
    with: the bar down a script's card. --em and --em-mark are the headline's
    word, "what": its colour, and the highlighter behind it, none by default.
    A brand whose accent reads on its ground sets all three to it; a brand
    whose accent is a highlighter - lime on white - writes with its ink and
    marks with the accent, and puts the accent behind the word."""
    if not theme:
        return page
    if not THEME_BLOCKS.search(page):
        raise SystemExit("the page's palettes were not where --theme puts the theme: this is a bug in the engine")
    return THEME_BLOCKS.sub(lambda _: theme.rstrip("\n") + "\n", page, count=1)


def page(m, home=None):
    """One self-contained HTML page: no font, script or style from anywhere else.
    `home` is (url, words or None): a way back to the site the map is of."""
    data = json.dumps(m, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    title = f"What builds what: {m['repository']}"
    back = ""
    if home:
        url, words = home
        back = f' <a class="home" href="{html.escape(url, quote=True)}">\u2190 {html.escape(words or m["repository"])}</a>'
    return (PAGE.replace("@@TITLE@@", html.escape(title))
                .replace("@@HOME@@", back)
                .replace("@@REPO@@", html.escape(m["repository"]))
                .replace("@@ENGINE@@", html.escape(m["engine"]))
                .replace("@@DATA@@", data))


# ── the command ─────────────────────────────────────────────────────────────

def parse(args):
    out = {"html": DEFAULT_HTML, "json": None, "theme": [], "home": None}
    it = iter(args)
    while True:
        a = next(it, None)
        if a is None:
            break
        if a in ("-h", "--help"):
            print(USAGE + "\n\n" + __doc__.split("\n\n")[1])
            return 0
        if a == "--theme":
            try:
                out["theme"].append(next(it))
            except StopIteration:
                print(f"::error::--theme takes a stylesheet\n{USAGE}")
                return 2
        elif a == "--home":
            # --home URL [WORDS]: the map links back to the site it is of, in
            # WORDS, or in the corpus's name. Next arg that is not an option.
            rest = list(it)
            if not rest or rest[0].startswith("--"):
                print(f"::error::--home takes an address, and may take the words to show for it\n{USAGE}")
                return 2
            out["home"] = (rest[0], rest[1] if len(rest) > 1 and not rest[1].startswith("--") else None)
            it = iter(rest[2 if out["home"][1] else 1:])
        elif a in ("--html", "--json"):
            try:
                out[a[2:]] = next(it)
            except StopIteration:
                print(f"::error::{a} takes a path{' (or - for stdout)' if a == '--json' else ''}\n{USAGE}")
                return 2
        else:
            print(f"::error::wherefore graph does not take {a}\n{USAGE}")
            return 2
    if out["html"] == "-" and out["json"] == "-":
        print(f"::error::only one of --html and --json can go to stdout\n{USAGE}")
        return 2
    return out


def main(cfg, args):
    opts = parse(args)
    if isinstance(opts, int):
        return opts
    configure(cfg)
    from . import generators as G
    tracked, wrote, reads, failures = observe()
    m = model(cfg.name, tracked, wrote, reads, failures)
    theme = ""
    for t in opts["theme"]:
        path = pathlib.Path(t)
        if not path.is_absolute():
            path = pathlib.Path.cwd() / path
        if not path.is_file():
            print(f"::error::--theme {t}: no such stylesheet")
            return 2
        theme += path.read_text(encoding="utf-8")
    to_stdout = "-" in (opts["html"], opts["json"])
    say = sys.stderr if to_stdout else sys.stdout
    written = []
    for kind, text in (("html", lambda: themed(page(m, opts["home"]), theme)),
                       ("json", lambda: json.dumps(m, indent=1, ensure_ascii=False) + "\n")):
        dest = opts[kind]
        if dest is None:
            continue
        if dest == "-":
            sys.stdout.write(text())
            continue
        path = pathlib.Path(dest)
        if not path.is_absolute():
            path = pathlib.Path.cwd() / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text(), encoding="utf-8")
        written.append(dest)
    for who, err in failures:
        print(f"::error::{who} failed while the graph ran it, so what it reads and makes "
              f"is not all here:\n{err}", file=say)
    print(summary(m, " and ".join(written) or None), file=say)
    return 1 if failures else 0


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="generator" content="wherefore @@ENGINE@@">
<title>@@TITLE@@</title>
<style>
:root {
  --ground: #F7F6F2; --surface: #FFFFFF; --line: #D9D7D0; --ink: #17181B; --muted: #5C5F66;
  --accent: #3F6B00; --accent-ink: #FFFFFF; --lit: #EEF5E1; --gen: #6E9F1A; --capt: #B8860B;
  --hand: #5B7397; --unk: #B3261E; --bad: #B3261E;
  --mark: var(--accent); --em: var(--accent); --em-mark: transparent;
  --sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --serif: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
  --r: 10px; color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root {
    --ground: #0B0C0E; --surface: #15171B; --line: #2E3138; --ink: #EDEBE6; --muted: #A3A6AD;
    --accent: #C3FF0F; --accent-ink: #0B0C0E; --lit: #1C2212; --gen: #C3FF0F; --capt: #F4D35E;
    --hand: #8FA3BF; --unk: #FF8A80; --bad: #FF8A80;
    --mark: var(--accent); --em: var(--accent); --em-mark: transparent; color-scheme: dark;
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--ground); color: var(--ink); font: 15px/1.55 var(--sans); overflow-wrap: anywhere; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 0 16px; }
header.wrap { padding-top: 28px; padding-bottom: 8px; }
.mark { font: italic 20px/1 var(--serif); color: var(--muted); }
.home { font: 14px/1 var(--sans); color: var(--muted); margin-left: 14px; }
h1 { font: 400 clamp(32px, 6vw, 54px)/1.05 var(--serif); margin: 16px 0 10px; }
h1 em { color: var(--em); background: var(--em-mark); font-style: italic; padding: 0 .06em; margin: 0 -.06em; border-radius: .08em; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
.lede { color: var(--muted); max-width: 64ch; margin: 0 0 20px; }
code { font: 0.9em var(--mono); }
.summary { display: grid; gap: 10px; margin-bottom: 18px; }
.bar { display: flex; height: 14px; border-radius: 999px; overflow: hidden; background: var(--line); }
.bar span { display: block; height: 100%; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 20px; color: var(--muted); }
.legend b { color: var(--ink); font-weight: 600; font-variant-numeric: tabular-nums; }
.dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 6px; vertical-align: 1px; }
.k-generated { background: var(--gen); } .k-captured { background: var(--capt); }
.k-authored { background: var(--hand); } .k-unknown { background: var(--unk); } .k-drift { background: var(--capt); }
.failures { border: 1px solid var(--bad); border-radius: var(--r); padding: 12px 14px; margin-bottom: 18px; }
.failures h2 { font: 600 15px var(--sans); color: var(--bad); margin: 0 0 6px; }
.failures pre { font: 12px/1.5 var(--mono); white-space: pre-wrap; overflow-wrap: anywhere; margin: 4px 0 10px; color: var(--muted); }
.trace { position: sticky; top: 0; z-index: 5; background: var(--ground); padding: 10px 0; border-bottom: 1px solid var(--line); margin-bottom: 14px; }
.trace p { margin: 0; min-height: 3em; }
.trace .hint { color: var(--muted); }
.trace b { color: var(--accent); font-weight: 600; }
button { font: inherit; color: inherit; }
.clear { font: 500 14px var(--sans); color: var(--muted); background: none; border: 1px solid var(--line); border-radius: 999px; padding: 0 16px; margin-top: 6px; cursor: pointer; min-height: 44px; }
button:focus-visible, summary:focus-visible, a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.map { position: relative; display: grid; grid-template-columns: 1fr 1.1fr 1fr; gap: 16px 64px; align-items: start; }
.col { min-width: 0; display: grid; gap: 8px; align-content: start; position: relative; z-index: 1; }
.col h2 { font: 500 12px/1.4 var(--mono); letter-spacing: .1em; text-transform: uppercase; color: var(--muted); margin: 0 0 4px; }
.col h2 small { display: block; text-transform: none; letter-spacing: 0; font: 13px/1.4 var(--sans); margin-top: 2px; }
.col .none { color: var(--muted); font-size: 14px; margin: 0; }
svg.lines { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; z-index: 0; overflow: visible; }
svg.lines path { fill: none; stroke: var(--line); stroke-width: 1.2; }
svg.lines path.on { stroke: var(--accent); stroke-width: 1.8; }
svg.lines path.chain { stroke-dasharray: 4 4; }
.node { text-align: left; width: 100%; min-height: 44px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--r); padding: 9px 12px; cursor: pointer; display: grid; gap: 2px; transition: opacity .15s, border-color .15s; }
.node .p { font: 13px/1.35 var(--mono); }
.node .n { font: 12px var(--mono); color: var(--muted); font-variant-numeric: tabular-nums; }
.node .d { font-size: 13px; color: var(--muted); line-height: 1.4; }
.node .kind { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 7px; vertical-align: 1px; }
.node.script { border-left: 3px solid var(--mark); }
.node.script .p { font-weight: 600; }
.node.failed { border-color: var(--bad); }
.node .bad { color: var(--bad); }
.map.picking .node { opacity: .3; }
.map.picking .node.on { opacity: 1; border-color: var(--accent); }
.map.picking .node.self { background: var(--lit); }
section.more { margin-top: 44px; }
section.more h2 { font: 400 28px/1.15 var(--serif); margin: 0 0 6px; }
section.more > p { color: var(--muted); max-width: 64ch; margin: 0 0 16px; }
.rules { display: grid; gap: 8px; }
details.rule { background: var(--surface); border: 1px solid var(--line); border-radius: var(--r); padding: 0 14px; }
details.rule summary { cursor: pointer; display: flex; gap: 12px; align-items: baseline; list-style: none; padding: 12px 0; min-height: 44px; }
details.rule summary::-webkit-details-marker { display: none; }
details.rule summary .p { font: 13px var(--mono); flex: none; max-width: 45%; }
details.rule summary .w { color: var(--muted); font-size: 14px; flex: 1; min-width: 0; }
details.rule summary .c { font: 12px var(--mono); color: var(--muted); flex: none; font-variant-numeric: tabular-nums; }
details.rule .body { padding: 0 0 12px; }
details.rule .body p { margin: 0 0 6px; color: var(--muted); font-size: 14px; }
details.rule ul { margin: 6px 0 0; padding-left: 18px; font: 12px/1.6 var(--mono); color: var(--muted); columns: 2 260px; }
details.rule a { color: var(--accent); }
.showall { font: 500 14px var(--sans); background: none; border: 1px solid var(--line); border-radius: 999px; padding: 0 16px; cursor: pointer; justify-self: start; min-height: 44px; }
footer.wrap { color: var(--muted); font-size: 13px; padding-top: 44px; padding-bottom: 32px; }
footer.wrap p { max-width: 70ch; margin: 0; }
@media (max-width: 899px) {
  .map { grid-template-columns: 1fr; gap: 26px; }
  svg.lines { display: none; }
  details.rule summary { flex-wrap: wrap; }
  details.rule summary .p { max-width: 100%; }
  details.rule summary .w { flex-basis: 100%; }
}
@media (prefers-reduced-motion: reduce) { .node { transition: none; } }
</style>
</head>
<body>
<header class="wrap">
  <span class="mark">Wherefore</span>@@HOME@@
  <h1>What builds <em>what</em></h1>
  <p class="lede">Every tracked file in <code>@@REPO@@</code>, how it is made, and what reads what. Sources on the left, the scripts that read them in the middle, everything they make on the right. Choose anything to trace its chain.</p>
</header>
<main class="wrap">
  <div class="summary" id="summary"></div>
  <div id="failures"></div>
  <div class="trace" id="trace" aria-live="polite"></div>
  <div class="map" id="map"></div>
  <section class="more">
    <h2>Captured, and stamped</h2>
    <p>Files nobody can regenerate here, like a render or a copy from elsewhere. Each is stamped with what it was made from, so the gate knows when it is out of date.</p>
    <div class="rules" id="captured"></div>
  </section>
  <section class="more">
    <h2>Written, not built, with a reason</h2>
    <p>Everything else is written - by a person, or by an agent - and never built: nothing regenerates it, so it is current only while someone keeps it so. Every rule that says so carries its reason.</p>
    <div class="rules" id="hand"></div>
  </section>
  <section class="more" id="driftSec">
    <h2>Drift</h2>
    <p>A value said by hand in two or more files that no source holds: a copy nobody is keeping current. Each is drawn beside the files that say it, and <code>wherefore check drift</code> holds the count to what the corpus allows, so it is seen, and seen shrinking.</p>
    <div class="rules" id="drift"></div>
  </section>
  <section class="more" id="unknownSec" hidden>
    <h2>Unclassified</h2>
    <p>Nothing wrote these during the run and nothing declares them. The gate fails each one.</p>
    <div class="rules" id="unknown"></div>
  </section>
</main>
<footer class="wrap"><p>Made by <code>wherefore graph</code> (Wherefore @@ENGINE@@): every generator run once with the engine's observer recording what each opened and wrote, every tracked file classified the way the gate classifies it, and the tree put back as it was. Nothing on this page is written; all of it is built.</p></footer>
<script>
const M = @@DATA@@;
const $ = s => document.querySelector(s);
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const plural = (n, one, many) => `${n} ${n === 1 ? one : (many || one + "s")}`;
const folder = p => p.includes("/") ? p.slice(0, p.lastIndexOf("/")) : "";
const shown = f => f ? f + "/" : "the top level";
const label = g => g.files.length === 1 ? g.files[0] : shown(g.folder);
const HINT = "Choose a source to see everything that changes with it, or a file to see where it comes from.";

// Groups: files by folder, generated ones by the script that first wrote them.
const G = {}, add = (id, kind, fold, owner, file, extra) => {
  const g = G[id] || (G[id] = Object.assign({id, kind, folder: fold, owner, files: [], also: []}, extra || {}));
  if (!g.files.includes(file)) g.files.push(file);
  return g;
};
const groupOf = rel => {
  const f = M.files[rel];
  if (!f) return null;
  if (f.kind === "generated") return `generated:${f.by}:${folder(rel)}`;
  if (f.kind === "captured") return `captured:${f.group}:${folder(rel)}`;
  return `${f.kind}::${folder(rel)}`;
};
// Generated groups hold every file a script made; a source group holds only the
// files some script was seen reading, so a count says what is read, not what is near.
for (const [rel, f] of Object.entries(M.files)) {
  if (f.kind !== "generated") continue;
  const g = add(groupOf(rel), f.kind, folder(rel), f.by, rel);
  for (const w of f.also || []) if (!g.also.includes(w)) g.also.push(w);
}
for (const s of M.generators) for (const rel of s.reads || []) {
  const f = M.files[rel];
  if (f.kind !== "generated") add(groupOf(rel), f.kind, folder(rel), f.group || "", rel);
}
const upstream = Object.fromEntries(M.captured.map(c => [c.name, c.upstream]));
const S = M.generators.map(g => {
  const id = "script:" + g.name, srcs = new Set(), chain = new Set(), outs = new Set();
  for (const rel of g.writes) outs.add(groupOf(rel));
  for (const rel of g.reads || []) (M.files[rel].kind === "generated" ? chain : srcs).add(groupOf(rel));
  return Object.assign({}, g, {id, srcs: [...srcs], chain: [...chain], outs: [...outs]});
});

function summary() {
  const c = M.counts, t = Math.max(c.files, 1), w = n => `${(100 * n / t).toFixed(3)}%`;
  $("#summary").innerHTML = `
    <div class="bar" role="img" aria-label="${c.generated} generated, ${c.captured} captured, ${c.authored} written, not built${c.unknown ? `, ${c.unknown} unclassified` : ""}, of ${c.files} files">
      <span class="k-generated" style="width:${w(c.generated)}"></span><span class="k-captured" style="width:${w(c.captured)}"></span><span class="k-authored" style="width:${w(c.authored)}"></span><span class="k-unknown" style="width:${w(c.unknown)}"></span></div>
    <div class="legend"><span><b>${c.files}</b> files, <b>${c.generators}</b> ${c.generators === 1 ? "script" : "scripts"}</span>
      <span><i class="dot k-generated"></i><b>${c.generated}</b> generated by a script</span>
      <span><i class="dot k-captured"></i><b>${c.captured}</b> captured and stamped</span>
      <span><i class="dot k-authored"></i><b>${c.authored}</b> written, not built, with a reason</span>
      ${c.unknown ? `<span><i class="dot k-unknown"></i><b>${c.unknown}</b> unclassified</span>` : ""}
      <span><b>${c.reads}</b> ${c.reads === 1 ? "read" : "reads"} traced</span>
      <span><i class="dot k-drift"></i><b>${c.drifting || 0}</b> ${c.drifting === 1 ? "value drifts" : "values drift"}${M.drift && M.drift.allow != null ? `, ${M.drift.allow} allowed` : ""}</span></div>`;
  const bad = M.generators.filter(g => g.failure);
  $("#failures").innerHTML = bad.length ? `<div class="failures" role="alert"><h2>${plural(bad.length, "generator")} failed, so what ${bad.length === 1 ? "it reads and makes is" : "they read and make is"} not all here</h2>${
    bad.map(g => `<code>${esc(g.name)}</code><pre>${esc(g.failure)}</pre>`).join("")}</div>` : "";
}

function map() {
  const srcs = Object.values(G).filter(g => g.kind !== "generated" && S.some(s => s.srcs.includes(g.id)))
    .sort((a, b) => a.folder.localeCompare(b.folder));
  const outs = S.flatMap(s => s.outs.map(id => G[id]));
  const node = g => `<button type="button" class="node" data-id="${esc(g.id)}"><span class="p"><i class="kind k-${g.kind}"></i>${esc(label(g))}</span>
    <span class="n">${plural(g.files.length, "file")}${g.kind === "captured" ? " · captured" : ""}${g.kind === "generated" ? " · by " + esc(g.owner) : ""}</span></button>`;
  const made = s => s.outs.reduce((n, id) => n + G[id].files.length, 0);
  const reads = s => s.reads === null ? "reads not observed: a command, not Python"
    : `reads ${plural(s.srcs.length, "source folder")}${s.chain.length ? `, and ${plural(s.chain.length, "folder")} another script made` : ""}`;
  $("#map").innerHTML = `<svg class="lines" id="lines" aria-hidden="true"></svg>
    <div class="col"><h2>Sources<small>written or captured, read by a script</small></h2>${srcs.map(node).join("") || `<p class="none">No script was seen reading one.</p>`}</div>
    <div class="col"><h2>Scripts<small>run on every build, twice, and compared</small></h2>${S.map(s =>
      `<button type="button" class="node script${s.failure ? " failed" : ""}" data-id="${esc(s.id)}"><span class="p">${esc(s.name)}</span><span class="d">${esc(s.makes)}</span>
       <span class="n">${reads(s)} · makes ${plural(made(s), "file")}${s.rewrites.length ? `, and rewrites ${s.rewrites.length} another script made` : ""}${s.failure ? ` · <span class="bad">failed</span>` : ""}</span></button>`).join("")}</div>
    <div class="col"><h2>What they make<small>generated, rebuilt and compared on every push</small></h2>${outs.map(node).join("") || `<p class="none">Nothing generated yet.</p>`}</div>`;
  $("#map").onclick = e => { const b = e.target.closest(".node"); if (b) pick(b.dataset.id === picked ? null : b.dataset.id); };
}

const fwd = {}, back = {};
for (const s of S) {
  const edge = (a, b) => { (fwd[a] = fwd[a] || []).push(b); (back[b] = back[b] || []).push(a); };
  s.srcs.forEach(g => edge(g, s.id)); s.outs.forEach(g => edge(s.id, g)); s.chain.forEach(g => edge(g, s.id));
}
const reach = (start, edges) => { const seen = new Set([start]), q = [start];
  while (q.length) for (const n of edges[q.shift()] || []) if (!seen.has(n)) { seen.add(n); q.push(n); } return seen; };

let picked = null;
function pick(id) {
  picked = id;
  const mapEl = $("#map");
  mapEl.querySelectorAll(".node").forEach(n => { n.classList.remove("on", "self"); n.setAttribute("aria-pressed", "false"); });
  if (!id) { mapEl.classList.remove("picking"); $("#trace").innerHTML = `<p class="hint">${HINT}</p>`; draw(); return; }
  const down = reach(id, fwd), up = reach(id, back), all = new Set([...down, ...up]);
  mapEl.classList.add("picking");
  mapEl.querySelectorAll(".node").forEach(n => { if (all.has(n.dataset.id)) n.classList.add("on");
    if (n.dataset.id === id) { n.classList.add("self"); n.setAttribute("aria-pressed", "true"); } });
  const files = ids => [...ids].filter(x => G[x] && G[x].kind === "generated").reduce((n, x) => n + G[x].files.length, 0);
  const scripts = ids => [...ids].filter(x => x.startsWith("script:")).map(x => x.slice(7));
  let text;
  if (id.startsWith("script:")) {
    const s = S.find(s => s.id === id), n = s.srcs.reduce((k, g) => k + G[g].files.length, 0);
    text = `<b>${esc(s.name)}</b> ${s.reads === null ? "is a command, so its reads are not observed;" : `reads ${plural(n, "source file")} and`} makes ${plural(files(new Set(s.outs)), "file")}. ${esc(s.makes)}.`;
  } else if (G[id].kind === "generated") {
    const g = G[id], from = [...up].filter(x => G[x] && G[x].kind !== "generated").map(x => label(G[x]));
    const owner = S.find(s => s.name === g.owner);
    text = `<b>${esc(label(g))}</b>: ${plural(g.files.length, "file")} made by ${esc(g.owner)}, from ${from.length ? "sources " + esc(from.join(", ")) : owner && owner.reads === null ? "sources not observed (a command, not Python)" : "its code and the engine alone"}.${g.also.length ? ` Also rewritten by ${esc(g.also.join(", "))}.` : ""}`;
  } else {
    const g = G[id], ss = scripts(down), n = files(down);
    const named = ss.length > 8 ? ss.slice(0, 8).join(", ") + `, and ${ss.length - 8} more` : ss.join(", ");
    const up = g.kind === "captured" && upstream[g.owner] ? ` It is a copy of ${esc(upstream[g.owner])}, checked by <code>wherefore check upstream</code>.` : "";
    text = `Change <b>${esc(label(g))}</b> and ${plural(ss.length, "script")} rebuild${ss.length === 1 ? "s" : ""} <b>${plural(n, "file")}</b>${ss.length ? ": " + esc(named) : ""}.${up}`;
  }
  $("#trace").innerHTML = `<p>${text}</p><button type="button" class="clear" id="clear">Clear</button>`;
  $("#clear").onclick = () => pick(null);
  draw(all);
}

function draw(lit) {
  const svg = $("#lines"), mapEl = $("#map");
  if (!svg || getComputedStyle(svg).display === "none") return;
  const box = mapEl.getBoundingClientRect();
  const at = (id, side) => { const el = [...mapEl.querySelectorAll(".node")].find(n => n.dataset.id === id); if (!el) return null;
    const r = el.getBoundingClientRect(); return [(side === "r" ? r.right : r.left) - box.left, r.top - box.top + r.height / 2]; };
  const curve = (a, b) => { const dx = Math.max(30, (b[0] - a[0]) / 2); return `M${a[0]},${a[1]} C${a[0] + dx},${a[1]} ${b[0] - dx},${b[1]} ${b[0]},${b[1]}`; };
  let paths = "";
  for (const s of S) {
    const on = g => lit && lit.has(g) && lit.has(s.id);
    for (const g of s.srcs) { const a = at(g, "r"), b = at(s.id, "l"); if (a && b) paths += `<path class="${on(g) ? "on" : ""}" d="${curve(a, b)}"/>`; }
    for (const g of s.outs) { const a = at(s.id, "r"), b = at(g, "l"); if (a && b) paths += `<path class="${on(g) ? "on" : ""}" d="${curve(a, b)}"/>`; }
    for (const g of s.chain) { const a = at(g, "l"), b = at(s.id, "r"); if (a && b) paths += `<path class="chain ${on(g) ? "on" : ""}" d="${curve(b, a)}"/>`; }
  }
  svg.setAttribute("viewBox", `0 0 ${box.width} ${box.height}`);
  svg.innerHTML = paths;
}

function rules() {
  const link = u => u ? ` Copied from <a href="${esc(u)}">${esc(u)}</a>, checked by <code>wherefore check upstream</code>.` : "";
  $("#captured").innerHTML = M.captured.length ? M.captured.map(c => `<details class="rule"><summary><span class="p">${esc(c.name)}</span>
    <span class="w">${esc(c.why)}</span><span class="c">${plural(c.files.length, "file")}</span></summary>
    <div class="body"><p>${c.stamp ? `Stamped <code>${esc(c.stamp)}</code>.` : c.no_stamp ? `No stamp: ${esc(c.no_stamp)}` : "No stamp yet."}${link(c.upstream)}</p>
    <ul>${c.files.map(f => `<li>${esc(f)}</li>`).join("")}</ul></div></details>`).join("") : `<p>None.</p>`;
  const all = M.authored.filter(r => r.files.length).sort((a, b) => b.files.length - a.files.length);
  const show = n => {
    $("#hand").innerHTML = all.slice(0, n).map(r => `<details class="rule"><summary><span class="p">${esc(r.rule)}</span><span class="w">${esc(r.why)}</span>
      <span class="c">${r.files.length}</span></summary><div class="body"><ul>${r.files.map(f => `<li>${esc(f)}</li>`).join("")}</ul></div></details>`).join("")
      + (all.length > n ? `<button class="showall" type="button" id="showall">Show all ${all.length} rules</button>` : "");
    const b = $("#showall"); if (b) b.onclick = () => show(all.length);
  };
  show(8);
  const D = M.drift || {values: []};
  $("#drift").innerHTML = D.error ? `<p>Not read: <code>${esc(D.error)}</code></p>`
    : D.values.length ? D.values.map(v => `<details class="rule"><summary><span class="p">${esc(v.value)}</span>
      <span class="w">${esc(v.says.replace("{}", v.value))}</span><span class="c">${plural(v.files.length, "file")}, ${v.count}x</span></summary>
      <div class="body"><ul>${v.files.map(f => `<li>${esc(f)}</li>`).join("")}</ul></div></details>`).join("")
      + `<p class="none">${plural(D.values.length, "value")} held by no source, in ${plural(D.read, "hand-written file")} read${D.allow != null ? `; ${D.allow} allowed` : ""}.</p>`
    : `<p>None: every value said by hand in two or more of ${plural(D.read, "hand-written file")} is held by a source.</p>`;
  const unknown = Object.keys(M.files).filter(r => M.files[r].kind === "unknown");
  if (unknown.length) { $("#unknownSec").hidden = false;
    $("#unknown").innerHTML = `<details class="rule" open><summary><span class="w">${plural(unknown.length, "file")}</span></summary><div class="body"><ul>${unknown.map(f => `<li>${esc(f)}</li>`).join("")}</ul></div></details>`; }
}

summary(); map(); rules(); pick(null);
let t; addEventListener("resize", () => { clearTimeout(t); t = setTimeout(() => pick(picked), 120); });
</script>
</body>
</html>
"""
