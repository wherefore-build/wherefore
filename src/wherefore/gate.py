#!/usr/bin/env python3
"""Every tracked file is accounted for, and every generated one was really written.

IN WHEREFORE. Moved from chaotic-pendulums-co's checks/coverage_gate.py, its
docstring and comments kept: the bugs it names are that repository's, and they
are why each line is here. What changed is whose corpus it is. ROOT, the
inventory, the source a capture's `spec_values` are read from, and how a
message names the inventory and this command are set by configure(). "Is this
file what was committed?" is compare.py's, which holds the exceptions to
byte-identity a client declares in wherefore.json `compare`, each with its
reason - the thresholds, and the measurements that set them, stay with the
client whose renderers they were measured on. A file the client compares by
its cells is the one the second pass ignores, as .xlsx was here.

THE QUESTION. Not "does this file still match itself" - everything else in this
repo already asks that - but "is there anything here that nobody is keeping
current, and would anyone notice?" Every other check compares two things that
both exist and are already wired to each other, so absence is the one thing
none of them can see, and absence is what keeps getting through.

So this one enumerates. Every file `git ls-files` names is generated, authored
or captured, and NO FILE MAY BE UNCLASSIFIED - a new file forces the decision,
because a file nobody has classified is a file nobody has taken responsibility
for. The three bugs that caused it, all from one release:

  1. A GENERATOR HOLDING ITS OWN COPY.  build_dxf.py opened `H=114; W=38` with
     the derivation in a comment beside it. It reproduced itself perfectly, for
     ever, and every drift job passed. checks/spec_reaches_the_shop.py is the
     answer to that one; it is not this one.
  2. A GENERATOR NEVER INVOKED.  sideview.build() was written inside an
     `if __name__ == "__main__"` block, so buildpack.py imported it and ran
     nothing. The side elevations sat at V8 through two releases. A drift job
     diffs what a generator WROTE and is structurally blind to one that wrote
     nothing, so nothing could catch it. THIS IS THE BUG THIS CHECK EXISTS FOR.
  3. AN ASSET THAT CANNOT BE REGENERATED.  The hero and room stills are
     hand-captured. No check can make them correct. This one records what each
     was made from and fails when that source moves and the capture does not,
     which is the most a check can honestly do: it turns rotting into a list.
     brand/code/cycle.baked.json is the subtle member of this class and was
     filed as `authored` at first: it is 335 poses of the real pendulum, baked
     because a chaotic trajectory is not reproducible across machines, and
     cycle.py integrates it from inertia terms built out of five spec values.
     Change the fork's length and cp-cycle.svg redraws the NEW shape at the OLD
     motion - its bytes change, so every drift job passes, while the animation
     plays the mechanics of an object that no longer exists.

HOW IT ANSWERS. It runs every generator with a hook on Python's `open` audit
event and records what each one actually writes - see checks/generators.py and
checks/_observe/sitecustomize.py. GENERATED IS DERIVED, NEVER DECLARED, because
a hand-kept list of outputs drifts from the outputs and the drift is invisible
in exactly the direction that matters. What cannot be derived - which files are
sources, which are hand-made - is declared in checks/inventory.json, where
every rule carries its reason.

Then every generated file must satisfy BOTH halves:

  - it was REWRITTEN during the run, and
  - its content is byte-identical to what was committed.

The first half is the new part and it is the whole point. A file nobody wrote
is not covered, however right its contents look, and that kills mode 2
permanently: delete `SV.build(ROOT)` and the six side elevations stop being
written, fall out of `generated`, match no authored rule, and fail as
unclassified - naming themselves, on the commit that did it.

THE mtime TRAP, and why the fix went in the generator. mtime cannot prove
coverage, because a generator that skips its write when nothing changed leaves
the mtime alone and reads as uncovered. brand/code/hero_params.py did exactly
that - it printed "hero already matches the spec" and wrote nothing. The fix
was to make it write unconditionally, which is what a generator being a pure
function of its inputs actually means, rather than to teach this check that
some files are allowed not to be written. A gate with an exception for the file
that most needs watching is not a gate.

THE ORDERING TRAP: snapshot first, THEN regenerate, THEN compare. Comparing
against anything read after the run compares the output with itself.

AND THE CORPUS MUST BE A FIXED POINT. Running the generators twice has to
change nothing the second time, and this checks it, because the generators are
not a straight line: spec/build_manifest.py WRITES spec/manifest.json, and
sideview.py, sketch.py and buildpack.py READ it - that is where the REV letters
in the drawn views come from - and it runs after them, because it can only work
out which release an asset last changed in once the assets are current. So a
change that moves the manifest lands in the views one pass LATE. Bump V and
regenerate once and you get 37 files that disagree with a manifest that is
itself correct; regenerate again and they agree. Without this test that shows
up as "37 generated files differ", which is true, unhelpful, and sends whoever
reads it looking for a spec change that never happened.

IT DOES NOT ASK GIT, for the same reason checks/shipped_solids.py does not:
`*.step`, `*.png`, `*.xlsx` and the fonts are LFS-tracked, so `git diff` on one
shows two lines of pointer oid and never the content. A version of that check
built on git diff reported "byte-identical" for a file that had just been
modified. Every comparison here is against the byte snapshot taken first.
The one thing it asks git is not a comparison: WHICH committed picture a
capture was made from, when that source is a render - see stamp_for.

WHAT IT CANNOT SEE.
  - Whether a generated file is RIGHT. It proves the committed bytes are the
    bytes the generator makes today; it cannot tell you the generator is wrong.
    drawn_dimensions and spec_reaches_the_shop ask that, from two sides.
  - A source misfiled as authored that should be generated. Nothing writes it,
    it matches a rule, and it passes. The rules in inventory.json are kept
    narrow for this reason - none of them matches an svg, dxf, step or png in
    an output directory - but a wrong rule is a wrong answer, so the rules are
    where to look when something is stale and this check is quiet.
  - A write that does not go through Python's open(). Nothing here does one.

Usage:  python3 checks/coverage_gate.py             the gate
        python3 checks/coverage_gate.py --keep      leave what it regenerated
        python3 checks/coverage_gate.py --restamp <group>   after re-shooting
                                                    or re-baking one of them
"""
import fnmatch
import hashlib
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile

