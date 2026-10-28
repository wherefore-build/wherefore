#!/usr/bin/env python3
"""The harness the proof scripts share: break one thing, run a check, put it back.

IN WHEREFORE. Moved from chaotic-pendulums-co's checks/_prove.py, its words
kept. Two things changed. ROOT is the client's: WHEREFORE_ROOT if it is set,
else the nearest directory holding wherefore.json at or above the working
directory, else the working directory - and set_root() for a client whose
proofs import this through a module of their own. And the copy of the tree
Tree takes is named with the client's TEMP_PREFIX.

The repo's rule is that a check is not trusted until it has been shown to FAIL
on the thing it was written for, because first drafts do not - shipped_solids's
first version reported "byte-identical" for a file that had just been modified,
and the first coverage gate reported zero problems while sideview.py was quietly
being run twice. Proving it is therefore part of writing it, and a proof that
lives only in somebody's terminal history is not a proof anybody else has.

Three pieces, all small on purpose:

  Edit   copies a file's bytes aside, hands it to you to break, and puts them
         back in a finally - whatever happens, including when the check under
         test throws. Nest them with `with Edit(a) as p, Edit(b) as q` when a
         break needs two files moved at once. It also requires that the bytes
         actually MOVED: see below.
AND THE BREAK HAS TO BE A BREAK. Most of these plant a fault by replacing a
string: `src.replace("var REST=[0,0];", ...)`. The day that anchor moves - a
generator renames it, a template is rewritten - `replace` returns the text
unchanged, the check under test passes because there is nothing wrong with the
tree, and the proof reports a MISS. That is the good case, and it is the one
the exit code catches.

The bad case is the same no-op inside a case whose check fails ANYWAY, for its
own reasons, saying the words the case asked for: the proof goes green while
proving nothing. Two of these have happened here. So Edit refuses to leave a
block that put the same bytes back, naming the file and saying the anchor has
moved; a block that is only guarding a file it does not mean to change says so
with `Edit(rel, unchanged_ok=True)`.

This is the backstop, not the first line. The proofs that plant a lot of faults
carry their own `plant()` or `swap()` - no_stale_numbers_proof.py,
us_spelling_proof.py, brand_integrity_proof.py, stages_are_the_process_proof.py -
which exit naming the anchor text itself, which is the better message. Edit
catches the cases nobody wrote one for.

This matters more now than it did. A proof used to run on every push, so a
moved anchor was found by the next one; with checks/foundation.py skipping a
proof whose own fingerprint has not moved, a vacuous case could sit green for
as long as nothing else in the proof's inputs changed. The fingerprint keeps
every file a proof edits - checks/selection_holds.py holds it to that, from
these calls - so the push that MOVES an anchor still runs the proof. This is
what makes that run say so.
  Tree   the same for every tracked file, around anything that rewrites what
         it was not handed - the generators, run bare.
  check  runs a command, and requires BOTH the exit code and the words. A check
         that fails for the wrong reason has not caught anything, and without
         the words that is indistinguishable from one that has.
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

def _root():
    env = os.environ.get("WHEREFORE_ROOT")
    if env:
        return pathlib.Path(env).resolve()
    here = pathlib.Path.cwd().resolve()
    for d in (here, *here.parents):
        if (d / "wherefore.json").is_file():
            return d
    return here


ROOT = _root()
TEMP_PREFIX = "wherefore-"


def set_root(root, temp_prefix=None):
    """Prove against this tree. Edit, Tree and run all resolve against it."""
    global ROOT, TEMP_PREFIX
    ROOT = pathlib.Path(root).resolve()
    if temp_prefix is not None:
        TEMP_PREFIX = temp_prefix

# A copy of every tracked file is not an examination of every tracked file. Under
# checks/_observe (CI's read log) the copies are declared as copies, the way
# coverage_gate.py declares its snapshot; anywhere else this does nothing.
try:
    from sitecustomize import copying as _copying
except ImportError:
    import contextlib as _contextlib
    _copying = _contextlib.nullcontext


# EVERY STAMP THIS PROCESS HANDS OUT, STRICTLY INCREASING. Python validates a
# cached .pyc against the source's (mtime, size) with mtime to whole seconds, so
# any two writes inside one second are indistinguishable to it when the bytes
# are the same length - which a planted value usually is. Stamping "now" is
# therefore not enough: the plant and the restore can land on the same second
# and the restore then revalidates the planted .pyc. A counter that only ever
# goes forward gives each write a second of its own.
_STAMP = [0.0]


def _bump(p):
    """Move `p`'s mtime past every stamp handed out so far in this process."""
    _STAMP[0] = max(_STAMP[0] + 1, time.time() + 1)
    os.utime(p, (_STAMP[0],) * 2)


