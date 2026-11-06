"""Every feature, in motion: src/wherefore/motion.py and the claims in features.json.

A clip is compiled from facts, so what can go wrong is the compiling: a claim
too long to read, a scene that asks more words a second than a person can
take, a clip too short to say anything or too long to watch, a command typed
that the CLI does not have, a line printed that the command never prints, a
page that drops a scene's words. These hold each, for every feature.
"""
import json
import os
import re
import subprocess
import sys
import unittest

from _util import ENGINE, SRC, repo, wherefore
from wherefore import cli, motion


class EveryClaimReads(unittest.TestCase):
    def test_every_feature_has_a_claim_of_at_most_twelve_words_that_is_a_sentence(self):
        for f in motion.features():
            claim = f.get("claim", "")
            self.assertTrue(claim.strip(), f"{f['id']} has no claim: the one sentence its clip ends on")
            self.assertLessEqual(motion.words(claim), motion.CLAIM_WORDS,
                                 f"{f['id']}: the claim is {motion.words(claim)} words; a clip reads {motion.CLAIM_WORDS} at most")
            self.assertRegex(claim, r"[.!?]$", f"{f['id']}: the claim is a sentence, ending in a full stop")


class EveryMechanismIsDrawn(unittest.TestCase):
    """The mechanism scene: each feature names one of four, and in a corpus the
    scene is drawn from that corpus's own numbers, said again in its caption."""

    def test_every_feature_names_a_mechanism_the_engine_draws(self):
        from wherefore import mechanism
        for f in motion.features():
            self.assertIn(f.get("mechanism"), mechanism.KINDS, f"{f['id']} names no mechanism, or one the engine does not draw")

    def test_in_a_corpus_the_scene_is_drawn_from_its_numbers(self):
        from wherefore import config as cfgmod, mechanism
        root = repo({"wherefore.json": {"wherefore": 1, "name": "t",
                                        "sources": {"facts": {"path": "facts.json", "why": "the source"}},
                                        "generators": [{"script": "make.py", "cwd": "gen", "makes": "site/index.html"}],
                                        "inventory": {"authored": {"rules": [["*.py", "code"], ["facts.json", "the source"],
                                                                             ["wherefore.json", "this"], ["*.md", "prose"]]}},
                                        "reach": {"probes": [{"name": "the name", "fact": "company.name", "reaches": "the page",
                                                              "files": ["site/index.html"]}]}},
                     "facts.json": {"company": {"name": "Fernhollow", "city": "Porto"}, "price": 89},
                     "gen/make.py": "print('x')\n", "README.md": "Fernhollow, in Porto.\n",
                     "site/index.html": "<p>Fernhollow costs 89.</p>\n", "site/about/index.html": "<p>Porto, 89.</p>\n"})
        cfg = cfgmod.load(root)
        data = mechanism.gather(cfg, [{"id": "x", "state": "shipped", "feature": "gate", "issues": ["u/1", "u/2"]}],
                                [{"version": "0.1.0"}])
        self.assertEqual(data["sort"], {"files": 6, "built": 2, "authored": 4, "captured": 0, "left": 0})
        self.assertEqual((data["hold"]["facts"], data["hold"]["pages"], data["hold"]["probe"]), (3, 2, {"fact": "company.name", "files": 1}))
        self.assertEqual((data["compare"]["places"], data["compare"]["files"]), (["site"], 2))
        self.assertEqual(data["handover"], {"issues": 2, "items": 1, "releases": 1,
                                            "steps": ["an issue", "the plan, on it", "the release", "the note that closes it"]})
        boards = {b["id"]: b for b in motion.storyboards(["gate", "reach", "scan", "docs"], root, {}, cfg)}
        # the handover is the ledger's: a corpus names its copy with motion.roadmap, else the engine's own is read
        own = motion.ledger_items(ENGINE)
        handed = (f"{sum(len(it['issues']) for it in own if it.get('issues'))} issues answered by "
                  f"{sum(1 for it in own if it.get('issues'))} roadmap items across {len(motion.releases())} releases")
        for fid, kind, said in (("gate", "sort", "6 files tracked: 2 built by a script"), ("reach", "hold", "3 facts in facts.json, and 2 pages"),
                                ("scan", "compare", "pages in site; 0 disagree"), ("docs", "handover", handed)):
            sc = next(s for s in boards[fid]["scenes"] if s["kind"] == "mechanism")
            self.assertEqual(sc["mechanism"], kind)
            self.assertIn(said, sc["caption"], fid)
            page = motion.page(boards[fid])
            self.assertIn(f'<div class="viz {kind}">', page)
            self.assertIn(motion.html.escape(sc["caption"]), page)
        for b in boards.values():
            self.assertLessEqual(b["duration"], motion.MAX_SECONDS, f"{b['id']} runs {b['duration']} s with its mechanism")

    def test_without_a_corpus_only_the_handover_is_drawn(self):
        boards = motion.storyboards(["gate", "docs"], ENGINE, {})
        self.assertFalse(any(s["kind"] == "mechanism" for s in boards[0]["scenes"]), "gate's sort scene needs a corpus")
        self.assertTrue(any(s["kind"] == "mechanism" for s in boards[1]["scenes"]), "the ledger is the engine's own")