from . import compare as _C
from . import generators as G
from . import sources as _S

# The snapshot and the restore copy every tracked file, and a copy is not an
# examination. When this runs under checks/_observe with $CP_READ_LOG set -
# which CI does, so checks/leaves_are_leaves.py can see what the heavy tier
# reads - those copies are declared as copies, or the log would say the gate
# reads the whole repository: true, and no use to anyone. Anywhere else the
# observer is not on the path and this is a context that does nothing.
try:
    from sitecustomize import copying
except ImportError:
    import contextlib
    copying = contextlib.nullcontext

# The client's, set by configure(). See the module docstring.
ROOT = None
DECL = None             # () -> the inventory, read fresh
WRITE_DECL = None       # (inventory) -> the path it was written to
DECL_NAME = "wherefore.json"
SPEC = None             # repo-relative path of the source spec_values read
ADAPTER = "leaves"
COMPARE = _C.Comparators()
COMMAND = "wherefore gate"
RESETTLE_HINT = ("A generator reads a file that a later one writes, so it\n"
                 "           lands one pass late.")


def configure(root, decl, write_decl, decl_name, spec, adapter, comparators,
              command=None, resettle_hint=None):
    """Say whose corpus this is. configure generators.py first: this runs them."""
    global ROOT, DECL, WRITE_DECL, DECL_NAME, SPEC, ADAPTER, COMPARE, COMMAND, RESETTLE_HINT
    ROOT = pathlib.Path(root).resolve()
    DECL, WRITE_DECL, DECL_NAME = decl, write_decl, decl_name
    SPEC, ADAPTER, COMPARE = spec, adapter, comparators
    if command is not None:
        COMMAND = command
    if resettle_hint is not None:
        RESETTLE_HINT = resettle_hint


