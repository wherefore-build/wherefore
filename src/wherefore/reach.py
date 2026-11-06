#!/usr/bin/env python3
"""Change the spec, and the files a supplier receives must change.

IN WHEREFORE. Moved from chaotic-pendulums-co's checks/spec_reaches_the_shop.py,
its words kept. What it watches, which facts it moves and by how much, what is
exempt and which facts must move which files are the client's now, in
wherefore.json `reach`. A source read by the `params` adapter is swept as
the pendulum's spec always was - every nominal, value and band in the named
families, sized in the object's unit - and one read by `leaves` has every
scalar moved: a number by a nudge big enough to show, a string by a marker
appended, because a company whose facts are a name and a price has facts too.
A comparison is the gate's, by the client's declared rules, so a workbook is
its cells and a solid its numbers here exactly as there.

This is the check the bore-19 evaluation asked for a month ago and never got.

Its report said a spec edit does not reach the shop, and it was still true on
V10: applying a full geometry change to spec/mk3.params.json - the fork from
210 to 216, every bore index from 16 to 19 - regenerated every DXF and every
STEP BYTE-IDENTICAL. build_dxf.py opened `H=114; W=38` and drilled at H-16 and
H-194; build_step.py called rounded_rect(38,210,3). The spec was decorative
with respect to the only files anybody cuts metal from.

Every drift job passed throughout, and could not have done otherwise: a drift
job regenerates a file and compares it with the one committed, so a generator
holding its own copy of a number reproduces it perfectly, for ever. The whole
harness was pointed at self-consistency and none of it at the binding.

So this asks the opposite question. It moves a number in the spec, regenerates,
and REQUIRES the shipped files to move - then puts the spec back. A pass means
the pipeline carries a change; a failure means the spec is decoration again.

It runs the edits below one at a time, because "something moved" is too weak:
a generator can bind the fork's length and still hold its own copy of the bore
index, and one probe that changes both would not notice.

IT COVERS THE BRAND ASSETS TOO, and it did not always. It watched the DXF, the
STEP and the BOM - the files a supplier receives - and that is where the fork
was bound and where the binding was proved. Meanwhile wmfinal.py held
`FORK_R = 38.0/210.0` and `BORE_IN = 16.0/210.0` and cp_mark.py held
`HOUSE_POSE = (-12.0, 130.0)`, and every one of those is the object's geometry
written down a second time, in the files the company shows people. (The pose
is derived from the fold construction now and comes out at 132 - and for a
release after that, the hero and the sketches went on drawing their own 130,
which checks/mark_lines_up.py now measures.) A probe that
watches half the repo proves the spec reaches half the repo. So the watched set
is now the supplier files AND the drawn brand, and the exemptions that used to
read "the brand elevations; not a shipped file" are gone, because that sentence
stopped being true the moment this check could see them.

WHICH GENERATORS IT RUNS: all of them, from checks/generators.py, rather than a
second list kept here. That list is the coverage gate's, it is the one the gate
proves complete on every run, and a probe that regenerates a DIFFERENT set from
the gate would quietly stop probing whatever the two disagreed about.

AND EVERY TOLERANCE, since V17. The sweep moved nominals and values and
nothing else, so a band was never probed: "+/-0.01" on the seat, "(+0.1/0)" on
the counterbore, "+/-0.05" on the pitch and "D6 H7" on the shoulder hole were
typed into build_bom.py and build_dxf.py beside a spec that held the same
numbers, and the probe could not tell. Every `tol` is widened now, one at a
time, like any other number - the widened band has to reach a file too. The
geometric controls are ordinary `value` params in the tolerances family, so
they were always going to be swept; the bands beside the dimensions were not.

Usage:  wherefore check reach
        wherefore check reach --only PATTERN [PATTERN ...]
                probe only the parameters whose dotted name matches a pattern
                (fnmatch) - the baseline, the restore and the verdict are the
                same; it is a way to ask about one number without the rest
"""
import fnmatch
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import textwrap

from . import compare as _C
from . import generators as G
from . import sources as _Src

# The client's, set by configure(). See the module docstring.
ROOT = None
SPEC = None             # the source the probe moves, as a path
WATCHED = []            # [(path, the name a message gives it)]
EXCLUDE = []            # substrings of a path that is never watched
COMPARE = _C.Comparators()
AUDIENCE = "a reader"
SUCCESS = "every fact probed reaches something {audience} receives"