class EveryStoryboardHolds(unittest.TestCase):
    def setUp(self):
        self.boards = motion.storyboards(root=ENGINE)
        self.heads = {motion.head(c["usage"]) for c in cli.commands()}
        self.printed = set()
        for r in motion.releases().values():
            self.printed.update((r.get("shows") or {}).get("output", []))
        for _cmd, lines in motion.docs_examples():
            self.printed.update(lines)

    def test_there_is_one_per_feature_in_order_with_the_scenes_a_clip_has(self):
        self.assertEqual([b["id"] for b in self.boards], [f["id"] for f in motion.features()])
        for b in self.boards:
            kinds = [s["kind"] for s in b["scenes"]]
            self.assertEqual(kinds[:2], ["open", "ask"], b["id"])
            self.assertEqual(kinds[-2:], ["claim", "close"], b["id"])
            self.assertTrue(set(kinds[2:-2]) <= {"command", "answer", "more", "mechanism"}, b["id"])
            self.assertEqual(b["scenes"][0]["start"], 0.0)
            for a, c in zip(b["scenes"], b["scenes"][1:]):
                self.assertEqual(a["end"], c["start"], f"{b['id']}: the scenes run end to start")
            self.assertEqual(b["duration"], b["scenes"][-1]["end"])

    def test_it_runs_sixteen_to_thirty_seconds_and_no_scene_outruns_a_reader(self):
        for b in self.boards:
            self.assertGreaterEqual(b["duration"], motion.MIN_SECONDS, f"{b['id']} is too short to say anything")
            self.assertLessEqual(b["duration"], motion.MAX_SECONDS, f"{b['id']} is too long to watch")
            for s in b["scenes"]:
                n, d = sum(motion.words(t) for t in motion.texts(s)), s["end"] - s["start"]
                self.assertLessEqual(n / d, motion.WORDS_PER_SECOND + 1e-9,
                                     f"{b['id']}/{s['kind']}: {n} words in {d} s is more than {motion.WORDS_PER_SECOND} a second")
                for t in motion.texts(s):
                    self.assertLessEqual(motion.words(t), max(motion.LINE_WORDS, 24),
                                         f"{b['id']}/{s['kind']}: a line of {motion.words(t)} words")

    def test_the_command_typed_is_one_the_cli_has(self):
        for b in self.boards:
            for s in b["scenes"]:
                if s["kind"] == "command":
                    self.assertTrue(any(s["typed"] == h or s["typed"].startswith(h + " ") for h in self.heads),
                                    f"{b['id']} types `{s['typed']}`, which no command's usage begins")

    def test_every_line_printed_is_one_a_release_picture_or_a_docs_example_prints(self):
        for b in self.boards:
            for s in b["scenes"]:
                if s["kind"] != "answer":
                    continue
                for line in s["lines"]:
                    whole = line[:-1] if line.endswith(motion.ELIDED) else line
                    self.assertTrue(any(p == line or p.startswith(whole) for p in self.printed),
                                    f"{b['id']} shows `{line}`, which nothing the engine replays prints")

    def test_the_page_carries_every_word_of_every_scene(self):
        for b in self.boards:
            html = motion.page(b)
            for s in b["scenes"]:
                for t in motion.texts(s):
                    if s["kind"] == "claim" and t == s["text"]:
                        for word in t.split():               # set word by word
                            self.assertIn(motion.html.escape(word), html, f"{b['id']}: the page drops `{word}`")
                        continue
                    if s["kind"] == "command" and t == s["typed"]:
                        # typed a line at a time; a long one broken with the shell's backslash
                        self.assertEqual(" ".join(l.rstrip(" \\") for l in motion.typed_lines(t)), t)
                        for part in motion.typed_lines(t):
                            self.assertLessEqual(len(part), motion.TYPED_LINE + 2, f"{b['id']}: a typed line too long for a frame")
                            self.assertIn(motion.html.escape(part), html, f"{b['id']}: the page drops `{part}`")
                        continue
                    self.assertIn(motion.html.escape(t), html, f"{b['id']}/{s['kind']}: the page drops `{t}`")
            self.assertIn('<pre class="term">', html) if any(s["kind"] in ("command", "answer") for s in b["scenes"]) else None
            self.assertIn(f'data-duration="{b["duration"]}"', html)
            self.assertIn("html.still", html, "a renderer can pause the page at --t")
            self.assertIn("prefers-reduced-motion:reduce){.scene,.typed,.answer .ln,.mark .l,.ver,.claim .w,.close .w{animation:none}"
                          ".scene{opacity:0}.scene.claim,.mark .l,.ver,.claim .w,.close .w{opacity:1}", html,
                          "less motion shows the claim, not a blank frame")

    def test_the_brand_comes_from_a_stylesheet_when_one_is_given_and_plain_colours_otherwise(self):
        b = self.boards[0]
        linked = motion.page(b, "../../brand.css", {"accent": "--brand-accent"})
        self.assertIn('<link rel="stylesheet" href="../../brand.css">', linked)
        self.assertIn("var(--brand-accent)", linked)
        self.assertNotIn("#", re.sub(r"#[a-z0-9-]+|&#\d+;", "", linked.split("<style>")[1].split("</style>")[0]),
                         "with a stylesheet the page states no colour of its own")
        plain = motion.page(b)
        self.assertNotIn("<link", plain)
        for v in motion.PLAIN.values():
            self.assertIn(v, plain)


