#!/usr/bin/env python3
"""Every generator this repo runs, and a way to run them all while watching.

IN WHEREFORE. Moved from chaotic-pendulums-co's checks/generators.py, with its
docstring and comments kept as they were: the stories are that repository's,
and they are the reason each line is the way it is. What changed is only
where the lists come from. ROOT, GENERATORS, NOT_A_GENERATOR, the observer and
the names it reads are the CLIENT's now, set by configure() - from
wherefore.json, or by a client that keeps its generator list in code, which
is how the pendulum keeps the text its proofs plant faults into where it is.
Each process the runner starts is also told the root, in WHEREFORE_ROOT, for
an observer that does not live inside the client's tree. And roll() runs
whichever gate the client names, rather than one path in one repository.

This is the half of the coverage gate that answers "which files are generated,
and by what". It answers it by RUNNING the generators and recording what they
open for writing - see checks/_observe/sitecustomize.py for the mechanism and
for why a scrape of the source is not good enough.

WHAT IS AND IS NOT A GENERATOR. Twenty-two tracked .py files write into the
repo. That does not make twenty-two generators: a check writing a scratch file,
a tool writing a report, and a release script writing into the untracked dist/
all write, and none of them produce a tracked asset anyone ships. Deciding
which is which IS the inventory, so the decision is written down here, on both
lists, with the reason - never left to a pattern.

ORDER MATTERS and it is not alphabetical. sketch.py writes the two draft sheets
that hero_params.py inlines into the hero; build_dxf.py writes the profiles
that build_handoff.py renders into the hand-over page. A generator that reads
another's output runs after it. If you add one, put it where its inputs already
exist, and the gate will tell you if you got it wrong - its output will not be
byte-identical.

IT IS NOT A STRAIGHT LINE, AND IT CANNOT BE. build_manifest.py writes
spec/manifest.json, and sideview.py, sketch.py and buildpack.py read it - the
REV letters on the drawn views come from there - but it runs LAST, because it
works out which release each asset last changed in by hashing the assets, so it
needs them current before it can be right. Whichever end it goes, something
reads a manifest written before the pass that made it true. So the corpus takes
TWO passes to settle after anything that moves the manifest, a V bump most of
all, and checks/coverage_gate.py tests for exactly that rather than leaving it
to be rediscovered: it regenerates twice and requires the second pass to change
nothing.

Usage:  python3 checks/generators.py        list them, and what each wrote
        python3 checks/generators.py --roll  run them twice, and say what moved
"""
import collections
import hashlib
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

# The client's, set by configure(). See the module docstring.
ROOT = None
OBSERVER = pathlib.Path(__file__).resolve().parent / "_observe"
ENV_PREFIX = "WHEREFORE_"
TEMP_PREFIX = "wherefore-"
GATE_ARGV = [sys.executable, "-m", "wherefore", "gate", "--keep"]
GATE_NAME = "`wherefore gate`"

# script    the file to run - or `-m MODULE`, a module of an installed package,
#           run as `python -m` runs it: how a corpus declares the engine's own
#           skill writer, wherefore.skill, without a copy of it
# cwd       the directory it must run in. This matters: the brand generators
#           are written for `cd code && python3 buildpack.py`, so the pack can
#           be rebuilt from inside the pack, and running them from the repo
#           root silently changes where they write.
# makes     what it is for, in a few words
# stdout_to where its output goes, for the two that print their product to
#           stdout instead of writing it. The redirect is part of the
#           generator, not a detail of how CI happens to call it: leave it in
#           the workflow and the file it makes is invisible to the inventory.
# probe     whether checks/spec_reaches_the_shop.py runs it while sweeping the
#           spec. Default yes. It is off for exactly one generator and the
#           reason is arithmetic: the probe regenerates twice per parameter,
#           46 parameters, and stills.py takes 49 seconds to drive a browser
#           through thirteen renders - 75 minutes of rendering that could not
#           change the answer, because the probe's watched set excludes the
#           stills on purpose. A generator whose output nothing watches does
#           not need re-running ninety-two times to prove it did not move.
# resettle  whether checks/coverage_gate.py's SECOND pass - the one that
#           proves the corpus is a fixed point - has to re-run it. Default yes.
#           Off only where a generator provably cannot be a pass behind:
#           stills.py's one generated input is brand/model/mk3-hero.html, and
#           hero_params.py writes that EARLIER IN THE SAME PASS, so there is no
#           state in which running it twice says anything running it once did
#           not. It reads no manifest, so it is not in the cycle the second
#           pass exists for. Leaving it in cost 49 seconds on every gate run
#           and about twenty minutes across the nine runs the proof makes.
Gen = collections.namedtuple("Gen", "script cwd makes stdout_to probe resettle")
Gen.__new__.__defaults__ = (None, True, True)

