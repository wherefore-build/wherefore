"""`wherefore gate --since REF`: only what a change since REF can reach, to the full gate's verdict.

Every case runs on a committed copy of the fixture company that publishes its
own map (`wherefore graph --json`) and has one more source, hours.json, read by
one generator only - so a change can reach part of the corpus and not the rest.
Each change is judged twice, by the full gate and by --since, and the two must
agree; then --since must say what it ran and what it skipped, and why.
"""
import json
import pathlib
import re
import shutil
import sys
import tempfile
import unittest

from _util import ENGINE, git, wherefore

FIXTURE = ENGINE / "tests" / "fixture"
MAP = ["-m", "wherefore", "graph", "--html", "map/index.html", "--json", "map/map.json"]
HOURS = ('"""site/hours.txt: the opening hours, from hours.json alone."""\n'
         "import json\nfrom kit import ROOT\n"
         'h = json.loads((ROOT / "hours.json").read_text(encoding="utf-8"))\n'
         '(ROOT / "site/hours.txt").write_text(f"Open {h[\'open\']} to {h[\'close\']}.\\n", encoding="utf-8")\n')
ROBOTS = ["sh", "-c", "printf 'User-agent: *\\n' > ../site/robots.txt"]


def commit(root, msg):
    git(root, "add", "-A")
    git(root, "-c", "user.email=t@wherefore", "-c", "user.name=t", "commit", "-qm", msg)