# The Edit blocks that are open right now. run() stamps each one's file before
# it launches anything, because by then the case has written its fault into it
# and that write may be invisible to the import system for the reason above.
_OPEN = []


class Edit:
    """Change a file, run something, put it back - byte for byte, always.

    And require that it WAS changed, unless the block says otherwise with
    `unchanged_ok=True`: a block that put the same bytes back planted nothing,
    and whatever the check said, it did not say it about this fault. See the
    module docstring. The restore happens first and always; the complaint is
    raised only when the block itself did not already fail, because an
    exception on the way out would hide the real one.
    """

    def __init__(self, rel, unchanged_ok=False):
        self.rel = rel
        self.p = ROOT / rel
        self.unchanged_ok = unchanged_ok

    def __enter__(self):
        self.bak = pathlib.Path(tempfile.mkdtemp()) / "bak"
        shutil.copy2(self.p, self.bak)
        _OPEN.append(self)
        return self.p

    def __exit__(self, kind, *rest):
        if self in _OPEN:
            _OPEN.remove(self)
        was = self.bak.read_bytes()
        now = self.p.read_bytes() if self.p.is_file() else None
        shutil.copy2(self.bak, self.p)
        # AND MAKE THE RESTORE VISIBLE TO THE IMPORT SYSTEM. Python validates a
        # cached .pyc against the source's (mtime, size), with mtime to whole
        # seconds. copy2 puts the original mtime back exactly, and a plant of the
        # same character count puts the original size back too - so a .pyc cached
        # while the fault was planted still validates, and a fresh interpreter
        # goes on serving the PLANTED module after the edit was undone. macOS's
        # system Python keeps those in ~/Library/Caches/com.apple.python rather
        # than a __pycache__ beside the file, so a clean tree does not clear them
        # and nothing in the repo shows them: local runs disagreed with CI for
        # hours, with tools/sourced.py reporting a screw length the file did not
        # contain. Stamping the restore past every mtime the planted file can
        # have had invalidates each of those copies.
        _bump(self.p)
        shutil.rmtree(self.bak.parent, ignore_errors=True)
        if kind is None and now == was and not self.unchanged_ok:
            sys.exit(f"::error::{self.rel} came back byte for byte out of a block that "
                     f"meant to break it: the anchor this case plants against has moved, so "
                     f"the check under test was run on a clean tree and proved nothing.\n"
                     f"Find what the case replaces in {self.rel} and give it the text that "
                     f"is there now - or, if the block is only guarding the file and never "
                     f"meant to change it, say Edit({self.rel!r}, unchanged_ok=True).")


class Tree:
    """Every tracked file put back, byte for byte, after running something that
    rewrites the tree - the generators, run bare.

    Edit restores the file it was handed; nothing restored what a generator
    run wrote BESIDE the break. On a Mac that went unseen, because the software
    renderer there reproduces the committed PNGs exactly. On a CI runner the
    generators draw them as different bytes, the next gate run snapshots those
    as "what is committed", and the proof goes on to test the runner's pictures
    against themselves - or, as it did, fails a clean tree on a stamp."""

    def __enter__(self):
        names = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True,
                               text=True, check=True).stdout.split("\0")
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix=f"{TEMP_PREFIX}tree-"))
        self.kept = []
        with _copying():
            for rel in filter(None, names):
                src = ROOT / rel
                if src.is_file():
                    dst = self.dir / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    self.kept.append(rel)
        return self

    def __exit__(self, *exc):
        with _copying():
            for rel in self.kept:
                was, now = self.dir / rel, ROOT / rel
                if not now.is_file() or was.read_bytes() != now.read_bytes():
                    now.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(was, now)
        shutil.rmtree(self.dir, ignore_errors=True)