GENERATORS = []

# Scripts that write into the repo and are NOT generators of a tracked asset.
# Every one is a deliberate exclusion with its reason, because "it writes, so
# run it" and "it writes, so ignore it" are both wrong, and the difference
# between them is the whole inventory.
NOT_A_GENERATOR = {}


def configure(root, generators, not_a_generator=None, observer=None,
              env_prefix="WHEREFORE_", temp_prefix="wherefore-",
              gate_argv=None, gate_name=None):
    """Say whose corpus this is. Every function below reads these."""
    global ROOT, OBSERVER, ENV_PREFIX, TEMP_PREFIX, GATE_ARGV, GATE_NAME
    ROOT = pathlib.Path(root).resolve()
    GENERATORS[:] = list(generators)
    NOT_A_GENERATOR.clear()
    NOT_A_GENERATOR.update(not_a_generator or {})
    if observer is not None:
        OBSERVER = pathlib.Path(observer)
    ENV_PREFIX, TEMP_PREFIX = env_prefix, temp_prefix
    if gate_argv is not None:
        GATE_ARGV, GATE_NAME = list(gate_argv), gate_name


def configure_from(cfg):
    """configure() from a loaded wherefore.json."""
    configure(cfg.root, cfg.generators, cfg.not_a_generator, cfg.observer_dir,
              cfg.env_prefix, cfg.temp_prefix)


def argv(g):
    """The command that runs generator `g`: `python SCRIPT`, or `python -m MODULE`."""
    if g.script.startswith("-m "):
        return [sys.executable, "-m", g.script[3:].strip()]
    return [sys.executable, g.script]


def run_all(quiet=True, only_resettle=False):
    """Run every generator in order, watching what each one writes.

    Returns (wrote, failures):
      wrote     {absolute path: [generator names, in the order they wrote it]}
      failures  [(generator, stderr tail)]

    A file written by two generators is not an error here - the last one wins
    and the gate compares bytes - but it is worth seeing, so the list keeps
    every writer rather than the last.
    """
    wrote, failures = {}, []
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(OBSERVER)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    env["WHEREFORE_ROOT"] = str(ROOT)
    # Generators that rasterise through a browser must not be skipped quietly;
    # webassets.py catches its own ImportError and buildpack.py prints "web:
    # skipped". Under the gate a skipped stage means uncovered files, which is
    # reported as such rather than passing silently.
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"{TEMP_PREFIX}coverage-"))
    try:
        for i, g in enumerate(GENERATORS):
            if only_resettle and not g.resettle:
                continue
            # Named outside the f-string: a backslash inside one is a syntax
            # error before Python 3.12, and the engine runs on 3.10.
            safe = re.sub(r"[^\w.-]+", "_", g.script)
            log = tmp / f"{i:02d}-{safe}.log"
            env[f"{ENV_PREFIX}WRITE_LOG"] = str(log)
            if not (ROOT / g.cwd).is_dir():
                failures.append((g.script, f"its cwd, {g.cwd!r}, is not a directory in "
                                           f"{ROOT}: nothing ran"))
                if not quiet:
                    print(f"  FAIL {g.script}")
                continue
            r = subprocess.run(argv(g), cwd=ROOT / g.cwd,
                               capture_output=True, text=True, env=env)
            if r.returncode:
                failures.append((g.script, (r.stderr or r.stdout)[-1800:]))
            elif g.stdout_to:
                # The redirect IS the write. Doing it here rather than in the
                # workflow is what puts DERIVATIONS.txt in the inventory at
                # all; a file made by a shell `>` is a file no gate can see.
                out = ROOT / g.stdout_to
                out.write_text(r.stdout, encoding="utf-8")
                wrote.setdefault(os.path.realpath(out), []).append(g.script)
            if not quiet:
                print(f"  {'FAIL' if r.returncode else 'ok  '} {g.script}")
            if log.exists():
                for line in log.read_text(encoding="utf-8",
                                          errors="replace").splitlines():
                    wrote.setdefault(line, []).append(g.script)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return wrote, failures