# EVERY numeric parameter is probed, not a chosen few.
#
# The hand-picked five were all numbers that were already wired, so they all
# passed while two parameters added in the same release - the bearing seat's
# depth and its through pilot - reached nothing at all. The drawings gained a
# note saying "⌀19.03 x 5.95 pocket over a ⌀17 pilot" and the DXF went on
# drawing one circle and the solids went on modelling a through bore. Nothing
# could catch it: a check compares things that are wired to each other, and a
# parameter nothing consumes cannot disagree with anything.
#
# So the question became: is every number in the spec actually consumed? A
# parameter that reaches no shipped file is either dead or a lie, and both are
# worth failing on the day they appear.
#
# WHAT THIS STILL CANNOT SEE, and it is worth being plain about: it proves a
# number is CONSUMED, not that it is consumed CORRECTLY. The seat's depth and
# its pilot both reached a shipped file the day they were added - into the
# note text, which now read "⌀19.03 x 5.95 pocket over a ⌀17 pilot" beside a
# drawing with one circle in it and a solid with a through bore. A probe cannot
# tell prose from geometry. Only reading the drawing does that.

# Parameters that legitimately reach no supplier file, each with the reason.
# This list is the honest part of the check: everything on it is a deliberate
# exemption someone has to justify, not a silent gap.
EXEMPT = {}


# Parameters PROVEN to reach nothing, which is a defect and not an exemption.
#
# The difference between this and EXEMPT is the whole point of having two
# lists. An EXEMPT entry says "this correctly reaches no file, and here is
# why". An entry here says "this reaches no file and somebody has to decide
# what to do about it" - it is reported, loudly, on every run, and it does not
# pass quietly as an exemption would. Putting a dead parameter in EXEMPT is how
# a dead parameter lives forever.
UNCONSUMED = {}


# (what it is, where it lives, what must move because of it, and the files that
# are what must move)
#
# THIS TABLE WAS NEVER READ. It began as the five hand-picked probes, each with
# a nudge of its own - a NUDGE and not a target, since "set the fork to 216"
# became a no-op the release the fork reached 216 - and when the sweep below
# took over every parameter, these five included, nothing read the table
# again. The sweep passes a parameter the moment ANYTHING moves, so "the fork's
# length reaches both forks" was a comment: build_step_brep.py could hold its
# own blade length, the blade's b-rep solid never follow, and the blade's
# length passed on the sixty other files that did.
#
# So a parameter named here must move ITS files, and each one that does not is
# named. The nudge is the sweep's, as for every other parameter: the old ones
# said nothing it does not, and the counterbore's +1.0 was worse - an
# unassemblable stack that build_drawings.py refuses, where 0.4 redraws the
# sheet.
#
# AND THE TABLE MOVED WITH THE SOURCE. Three of these probed the PIN -
# mark.reference's fork_length, hole and bronze_length - for the parts' solids,
# and that was right for as long as both STEP writers read the pin. They do not
# any more: the profiles, the sheets, the solids and the workbook all draw a
# part's outline from geometry.proportions, so a nudge to the pin moves the MARK
# and is not meant to move a supplier file at all. That is what the pin is:
# spec/check_mark_pin.py holds the two copies in step, and it reports drift
# rather than propagating it, which is exactly why a probe must not be left
# asking the object's question of the mark's parameter. It would pass on the
# logotype and say nothing about the shop.
#
# So each of the three now names the mark it draws, and the object's own
# parameters - the width and the pitch - name the four solids, the four
# profiles, the four sheets and the workbook that follow them.
#
# AND THE CORNER RADIUS IS TWO PARAMETERS SINCE V21, which is why it is two
# rows. It was one, in mark.reference, and it was the object's only copy of R3:
# every made part was profiled from the group that exists to hold a portrait.
# The object's is geometry.proportions.corner_r and reaches what a made part
# reaches; the mark keeps a pinned copy because it draws corners too, and that
# one reaches the mark and must not reach a supplier file. Two rows, and each
# names a different set of files - which is the whole difference between a
# dimension and a drawing of one.
PROBES = []             # [(name, path, what it must reach, [files])]
PUBLISHED = {}          # dotted fact -> the published page that states it, which nothing built need move


