"""`wherefore status`: where a repository stands, in one read.

What can go wrong: a count that is not what the gate or drift says; the gate
run when it was not asked for, or its failure read as a pass; the pin misread;
a repository with no wherefore.json refused instead of scanned; a corpus whose
gate is its own script given counts the engine guessed; the document written
somewhere other than asked, or not written at all.
"""
import json
import unittest

from _util import ENGINE, repo, wherefore
from wherefore import status

BASE = {"wherefore": 1, "name": "kettles",
        "sources": {"facts": {"path": "facts.json", "why": "the source"}},
        "generators": [{"script": "page.py", "cwd": "gen", "makes": "site/index.html"}],
        "inventory": {"authored": {"rules": [["*.json", "sources"], ["gen/*.py", "code"], ["*.md", "prose"],
                                             ["requirements-engine.txt", "the pin"], [".gitignore", "git"]]},
                      "captured": {"groups": {}}}}
PAGE = ('import json, pathlib\n'
        'facts = json.loads(pathlib.Path("../facts.json").read_text())\n'
        'pathlib.Path("../site").mkdir(exist_ok=True)\n'
        'pathlib.Path("../site/index.html").write_text(f"<p>{facts[\'price\']} dollars</p>\\n")\n')


def corpus(extra=None, page=None, pin="wherefore-build==0.20.1\n"):
    files = {"wherefore.json": BASE, "facts.json": {"price": 89}, "gen/page.py": PAGE,
             "site/index.html": "<p>89 dollars</p>\n", "requirements-engine.txt": pin, ".gitignore": "__pycache__/\n"}
    files.update(extra or {})
    if page is not None:
        files["site/index.html"] = page
    return repo(files)


class TheDocument(unittest.TestCase):
    def test_what_each_file_is_declared_without_running_anything(self):
        doc = status.find(corpus())
        self.assertEqual((doc["name"], doc["set_up"], doc["status"]), ("kettles", True, 1))
        self.assertEqual(doc["files"], {"tracked": 6, "written": 5, "captured": 0, "left": 1},
                         "the page is left for the gate: nothing ran")
        self.assertEqual(doc["pins"], {"version": "0.20.1"})
        self.assertEqual(len(doc["commit"]), 40)

    def test_drift_and_launch_are_what_their_checks_say(self):
        root = corpus({"README.md": "Ships in 5 working days.\n", "docs/faq.md": "It ships in 5 working days.\n"})
        doc = status.find(root)
        self.assertEqual((doc["drift"]["values"], doc["drift"]["allowed"]), (1, None))
        self.assertEqual(doc["drift"]["list"][0]["files"], ["README.md", "docs/faq.md"])
        self.assertEqual(doc["launch"], {"ladders": []})

    def test_a_pin_to_a_commit_is_read_as_a_commit(self):
        doc = status.find(corpus(pin="wherefore-build @ git+https://github.com/wherefore-build/wherefore@fb4ac3ae35af\n"))
        self.assertEqual(doc["pins"], {"commit": "fb4ac3ae35af"})


class WithTheGate(unittest.TestCase):
    def test_the_gates_verdict_and_counts_when_asked(self):
        code, out = wherefore(corpus(), "status", "--gate", "--json")
        self.assertEqual(code, 0, out)
        judged = json.loads(out)["files"]["gate"]
        self.assertEqual(judged, {"passed": True, "built": 1, "written": 5, "captured": 0, "unaccounted": 0})

    def test_a_stale_page_fails_and_status_says_so(self):
        root = corpus(page="<p>79 dollars</p>\n")
        code, out = wherefore(root, "status", "--gate")
        self.assertEqual(code, 1, out)
        self.assertIn("the gate FAILED", out)


class TheLinesAndTheFile(unittest.TestCase):
    def test_out_writes_the_document_and_prints_the_lines(self):
        root = corpus()
        code, out = wherefore(root, "status", "--out", "build/status.json")
        self.assertEqual(code, 0, out)
        self.assertIn("  files    6 tracked: 5 written, 0 captured, 1 for the gate to judge", out)
        self.assertIn("(pins 0.20.1)", out)
        doc = json.loads((root / "build/status.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["name"], "kettles")

    def test_a_repository_not_set_up_is_scanned(self):
        root = repo({"README.md": "Ships in 5 working days.\n", "docs/faq.md": "Ships in 7 working days.\n"})
        code, out = wherefore(root, "status", "--json")
        self.assertEqual(code, 0, out)
        doc = json.loads(out)
        self.assertEqual(doc["set_up"], False)
        self.assertEqual((doc["scan"]["files"], doc["scan"]["disagree"]), (2, 1))

    def test_a_gate_handed_to_the_corpus_own_script_is_not_counted_by_guess(self):
        doc = dict(BASE, entry={"gate": ["tools/gate.py"], "why": "the corpus sorts its own files"})
        for said_by_the_script in ("inventory", "generators"):
            doc.pop(said_by_the_script)
        root = repo({"wherefore.json": doc, "facts.json": {"price": 89}, "tools/gate.py": "print('own gate')\n"})
        got = status.find(root)
        self.assertNotIn("tracked", got["files"], "the corpus's own gate sorts its files; nothing is guessed")

    def test_a_wherefore_json_that_is_refused_is_said_not_scanned(self):
        root = corpus({"wherefore.json": dict(BASE, wherefore=7)})
        code, out = wherefore(root, "status")
        self.assertEqual(code, 1, out)
        self.assertIn("  refused  wherefore.json: `wherefore` must be 1", out)

    def test_usage(self):
        self.assertEqual(wherefore(corpus(), "status", "--colour")[0], 2)


class TheEngineItself(unittest.TestCase):
    def test_the_engine_reads_its_own_status(self):
        code, out = wherefore(ENGINE, "status")
        self.assertEqual(code, 0, out)
        self.assertIn("  launch   default: ", out)


if __name__ == "__main__":
    unittest.main()
