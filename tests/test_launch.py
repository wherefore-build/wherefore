"""Launches that wait: src/wherefore/launch.py and `wherefore check launch`.

A thing moves to a stage only when what that stage needs is there. What can
go wrong: a requirement of a later stage asked of an earlier thing, or an
earlier stage's not asked of a later one; something public before its stage
let through; a name split by markup not found, so a page that says it
fails; a field the thing lacks treated as met; the next stage's wants not
said; the one-thing form (a site's own status) not read; a section that
cannot be meant accepted; the engine's own roadmap not holding.
"""
import json
import unittest

from _util import ENGINE, repo, wherefore
from wherefore import config as cfgmod, launch

LADDER = {"of": {"source": "facts", "at": "features", "id": "id", "stage": "stage"},
          "stages": ["building", "beta", "live"],
          "needs": {"beta": [{"file": "docs/{id}.md", "why": "a help doc"},
                             {"in": "CHANGELOG.md", "says": "{name} (beta)", "why": "the changelog marks it beta"}],
                    "live": [{"in": "site/**", "says": "{name}", "why": "the site names it"},
                             {"has": "price", "why": "a price"}]},
          "until": {"beta": [{"in": "site/**", "lacks": "{name}", "why": "nothing public names it"}]}}


def corpus(features, files=None, section=None, facts_extra=None):
    doc = {"wherefore": 1, "name": "kettles", "sources": {"facts": {"path": "facts.json", "why": "the source"}},
           "launch": LADDER if section is None else section}
    facts = {"features": features, **(facts_extra or {})}
    return repo({"wherefore.json": doc, "facts.json": facts, **(files or {})})


def found(root):
    return {t["id"]: t for lad in launch.find(cfgmod.load(root))["ladders"] for t in lad["things"]}


def missing(t):
    return [r["why"] for r in t["now"] if not r["held"]]


class WhatEachStageAsks(unittest.TestCase):
    def test_a_stage_asks_its_own_needs_and_every_earlier_one_and_nothing_later(self):
        root = corpus([{"id": "lid", "name": "Steel lid", "stage": "beta"}],
                      {"docs/lid.md": "# Steel lid\n", "CHANGELOG.md": "Steel lid (beta)\n", "site/index.html": "<p>Steel lid</p>\n"})
        t = found(root)["lid"]
        self.assertEqual(missing(t), [])
        self.assertEqual({r["stage"] for r in t["now"]}, {"beta"}, "live's needs are not asked of a beta thing")
        self.assertEqual([w["why"] for w in t["next"]["wants"] if not w["held"]], ["a price"],
                         "what live still waits on is said: the site names it already")

    def test_a_later_stage_still_needs_what_an_earlier_one_did(self):
        root = corpus([{"id": "lid", "name": "Steel lid", "stage": "live", "price": 12}],
                      {"CHANGELOG.md": "Steel lid (beta)\n", "site/index.html": "<p>Steel lid</p>\n"})
        self.assertEqual(missing(found(root)["lid"]), ["a help doc"], "beta's help doc is still live's")

    def test_nothing_public_before_its_stage(self):
        root = corpus([{"id": "spout", "name": "Pour spout", "stage": "building"}],
                      {"site/index.html": "<p>Coming soon: the <em>Pour</em> spout.</p>\n"})
        t = found(root)["spout"]
        self.assertEqual(missing(t), ["nothing public names it"],
                         "a name split by a tag is still said")
        self.assertIn("site/index.html says", t["now"][0]["said"])

    def test_a_field_the_thing_lacks_is_a_requirement_it_cannot_meet(self):
        root = corpus([{"id": "lid", "stage": "beta"}], {"docs/lid.md": "x\n", "CHANGELOG.md": "x\n"})
        t = found(root)["lid"]
        self.assertEqual(missing(t), ["the changelog marks it beta"])
        self.assertIn("it has no `name` to say", [r["said"] for r in t["now"] if not r["held"]][0])

    def test_a_stage_that_is_not_one_of_the_stages_fails(self):
        root = corpus([{"id": "lid", "name": "Steel lid", "stage": "gamma"}])
        code, out = wherefore(root, "check", "launch")
        self.assertEqual(code, 1, out)
        self.assertIn("lid is at 'gamma', which is not one of the stages (building, beta, live)", out)