def watched():
    """Every file in the watched set, by its repo-relative path.

    Recursive, and keyed by the full relative path rather than the directory's
    own name: brand/views/dark and brand/wordmark/dark are both called "dark",
    and keying on the basename silently collapsed them into one.

    The hand-captured stills under brand/model are excluded. They are not
    regenerated by anything - checks/coverage_gate.py holds them against what
    they were shot from instead - so they can never move under a probe, and
    including them would only slow the copy down.
    """
    out = {}
    for d, alias in WATCHED:
        if d.is_file():
            out[alias or str(d.relative_to(ROOT))] = d
            continue
        for f in sorted(d.rglob("*")):
            if f.is_file() and not any(x in str(f) for x in EXCLUDE):
                out[str(f.relative_to(ROOT))] = f
    return out


def snapshot(into):
    for rel, f in watched().items():
        dst = into / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dst)


def moved(against):
    """Which watched files differ from the snapshot.

    NOT BY BYTES FOR A SOLID, and the argument is not this file's - it is
    already written out in checks/coverage_gate.py's same(), which this borrows
    rather than restates: a circle is drawn through sin and cos, libm
    implementations differ by an ulp, and the writer rounds to five decimals,
    which is exactly where an ulp becomes a whole digit. The gate has compared
    a .step and a .dxf that way for as long as it has had the exception. This
    did not, so the baseline pass refused on four STEP files whose numbers were
    identical - "5 lines differ; the largest move is 0.00e+00 mm" - and the
    800-second sweep behind it never ran. It surfaced only when a branch
    changed enough content for the job to stop being skipped, which is to say
    it had been true and unseen for a while.

    The probe is not weakened by it: the smallest nudge this file makes is
    0.04 mm, four hundred times the 1e-4 tolerance, so a parameter that
    reaches a solid still moves it unmistakably.

    The BOM keeps its own comparison below for the same reason in a different
    shape - a workbook records when each member was zipped, so its bytes move
    when nothing in it does. What a supplier reads is the cells.
    """
    out = []
    for rel, f in watched().items():
        was = against / rel
        if not was.exists():
            out.append(rel)
        elif not COMPARE.same(was, f, str(f.relative_to(ROOT))):
            out.append(rel)
    return out