def configure_from(cfg):
    """configure() this module and the runner from a loaded wherefore.json."""
    import json as _json
    G.configure_from(cfg)
    # A corpus with no source yet - what `wherefore init` writes - can still be
    # classified, and that is the first thing it needs. Only spec_values reads
    # the source, and stamp_for says so if one asks for it with none declared.
    if cfg.doc.get("sources"):
        _name, src = cfg.source()
    else:
        src = {"path": None, "adapter": None}
    msg = cfg.doc.get("messages", {})
    if "inventory" in cfg.included:
        path = cfg.root / cfg.included["inventory"]
        decl = lambda: _json.loads(path.read_text(encoding="utf-8"))
    else:
        decl = lambda: _json.loads((cfg.root / "wherefore.json").read_text(
            encoding="utf-8")).get("inventory", {})
    configure(cfg.root, decl, lambda d: cfg.write_section("inventory", d),
              cfg.where("inventory"), src["path"], src.get("adapter", "leaves"),
              _C.Comparators(cfg.doc.get("compare", [])),
              msg.get("gate_command"), msg.get("resettle_hint"))


def digest(data):
    return hashlib.sha256(data).hexdigest()[:16]


MEASURED = _C.MEASURED


def same(was, now):
    """Is this file what was committed? compare.py says, by the client's rules."""
    rel = str(now.resolve()).replace(str(ROOT) + "/", "")
    return COMPARE.same(was, now, rel)


def first_difference(was, now, context=70):
    """The first line that differs, both sides, for anything readable as text.

    Binary and anything that decodes as mojibake is skipped - a hexdump in a CI
    log helps nobody.
    """
    try:
        a = was.read_text(encoding="utf-8").splitlines()
        b = now.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
        return ""
    for i, (x, y) in enumerate(zip(a, b), 1):
        if x != y:
            return (f"\n           first differs at line {i}"
                    f"\n             committed: {x.strip()[:context]}"
                    f"\n             rebuilt:   {y.strip()[:context]}")
    if len(a) != len(b):
        return f"\n           {len(a)} lines committed, {len(b)} rebuilt"
    return ""


def snapshot(names, into):
    """Every tracked file's bytes, before anything runs. The ordering trap."""
    into.mkdir(parents=True, exist_ok=True)
    kept = {}
    for rel in names:
        src = ROOT / rel
        if not src.is_file():
            continue                      # deleted in the working tree; git will say so
        dst = into / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        kept[rel] = dst
    return kept


def matches(rel, pattern):
    """fnmatch against the repo-relative path, where * crosses directories.

    So `*.py` claims every .py anywhere in the tree, and `README.md` claims
    exactly the one at the root - which is the point, because brand/fonts is
    written by buildpack.py and must not be quietly claimed by a rule about
    the repo's front door.
    """
    return fnmatch.fnmatch(rel, pattern)


def authored_rule(rel, rules):
    """The first rule that claims this file, or None.

    A rule may carry EXCEPTIONS, and they are not decoration. Two files match
    `*.md` and are written by a generator - docs/REVISIONS.md and
    brand/fonts/README.md - and the tempting fix is to let `generated` quietly
    win whenever the two overlap. That is the hole: let a declaration and a
    generator both claim a file, and the day the generator stops writing it the
    declaration catches it and the gate goes silent, which is the exact failure
    this whole check exists to make impossible. So overlap is an error, the
    exceptions are written down, and a generated file that stops being written
    lands in UNKNOWN where it belongs.
    """
    for rule in rules:
        pattern, why = rule[0], rule[1]
        if not matches(rel, pattern):
            continue
        if any(matches(rel, x) for x in (rule[2] if len(rule) > 2 else [])):
            continue
        return pattern, why
    return None


