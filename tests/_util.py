import json
import os
import pathlib
import subprocess
import sys
import tempfile

ENGINE = pathlib.Path(__file__).resolve().parents[1]
SRC = ENGINE / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def repo(files):
    """A committed git repository holding `files` ({path: text})."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-test-"))
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text if isinstance(text, str) else json.dumps(text, indent=1) + "\n",
                     encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "-c", "user.email=t@wherefore", "-c", "user.name=t", "commit", "-qm", "x")
    return root


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def wherefore(root, *args):
    env = dict(os.environ, PYTHONPATH=str(SRC), WHEREFORE_ROOT=str(root))
    r = subprocess.run([sys.executable, "-m", "wherefore", *args], cwd=root, env=env,
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr
