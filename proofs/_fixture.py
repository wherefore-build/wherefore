"""A fresh, committed copy of the fixture company, for a proof to break.

THE ENGINE'S PROOFS PLANT INTO A COPY, not into tests/fixture. A proof edits
the tree it proves and puts it back, and the fixture is part of this
repository's own tree: proving there would leave the engine's own checkout
half-planted the day a proof died between the break and the restore. So each
proof gets a temporary directory with the fixture copied in, `git init`, and
everything committed - the one shape a client always has, since the gate's
corpus is what git tracks.
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ENGINE = HERE.parent
FIXTURE = ENGINE / "tests" / "fixture"


def git(root, *args, **kw):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True,
                          text=True, **kw)


def fresh(name="fixture"):
    """A committed copy of the fixture; the proof harness pointed at it."""
    root = pathlib.Path(tempfile.mkdtemp(prefix=f"wherefore-{name}-")) / "fernhollow"
    shutil.copytree(FIXTURE, root, ignore=shutil.ignore_patterns("__pycache__"))
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "-c", "user.email=proof@wherefore", "-c", "user.name=proof",
        "commit", "-qm", "the fixture, as committed")
    # The engine under test is this checkout's, whether or not it is installed.
    src = str(ENGINE / "src")
    os.environ["PYTHONPATH"] = os.pathsep.join(
        [src] + ([os.environ["PYTHONPATH"]] if os.environ.get("PYTHONPATH") else []))
    os.environ["WHEREFORE_ROOT"] = str(root)
    sys.path.insert(0, src)
    from wherefore import prove
    prove.set_root(root)
    return root