def corpus(edit=None, mapped=True):
    """A committed fixture copy with hours.json and gen/hours.py, and the map
    as a generator unless `mapped` is false - built until it settles, so the
    commit is one the full gate passes."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-since-")) / "fernhollow"
    shutil.copytree(FIXTURE, root, ignore=shutil.ignore_patterns("__pycache__"))
    (root / "hours.json").write_text('{\n "open": "9",\n "close": "17"\n}\n', encoding="utf-8")
    (root / "gen/hours.py").write_text(HOURS, encoding="utf-8")
    p = root / "wherefore.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["generators"].append({"script": "hours.py", "cwd": "gen", "makes": "site/hours.txt"})
    d["inventory"]["authored"]["rules"].append(["hours.json", "the opening hours: a source"])
    if mapped:
        d["generators"].append({"run": [sys.executable, *MAP], "cwd": ".", "makes": "map/, the map"})
    if edit:
        edit(d)
    p.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
    git(root, "init", "-q")
    commit(root, "the sources")
    for _ in range(2):
        wherefore(root, "build")
        git(root, "add", "-A")
    commit(root, "built")
    code, out = wherefore(root, "gate")
    assert code == 0, out
    return root


def errors(out):
    return sorted(set(re.findall(r"^::error::(\S+)", out, re.M)))


def decided(out):
    """{generator: (ran|skipped|composed, why)} from what --since printed."""
    return {m.group(2): (m.group(1), m.group(3))
            for m in re.finditer(r"^  (ran|skipped|composed) +(.+?) - (.*)$", out, re.M)}


def sub(root, rel, old, new):
    p = root / rel
    s = p.read_text(encoding="utf-8")
    assert old in s, (rel, old)
    p.write_text(s.replace(old, new, 1), encoding="utf-8")


class Since(unittest.TestCase):
    """One corpus for the class; each case changes it and puts it back."""

    @classmethod
    def setUpClass(cls):
        cls.root = corpus()
        cls.map_name = f"{sys.executable} {' '.join(MAP)}"

    def tearDown(self):
        git(self.root, "checkout", "-q", "--", ".")
        git(self.root, "clean", "-qfd")

    def both(self):
        """(full gate, --since HEAD), each as (exit, output)."""
        return wherefore(self.root, "gate"), wherefore(self.root, "gate", "--since", "HEAD")

    def same_verdict(self, why):
        (fc, fo), (sc, so) = self.both()
        self.assertEqual((fc, errors(fo)), (sc, errors(so)),
                         f"{why}: the full gate and --since disagree\n--- full\n{fo}\n--- since\n{so}")
        return fc, so

    def test_a_clean_tree_skips_every_generator_and_passes(self):
        code, out = self.same_verdict("nothing changed")
        self.assertEqual(code, 0, out)
        d = decided(out)
        for g in ("landing.py", "deck.py", "notes.py", "ledger.py", "hours.py"):
            self.assertEqual(d[g][0], "skipped", out)
        self.assertEqual(d[self.map_name][0], "composed", out)
        self.assertIn("0 ran, 5 skipped, 1 composed", out)
        self.assertIn("every generated one a change since HEAD\ncan reach was written", out)

    def test_a_fact_runs_only_the_generators_that_read_it(self):
        sub(self.root, "hours.json", '"17"', '"18"')
        code, out = self.same_verdict("a fact, not rebuilt")
        self.assertEqual(code, 1)
        self.assertIn("site/hours.txt regenerated DIFFERENT", out)
        d = decided(out)
        self.assertEqual(d["hours.py"], ("ran", "it reads hours.json, changed since HEAD"))
        for g in ("landing.py", "deck.py", "notes.py", "ledger.py"):
            self.assertEqual(d[g][0], "skipped", out)
        wherefore(self.root, "build")
        code, out = self.same_verdict("a fact, rebuilt")
        self.assertEqual(code, 0, out)
        self.assertIn("1 ran, 4 skipped, 1 composed", out)

    def test_a_fact_every_generator_reads_runs_them_all(self):
        sub(self.root, "facts.json", '"price_usd": 89', '"price_usd": 99')
        code, out = self.same_verdict("the price")
        self.assertEqual(code, 1)
        d = decided(out)
        for g in ("landing.py", "deck.py", "notes.py", "ledger.py"):
            self.assertEqual(d[g][0], "ran", out)
        self.assertEqual(d["hours.py"][0], "ran", "hours.py imports kit, which reads facts.json")

    def test_a_change_to_a_generator_script_runs_it(self):
        sub(self.root, "gen/notes.py", "Say the size", "Give the size")
        code, out = self.same_verdict("a generator script")
        self.assertEqual(code, 1)
        self.assertIn("deck/speaker-notes.txt regenerated DIFFERENT", out)
        d = decided(out)
        self.assertEqual(d["notes.py"], ("ran", "its script, gen/notes.py, changed since HEAD"))
        self.assertEqual(d["deck.py"][0], "skipped")

    def test_a_generated_file_edited_by_hand_runs_its_generator(self):
        sub(self.root, "site/hours.txt", "Open", "open")
        code, out = self.same_verdict("by hand")
        self.assertEqual(code, 1)
        self.assertEqual(decided(out)["hours.py"], ("ran", "it writes site/hours.txt, changed since HEAD"))

    def test_a_skipped_generators_files_are_classified_not_unclassified(self):
        sub(self.root, "README.md", "Fernhollow", "Fernhollo")
        (fc, fo), (sc, so) = self.both()
        self.assertEqual((fc, sc), (0, 0), so)
        counts = lambda out: {k: re.search(rf"^\s+{k}\s+(\d+)", out, re.M).group(1)
                              for k in ("generated", "authored", "captured", "UNKNOWN")}
        self.assertEqual(counts(fo), counts(so))
        self.assertEqual(counts(so)["UNKNOWN"], "0")
        self.assertIn("of the generated, 5 are as committed: written by a generator this run skipped", so)

    def test_a_file_an_earlier_generator_rewrites_runs_its_reader(self):
        # deck.py changes and only the deck is remade: the ledger reads the deck
        # (changed since HEAD), and the landing page reads the ledger, which the
        # ledger's run rewrites after the page's turn - so it runs in the second
        # pass, and the corpus does not settle, as the full gate says too.
        sub(self.root, "gen/deck.py", "minutes to the boil", "min to the boil")
        import subprocess
        subprocess.run([sys.executable, "deck.py"], cwd=self.root / "gen", check=True)
        code, out = self.same_verdict("the deck, remade alone")
        self.assertEqual(code, 1)
        self.assertIn("the corpus is not a fixed point", out)
        d = decided(out)
        self.assertEqual(d["ledger.py"], ("ran", "it reads deck/one-pager.svg, changed since HEAD"))
        self.assertIn("  again    landing.py - it reads ledger.json, which this run rewrote", out)

    def test_the_map_is_composed_and_held_to_its_bytes(self):
        sub(self.root, "map/map.json", '"repository": "fernhollow-kettles"', '"repository": "fernhollow"')
        code, out = self.same_verdict("the map by hand")
        self.assertEqual(code, 1)
        self.assertIn("map/map.json regenerated DIFFERENT", out)

    def test_the_verdict_is_the_full_gates_for_each_kind_of_change(self):
        cases = {
            "a library every generator imports": ("gen/kit.py", 'return f"${x:,}"', 'return f"USD {x:,}"'),
            "the source a capture was made from": ("facts.json", '"capacity_l": 1.5', '"capacity_l": 1.7'),
            "the ledger by hand": ("ledger.json", '"deck": "', '"deck": "0'),
            "the hours' generator, rebuilt": ("gen/hours.py", "Open {", "Opens {"),
        }
        for name, (rel, old, new) in cases.items():
            with self.subTest(name):
                sub(self.root, rel, old, new)
                if name.endswith("rebuilt"):
                    wherefore(self.root, "build")
                self.same_verdict(name)
                git(self.root, "checkout", "-q", "--", ".")

    def test_a_ref_git_does_not_know_is_refused(self):
        code, out = wherefore(self.root, "gate", "--since", "no-such-ref")
        self.assertEqual(code, 2, out)
        self.assertIn("--since no-such-ref: git knows no commit by that name", out)
        code, out = wherefore(self.root, "gate", "--since")
        self.assertEqual(code, 2, out)


class EveryGeneratorRunsWhenTheMapCannotSay(unittest.TestCase):
    def full(self, root, ref="HEAD"):
        code, out = wherefore(root, "gate", "--since", ref)
        m = re.search(r"^since .*: every generator runs - (.*)$", out, re.M)
        self.assertTrue(m, out)
        self.assertNotIn("skipped", out)
        return code, m.group(1)

    @classmethod
    def setUpClass(cls):
        cls.root = corpus()

    def tearDown(self):
        git(self.root, "checkout", "-q", "--", ".")
        git(self.root, "clean", "-qfd")

    def test_no_map_generator(self):
        code, why = self.full(corpus(mapped=False))
        self.assertEqual(code, 0)
        self.assertIn("no generator writes the map (`wherefore graph --json PATH`)", why)

    def test_no_map_at_ref(self):
        first = git(self.root, "rev-list", "--max-parents=0", "HEAD").stdout.strip()   # the sources alone
        _code, why = self.full(self.root, first)
        self.assertRegex(why, r"map/map.json is not in [0-9a-f]{7}")

    def test_a_map_from_another_release(self):
        sub(self.root, "map/map.json", '"engine": "', '"engine": "0.0.')
        commit(self.root, "a map from another engine")
        try:
            _code, why = self.full(self.root)
            self.assertIn("was written by wherefore 0.0.", why)
        finally:
            git(self.root, "reset", "-q", "--hard", "HEAD~1")

    def test_a_file_added(self):
        (self.root / "site/about.html").write_text("<p>about</p>\n", encoding="utf-8")
        git(self.root, "add", "site/about.html")
        try:
            code, why = self.full(self.root)
            self.assertEqual(code, 1, "and the full gate it ran names the new file")
            self.assertIn("added (site/about.html)", why)
        finally:
            git(self.root, "rm", "-q", "--cached", "site/about.html")

    def test_a_file_git_does_not_track(self):
        (self.root / "gen/draft.json").write_text("{}\n", encoding="utf-8")
        _code, why = self.full(self.root)
        self.assertIn("git does not track or ignore (gen/draft.json)", why)

    def test_what_the_gate_is_told(self):
        sub(self.root, "wherefore.json", '"note": "', '"note": "Still: ')
        _code, why = self.full(self.root)
        self.assertIn("what the gate is told changed since HEAD", why)
        self.assertIn("wherefore.json", why)


class AGeneratorWhoseReadsAreNotObservedAlwaysRuns(unittest.TestCase):
    def test_a_command_runs_on_a_clean_tree(self):
        def robots(d):
            d["generators"].insert(0, {"run": ROBOTS, "cwd": "gen", "makes": "site/robots.txt"})
        root = corpus(robots)
        code, out = wherefore(root, "gate", "--since", "HEAD")
        self.assertEqual(code, 0, out)
        d = decided(out)
        robots = next(v for k, v in d.items() if k.startswith("sh -c"))
        self.assertEqual(robots, ("ran", "a command: what it reads is not observed"))
        self.assertEqual(d["landing.py"][0], "skipped")


class TheMapCreditsWhatTheCommandWrites(unittest.TestCase):
    def test_json_alone_still_writes_the_page_and_is_credited_with_it(self):
        from wherefore import generators as G, graph
        g = G.Gen(script=None, cwd="out", makes="the map", run=("wherefore", "graph", "--json", "m.json"))
        self.assertEqual(graph.maps_itself(g), ["out/wherefore-graph.html", "out/m.json"])
        g = G.Gen(script=None, cwd=".", makes="the map", run=("wherefore", "graph", "--html", "-", "--json", "m.json"))
        self.assertEqual(graph.maps_itself(g), ["m.json"])
        g = G.Gen(script=None, cwd=".", makes="x", run=("wherefore", "graph", "--nonsense"))
        self.assertIsNone(graph.maps_itself(g))


class ACorpusThatHandsItsGateToItsOwnScript(unittest.TestCase):
    def test_since_reaches_the_script_and_with_no_map_it_runs_everything(self):
        from _util import scripted
        root = scripted({"authored": {"rules": [["*.py", "code"], ["*.json", "config"],
                                                [".gitignore", "ignored"]]},
                         "captured": {"groups": {}}},
                        files={"gen/page.py": "import pathlib\n"
                                              "pathlib.Path('../out/page.txt').write_text('x\\n')\n",
                               "out/page.txt": "x\n"}, gens=["page.py"])
        code, out = wherefore(root, "gate", "--since", "HEAD")
        self.assertEqual(code, 0, out)
        self.assertIn("every generator runs - no generator writes the map", out)


if __name__ == "__main__":
    unittest.main()
