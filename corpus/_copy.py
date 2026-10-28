"""A committed copy of this repository, for a corpus proof to break.

The corpus proofs plant into a copy, never into this checkout, for the reason
the engine's own proofs do (proofs/_fixture.py): a proof that died between
the break and the restore would leave the tree it proves half-planted. The copy
is every file git would carry - tracked, or new and not ignored - as it stands
in the working tree, so a proof run before a commit proves what is about to be
committed. It is `git init`-ed and committed, because the gate's corpus is what
git tracks.

The engine that judges the copy is whichever this process imports - in CI the
previous release, installed from requirements-engine.txt, as for the gate
itself.
"""
import os
import pathlib
import shutil
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def fresh():
    files = git(ROOT, "ls-files", "-z", "--cached", "--others", "--exclude-standard").stdout
    root = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-corpus-")) / "wherefore"
    for rel in sorted({p for p in files.split("\0") if p and (ROOT / p).is_file()}):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, root / rel)
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "-c", "user.email=proof@wherefore", "-c", "user.name=proof",
        "commit", "-qm", "this repository, as it stands")
    from wherefore import prove
    prove.set_root(root, temp_prefix="wherefore-corpus-")
    os.environ["WHEREFORE_ROOT"] = str(root)
    return root
