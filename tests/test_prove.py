"""The proof harness, proved: a proof that cannot fail proves nothing."""
import io
import pathlib
import sys
import unittest
from contextlib import redirect_stdout

from _util import repo
from wherefore import prove


class Harness(unittest.TestCase):
    def setUp(self):
        self.root = repo({"a.txt": "alpha\n", "check.py":
                          "import pathlib, sys\n"
                          "t = pathlib.Path('a.txt').read_text()\n"
                          "print('saw', t.strip())\n"
                          "sys.exit(0 if t == 'alpha\\n' else 1)\n"})
        prove.set_root(self.root)

    def test_edit_puts_the_bytes_back_even_when_the_block_throws(self):
        with self.assertRaises(RuntimeError):
            with prove.Edit("a.txt") as p:
                p.write_text("broken\n")
                raise RuntimeError
        self.assertEqual((self.root / "a.txt").read_text(), "alpha\n")

    def test_an_edit_that_changed_nothing_is_refused(self):
        with self.assertRaises(SystemExit) as e:
            with prove.Edit("a.txt"):
                pass
        self.assertIn("came back byte for byte", str(e.exception.code))
        with prove.Edit("a.txt", unchanged_ok=True):
            pass

    def test_the_exit_code_and_the_words(self):
        results = []
        with redirect_stdout(io.StringIO()) as out, prove.Edit("a.txt") as p:
            p.write_text("beta\n")
            self.assertTrue(prove.check(results, "caught", "check.py", True, ["saw beta"]))
            self.assertFalse(prove.check(results, "wrong words", "check.py", True, ["saw gamma"]))
            self.assertFalse(prove.check(results, "said too much", "check.py", True, ["saw"],
                                         forbid=["beta"]))
        self.assertIn("MISS  wrong words", out.getvalue())

    def test_a_case_that_planted_nothing_is_not_a_miss(self):
        results = []
        with redirect_stdout(io.StringIO()) as out:
            prove.check(results, "stale case", "check.py", True, ["x"], planted=False)
        self.assertIn("NOPLANT  stale case", out.getvalue())
        self.assertEqual(results, [False])
        prove.NOT_PLANTED.clear()

    def test_tree_puts_back_what_a_run_rewrote_beside_the_break(self):
        with prove.Tree():
            (self.root / "a.txt").write_text("rewritten by a generator\n")
        self.assertEqual((self.root / "a.txt").read_text(), "alpha\n")


if __name__ == "__main__":
    unittest.main()
