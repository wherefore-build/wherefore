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
        cfg = json.loads((root / "wherefore.json").read_text())
        cfg["sources"] = {"facts": {"path": "facts.json", "why": "the source"}}
        (root / "wherefore.json").write_text(json.dumps(cfg, indent=1))
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


if __name__ == "__main__":
    unittest.main()
