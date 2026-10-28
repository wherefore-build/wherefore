import json
import unittest

from _util import repo
from wherefore import config


def base(**over):
    d = {"wherefore": 1, "name": "t", "sources": {"facts": {"path": "facts.json"}},
         "generators": [], "inventory": {"authored": {"rules": [["*", "everything"]]}}}
    d.update(over)
    return d


class Refusals(unittest.TestCase):
    def refused(self, doc, words):
        root = repo({"wherefore.json": doc, "facts.json": {}})
        with self.assertRaises(config.ConfigError) as e:
            config.load(root)
        self.assertIn(words, str(e.exception.code))

    def test_schema(self):
        self.refused(base(wherefore=2), "`wherefore` must be 1")

    def test_command_is_reserved(self):
        self.refused(base(generators=[{"command": ["make"], "script": "x.py", "cwd": ".",
                                       "makes": "x"}]), "`command`, which is reserved")

    def test_exemption_needs_a_reason(self):
        self.refused(base(generators=[{"script": "x.py", "cwd": ".", "makes": "x",
                                       "probe": False}]), "carries no reason")
        self.refused(base(not_a_generator={"tools/report.py": ""}), "carries no reason")
        self.refused(base(compare=[{"glob": "*.xlsx", "as": "xlsx-cells"}]), "carries no reason")
        self.refused(base(inventory={"authored": {"rules": [["*.md", " "]]}}), "carries no reason")

    def test_a_generator_listed_twice(self):
        g = {"script": "x.py", "cwd": ".", "makes": "x"}
        self.refused(base(generators=[g, dict(g)]), "is listed twice")

    def test_unknown_adapter(self):
        self.refused(base(sources={"facts": {"path": "facts.json", "adapter": "yaml"}}),
                     "is not one this engine has")


class Includes(unittest.TestCase):
    def test_a_section_from_its_own_file_is_written_back_there(self):
        inv = {"authored": {"rules": [["*", "everything"]]}, "captured": {"groups": {}}}
        root = repo({"wherefore.json": base(inventory="checks/inventory.json"),
                     "checks/inventory.json": inv, "facts.json": {}})
        cfg = config.load(root)
        self.assertEqual(cfg.where("inventory"), "checks/inventory.json")
        self.assertEqual(cfg.doc["inventory"], inv)
        inv["captured"]["groups"]["g"] = {"files": [], "why": "w", "no_stamp": "n"}
        cfg.write_section("inventory", inv)
        self.assertEqual(json.loads((root / "checks/inventory.json").read_text())["captured"]
                         ["groups"]["g"]["why"], "w")
        self.assertEqual(json.loads((root / "wherefore.json").read_text())["inventory"],
                         "checks/inventory.json")

    def test_root_is_found_upward(self):
        root = repo({"wherefore.json": base(), "facts.json": {}, "deep/er/x.txt": "x"})
        self.assertEqual(config.find_root(root / "deep/er"), root.resolve())


if __name__ == "__main__":
    unittest.main()