def captured_files(decl):
    """rel path -> (group name, the group), for every file a group claims."""
    out = {}
    for name, grp in decl["captured"]["groups"].items():
        for pattern in grp.get("files", []):
            for f in sorted(ROOT.glob(pattern)):
                out[str(f.relative_to(ROOT))] = (name, grp)
    return out


def spec_value(spec, dotted):
    """One parameter out of the spec, by its family.group.name path - or, for a
    source read by the `leaves` adapter, by its dotted path. See sources.py."""
    return _S.value(spec, dotted, ADAPTER)


def is_raster(rel):
    """A picture a browser rasterised, whose bytes are the machine's business."""
    return COMPARE.is_raster(rel)


def committed_blob(rel):
    """The object id git holds for this path in the index, or None.

    For an LFS file that is the pointer's id, and the pointer carries the sha256
    of the content - so it names WHICH committed picture this is, the same on
    every machine, whatever any machine has rendered over the working copy."""
    import subprocess
    out = subprocess.run(["git", "ls-files", "-s", "--", rel], cwd=ROOT,
                         capture_output=True, text=True).stdout.split()
    return out[1] if len(out) >= 2 else None


def stamp_for(grp, snap):
    """What this captured group was made FROM, as one hash.

    Read out of the SNAPSHOT, not the working tree: the generators run in
    between, and brand/model/mk3-hero.html - the scene most of these were shot
    from - is rewritten by hero_params.py on every run. Hashing the live file
    would hash whatever this machine just produced.

    EXCEPT A RASTERISED SOURCE, which is stamped by what git holds for it. Its
    bytes are exactly what `same()` refuses to demand of it: webassets.py on a
    CI runner draws brand/web/apple-touch-icon-180.png as a different PNG from
    the Mac's, the same picture. checks/coverage_gate_proof.py regenerated the
    tree and then ran the gate on it, the snapshot held the runner's icon, and
    'the other rasteriser' was reported as made from something that had moved -
    on a clean tree, on CI only, because a Mac's software renderer reproduces
    the committed bytes exactly. A source a picture was made from moves when a
    DIFFERENT picture is committed for it, and the index says when that is.
    """
    parts = []
    for rel in grp.get("shot_from", []):
        f = snap.get(rel)
        if f and is_raster(rel):
            blob = committed_blob(rel)
            parts.append(f"{rel}=git:{blob}" if blob else f"{rel}=MISSING")
            continue
        parts.append(f"{rel}={digest(f.read_bytes()) if f else 'MISSING'}")
    wanted = grp.get("spec_values", [])
    if wanted:
        if SPEC is None:
            raise SystemExit("::error::a captured group reads spec_values, and no source is "
                             "declared to read them from: declare one in `sources`")
        if SPEC not in snap:
            raise SystemExit(f"::error::a captured group reads spec_values from {SPEC}, "
                             f"which git does not track or the working tree does not have. "
                             f"A stamp is over what is committed: add it")
        spec = json.loads(snap[SPEC].read_text(encoding="utf-8"))
        for dotted in wanted:
            parts.append(f"{dotted}={spec_value(spec, dotted)!r}")
    return digest("\n".join(parts).encode())


def untracked_writes(wrote, tracked_now):
    """{repo-relative path: [generators]} for every file a generator wrote in
    the repository that git does not track and .gitignore does not exclude.

    A GENERATED FILE GIT DOESN'T TRACK. Everything above is keyed on `git
    ls-files`, so a generated file that stops being tracked - `git rm --cached`,
    or a new output nobody added - is not generated, authored, captured or
    unknown: it is not in the corpus at all, and the gate said nothing. Only
    the STEP and DXF had a second line, in checks/shipped_solids.py, which
    compares their directories by listing; brand-drift's `git diff` cannot see
    an untracked file either. The deliberate build outputs are untracked on
    purpose, and .gitignore is where that purpose is written - the prototype
    build, dist/, the storefront's public/ - so that is what excuses one. A
    write outside the repository is a temp file, and none of this concerns it.
    """
    import subprocess
    root = os.path.realpath(ROOT) + os.sep
    loose = {}
    for p, by in wrote.items():
        if p.startswith(root) and p not in tracked_now and os.path.isfile(p):
            loose[os.path.relpath(p, root)] = sorted(set(by))
    if not loose:
        return {}
    ignored = set(subprocess.run(["git", "check-ignore", "-z", "--stdin"], cwd=ROOT,
                                 capture_output=True, text=True,
                                 input="\0".join(loose) + "\0").stdout.split("\0"))
    return {rel: by for rel, by in loose.items() if rel not in ignored}