class TheCheck(unittest.TestCase):
    def test_it_fails_in_the_sections_own_words_and_says_what_waits(self):
        root = corpus([{"id": "lid", "name": "Steel lid", "stage": "beta"},
                       {"id": "spout", "name": "Pour spout", "stage": "building"}],
                      {"CHANGELOG.md": "Steel lid (beta)\n"})
        code, out = wherefore(root, "check", "launch")
        self.assertEqual(code, 1, out)
        self.assertIn("::error::lid is beta, and from beta it needs a help doc: no tracked file is docs/lid.md", out)
        self.assertIn("spout     building  1 held; beta waits on a help doc; the changelog marks it beta", out)
        self.assertIn("1 of 2 things lacks what its stage needs", out)

    def test_it_passes_when_every_thing_has_its_stage_and_counts_who_could_move(self):
        root = corpus([{"id": "lid", "name": "Steel lid", "stage": "beta", "price": 12}],
                      {"docs/lid.md": "x\n", "CHANGELOG.md": "Steel lid (beta)\n", "site/a.html": "<p>Steel lid</p>\n"})
        code, out = wherefore(root, "check", "launch")
        self.assertEqual(code, 0, out)
        self.assertIn("ready for live", out)
        self.assertIn("ok   1 thing in facts.json, each at a stage it has everything for; 1 ready for the next", out)

    def test_json_is_every_thing_its_stage_and_each_requirement(self):
        root = corpus([{"id": "lid", "name": "Steel lid", "stage": "building"}])
        code, out = wherefore(root, "check", "launch", "--json")
        self.assertEqual(code, 0, out)
        got = json.loads(out)
        self.assertEqual([lad["name"] for lad in got["ladders"]], ["default"], "one ladder is the default one")
        self.assertEqual(got["ladders"][0]["stages"], ["building", "beta", "live"])
        t = got["ladders"][0]["things"][0]
        self.assertEqual((t["id"], t["stage"], t["next"]["stage"], t["next"]["ready"]), ("lid", "building", "beta", False))
        self.assertEqual(t["now"][0], {"part": "until", "stage": "beta", "why": "nothing public names it", "held": True,
                                       "said": "nothing in site/** says “Steel lid”"})

    def test_without_a_section_it_says_so_and_passes(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "t"}})
        code, out = wherefore(root, "check", "launch")
        self.assertEqual(code, 0, out)
        self.assertIn("no launch section", out)

    def test_the_corpus_itself_as_the_one_thing(self):
        section = {"of": {"source": "facts", "stage": "site.status"}, "stages": ["draft", "launched"],
                   "needs": {"launched": [{"in": "site/**", "lacks": "{site.banner}", "why": "no draft banner"}]}}
        root = corpus([], {"site/index.html": "<p>Not launched yet.</p>\n"}, section,
                      {"site": {"status": "launched", "banner": "Not launched yet."}})
        code, out = wherefore(root, "check", "launch")
        self.assertEqual(code, 1, out)
        self.assertIn("::error::kettles is launched, and from launched it needs no draft banner: site/index.html says", out)


