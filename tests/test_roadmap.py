"""The roadmap, beside the code, and the inbox's ledger: roadmap.json.

A file at the root, not a tracker, so a build can read it with no token: the
company's site copies it and holds the copy with `wherefore check upstream`.
These hold it well-formed, and hold the chain from a request to what shipped:
an item that answers issues carries its plan; an item that shipped says the
release and the feature, and that feature names the same issues; an item whose
id the engine ships as a feature is marked shipped, never left as a promise.
"""
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATES = ("next", "later", "shipped")
KEYS = {"id", "state", "name", "words", "issues", "asked_by", "plan", "since", "feature"}
ISSUE = re.compile(r"^https://github\.com/wherefore-build/wherefore/issues/\d+$")


def roadmap():
    return json.loads((ROOT / "roadmap.json").read_text(encoding="utf-8"))


def features():
    return json.loads((ROOT / "src/wherefore/features.json").read_text(encoding="utf-8"))["features"]


def releases():
    return json.loads((ROOT / "src/wherefore/releases.json").read_text(encoding="utf-8"))["releases"]


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
            self.assertEqual(set(it) - KEYS, set(), f"roadmap item {it['id']!r} has a key this test does not know")

    def test_an_issue_is_one_of_this_repositorys_and_comes_with_a_plan_and_who_asked(self):
        for it in roadmap()["items"]:
            if "issues" in it:
                self.assertTrue(isinstance(it["issues"], list) and it["issues"],
                                f"roadmap item {it['id']!r}: `issues` is a list of the issues it answers")
                for url in it["issues"]:
                    self.assertRegex(url, ISSUE, f"roadmap item {it['id']!r} links something that is not an issue here")
                self.assertTrue(it.get("plan", "").strip(),
                                f"roadmap item {it['id']!r} answers an issue and has no `plan`: say the design intent, "
                                f"in words, when the item is taken on - the release writes it on the issue")
                self.assertIn("asked_by", it, f"roadmap item {it['id']!r} answers an issue and does not say who asked")
            if "asked_by" in it:
                self.assertIn("issues", it, f"roadmap item {it['id']!r} says who asked but not where: `issues` names them")
                self.assertRegex(it["asked_by"], r"^[A-Za-z0-9-]{1,39}$", f"roadmap item {it['id']!r}: asked_by is a GitHub login")

    def test_a_shipped_item_names_its_release_and_its_feature_and_the_feature_answers_the_same_issues(self):
        cut = {r["version"] for r in releases()}
        feats = {f["id"]: f for f in features()}
        for it in roadmap()["items"]:
            if it["state"] != "shipped":
                self.assertNotIn("since", it, f"roadmap item {it['id']!r} is {it['state']} and says since")
                self.assertNotIn("feature", it, f"roadmap item {it['id']!r} is {it['state']} and names a feature")
                continue
            self.assertIn(it.get("since"), cut, f"roadmap item {it['id']!r} shipped in {it.get('since')!r}, a release never cut")
            self.assertIn(it.get("feature"), feats, f"roadmap item {it['id']!r} shipped as {it.get('feature')!r}, a feature the engine does not have")
            for url in it.get("issues", []):
                self.assertIn(url, feats[it["feature"]].get("issues", []),
                              f"roadmap item {it['id']!r} answers {url} and shipped as {it['feature']}, which does not name that issue")

    def test_an_item_the_engine_ships_as_a_feature_is_marked_shipped(self):
        shipped = {f["id"]: f for f in features()}
        for it in roadmap()["items"]:
            if it["id"] in shipped:
                self.assertEqual(it["state"], "shipped",
                                 f"roadmap item {it['id']!r} ({it['name']}) is a feature the engine ships since "
                                 f"{shipped[it['id']]['since']}: mark it shipped, with since and feature, in the change that ships it")


if __name__ == "__main__":
    unittest.main()