def restamp(decl, snap, only=None):
    """Record captured groups against their sources as they are NOW.

    The only thing that should ever write `stamp`: saying "this capture is
    current" is a claim about a photograph that only a person who just took it
    can make.

    ONE GROUP AT A TIME, by name, because re-shooting is not something anyone
    does to everything at once. Without the filter the only way to record a
    re-baked cycle was to restamp every group in the file, which would certify
    eleven stills nobody had been anywhere near - a command that quietly
    certifies work that was not done.
    """
    if only is not None and only not in decl["captured"]["groups"]:
        sys.exit(f"no captured group called {only!r}. There is: "
                 + ", ".join(repr(k) for k in decl["captured"]["groups"]))
    for name, grp in decl["captured"]["groups"].items():
        if only is not None and name != only:
            continue
        was, now = grp.get("stamp"), stamp_for(grp, snap)
        grp["stamp"] = now
        if was == now:
            print(f"  --   {name:32} unchanged")
        else:
            print(f"  re   {name:32} {was or 'unstamped'} -> {now}")
    # indent=1, which is how the file is written; 2 re-indented all of it.
    written = WRITE_DECL(decl)
    print(f"\nwrote {pathlib.Path(written).relative_to(ROOT)}. Commit it with the re-shot files, "
          f"in the same commit,\nso the capture and what it claims to depict "
          f"move together.")


USAGE = ("usage: wherefore gate [--keep]\n"
         "       wherefore gate --restamp GROUP")


def parse(argv):
    """(keep, restamp group or None), or an exit code for a line that means nothing.

    A flag the gate does not know is refused rather than ignored: `--kep` used to
    run the whole gate without --keep and pass, and `--help` ran it too.
    """
    args = list(argv[1:])
    if any(a in ("-h", "--help") for a in args):
        print(USAGE)
        return 0
    if "--restamp" in args:
        i = args.index("--restamp")
        rest = args[:i] + args[i + 2:]
        group = args[i + 1] if len(args) > i + 1 and not args[i + 1].startswith("-") else None
        if group is None or rest:
            print("::error::--restamp takes exactly one GROUP, and nothing else. Re-stamping "
                  "every group at once would certify captures nobody re-made.\n" + USAGE)
            return 2
        return False, group
    unknown = [a for a in args if a != "--keep"]
    if unknown:
        print(f"::error::the gate does not take {' '.join(unknown)}\n{USAGE}")
        return 2
    return "--keep" in args, None


def _palette_notice(made):
    """Colours said in several of the files the build made, and no palette
    declared: say so, once, and go on. The gate never fails for it;
    `wherefore check palette` does, when asked. It reads only `made` - the
    generated files, which this run wrote and compared - so the gate opens
    nothing for the notice that it did not open to judge: a client that
    records what its gate reads (the first client does) sees no new read."""
    try:
        from . import config, palette
        said = palette.notice(config.load(), made)
    except Exception:          # the notice is a courtesy, never a verdict
        return
    if said:
        print(f"\n  {said}")


def main(argv=None):
    argv = sys.argv if argv is None else argv
    parsed = parse(argv)
    if isinstance(parsed, int):
        return parsed
    keep, only = parsed
    doing_restamp = only is not None

    decl = DECL()
    decl.setdefault("authored", {}).setdefault("rules", [])
    decl.setdefault("captured", {}).setdefault("groups", {})
    names = sorted(G.tracked().values())
    # TRACKED, AND NOT IN THE WORKING TREE. The snapshot cannot hold what is not
    # there, so a generator that recreates it would be compared with nothing and
    # pass - while what is committed may be stale. Said, not skipped.
    missing = [rel for rel in names if not (ROOT / rel).is_file()]
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"{G.TEMP_PREFIX}gate-"))
    try:
        with copying():
            snap = snapshot(names, tmp / "before")

        if doing_restamp:
            print(f"Re-stamping {only!r}\n")
            restamp(decl, snap, only)
            return 0

        print(f"{len(names)} tracked files; {len(G.GENERATORS)} generators\n")
        wrote, failures = G.run_all(quiet=True)
        tracked_now = G.tracked()
        written = {tracked_now[p] for p in wrote if p in tracked_now}

        # ── classify ─────────────────────────────────────────────────────────
        rules = decl["authored"]["rules"]
        captured = captured_files(decl)
        generated, authored, capt = {}, {}, {}
        unclassified, contradictions = [], []
        for rel in names:
            by = sorted({g for p, gs in wrote.items()
                         for g in gs if tracked_now.get(p) == rel})
            rule = authored_rule(rel, rules)
            grp = captured.get(rel)
            if rel in written:
                if rule or grp:
                    what = f"authored ({rule[0]})" if rule else f"captured ({grp[0]})"
                    contradictions.append((rel, by, what))
                generated[rel] = by
            elif grp:
                capt[rel] = grp
            elif rule:
                authored[rel] = rule
            else:
                unclassified.append(rel)
        loose = untracked_writes(wrote, tracked_now)

        print(f"  generated   {len(generated):4}   written by a generator during this run")
        print(f"  authored    {len(authored):4}   declared a source in {DECL_NAME}")
        print(f"  captured    {len(capt):4}   declared hand-made, and stamped")
        print(f"  UNKNOWN     {len(unclassified):4}")
        print(f"  UNTRACKED   {len(loose):4}   written by a generator, and neither tracked nor ignored\n")

        fails = []
        for rel in missing:
            fails.append(
                f"{rel} is tracked and is not in the working tree, so what is committed "
                f"cannot be\n           compared with what the sources make now. Restore "
                f"it (git checkout -- {rel}),\n           or remove it from git (git rm) if "
                f"it is meant to go.")
        for rel, by in sorted(loose.items()):
            fails.append(
                f"{rel} is a generated file git doesn't track (written by "
                f"{', '.join(by)}).\n           Nothing here can hold it to "
                f"anything: every comparison is over what git tracks. Track it, "
                f"or - if it is a\n           build output nobody commits - say so "
                f"in .gitignore.")

        for script, err in failures:
            fails.append(f"{script} failed while the gate ran it. A generator "
                         f"that throws covers nothing:\n{err}")

        for rel in unclassified:
            fails.append(
                f"{rel} is unclassified. Nothing wrote it during this run and "
                f"nothing declares it.\n           Either a generator should "
                f"write it and does not any more - which is the bug this gate "
                f"exists\n           to catch - or it is a source or a capture, "
                f"and {DECL_NAME} needs\n           the rule that "
                f"says so, with the reason.")

        for rel, by, what in contradictions:
            fails.append(f"{rel} is declared {what} and was written by "
                         f"{', '.join(by)}. One of the two is wrong.")

        # ── coverage: written AND byte-identical ─────────────────────────────
        # A SECOND PASS FIRST, because the generators are not a straight line:
        # build_manifest.py writes spec/manifest.json and several generators
        # read it for their REV stamps and run BEFORE it, so a change that moves
        # the manifest lands one pass late. That is a cycle, not drift, and it
        # is named in the docstring.
        #
        # This used to compare after ONE pass, which meant any change touching
        # the manifest reported the one-pass-late files as having drifted from
        # what is committed - while the committed bytes were the fixed point and
        # correct. Moving the pose to 132 is what exposed it: three files,
        # green tree, red gate, and nothing actually wrong.
        #
        # So the two questions are asked separately, in the order that makes
        # each answerable: does it SETTLE, and does the settled corpus match.
        after_one = {rel: (ROOT / rel).read_bytes() for rel in generated
                     if (ROOT / rel).is_file()}
        # ITS FAILURES COUNT. A generator that succeeds once and throws on the
        # second pass - choking on something the first pass wrote, which is
        # what this pass exists to expose - wrote nothing, and "nothing moved"
        # would read its crash as settled.
        _again, failed_again = G.run_all(only_resettle=True)
        failed_once = {script for script, _err in failures}
        for script, err in failed_again:
            if script not in failed_once:
                fails.append(f"{script} failed on the second pass, after the first "
                             f"succeeded. A generator that throws covers nothing:\n{err}")
        unsettled = sorted(rel for rel, b in after_one.items()
                           if (ROOT / rel).is_file()
                           and (ROOT / rel).read_bytes() != b
                           and COMPARE.rule_for(rel)[0] != "xlsx-cells")

        moved = []
        for rel, by in sorted(generated.items()):
            was = snap.get(rel)
            now = ROOT / rel
            if was is None:
                continue                  # a generator made a file git does not track
            if not same(was, now):
                moved.append((rel, by))

        for rel, by in moved:
            extra = ""
            if rel in MEASURED:
                d = MEASURED[rel]
                extra = "".join(f"\n           {w}" for w in _C.picture_faults(
                    d, **COMPARE.picture_tolerances(rel)))
                if d is not None:
                    extra += (f"\n           (edge {d[0]:.4f}, tone {d[2]:.1f}, "
                              f"flat {d[1]:.4f})")
            # WHAT differs, not just THAT it does. Three CI rounds were spent
            # guessing at two files, when the first differing line would have
            # said it outright - and a gate that names a file and stops is a
            # gate somebody has to reproduce the environment to read.
            # snap.get(rel), NOT `was` - that name is left over from the loop
            # above and holds whatever file it stopped on, so the first report
            # this wrote compared index.html against a JSON snapshot.
            if rel in MEASURED:
                where = ""
            else:
                snapped = snap.get(rel)
                where = first_difference(snapped, ROOT / rel) if snapped else ""
            fails.append(f"{rel} regenerated DIFFERENT from what is committed "
                         f"(written by {', '.join(by)}).{extra}{where}\n           "
                         f"Either the spec moved and this was not re-recorded, "
                         f"or it was edited by hand.")

        # The rasterised files are the ones whose agreement is a JUDGEMENT, so
        # the judgement is shown even when it passes. The first run on any new
        # machine is the only place the real cross-rasteriser number can be
        # learned, and a gate that prints nothing on success throws it away.
        seen = {r: d for r, d in MEASURED.items() if d is not None}
        if seen:
            # Each against its own rule's tolerances; a client with one rule
            # for every picture reads exactly what it read before.
            tol = {r: COMPARE.picture_tolerances(r) for r in seen}
            we = max(seen, key=lambda r: seen[r][0])
            wt = max(seen, key=lambda r: seen[r][2])
            worst, toned = seen[we][0], seen[wt][2]
            print(f"       {len(seen)} rasterised file(s) compared as pictures, "
                  f"not bytes — worst edge {worst:.4f} of {tol[we]['edge_tol']:g} allowed, "
                  f"worst tone {toned:.1f} of {tol[wt]['tone_tol']:g}")
            # The six worst by EITHER term, as a share of its own tolerance, so
            # a picture whose color is closest to the line is not hidden behind
            # six whose drawing is.
            for r, d in sorted(seen.items(), key=lambda kv: -max(
                    kv[1][0] / tol[kv[0]]["edge_tol"], kv[1][2] / tol[kv[0]]["tone_tol"]))[:6]:
                print(f"         edge {d[0]:7.4f}   tone {d[2]:5.1f}   "
                      f"flat {d[1]:7.4f}   {r}")
        print(f"  {'ok  ' if not moved else 'FAIL'} {len(generated)} generated "
              f"files, {len(moved)} differ from what is committed")

        if unsettled:
            fails.append(
                f"the corpus is not a fixed point: {len(unsettled)} files "
                f"changed again on a SECOND\n           regeneration, so one "
                f"pass does not settle them. {RESETTLE_HINT}"
                f" Regenerate a second time and commit that. First "
                f"five:\n"
                + "".join(f"             {u}\n" for u in unsettled[:5]))
        print(f"  {'ok  ' if not unsettled else 'FAIL'} the corpus settles: a "
              f"second regeneration moves {len(unsettled)} files")

        # ── the captured assets, against what they were shot from ────────────
        reshoot, unstamped = [], []
        for name, grp in decl["captured"]["groups"].items():
            here = sorted(rel for rel, (n, _) in captured.items() if n == name)
            now = stamp_for(grp, snap)
            # THERE IS NO known_stale ANY MORE. It excused a group whose source
            # had moved, printed it as a debt, and passed - with no release it
            # was granted in and nothing that ever took it back, so a debt
            # recorded once was a pass for ever. No group has carried it since
            # the "photographs" were sorted into renders and history (16604da),
            # and nothing documents a need for it. The
            # key is refused rather than ignored, so nobody writes it expecting
            # it to do what it used to.
            if "known_stale" in grp:
                fails.append(
                    f"the captured group {name!r} carries known_stale, which this "
                    f"gate no longer honors:\n           a capture whose source "
                    f"moved is re-made, or its group says no_stamp and why. "
                    f"Remove the key.")
            if grp.get("no_stamp"):
                # A capture that derives from nothing cannot be out of date
                # with respect to anything. The camera originals are the
                # clearest case: they ARE the source. This is a claim someone
                # made in writing, in inventory.json, not an absence.
                unstamped.append((name, here, grp["no_stamp"]))
            elif grp.get("stamp") is None:
                fails.append(
                    f"the captured group {name!r} declares neither a stamp, nor "
                    f"no_stamp with a reason. A\n           "
                    f"hand-made asset has to say what it was made from, or say "
                    f"why\n           there is nothing for it to go stale "
                    f"against. Run --restamp, or write the reason.")
            elif grp["stamp"] != now:
                reshoot.append((name, here, grp["stamp"], now))
        for name, here, was, now in reshoot:
            # Neutral about HOW it was made: these groups are photographs, screen
            # captures and one baked integration, and "re-shoot the baked cycle"
            # sends the reader looking for a camera. Each group's `why` carries
            # its own instruction; this says which ones and how to record it.
            fails.append(
                f"what {name!r} was made from has moved ({was} -> {now}) and it "
                f"has not.\n           THESE {len(here)} NEED RE-MAKING:\n"
                + "".join(f"             {h}\n" for h in here)
                + f"           Then: {COMMAND} "
                  f"--restamp {name!r}")
        print(f"  {'ok  ' if not reshoot else 'FAIL'} {len(captured)} captured "
              f"files in {len(decl['captured']['groups'])} groups, "
              f"{len(reshoot)} groups out of date, "
              f"{len(unstamped)} deriving from nothing")

        _palette_notice(sorted(generated))
        if fails:
            print()
            for f in fails:
                print(f"::error::{f}")
            print("\nA file nobody wrote and nobody claimed is a file nobody is")
            print("keeping current. That is what this gate is for.")
            return 1
        print("\nevery tracked file is classified, and every generated one was "
              "written\nduring this run and matches what is committed")
        return 0
    finally:
        if not doing_restamp and not keep:
            with copying():
                for rel in missing:
                    # It was not there when the gate began; it is not there after.
                    if (ROOT / rel).is_file():
                        (ROOT / rel).unlink()
                for rel in names:
                    was = tmp / "before" / rel
                    now = ROOT / rel
                    if was.is_file() and (not now.is_file()
                                          or was.read_bytes() != now.read_bytes()):
                        now.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(was, now)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