def tracked():
    """Every tracked file, as an absolute realpath -> repo-relative name."""
    r = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"::error::{ROOT} is not a git repository, or git cannot read it "
                         f"({r.stderr.strip()}). Every judgement here is over what git "
                         f"tracks, so there is nothing to judge until it is one.")
    return {os.path.realpath(ROOT / f): f for f in r.stdout.split("\0") if f}


def roll():
    """Roll the corpus: make every document again, and say what moved.

    THE COMMAND FOR CHANGING A NUMBER. Edit spec/mk3.params.json, run this, and
    every document that number reaches is made again - the drawing sheets, the
    DXFs, all ten STEP exports, the thirteen renders, the hand-over, the bill,
    the derivations, the manifest. Measured on a corner radius, 3.0 to 4.0: 79
    seconds, 41 files.

    NOTHING IN CI DOES THIS. The deploy assembles what is COMMITTED, and that
    is deliberate - the committed bytes are what an archive freezes and what a
    shop downloads - so a spec change that was not rolled through is a preview
    showing the old object and saying nothing about it. That silence is what
    .githooks/pre-push exists to break.

    IT IS THE GATE, RUN FOR A DIFFERENT REASON, and this delegates rather than
    reimplements. The first version of this function did reimplement it, and
    got two passes and a sha256 per file before BOM.xlsx failed it on the first
    run: a workbook records when each member was zipped, so its bytes move
    every time while every cell in it is identical. The gate has always known
    that, along with an ulp in a STEP and a re-encoded PNG, and a second
    comparison that had to learn all three would go wrong in a way nobody would
    notice - it would be quietly WRONGER than the gate, on the same files.

    So what is added here is the name. `coverage_gate` is what it is called
    because it answers "is every file classified and current"; it is also the
    only thing that regenerates the corpus twice and compares it properly, and
    nobody looking for "I changed a dimension, roll it through" would guess it.
    """
    # --keep, AND THE WHOLE COMMAND TURNS ON IT. The gate puts every tracked
    # file back the way it found it when it finishes - it is a check, and a
    # check that leaves a tree rewritten is a check nobody can run safely. This
    # command wants the opposite: the regenerated files are the POINT, and
    # without --keep it reported what would move and then undid it, leaving a
    # person to run something else to get what they had just been told about.
    # The hook was worse off: it said "they have just been regenerated in your
    # working tree", which was false, and it was I who wrote both.
    print("Rolling the corpus: every generator, twice, then compared with what "
          f"is committed.\nThis is {GATE_NAME} - it is the one thing "
          "that knows how to compare\na workbook by its cells and a solid by "
          "its numbers rather than by bytes.\n")
    r = subprocess.run(GATE_ARGV, cwd=ROOT)
    if r.returncode:
        print("\nThe files it named are the corpus catching up with the spec. "
              "Commit them WITH\nthe change that caused them - a document and "
              "the number it prints belong in\none commit.")
    return r.returncode


def main():
    if "--roll" in sys.argv:
        return roll()
    print(f"{len(GENERATORS)} generators, in order\n")
    wrote, failures = run_all(quiet=False)
    names = tracked()
    print()
    by_gen = {}
    for path, gens in wrote.items():
        for g in gens:
            if path in names:
                by_gen.setdefault(g, []).append(names[path])
    for g in GENERATORS:
        got = sorted(set(by_gen.get(g.script, [])))
        print(f"  {g.script:20} {len(got):3} tracked files   {g.makes}")
    untracked = len(wrote) - len([p for p in wrote if p in names])
    print(f"\n{sum(len(v) for v in by_gen.values())} tracked writes, "
          f"{untracked} writes to paths git does not track")
    for script, err in failures:
        print(f"\n::error::{script} failed:\n{err}")
    print("\nWhat they wrote is left in the working tree: `git status` shows what moved.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
