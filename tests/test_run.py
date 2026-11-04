"""A generator that is any command: `run`, held exactly as a Python one is.

Each case writes a small corpus whose one generator is `sh`, not Python - so
the observer never loads, and what the generator wrote is known only from the
tree before and after it ran. `sh` because every machine CI runs on has it.
"""
import json
import unittest

from _util import repo, wherefore
from wherefore import config

PAGE = 'printf "<p>Start your %s day trial.</p>\\n" "$(cat ../facts.txt)" > ../site/index.html\n'
RULES = [["wherefore.json", "the corpus"], ["gen/*", "the generators"], ["facts.txt", "the one fact"]]


def corpus(script=PAGE, run=("sh", "page.sh"), extra=None):
    """A committed corpus: one fact, one `sh` generator, the page it makes."""
    gen = {"run": list(run), "cwd": "gen", "makes": "site/index.html, the page"}
    files = {"wherefore.json": {"wherefore": 1, "name": "shc", "generators": [gen],
                                "inventory": {"authored": {"rules": RULES}}},
             "facts.txt": "14\n", "gen/page.sh": script,
             "site/index.html": "<p>Start your 14 day trial.</p>\n"}
    files.update(extra or {})
    return repo(files)


class ACommandIsHeldAsAScriptIs(unittest.TestCase):
    def test_what_it_writes_is_generated_and_the_gate_passes(self):
        code, out = wherefore(corpus(), "gate")
        self.assertEqual(code, 0, out)
        self.assertIn("generated      1", out)
        self.assertIn("UNKNOWN        0", out)

    def test_list_names_the_command_and_what_it_wrote(self):
        code, out = wherefore(corpus(), "list")
        self.assertEqual(code, 0, out)
        self.assertIn("sh page.sh             1 tracked files   site/index.html, the page", out)

    def test_a_fact_moved_and_the_page_not_rebuilt_is_different(self):
        root = corpus()
        (root / "facts.txt").write_text("30\n", encoding="utf-8")
        code, out = wherefore(root, "gate")
        self.assertEqual(code, 1, out)
        self.assertIn("site/index.html regenerated DIFFERENT", out)

    def test_a_file_it_writes_that_nobody_tracks_is_named(self):
        code, out = wherefore(corpus(PAGE + "cp ../site/index.html ../site/draft.html\n"), "gate")
        self.assertEqual(code, 1, out)
        self.assertIn("site/draft.html is a generated file git doesn't track (written by sh page.sh)", out)

    def test_a_file_it_skips_writing_when_unchanged_goes_unknown(self):
        # The trap the observer exists for, in shell: write only when it moved.
        skip = PAGE.replace("> ../site/index.html", "> /tmp/wherefore-page.$$") + \
            'cmp -s /tmp/wherefore-page.$$ ../site/index.html || cp /tmp/wherefore-page.$$ ../site/index.html\n' \
            'rm -f /tmp/wherefore-page.$$\n'
        code, out = wherefore(corpus(skip), "gate")
        self.assertEqual(code, 1, out)
        self.assertIn("site/index.html is unclassified", out)

    def test_a_write_that_puts_the_old_mtime_back_is_still_seen(self):
        # touch -r restores the mtime; nothing can restore the ctime.
        keep = 'touch -r ../site/index.html ../stamp.ref\n' + PAGE + 'touch -r ../stamp.ref ../site/index.html\nrm ../stamp.ref\n'
        code, out = wherefore(corpus(keep), "gate")
        self.assertEqual(code, 0, out)
        self.assertIn("generated      1", out)

    def test_a_command_that_fails_is_reported_as_a_script_that_fails_is(self):
        code, out = wherefore(corpus('echo "no page today" >&2\nexit 3\n'), "gate")
        self.assertEqual(code, 1, out)
        self.assertIn("sh page.sh failed while the gate ran it", out)
        self.assertIn("no page today", out)

    def test_a_command_that_is_not_installed_is_said_not_a_traceback(self):
        code, out = wherefore(corpus(run=("wherefore-no-such-program", "page.sh")), "gate")
        self.assertEqual(code, 1, out)
        self.assertIn("could not start 'wherefore-no-such-program'", out)
        self.assertNotIn("Traceback", out)

    def test_it_runs_as_given_with_no_shell_between(self):
        # A word with a space and a $ reaches the command as one word, unexpanded.
        script = 'test "$1" = "two words \\$HOME" || { echo "got: $1" >&2; exit 1; }\n' + PAGE
        code, out = wherefore(corpus(script, run=("sh", "page.sh", "two words $HOME")), "gate")
        self.assertEqual(code, 0, out)


class TheProbeSeesWhatACommandWrote(unittest.TestCase):
    def test_the_reach_probe_counts_a_commands_writes_as_the_gate_does(self):
        from wherefore import generators as G, reach
        root = corpus()
        old = (G.ROOT, list(G.GENERATORS), reach.ROOT)
        try:
            G.configure(root, config.load(root).generators)
            reach.ROOT = G.ROOT
            wrote = set()
            self.assertEqual(reach.regenerate(wrote=wrote), [])
            self.assertIn(str(G.ROOT / "site/index.html"), wrote)
        finally:
            G.ROOT, G.GENERATORS[:], reach.ROOT = old[0], old[1], old[2]


class ARunThatCannotBeRunIsRefused(unittest.TestCase):
    def refused(self, gen, words):
        root = repo({"wherefore.json": {"wherefore": 1, "generators": [gen],
                                        "inventory": {"authored": {"rules": RULES}}}})
        with self.assertRaises(config.ConfigError) as e:
            config.load(root)
        self.assertIn(words, str(e.exception.code))

    def test_both_script_and_run(self):
        self.refused({"script": "page.py", "run": ["sh", "page.sh"], "cwd": "gen", "makes": "x"},
                     "says both `script` and `run`")

    def test_neither_script_nor_run(self):
        self.refused({"cwd": "gen", "makes": "x"}, "needs `script` - a Python file")

    def test_run_that_is_not_a_list_of_words(self):
        for run in ("sh page.sh", [], ["sh", ""], ["sh", 3]):
            with self.subTest(run=run):
                self.refused({"run": run, "cwd": "gen", "makes": "x"},
                             "`run` is a command as a list of its words")

    def test_the_same_command_twice(self):
        g = {"run": ["sh", "page.sh"], "cwd": "gen", "makes": "x"}
        root = repo({"wherefore.json": {"wherefore": 1, "generators": [g, dict(g)],
                                        "inventory": {"authored": {"rules": RULES}}}})
        with self.assertRaises(config.ConfigError) as e:
            config.load(root)
        self.assertIn("gen/sh page.sh is listed twice", str(e.exception.code))

    def test_a_run_loads_as_its_words(self):
        root = corpus(run=("sh", "page.sh", "--quiet"))
        self.assertEqual(config.load(root).generators[0].run, ("sh", "page.sh", "--quiet"))


if __name__ == "__main__":
    unittest.main()
