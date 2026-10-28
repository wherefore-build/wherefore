import json
import shutil
import tempfile
import unittest
import pathlib

from _util import ENGINE, git, wherefore
import subprocess, os, sys
from _util import SRC


def push(root, refs):
    env = dict(os.environ, PYTHONPATH=str(SRC), WHEREFORE_ROOT=str(root))
    r = subprocess.run([sys.executable, "-m", "wherefore", "hook", "pre-push"], cwd=root,
                       env=env, input=refs, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


class Hook(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-hook-")) / "fernhollow"
        shutil.copytree(ENGINE / "tests/fixture", self.root,
                        ignore=shutil.ignore_patterns("__pycache__"))
        git(self.root, "init", "-q")
        git(self.root, "add", "-A")
        git(self.root, "-c", "user.email=t@w", "-c", "user.name=t", "commit", "-qm", "base")
        self.base = git(self.root, "rev-parse", "HEAD").stdout.strip()

    def commit(self, rel, edit):
        p = self.root / rel
        p.write_text(edit(p.read_text()))
        git(self.root, "-c", "user.email=t@w", "-c", "user.name=t", "commit", "-qam", rel)
        return git(self.root, "rev-parse", "HEAD").stdout.strip()

    def test_prose_alone_skips_the_roll(self):
        head = self.commit("README.md", lambda s: s + "\nMore prose.\n")
        code, out = push(self.root, f"refs/heads/x {head} refs/heads/x {self.base}\n")
        self.assertEqual(code, 0, out)
        self.assertNotIn("rolling the corpus", out)

    def test_a_source_moved_without_its_documents_stops_the_push(self):
        def cheaper(s):
            d = json.loads(s); d["product"]["price_usd"] = 95; return json.dumps(d, indent=1)
        head = self.commit("facts.json", cheaper)
        code, out = push(self.root, f"refs/heads/x {head} refs/heads/x {self.base}\n")
        self.assertEqual(code, 1, out)
        self.assertIn("STOPPED", out)
        self.assertIn("site/index.html regenerated DIFFERENT", out)

    def test_install_writes_an_executable_hook_and_refuses_to_replace_another(self):
        code, out = wherefore(self.root, "hook", "install")
        self.assertEqual(code, 0, out)
        hook = self.root / ".git/hooks/pre-push"
        self.assertTrue(os.access(hook, os.X_OK))
        hook.write_text("#!/bin/sh\necho someone else's\n")
        code, out = wherefore(self.root, "hook", "install")
        self.assertEqual(code, 1)
        self.assertIn("is not this hook", out)


if __name__ == "__main__":
    unittest.main()
