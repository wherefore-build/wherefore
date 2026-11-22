"""`wherefore gate --since REF`: run only what a change since REF can reach.

THE QUESTION IS THE GATE'S, asked of less. The full gate runs every generator
twice and compares what each writes with what is committed. Most changes move
one fact, and most generators never read it: running them proves again what
the last full run already proved. So, given a commit the full gate passed,
this runs a generator only when something it depends on has moved since, and
takes the rest at the bytes committed. The verdict is meant to be the full
gate's, and every rule below leans towards running when it cannot be sure.
Design: docs/scale.md, "Stage 1".

WHAT IT TRUSTS IS THE GATE'S OWN OUTPUT. The read map - what each generator
read and wrote on a real run - is `wherefore graph --json PATH`, declared as
a generator of the corpus, so the full gate holds it current like any other
file it builds. Nothing here is a list a person keeps. GENERATED IS STILL
DERIVED: a skipped generator's files are generated because the last full run
saw it write them, and the map is that run, written down.

A GENERATOR RUNS when any of these hold, and is skipped otherwise:

  - it is a command, not Python: what it reads is not observed;
  - it is a module run with -m that is not the engine's: its code is not in
    the tree, where a change could be seen;
  - the map did not observe its reads, or it failed when the map was made;
  - its script changed since REF;
  - a file it read (code or source) changed since REF, or was rewritten
    during this run by a generator that ran before it;
  - a file it writes changed since REF, or is missing.

And in the second pass, the one that proves the corpus settles, a generator
skipped in the first runs when a file it reads is no longer what was
committed: the full gate's second pass would see its output move.

A NEW GENERATOR IS A FULL RUN, not a run of that one alone: adding one
changes wherefore.json, or the script that lists the generators, and either
changes what the gate is told - so the conservative answer is the cheap one
to state.

EVERY GENERATOR RUNS - a full gate - when the map cannot be trusted to say:

  - no generator is `wherefore graph --json PATH`, or REF has no map there,
    or the map is not one this engine reads;
  - the map was written by another release of the engine;
  - the generators are not the ones the map names;
  - a file was added or removed since REF, or the tree holds a file git does
    not track and does not ignore: a generator that lists a directory reads
    a file the map cannot name, because it did not exist;
  - wherefore.json, a file it includes, a script `entry` hands a command
    to, the observer, any module the gate itself has loaded from the tree,
    a .gitignore or a .gitattributes changed: what the gate is told changed;
  - a generator reads the map, which is written after the run.

THE MAP ITSELF IS NOT RUN, IT IS COMPOSED. Running `wherefore graph` runs
every generator, so a map generator run would make every gate a full one.
Its output is what it would write if each skipped generator read and wrote
what the map at REF says - which is exactly what skipping assumed - and this
run's observations for the rest, put through graph.model and graph.write, the
code the command runs. Its bytes are then compared like any other file's.

WHAT IT CANNOT SEE. A read the observer does not record: a file opened by a
child process that is not Python, by a C extension, or from outside the tree
(an installed package, the network, the clock). A generator that reads one is
skipped when only that moved. proofs/since_proof.py plants exactly that, "a
read through a shell", and shows the full gate catching what this passed. So
the full gate stays the backstop: on main, and on a schedule. And REF must be
a commit the full gate passed; a skipped file is trusted to be what REF's
generators made, which is only true of a tree the full gate held.
"""
import json
import os
import pathlib
import subprocess
import sys

from . import __version__


class Plan:
    """What `--since REF` decided, and why: `full` says why every generator
    runs instead, or is None."""

    def __init__(self, root, ref):
        self.root = pathlib.Path(root)
        self.ref = ref
        self.sha = None
        self.full = None
        self.map_rel = None
        self.entries = {}            # generator name -> its entry in the map at REF
        self.composers = []          # [(generator, graph options)] - the maps, composed
        self.changed = set()         # rel paths that differ between REF and the tree
        self.decided = []            # [(name, "ran" | "skipped" | "composed", why)]
        self.again = []              # [(name, why)]: run in the second pass only
        self.ran, self.skipped = set(), set()
        self.themes = {}             # composer name -> the theme's text at its turn
        self.snap = {}
        self._same = {}              # (rel, the file's stat) -> is it the bytes snapshotted

    # ── what REF is, and whether its map can be used ───────────────────────

    def short(self):
        return f"{self.ref} ({self.sha[:7]})" if self.sha and not self.sha.startswith(self.ref) else self.ref