def regenerate(strict=True, wrote=None):
    """Every generator, in the registry's order. See the docstring: one list.

    Returns the generators that REFUSED the spec they were given. If `wrote` is
    a set, every path the generators opened for writing is added to it - by
    the same observer checks/generators.py runs them under, so "what the
    generators write" means the same thing here as it does in the gate.

    Some of them validate rather than just draw. build_handoff.py checks the
    clamp chain and stops - "it clamps 39.4 and the order string buys a 35
    shoulder ... The head will not seat" - and a probe that adds 1.65 mm to the
    stock thickness hands it a pendulum that cannot be assembled. That refusal
    is not a problem with the probe. It is the strongest possible evidence that
    the parameter reached the generator: it read the number, worked out what it
    meant, and would not build the thing. So under a probe a refusal COUNTS as
    a reach, and only the baseline run - where the spec is the committed one
    and any failure is real - is strict.
    """
    refused = []
    env = dict(os.environ)
    log = None
    if wrote is not None:
        log = pathlib.Path(tempfile.mkdtemp(prefix=f"{G.TEMP_PREFIX}probe-")) / "wrote.log"
        env["PYTHONPATH"] = os.pathsep.join(
            [str(G.OBSERVER)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
        env[f"{G.ENV_PREFIX}WRITE_LOG"] = str(log)
        env["WHEREFORE_ROOT"] = str(ROOT)
    try:
        for g in G.GENERATORS:
            if not g.probe:
                continue        # see checks/generators.py: nothing watched moves
            # A `run` generator's writes are seen by the before-and-after
            # picture the gate takes, so "what the generators write" stays one
            # meaning here too; there is nothing to picture when nobody asked.
            if wrote is None:
                r, seen = G.launch(g, env), []
            else:
                with G.watching(g) as seen:
                    r = G.launch(g, env)
                wrote.update(seen)
            if r.returncode:
                if strict:
                    sys.exit(f"::error::{G.name(g)} failed on the committed spec:\n"
                             f"{(r.stderr or r.stdout)[-1500:]}")
                refused.append((G.name(g), ((r.stderr or r.stdout).strip()
                                            .splitlines() or [""])[-1][:110]))
                continue
            if g.stdout_to:
                (ROOT / g.stdout_to).write_text(r.stdout, encoding="utf-8")
                if wrote is not None:
                    wrote.add(os.path.realpath(ROOT / g.stdout_to))
        if log is not None and log.exists():
            wrote.update(log.read_text(encoding="utf-8",
                                       errors="replace").splitlines())
    finally:
        if log is not None:
            shutil.rmtree(log.parent, ignore_errors=True)
    return refused


# ── putting things back ─────────────────────────────────────────────────────
#
# Each probe used to be undone by writing the committed spec back and running
# every generator a second time, purely to restore: two regenerations a probe,
# 86 in a run, and nearly half of them re-making files that had been made from
# that exact spec a moment before. It is undone by COPY now, from a snapshot
# taken once, straight after the baseline regeneration, of every file that
# regeneration wrote.
#
# EVERY file it wrote, not the watched set, and the difference is the manifest
# cycle. The baseline writes twenty-one files outside the watched set -
# spec/manifest.json, brand/index.html, the hand-over pages, DERIVATIONS.txt,
# docs/REVISIONS.md, the web icons - and the manifest among them is READ by
# generators that run earlier in the next pass. Put back only the watched files and a probe's manifest
# survives into the next probe, where it moves REV letters in the drawn views
# on its own: the next parameter "reaches" files it never touched, and a dead
# parameter sweeps past as ok on the strength of its neighbour's change. That
# is the one failure this check must not have, so the restore set is not a list
# anybody keeps. It is what checks/_observe saw the generators open for writing,
# the same record the coverage gate is built on.
#
# The restore point is the state AFTER the baseline pass, not the committed
# tree, and that is deliberate: it is the state every probe is compared from,
# so it is the state every probe must start from.
#
# WHAT IT CANNOT RESTORE: a file a probe writes that the baseline did not. If
# it did not exist after the baseline it is deleted, because it is that probe's
# and nobody else's. If it did exist, there is no copy of it and nothing honest
# to do but stop - putting it back by regenerating is the thing this replaced,
# and silently leaving it is the leak above.

def keep(paths, into):
    """Copy every path under the repo aside. Returns {path: copy or None}.

    None records a path that was written and does not exist any more - a
    generator's scratch, deleted before it finished - so that a probe leaving
    one behind is cleaned up rather than overlooked.
    """
    root = os.path.realpath(ROOT) + os.sep
    kept = {}
    for i, p in enumerate(sorted(paths)):
        if not p.startswith(root):
            continue                    # a temp file or a cache; not the corpus
        if not os.path.isfile(p):
            kept[p] = None
            continue
        dst = into / f"{i:05d}"
        shutil.copyfile(p, dst)
        kept[p] = dst
    return kept


def put_back(kept, wrote, listed):
    """Undo one probe: every kept file to its copy, anything new removed.

    `listed` is every file that existed after the baseline in the directories
    the generators wrote into, which is what tells a new file from an old one.
    """
    root = os.path.realpath(ROOT) + os.sep
    for p, copy in kept.items():
        if copy is None:
            if os.path.isfile(p):
                os.unlink(p)
            continue
        # Bytes, not filecmp: filecmp caches on size and mtime, and a probe
        # that rewrites a file inside one mtime tick would be taken as unmoved.
        data = copy.read_bytes()
        if not os.path.isfile(p) or pathlib.Path(p).read_bytes() != data:
            pathlib.Path(p).write_bytes(data)
    files, dirs = listed
    for p in sorted(wrote):
        if not p.startswith(root) or p in kept:
            continue
        # New only if it is in a directory whose contents were listed and it
        # was not among them. Anywhere else, whether it existed is unknown,
        # and unknown is treated as something that cannot be put back.
        if p in files or os.path.dirname(p) not in dirs:
            sys.exit(f"::error::a probe wrote {os.path.relpath(p, ROOT)}, which "
                     f"the committed spec's regeneration does not write, so "
                     f"there is no copy of it to put back. Restore by copy "
                     f"cannot undo this probe; see `putting things back`.")
        if os.path.isfile(p):
            os.unlink(p)


def listing(paths):
    """(every file beside every written path, the directories listed), now."""
    root = os.path.realpath(ROOT) + os.sep
    dirs = {os.path.dirname(p) for p in paths if p.startswith(root)}
    files = set()
    for d in dirs:
        if os.path.isdir(d):
            files.update(os.path.join(d, f) for f in os.listdir(d))
    return files, dirs


def nudge_params(doc, path, delta):
    """Move one number by delta, and report what it was and what it became.

    A path ending in "tol" WIDENS the band by delta at both ends: a band that
    moves as a whole can keep its width, and a document that prints the width
    alone would not be asked anything."""
    family, group, name = path[:3]
    p = doc[family][group]["params"][name]
    if path[3:] == ("tol",):
        was = list(p["tol"])
        p["tol"] = [round(was[0] - delta, 6), round(was[1] + delta, 6)]
        return "/".join(f"{v:g}" for v in was), "/".join(f"{v:g}" for v in p["tol"])
    key = "value" if "value" in p else "nominal"
    was = p[key]
    p[key] = round(was + delta, 6)
    return f"{was:g}", f"{p[key]:g}"


def sweep_params(doc, families, not_length):
    """Every numeric parameter in the spec, with a nudge big enough to show."""
    # IN THE OBJECT'S UNIT. The nudges were sized in millimetres - 1.7, 0.4, a
    # band widened by 0.04 - and on an inch object 0.4 is ten millimetres: the
    # blade no longer swings clear, the object refuses to build, nothing is
    # drawn, and every sheet reads as a sheet that ignores the number.
    u = 1 / 25.4 if doc.get("units") == "in" else 1.0
    out = []
    for family in families:
        for group, g in doc.get(family, {}).items():
            if not isinstance(g, dict) or "params" not in g:
                continue
            for name, p in g["params"].items():
                v = p.get("nominal", p.get("value"))
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    continue
                # an angle is not a length, and keeps its degrees
                k = 1.0 if name in not_length else u
                out.append((f"{family}.{group}.{name}", (family, group, name),
                            (1.7 if abs(v) > 3 * k else 0.4) * k))
                t = p.get("tol")
                if isinstance(t, list) and len(t) == 2 and any(t):
                    out.append((f"{family}.{group}.{name}.tol",
                                (family, group, name, "tol"),
                                0.04 * (1.0 if name in not_length else u)))
    return out


MARKER = " (probe)"


def sweep_leaves(doc, include, exclude):
    """Every scalar a `leaves` source holds, by dotted path, that `include`
    names and `exclude` does not (fnmatch): a number, nudged, or a string,
    marked. A boolean has no nudge that means anything, and is not moved."""
    out = []
    for dotted, v in _Src.leaves(doc):
        if not any(fnmatch.fnmatchcase(dotted, p) for p in include):
            continue
        if any(fnmatch.fnmatchcase(dotted, p) for p in exclude):
            continue
        if isinstance(v, bool) or v is None:
            continue
        if isinstance(v, (int, float)):
            out.append((dotted, tuple(dotted.split(".")),
                        1 if isinstance(v, int) else max(abs(v) * 0.1, 0.1)))
        elif isinstance(v, str):
            out.append((dotted, tuple(dotted.split(".")), MARKER))
    return out


def nudge_leaves(doc, path, delta):
    """Move one scalar: a number by delta, a string by the marker."""
    node = doc
    for p in path[:-1]:
        node = node[int(p)] if isinstance(node, list) else node[p]
    key = int(path[-1]) if isinstance(node, list) else path[-1]
    was = node[key]
    if isinstance(was, str):
        node[key] = was + delta
        return repr(was), repr(node[key])
    node[key] = round(was + delta, 6) if isinstance(was, float) else was + delta
    return f"{was:g}", f"{node[key]:g}"


SWEEP = lambda: []                  # noqa: E731  () -> [(name, path, delta)]
NUDGE = nudge_leaves


def sweep():
    return SWEEP()


def nudge(doc, path, delta):
    return NUDGE(doc, path, delta)


def configure(root, spec, watched, exclude, comparators, sweep_fn, nudge_fn,
              exempt=None, unconsumed=None, probes=None, audience=None, success=None):
    """Say whose corpus this is. configure generators.py first: this runs them."""
    global ROOT, SPEC, WATCHED, EXCLUDE, COMPARE, SWEEP, NUDGE, AUDIENCE, SUCCESS
    ROOT = pathlib.Path(root).resolve()
    SPEC = ROOT / spec
    WATCHED = [(ROOT / p, alias) for p, alias in watched]
    EXCLUDE = list(exclude)
    COMPARE = comparators
    SWEEP, NUDGE = sweep_fn, nudge_fn
    EXEMPT.clear(); EXEMPT.update(exempt or {})
    UNCONSUMED.clear(); UNCONSUMED.update(unconsumed or {})
    PROBES[:] = list(probes or [])
    if audience:
        AUDIENCE = audience
    if success:
        SUCCESS = success


def configure_from(cfg):
    """configure() this module and the runner from wherefore.json `reach`."""
    G.configure_from(cfg)
    r = cfg.doc.get("reach") or {}
    facts = r.get("facts", {})
    name, src = cfg.source(facts.get("source"))
    adapter = src.get("adapter", "leaves")
    path = cfg.root / src["path"]
    if adapter == "params":
        nl = facts.get("not_length", [])
        if isinstance(nl, str):
            nl = _attr(cfg.root, nl)
        fams = facts.get("families", [])
        sweep_fn = lambda: sweep_params(json.loads(path.read_text(encoding="utf-8")), fams, nl)  # noqa: E731
        nudge_fn = nudge_params
    else:
        inc, exc = facts.get("include", ["*"]), facts.get("exclude", [])
        sweep_fn = lambda: sweep_leaves(json.loads(path.read_text(encoding="utf-8")), inc, exc)  # noqa: E731
        nudge_fn = nudge_leaves
    watched = [(w, None) if isinstance(w, str) else (w["path"], w.get("as")) for w in r.get("watched", [])]
    probes = [(p["name"], tuple(p["fact"].split(".")), p["reaches"], p["files"])
              for p in r.get("probes", [])]
    for k, why in {**r.get("exempt", {}), **r.get("unconsumed", {})}.items():
        if not str(why).strip():
            raise SystemExit(f"::error::reach: {k} is exempt with no reason. An exemption is "
                             f"a justification, not a silence")
    configure(cfg.root, src["path"], watched, r.get("exclude", []),
              _C.Comparators(cfg.doc.get("compare", [])), sweep_fn, nudge_fn,
              r.get("exempt"), r.get("unconsumed"), probes, r.get("audience"),
              cfg.doc.get("messages", {}).get("reach_ok"))
    # A FACT STATED ON A PUBLISHED PAGE REACHES IT BY DECLARATION: nothing the
    # corpus builds need move for it, because the page is held by reading -
    # `wherefore check published` - until it can be built. The declaration is
    # the reach, and the probe says so rather than calling the fact dead.
    PUBLISHED.clear()
    for pname, page in (cfg.doc.get("published") or {}).items():
        for st in page.get("states", []):
            PUBLISHED.setdefault(st["fact"], pname)


def _attr(root, ref):
    """`path/to/module.py:NAME` - a value the client keeps in code, by reference."""
    import importlib.util
    file, name = ref.rsplit(":", 1)
    spec = importlib.util.spec_from_file_location("_wherefore_ref", root / file)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str((root / file).parent))
    spec.loader.exec_module(mod)
    return getattr(mod, name)


def main(argv=None):
    original = SPEC.read_text(encoding="utf-8")
    tmp = pathlib.Path(tempfile.mkdtemp())
    snapshot(tmp / "before")
    baseline = set()
    regenerate(wrote=baseline)
    if moved(tmp / "before"):
        sys.exit("::error::the shipped files are not up to date with the spec "
                 "as committed - regenerate and commit them before probing")
    # The restore point: see `putting things back`. Taken AFTER the baseline
    # pass, of everything it wrote and not only what is watched.
    # The watched files go in as well, though every one of them is a generator's
    # write and so already there: if one ever stops being seen - a writer that
    # goes round Python's open() - it must still be put back, or it would read
    # as "moved" under every probe after the first.
    restore = baseline | {os.path.realpath(f) for f in watched().values()}
    (tmp / "restore").mkdir()
    kept = keep(restore, tmp / "restore")
    listed = listing(restore)

    fails, dead = [], []
    probes = sweep()
    # a probe whose parameter left the spec would never run, and say nothing
    for name, path, _reaches, _files in PROBES:
        if path not in {pr[1] for pr in probes}:
            fails.append(f"{name} probes {'.'.join(path)}, which is no longer a "
                         f"number in the spec - so it probes nothing")
    argv = sys.argv if argv is None else argv
    only = argv[argv.index("--only") + 1:] if "--only" in argv else None
    if only:
        probes = [pr for pr in probes if any(fnmatch.fnmatchcase(pr[0], o) for o in only)]
        if not probes:
            sys.exit(f"::error::--only {' '.join(only)} matches no parameter")
    print(f"{len(probes)} parameters and bands; each moved ONE at a time and put back\n")
    try:
        for what, path, delta in probes:
            if what in EXEMPT:
                print(f"  --   {what:44} exempt: {EXEMPT[what]}")
                continue
            if what in UNCONSUMED:
                print(f"  DEAD {what:44} reaches nothing - see UNCONSUMED")
                dead.append(what)
                continue
            # THE NUDGE BACKS OFF WHEN THE OBJECT REFUSES TO BE BUILT, because
            # a refusal draws NOTHING, and a sheet that was never drawn cannot
            # have moved - so every file the probe names reads as missed and the
            # binding is blamed for the nudge's size. The counterbore's depth is
            # the case that found this: 4 -> 5.7 puts the screw head 0.76 short
            # of seating, build_drawings.py rightly exits, and P-003 is reported
            # as holding its own copy of a number it reads correctly. 4 -> 4.4
            # builds and moves the sheet. So halve and ask again, down to an
            # eighth of the original, and only then let the refusal stand as the
            # answer - at which point the parameter really cannot be probed.
            attempt, backoff = delta, []
            while True:
                doc = json.loads(original)
                was, value = nudge(doc, path, attempt)
                SPEC.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                                encoding="utf-8")
                wrote = set()
                refused = regenerate(strict=False, wrote=wrote)
                if not refused or not isinstance(delta, (int, float)) \
                        or abs(attempt) <= abs(delta) / 8:
                    break
                backoff.append(value)
                SPEC.write_text(original, encoding="utf-8")
                put_back(kept, wrote, listed)
                attempt = round(attempt / 2, 6)
            hits = moved(tmp / "before") + [f"{g} refused to build" for g, _ in refused]
            published = not hits and what in PUBLISHED
            mark = "ok  " if hits else "pub " if published else "FAIL"
            note = f"   {refused[0][0]} refused" if refused and not moved(tmp / "before") else ""
            if backoff:
                note += f"   (backed off from {', '.join(backoff)})"
            if published:
                note += (f"   stated on the published page {PUBLISHED[what]}, which nothing here builds: "
                         f"held by `wherefore check published`")
            print(f"  {mark} {what:44} {was} -> {value}   "
                  f"{len(hits):2} files{note}")
            if not hits and not published:
                fails.append(f"{what} moved from {was} to {value} and "
                             f"NOTHING {AUDIENCE} receives changed. Either a "
                             f"generator should read it and does not, or it is "
                             f"dead and should go — add it to EXEMPT with the "
                             f"reason if neither.")
            for name, _path, reaches, files in (pr for pr in PROBES if pr[1] == path):
                missed = [f for f in files if f not in hits]
                print(f"         {name} must reach {reaches}: "
                      f"{len(files) - len(missed)} of its {len(files)} files moved")
                for f in missed:
                    fails.append(f"{what} moved from {was} to {value}: {name} must reach "
                                 f"{reaches}, and {f} did not change. Its generator holds "
                                 f"its own copy, or does not read this number.")
            SPEC.write_text(original, encoding="utf-8")
            put_back(kept, wrote, listed)
    finally:
        SPEC.write_text(original, encoding="utf-8")
        regenerate()

    left = moved(tmp / "before")
    shutil.rmtree(tmp, ignore_errors=True)
    if left:
        fails.append(f"the probe did not put things back: {', '.join(left[:4])}")

    if dead:
        print(f"\n{len(dead)} parameter(s) reach nothing at all. Not exempt - "
              f"OPEN, and waiting\non a decision that is not this check's to "
              f"make:\n")
        for what in dead:
            print(f"  {what}")
            for line in textwrap.wrap(UNCONSUMED[what], 74):
                print(f"    {line}")

    if fails:
        print()
        for f in fails:
            print(f"::error::{f}")
        print("\nThe spec is decoration wherever this fails. A drift job cannot")
        print("see it: a generator holding its own copy reproduces it perfectly.")
        sys.exit(1)
    print("\n" + SUCCESS.format(audience=AUDIENCE))


if __name__ == "__main__":
    sys.exit(main())
