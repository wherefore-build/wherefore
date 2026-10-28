"""Phase 5: a company with no pendulum code compiles. init's shape, build, gate, prove."""
import shutil
import tempfile
import unittest
import pathlib

from _util import ENGINE, git, wherefore


class Compiles(unittest.TestCase):
    def test_from_sources_to_a_proven_corpus(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-p5-")) / "fernhollow"
        shutil.copytree(ENGINE / "tests/fixture", root,
                        ignore=shutil.ignore_patterns("__pycache__"))
        # Only the sources: every generated document deleted before the first commit.
        for rel in ("site/index.html", "deck/one-pager.svg", "deck/speaker-notes.txt"):
            (root / rel).unlink()
        git(root, "init", "-q")
        git(root, "add", "-A")
        git(root, "-c", "user.email=t@w", "-c", "user.name=t", "commit", "-qm", "sources")

        # The first build makes the documents and names each as untracked: the
        # right first instruction, because nothing can hold a file git does not keep.
        code, out = wherefore(root, "build")
        self.assertEqual(code, 1, out)
        for rel in ("site/index.html", "deck/one-pager.svg", "deck/speaker-notes.txt"):
            self.assertIn(f"{rel} is a generated file git doesn't track", out)
        git(root, "add", "-A")
        code, out = wherefore(root, "gate")
        self.assertEqual(code, 0, out)
        self.assertIn("UNKNOWN        0", out)
        git(root, "-c", "user.email=t@w", "-c", "user.name=t", "commit", "-qm",
            "the documents, with the sources that made them")
        for name in ("retired", "reach", "claims"):
            code, out = wherefore(root, "check", name)
            self.assertEqual(code, 0, f"{name}:\n{out}")
        code, out = wherefore(root, "prove")
        self.assertEqual(code, 0, out)
        self.assertIn("1/1 proofs held", out)
        self.assertEqual(git(root, "status", "--porcelain").stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