def run(script, *args):
    # AND THE PLANT HAS TO BE VISIBLE TOO. The case has just written its fault
    # into every file an Edit is holding open, and a write inside the same
    # second as the last one, at the same length, is a write Python's import
    # system cannot see: the check below would go on importing the module as it
    # was. That is the same stale-bytecode hazard the restore guards against,
    # caught on the way in - screws_clamp_proof.py used to carry its own
    # unlink of one file's .pyc because of it, which only ever covered that one.
    for e in _OPEN:
        if e.p.is_file():
            _bump(e.p)
    r = subprocess.run([sys.executable, script, *args], cwd=ROOT,
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


# THE CASES THAT PLANTED NOTHING, kept apart from the ones that planted a fault
# and did not catch it. Both used to print MISS, and they mean opposite things:
#
#   MISS     the fault is in the tree and the check did not see it. Something
#            is wrong with the CHECK, or with the object.
#   NOPLANT  the case never put a fault there at all - the margin it nudges by
#            a fixed amount now absorbs the nudge, the premise it needs is gone
#            from this object, the anchor moved. Nothing is wrong with the
#            check; the CASE has gone stale.
#
# The second is much the more common, and reading it as the first sends somebody
# looking for a defect in a part that does not have one. Edit already refuses a
# block that put the same bytes back, which catches a moved anchor; this catches
# the case whose bytes moved and whose fault did not land, which a case knows
# because it measured its own premise. Pass `planted=` what that measurement
# said. A case that does not measure passes nothing and reads as it always did.
NOT_PLANTED = []


def check(results, name, script, expect_fail, must_say, *args, forbid=(),
          planted=None):
    """Run `script`; require the exit code AND every phrase in `must_say`.

    `forbid` is for a proof whose claim is that something did NOT happen
    alongside something that did - a solid redrawn without its part's letter
    moving. The exit code cannot say that, because the redraw already fails;
    only the absence of the words can.

    `planted` is the case's own answer to "is the fault actually in the tree?",
    measured before the check is run. False reports NOPLANT rather than MISS and
    does not run the check at all: whatever it said, it did not say it about
    this fault. See NOT_PLANTED above.
    """
    if planted is not None and not planted:
        NOT_PLANTED.append(name)
        print(f"  NOPLANT  {name}")
        print(f"        this case measured its own premise and found it absent: "
              f"nothing was broken, so the check was not run. That is a stale "
              f"CASE, not a defect in the object.")
        results.append(False)
        return False
    code, out = run(script, *args)
    good = ((code != 0) == expect_fail and all(m in out for m in must_say)
            and not any(f in out for f in forbid))
    print(f"  {'PASS' if good else 'MISS'}  {name}")
    if not good:
        print(f"        exit {code}; wanted {must_say}"
              + (f", and none of {list(forbid)}" if forbid else ""))
        for f in forbid:
            if f in out:
                print(f"        | said {f!r}")
        for line in out.splitlines():
            if "error" in line.lower() or "UNKNOWN" in line:
                print("        |", line[:150])
    results.append(good)
    return good


def report(results):
    missed = len(results) - sum(results) - len(NOT_PLANTED)
    print(f"\n{sum(results)}/{len(results)} proofs passed")
    if NOT_PLANTED:
        print(f"\n{len(NOT_PLANTED)} case(s) planted NOTHING, and so proved "
              f"nothing either way:")
        for name in NOT_PLANTED:
            print(f"  - {name}")
        print("Go and look at the case, not at the object: size its nudge from "
              "the margin\nit is nudging, or have it plant the premise it needs "
              "rather than assume it.")
        if missed:
            print(f"\n{missed} further case(s) did plant a fault and the check "
                  f"did not catch it.")
    return 0 if all(results) else 1
