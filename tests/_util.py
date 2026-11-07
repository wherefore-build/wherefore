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


def scripted(inventory, files=None, gens=()):
    """A corpus shaped like the pendulum: wherefore.json hands `list` and `gate`
    to scripts of its own, which configure the engine - and its inventory lives
    in checks/inventory.json, read by those scripts, never in wherefore.json."""
    listed = ", ".join(f"G.Gen({g!r}, 'gen', 'out/{g}, a page')" for g in gens)
    gen_script = ("import pathlib, sys\n"
                  "from wherefore import generators as G\n"
                  "ROOT = pathlib.Path(__file__).resolve().parents[1]\n"
                  f"G.configure(ROOT, [{listed}])\n"
                  "if __name__ == '__main__':\n    sys.exit(G.main())\n")
    gate_script = ("import json, pathlib, sys\n"
                   "import generators\n"
                   "from wherefore import gate\n"
                   "ROOT = pathlib.Path(__file__).resolve().parents[1]\n"
                   "INV = ROOT / 'checks/inventory.json'\n"
                   "gate.configure(ROOT, lambda: json.loads(INV.read_text()), None, 'checks/inventory.json',\n"
                   "               None, None, gate.COMPARE)\n"
                   "if __name__ == '__main__':\n    sys.exit(gate.main())\n")
    tree = {"wherefore.json": {"wherefore": 1, "name": "pendulum-shaped", "entry": {
                "why": "its lists live in the scripts its proofs plant into",
                "list": "checks/generators.py", "gate": "checks/coverage_gate.py"}},
            "checks/generators.py": gen_script, "checks/coverage_gate.py": gate_script,
            "checks/inventory.json": inventory, ".gitignore": "__pycache__/\n"}
    tree.update(files or {})
    return repo(tree)