def _git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def _z(out):
    return {p for p in out.split("\0") if p}


def _few(paths, n=3):
    paths = sorted(paths)
    return ", ".join(paths[:n]) + (f" and {len(paths) - n} more" if len(paths) > n else "")


def plan(root, ref):
    """Plan a run since `ref`. Raises SystemExit(2), said, for a REF that is
    not a commit: a mistyped base must not quietly become a full run."""
    from . import config as cfgmod, generators as G, graph
    p = Plan(root, ref)
    r = _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    if r.returncode or not r.stdout.strip():
        print(f"::error::--since {ref}: git knows no commit by that name here. Give the commit "
              f"this change is to be judged against - in a pull request, its base")
        raise SystemExit(2)
    p.sha = r.stdout.strip()

    # The maps: every generator that is `wherefore graph`, and the first JSON one is read.
    for g in G.GENERATORS:
        opts = graph.call(g)
        if opts is not None:
            p.composers.append((g, opts))
            if p.map_rel is None and opts["json"] not in (None, "-"):
                p.map_rel = os.path.normpath(os.path.join(g.cwd, opts["json"]))
    if p.map_rel is None:
        p.full = ("no generator writes the map (`wherefore graph --json PATH`), so there is "
                  "nothing to skip by")
        return p
    shown = _git(root, "show", f"{p.sha}:{p.map_rel}")
    if shown.returncode:
        p.full = f"{p.map_rel} is not in {p.short()}: there is no map there to skip by"
        return p
    try:
        then = json.loads(shown.stdout)
    except ValueError:
        p.full = f"{p.map_rel} at {p.short()} is not JSON"
        return p
    if not isinstance(then, dict) or then.get("schema") != graph.SCHEMA:
        p.full = f"{p.map_rel} at {p.short()} is not a map this engine reads (schema {graph.SCHEMA})"
        return p
    if then.get("engine") != __version__:
        p.full = (f"the map at {p.short()} was written by wherefore {then.get('engine')}, and this "
                  f"is {__version__}: another engine may read and write differently")
        return p
    for g, _opts in p.composers:
        if g.stdout_to:
            p.full = f"{G.name(g)} sends its output to {g.stdout_to}, so its map cannot be composed"
            return p

    now = [(G.name(g), g.cwd, g.makes, "run" if g.run else "script") for g in G.GENERATORS]
    was = [(e.get("name"), e.get("cwd"), e.get("makes"), e.get("kind")) for e in then.get("generators", [])]
    if now != was:
        new = sorted({n for n, *_ in now} - {n for n, *_ in was})
        p.full = ("the generators are not the ones the map at " + p.short() + " names"
                  + (f": {_few(new)} is new" if new else ""))
        return p
    p.entries = {e["name"]: e for e in then["generators"]}

    # What moved: in the tree against REF, and which files came or went.
    tracked_now = _z(_git(root, "ls-files", "-z").stdout)
    tracked_then = _z(_git(root, "ls-tree", "-r", "-z", "--name-only", p.sha).stdout)
    came, went = tracked_now - tracked_then, tracked_then - tracked_now
    if came or went:
        p.full = ("files were " + " and ".join(
            w for w in (f"added ({_few(came)})" if came else "", f"removed ({_few(went)})" if went else "") if w)
            + f" since {p.short()}, and a generator that lists a directory reads what the map cannot name")
        return p
    loose = _z(_git(root, "ls-files", "-z", "--others", "--exclude-standard").stdout)
    if loose:
        p.full = (f"the tree holds {len(loose)} {'file' if len(loose) == 1 else 'files'} git does not "
                  f"track or ignore ({_few(loose)}), which a generator that lists a directory may read")
        return p
    diff = _git(root, "diff", "--name-only", "-z", "--no-renames", p.sha, "--")
    if diff.returncode:
        p.full = f"git could not say what changed since {p.short()}: {diff.stderr.strip()}"
        return p
    p.changed = _z(diff.stdout)

    told = _told(root, cfgmod)
    moved = sorted(rel for rel in p.changed
                   if rel in told or pathlib.PurePath(rel).name in (".gitignore", ".gitattributes"))
    if moved:
        p.full = f"what the gate is told changed since {p.short()}: {_few(moved)}"
        return p

    outs = {rel for g, _o in p.composers for rel in graph.maps_itself(g)}
    for e in then["generators"]:
        reads = set(e.get("reads") or []) | set(e.get("code") or [])
        if reads & outs:
            p.full = (f"{e['name']} reads the map ({_few(reads & outs)}), which --since writes "
                      f"after the run: only a full run puts them in order")
            return p
    return p


def _told(root, cfgmod):
    """Every file in the tree that says what the gate is: wherefore.json, what it
    includes, the scripts `entry` hands commands to, the observer, and every
    module this process has loaded from the tree - for a corpus that configures
    the engine in Python, that is where its lists are."""
    root = pathlib.Path(root).resolve()
    out = {cfgmod.NAME}
    try:
        cfg = cfgmod.load(root)
    except SystemExit:
        cfg = None
    if cfg is not None:
        out.update(cfg.included.values())
        for c in cfgmod.ENTRY:
            argv = cfg.entry(c)
            if argv:
                out.add(os.path.normpath(argv[0]))
        obs = cfg.observer_dir.resolve()
        if str(obs).startswith(str(root) + os.sep):
            for d, _dirs, files in os.walk(obs):
                out.update(os.path.relpath(os.path.join(d, f), root) for f in files)
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if f:
            f = os.path.realpath(f)
            if f.startswith(str(root) + os.sep):
                out.add(os.path.relpath(f, root))
    return out


# ── during the run ──────────────────────────────────────────────────────────

def _as_snapped(p, rel):
    """Is `rel` in the tree, byte for byte, what the snapshot holds? Asked once
    per state of the file: a large file many generators read is read once,
    and again only after something writes it."""
    was, now = p.snap.get(rel), p.root / rel
    if was is None or not now.is_file():
        return False
    st = now.stat()
    key = (rel, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    if key not in p._same:
        p._same[key] = (was.stat().st_size == st.st_size
                        and was.read_bytes() == now.read_bytes())
    return p._same[key]


def _moved(p, rel):
    """Why `rel` is not as REF left it, or None: changed since REF, missing,
    or rewritten during this run."""
    if rel in p.changed or rel not in p.snap:
        return f"changed since {p.ref}"
    if not (p.root / rel).is_file():
        return "missing"
    if not _as_snapped(p, rel):
        return "rewritten by a generator that ran before it"
    return None


def _why_run(p, g):
    """The first reason generator `g` must run, or None."""
    from . import generators as G
    e = p.entries[G.name(g)]
    if g.run:
        return "a command: what it reads is not observed"
    if g.script.startswith("-m "):
        mod = g.script[3:].strip()
        if mod != "wherefore" and not mod.startswith("wherefore."):
            return "a module run with -m: its code is not in the tree, where a change could be seen"
    if e.get("reads") is None:
        return f"the map at {p.ref} did not observe what it reads"
    if e.get("failure"):
        return f"it failed when the map at {p.ref} was made"
    script = os.path.normpath(os.path.join(g.cwd, g.script))
    why = _moved(p, script)
    if why:
        return f"its script, {script}, {why}"
    for kind, rels in (("reads", (e.get("code") or []) + (e.get("reads") or [])),
                       ("writes", (e.get("writes") or []) + (e.get("rewrites") or []))):
        hit = [(rel, _moved(p, rel)) for rel in rels]
        hit = [(rel, why) for rel, why in hit if why]
        if hit:
            more = f" (and {len(hit) - 1} more)" if len(hit) > 1 else ""
            return f"it {kind} {hit[0][0]}, {hit[0][1]}{more}"
    return None


def first_pass(p, theme_reader):
    """The `select` for the first pass: decide each generator at its turn."""
    from . import generators as G

    def select(g):
        name = G.name(g)
        for c, opts in p.composers:
            if c is g:
                # Its turn: read the stylesheets now, as the command would, from
                # the tree the generators before it left.
                p.themes[name] = theme_reader(opts, p.root / g.cwd)
                p.decided.append((name, "composed", "the map: this run's reads and writes, and the "
                                  f"map at {p.ref} for each generator skipped"))
                return False
        why = _why_run(p, g)
        if why:
            p.ran.add(name)
            p.decided.append((name, "ran", why))
            return True
        p.skipped.add(name)
        p.decided.append((name, "skipped", f"nothing it reads or writes has changed since {p.ref}"))
        return False
    return select


def second_pass(p):
    """The `select` for the settling pass: what ran, again, and any generator
    skipped whose reads a generator has since rewritten - the full gate's second
    pass would see it move, so this one runs it."""
    from . import generators as G

    def select(g):
        name = G.name(g)
        if any(c is g for c, _o in p.composers):
            return False
        if name in p.ran:
            return True
        e = p.entries[name]
        for rel in (e.get("code") or []) + (e.get("reads") or []):
            if rel in p.snap and (p.root / rel).is_file() and not _as_snapped(p, rel):
                p.again.append((name, f"it reads {rel}, which this run rewrote"))
                return True
        return False
    return select


def credit(p, wrote):
    """Add to `wrote` every file the map says each skipped generator writes,
    then every file each map writes, with every list of writers in the order
    the generators run - which is the order a run would have written them."""
    from . import generators as G, graph
    order = {G.name(g): i for i, g in enumerate(G.GENERATORS)}
    for name in p.skipped:
        e = p.entries[name]
        for rel in (e.get("writes") or []) + (e.get("rewrites") or []):
            wrote.setdefault(os.path.realpath(p.root / rel), []).append(name)
    for path, by in wrote.items():
        by.sort(key=lambda n: order.get(n, len(order)))
    for g, _opts in p.composers:
        for rel in graph.maps_itself(g):
            wrote.setdefault(os.path.realpath(p.root / rel), []).append(G.name(g))


def compose(p, name, wrote, reads, failures):
    """Write every map, as `wherefore graph` would have written it; return the
    failures composing them adds. `wrote` already holds every credit."""
    from . import config as cfgmod, generators as G, graph
    if not p.composers:
        return []
    rd = {}
    for g in G.GENERATORS:
        n = G.name(g)
        if n in reads:
            rd[n] = reads[n]
        elif n in p.skipped:
            e = p.entries[n]
            rd[n] = [("r", os.path.realpath(p.root / rel))
                     for rel in (e.get("code") or []) + (e.get("reads") or [])]
    was = os.environ.get("WHEREFORE_ROOT")
    os.environ["WHEREFORE_ROOT"] = str(p.root)
    try:
        m = graph.model(name or cfgmod.load(p.root).name, G.tracked(), wrote, rd, failures)
    finally:
        if was is None:
            os.environ.pop("WHEREFORE_ROOT", None)
        else:
            os.environ["WHEREFORE_ROOT"] = was
    more = []
    for g, opts in p.composers:
        theme = p.themes.get(G.name(g))
        if theme is None:
            more.append((G.name(g), f"--theme {', '.join(opts['theme'])}: no such stylesheet"))
            continue
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            graph.write(m, opts, theme, p.root / g.cwd)
    return more


def said(p):
    """The lines that say what ran, what was skipped, and why."""
    n = {k: sum(1 for _n, v, _w in p.decided if v == k) for k in ("ran", "skipped", "composed")}
    head = (f"since {p.short()}, by the map in {p.map_rel}: {n['ran']} ran, {n['skipped']} skipped"
            + (f", {n['composed']} composed" if n["composed"] else ""))
    return [head] + [f"  {v:8} {nm} - {w}" for nm, v, w in p.decided]
