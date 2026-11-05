"""The roadmap, beside the code: roadmap.json.

A file at the root, not a tracker, so a build can read it with no token: the
company's site copies it and holds the copy with `wherefore check upstream`.
These hold it well-formed, and hold the one rule that keeps it honest - an
item the release already ships has left the roadmap, in the same change that
shipped it.
"""
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATES = ("next", "later")
ISSUE = re.compile(r"^https://github\.com/wherefore-build/wherefore/issues/\d+$")


def roadmap():
    return json.loads((ROOT / "roadmap.json").read_text(encoding="utf-8"))


def features():
    return json.loads((ROOT / "src/wherefore/features.json").read_text(encoding="utf-8"))["features"]


class TheRoadmapIsHonest(unittest.TestCase):
    def test_it_says_what_it_is(self):
        self.assertTrue(roadmap().get("note", "").strip(), "roadmap.json says what it is in `note`")

    def test_each_item_is_whole(self):
        items = roadmap()["items"]
        self.assertTrue(items, "the roadmap has at least one item, or says why in the note")
        ids = [it["id"] for it in items]
        self.assertEqual(len(ids), len(set(ids)), "two roadmap items share an id")
        for it in items:
            for key in ("id", "state", "name", "words"):
                self.assertTrue(it.get(key, "").strip(), f"roadmap item {it.get('id')!r} has no {key}")
            self.assertIn(it["state"], STATES, f"roadmap item {it['id']!r} is {it['state']!r}, not one of {STATES}")
            self.assertEqual(set(it) - {"id", "state", "name", "words", "issue"}, set(),
                             f"roadmap item {it['id']!r} has a key this test does not know")

    def test_an_issue_is_one_of_this_repositorys(self):
        for it in roadmap()["items"]:
            if "issue" in it:
                self.assertRegex(it["issue"], ISSUE, f"roadmap item {it['id']!r} links something that is not an issue here")

    def test_a_shipped_feature_has_left_the_roadmap(self):
        shipped = {f["id"]: f for f in features()}
        for it in roadmap()["items"]:
            self.assertNotIn(it["id"], shipped,
                             f"roadmap item {it['id']!r} ({it['name']}) is a feature the engine ships since "
                             f"{shipped.get(it['id'], {}).get('since')}: take it off the roadmap in the change that ships it")


if __name__ == "__main__":
    unittest.main()
