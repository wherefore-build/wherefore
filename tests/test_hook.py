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

    def test_nothing_is_skipped_unless_the_corpus_says_so(self):
        # Prose used to be skipped by default, which excused a Markdown
        # template a generator reads.
        head = self.commit("README.md", lambda s: s + "\nMore prose.\n")
        code, out = push(self.root, f"refs/heads/x {head} refs/heads/x {self.base}\n")
        self.assertEqual(code, 0, out)
        self.assertIn("rolling the corpus", out)

    def test_what_the_corpus_declares_skippable_skips_the_roll(self):
        def skip_prose(s):
            d = json.loads(s); d["hook"] = {"skip": [r"\.md$"]}; return json.dumps(d, indent=1)
        self.base = self.commit("wherefore.json", skip_prose)
        head = self.commit("README.md", lambda s: s + "\nMore prose.\n")
        code, out = push(self.root, f"refs/heads/x {head} refs/heads/x {self.base}\n")
        self.assertEqual(code, 0, out)
        self.assertNotIn("rolling the corpus", out)

    def test_a_push_git_cannot_describe_rolls_rather_than_passes(self):
        # A remote tip this clone has never fetched: git cannot diff against it.
        def cheaper(s):
            d = json.loads(s); d["product"]["price_usd"] = 95; return json.dumps(d, indent=1)
        head = self.commit("facts.json", cheaper)
        unknown = "1" * 40
        code, out = push(self.root, f"refs/heads/x {head} refs/heads/x {unknown}\n")
        self.assertEqual(code, 1, out)
        self.assertIn("git cannot say what this push changes", out)
        self.assertIn("STOPPED", out)

    def test_the_first_push_of_a_new_repository_is_judged(self):
        # One root commit, no origin/main: there is nothing to diff against.
        root = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-hook-")) / "first"
        shutil.copytree(ENGINE / "tests/fixture", root,
                        ignore=shutil.ignore_patterns("__pycache__"))
        facts = root / "facts.json"
        d = json.loads(facts.read_text()); d["product"]["price_usd"] = 95
        facts.write_text(json.dumps(d, indent=1))
        git(root, "init", "-q")
        git(root, "add", "-A")
        git(root, "-c", "user.email=t@w", "-c", "user.name=t", "commit", "-qm", "first")
        head = git(root, "rev-parse", "HEAD").stdout.strip()
        code, out = push(root, f"refs/heads/main {head} refs/heads/main {'0' * 40}\n")
        self.assertEqual(code, 1, out)
        self.assertIn("STOPPED", out)

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
        # run by the interpreter the engine is installed in, not whatever
        # `python3` is first on PATH
        self.assertIn(sys.executable, hook.read_text())
        code, out = wherefore(self.root, "hook", "install")
        self.assertEqual(code, 0, out)       # its own hook, it may write again
        hook.write_text("#!/bin/sh\necho someone else's\n")
        code, out = wherefore(self.root, "hook", "install")
        self.assertEqual(code, 1)
        self.assertIn("is not this hook", out)


if __name__ == "__main__":
    unittest.main()
