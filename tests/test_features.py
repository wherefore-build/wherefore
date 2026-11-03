"""What the engine does, said once: src/wherefore/features.json.

A client that describes the product reads the features from the release it
pins and must say something about each, so a feature that ships reaches every
page that tells people about the product, or that page's build stops. That only
works if the list is whole: a command added to the CLI and to no feature is a
feature nobody is told about. These hold the list whole and well-formed.
"""
import json
import pathlib
import re
import unittest

from wherefore import __version__, cli

SRC = pathlib.Path(__file__).resolve().parents[1] / "src/wherefore"
README = SRC.parents[1] / "README.md"


def features():
    return json.loads((SRC / "features.json").read_text(encoding="utf-8"))["features"]


def version(v):
    return tuple(int(x) for x in v.split("."))


class EveryFeatureIsSaid(unittest.TestCase):
    def test_every_command_belongs_to_exactly_one_feature(self):
        usages = [c["usage"] for c in cli.commands()]
        claimed = [u for f in features() for u in f.get("commands", [])]
        self.assertEqual(sorted(claimed), sorted(set(claimed)), "a command is claimed by two features")
        self.assertEqual(set(usages) - set(claimed), set(),
                         "a command belongs to no feature: say which feature it is in features.json")
        self.assertEqual(set(claimed) - set(usages), set(), "a feature names a command the CLI does not have")

    def test_each_feature_has_a_name_a_release_and_words(self):
        ids = [f["id"] for f in features()]
        self.assertEqual(len(ids), len(set(ids)), "two features share an id")
        for f in features():
            self.assertTrue(re.fullmatch(r"[a-z][a-z0-9-]*", f["id"]), f["id"])
            self.assertTrue(f.get("name", "").strip(), f["id"])
            self.assertTrue(re.fullmatch(r"\d+\.\d+\.\d+", f.get("since", "")), f["id"])
            self.assertLessEqual(version(f["since"]), version(__version__),
                                 f"{f['id']} says it arrived in {f['since']}, after this release")
            self.assertTrue(bool(f.get("commands")) != bool(f.get("says", "").strip()),
                            f"{f['id']} needs its words from exactly one place: commands, or says")

    def test_the_readme_lists_every_feature(self):
        readme = README.read_text(encoding="utf-8")
        for f in features():
            self.assertIn(f"**{f['name']}** (since {f['since']})", readme)


if __name__ == "__main__":
    unittest.main()
