import json
import pathlib
import tempfile
import unittest

from _util import git, repo, wherefore


class Init(unittest.TestCase):
    def test_init_then_gate_names_every_undecided_file(self):
        root = repo({"README.md": "# a company\n", "facts.json": "{}\n"})
        code, out = wherefore(root, "init", str(root))
        self.assertEqual(code, 0, out)
        # exactly what init wrote, with no source declared yet: init says the
        # gate names every undecided file, and the gate must do it
        git(root, "add", "-A")
        code, out = wherefore(root, "gate")
        self.assertEqual(code, 1, out)
        self.assertIn("README.md is unclassified", out)
        self.assertIn("facts.json is unclassified", out)
        self.assertNotIn("wherefore.json is unclassified", out)

    def test_init_does_not_overwrite(self):
        d = pathlib.Path(tempfile.mkdtemp())
        self.assertEqual(wherefore(d, "init", str(d))[0], 0)
        code, out = wherefore(d, "init", str(d))
        self.assertEqual(code, 1)
        self.assertIn("already exists", out)


class HandedOver(unittest.TestCase):
    def test_a_command_runs_the_clients_own_script_with_what_was_typed(self):
        script = ("import os, sys\n"
                  "print('client gate', sys.argv[1:], os.getcwd() == os.environ['WHEREFORE_ROOT'])\n"
                  "sys.exit(3)\n")
        root = repo({"wherefore.json": {"wherefore": 1, "name": "t", "entry": {
                         "why": "its lists live in the scripts its proofs plant into",
                         "gate": "checks/gate.py",
                         "check retired": ["checks/gate.py", "--retired"]}},
                     "checks/gate.py": script})
        code, out = wherefore(root, "gate", "--keep")
        self.assertEqual(code, 3, out)
        self.assertIn("client gate ['--keep'] True", out)
        code, out = wherefore(root, "check", "retired")
        self.assertEqual(code, 3, out)
        self.assertIn("client gate ['--retired'] True", out)
        # a command not handed over is still the engine's, and says what it lacks
        code, out = wherefore(root, "check", "claims")
        self.assertNotIn("client gate", out)


if __name__ == "__main__":
    unittest.main()