class TheClose(unittest.TestCase):
    def test_the_tagline_comes_out_of_the_source_and_the_icon_is_linked_from_the_page(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "t", "sources": {"facts": {"path": "facts.json", "why": "x"}},
                                        "motion": {"out": "site/motion", "icon": "site/brand/icon.svg",
                                                   "tagline": {"fact": "line"}}},
                     "facts.json": {"line": "Kettles, compiled."}, "site/brand/icon.svg": "<svg xmlns='http://www.w3.org/2000/svg'/>\n"})
        code, out = wherefore(root, "motion", "gate")
        self.assertEqual(code, 0, out)
        close = json.loads((root / "site/motion/gate/storyboard.json").read_text(encoding="utf-8"))["scenes"][-1]
        self.assertEqual(close["tagline"], "Kettles, compiled.")
        page = (root / "site/motion/gate/index.html").read_text(encoding="utf-8")
        self.assertIn('<img class="icon" src="../../brand/icon.svg" alt="">', page)
        self.assertIn("Kettles, compiled.", page)
        self.assertIn("pip install wherefore-build<", page, "the install line names no version unless asked")


class TheCommand(unittest.TestCase):
    def test_it_writes_a_page_and_a_storyboard_per_feature_and_says_so(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "t", "sources": {},
                                        "motion": {"out": "clips", "name": "Fernhollow"}}})
        code, out = wherefore(root, "motion", "published", "gate")
        self.assertEqual(code, 0, out)
        self.assertIn("  published    6 scenes", out)
        self.assertIn("wrote clips/: 2 clips, each a page in motion", out)
        for fid in ("published", "gate"):
            self.assertTrue((root / "clips" / fid / "index.html").exists())
            board = json.loads((root / "clips" / fid / "storyboard.json").read_text(encoding="utf-8"))
            self.assertEqual(board["id"], fid)
            self.assertEqual(board["scenes"][0]["name"], "Fernhollow")
            self.assertNotIn("tagline", board["scenes"][-1], "no tagline unless one is given")
        self.assertFalse((root / "clips" / "scan").exists(), "only the ids named")
        code, out = wherefore(root, "motion", "docs", "--storyboards", "boards")
        self.assertEqual(code, 0, out)
        self.assertTrue((root / "clips/docs/index.html").exists())
        self.assertTrue((root / "boards/docs/storyboard.json").exists())
        self.assertFalse((root / "clips/docs/storyboard.json").exists(), "the storyboard goes where it is sent")

    def test_it_refuses_a_feature_it_does_not_have_and_a_flag_it_does_not_take(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "t", "sources": {}}})
        code, out = wherefore(root, "motion", "teleport")
        self.assertNotEqual(code, 0)
        self.assertIn("no feature called teleport", out)
        code, out = wherefore(root, "motion", "--fast")
        self.assertEqual(code, 2)
        self.assertIn("does not take --fast", out)

    def test_it_needs_no_wherefore_json_and_show_opens_the_first(self):
        root = repo({"README.md": "nothing here\n"})
        env = dict(os.environ, PYTHONPATH=str(SRC), BROWSER="true")
        env.pop("WHEREFORE_ROOT", None)
        r = subprocess.run([sys.executable, "-m", "wherefore", "motion", "docs", "--show"], cwd=root, env=env,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("wrote motion/: 1 clip", r.stdout)
        self.assertIn("opened", r.stdout)
        self.assertTrue((root / "motion/docs/index.html").exists())

    def test_the_section_is_checked_before_anything_runs(self):
        for bad, said in (({"motion": {"outt": "x"}}, "does not take"),
                          ({"motion": {"tagline": {"source": "facts"}}}, "motion.tagline"),
                          ({"motion": {"vars": {"accent": "accent"}}}, "CSS variable"),
                          ({"motion": "clips"}, "is an object")):
            root = repo({"wherefore.json": dict({"wherefore": 1, "name": "t", "sources": {}}, **bad)})
            code, out = wherefore(root, "motion", "docs")
            self.assertNotEqual(code, 0, bad)
            self.assertIn(said, out, bad)


if __name__ == "__main__":
    unittest.main()