class SeveralLadders(unittest.TestCase):
    SITE = {"of": {"source": "facts", "stage": "site.status"}, "stages": ["draft", "launched"],
            "needs": {"launched": [{"in": "site/**", "lacks": "Not launched yet.", "why": "no draft banner"}]}}

    def two(self, features, files, status="draft"):
        return corpus(features, files, {"ladders": {"features": LADDER, "site": self.SITE}},
                      {"site": {"status": status}})

    def test_each_ladder_holds_its_own_things_by_its_own_stages(self):
        root = self.two([{"id": "lid", "name": "Steel lid", "stage": "beta"}],
                        {"docs/lid.md": "x\n", "CHANGELOG.md": "Steel lid (beta)\n",
                         "site/index.html": "<p>Not launched yet.</p>\n"})
        got = launch.find(cfgmod.load(root))["ladders"]
        self.assertEqual([(lad["name"], lad["stages"][-1], [t["id"] for t in lad["things"]]) for lad in got],
                         [("features", "live", ["lid"]), ("site", "launched", ["kettles"])])
        code, out = wherefore(root, "check", "launch")
        self.assertEqual(code, 0, out)
        self.assertIn("features  building · beta · live  (facts.json)", out)
        self.assertIn("site  draft · launched  (facts.json)", out)
        self.assertIn("ok   2 things on 2 ladders, each at a stage it has everything for", out)

    def test_a_fault_names_its_ladder(self):
        root = self.two([{"id": "lid", "name": "Steel lid", "stage": "building"}],
                        {"site/index.html": "<p>Not launched yet.</p>\n"}, status="launched")
        code, out = wherefore(root, "check", "launch")
        self.assertEqual(code, 1, out)
        self.assertIn("::error::site: kettles is launched, and from launched it needs no draft banner:", out)
        self.assertNotIn("::error::features:", out, "the feature, still building, has everything building asks")

    def test_two_ladders_on_the_same_things_are_refused(self):
        doc = {"wherefore": 1, "name": "t", "sources": {"facts": {"path": "facts.json", "why": "x"}},
               "launch": {"ladders": {"a": LADDER, "b": {**LADDER, "of": {"path": "facts.json", "at": "features", "stage": "s"}}}}}
        with self.assertRaises(cfgmod.ConfigError) as e:
            launch.validate(doc)
        self.assertIn("`launch.ladders.b` reads the same things as `a` (facts.json, features): a thing is on one ladder",
                      str(e.exception))

    def test_beside_ladders_only_why(self):
        doc = {"wherefore": 1, "name": "t", "sources": {"facts": {"path": "facts.json", "why": "x"}},
               "launch": {"ladders": {"a": LADDER}, "stages": ["x", "y"]}}
        with self.assertRaises(cfgmod.ConfigError) as e:
            launch.validate(doc)
        self.assertIn("stages belongs to a ladder", str(e.exception))
        doc["launch"] = {"ladders": {"Features!": LADDER}}
        with self.assertRaises(cfgmod.ConfigError) as e:
            launch.validate(doc)
        self.assertIn("a ladder's name is lower case", str(e.exception))
        doc["launch"] = {"ladders": {"a": {**LADDER, "needs": {"beta": [{"has": "x"}]}}}}
        with self.assertRaises(cfgmod.ConfigError) as e:
            launch.validate(doc)
        self.assertIn("`launch.ladders.a.needs.beta[0]` has no `why`", str(e.exception))


class WhatCannotBeMeant(unittest.TestCase):
    def refused(self, section, words):
        doc = {"wherefore": 1, "name": "t", "sources": {"facts": {"path": "facts.json", "why": "x"}}, "launch": section}
        with self.assertRaises(cfgmod.ConfigError) as e:
            launch.validate(doc)
        self.assertIn(words, str(e.exception))

    def test_refusals(self):
        base = {"of": {"source": "facts", "at": "f", "stage": "stage"}, "stages": ["a", "b"]}
        self.refused({**base, "stages": ["a"]}, "at least two")
        self.refused({**base, "needs": {"c": [{"has": "x", "why": "y"}]}}, "not one of the stages")
        self.refused({**base, "until": {"a": [{"has": "x", "why": "y"}]}}, "before the first stage")
        self.refused({**base, "needs": {"b": [{"has": "x"}]}}, "has no `why`")
        self.refused({**base, "needs": {"b": [{"has": "x", "file": "y", "why": "z"}]}}, "exactly one")
        self.refused({**base, "needs": {"b": [{"says": "x", "why": "z"}]}}, "`in` names the files")
        self.refused({**base, "of": {"source": "nope", "at": "f", "stage": "s"}}, "not a source")
        self.refused({**base, "of": {"path": "x.json", "source": "facts", "stage": "s"}}, "one way")
        self.refused({**base, "colour": "red"}, "which it does not take")


class TheEnginesOwnRoadmap(unittest.TestCase):
    def test_every_item_holds_to_its_stage(self):
        code, out = wherefore(ENGINE, "check", "launch")
        self.assertEqual(code, 0, out)
        self.assertIn("in roadmap.json, each at a stage it has everything for", out)


if __name__ == "__main__":
    unittest.main()
