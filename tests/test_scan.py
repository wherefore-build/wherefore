"""`wherefore scan`: what a company says more than one way, found with no setup.

Each case writes a small published corpus - pages, docs, notes - and requires
the scan to report the stale copies planted in it, and nothing it was built to
leave alone: identifiers, dates, history, tables, numbered lists, code, and
files that are history by name. A scan that invents disagreements is worse
than none, so the quiet cases matter as much as the loud ones.
"""
import functools
import http.server
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
import unittest

from _util import SRC
from wherefore import scan


def corpus(files):
    root = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-scan-"))
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


def run(cwd, *args):
    """The command as a person types it, in a folder with no wherefore.json."""
    env = dict(os.environ, PYTHONPATH=str(SRC))
    env.pop("WHEREFORE_ROOT", None)
    r = subprocess.run([sys.executable, "-m", "wherefore", "scan", *args], cwd=cwd, env=env,
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


DRIFT = {
    "site/index.html": '<html><head><meta name="description" content="Acme 2.4.0: start your 14-day free '
                       'trial."></head><body><p>Start your <strong>14-day free trial</strong> today. Pro is '
                       '<b>$49</b> per month.</p><img alt="Acme dashboard" src="a.png"></body></html>',
    "site/pricing.html": "<table><tr><td>Pro</td><td>$49 per month</td></tr></table>"
                         "<p>Every plan starts with a 14-day free trial. We promise 99.9% uptime.</p>",
    "docs/start.md": "# Getting started\nAcme 2.4.0 needs Python 3.10.\n"
                     "Start your 14-day free trial from the dashboard. Pro is $49 per month.\n",
    "help/billing.md": "Start your 30-day free trial, no card needed. Pro is $59 per month.\n"
                       "We promise 99.5% uptime.\nAcme 2.3.0 changed the billing page.\n",
}


def said(result):
    return {g["says"]: {v["value"]: v["count"] for v in g["values"]} for g in result["disagree"]}


class StaleCopies(unittest.TestCase):
    def test_every_planted_disagreement_is_found_with_its_commonest_value_first(self):
        result = scan.scan([str(corpus(DRIFT))])
        self.assertEqual(said(result), {
            "start your {} day free": {"14": 3, "30": 1},
            "acme {}": {"2.4.0": 2, "2.3.0": 1},
            "pro is {} per month": {"$49": 2, "$59": 1},
            "we promise {} uptime": {"99.9%": 1, "99.5%": 1},
        })
        first = {g["says"]: g["values"][0]["value"] for g in result["disagree"]}
        self.assertEqual(first["start your {} day free"], "14")

    def test_it_names_every_place_and_exits_one_when_copies_disagree(self):
        root = corpus(DRIFT)
        code, out = run(root, ".")
        self.assertEqual(code, 1, out)
        self.assertIn("4 statements whose copies disagree", out)
        self.assertIn("help/billing.md:1", out)
        self.assertIn("wherefore init", out)

    def test_copies_that_agree_exit_zero(self):
        root = corpus({k: v for k, v in DRIFT.items() if k != "help/billing.md"})
        code, out = run(root, ".")
        self.assertEqual(code, 0, out)
        self.assertIn("says one thing everywhere", out)

    def test_json_lists_each_value_and_where(self):
        code, out = run(corpus(DRIFT), ".", "--json")
        self.assertEqual(code, 1, out)
        doc = json.loads(out)
        trial = next(g for g in doc["disagree"] if g["says"] == "start your {} day free")
        where = {(w["in"], w["at"]) for v in trial["values"] for w in v["where"]}
        self.assertIn((os.path.join("help", "billing.md"), 1), where)


class LeftAlone(unittest.TestCase):
    """What looks like a disagreement and is not."""

    def quiet(self, files, *args):
        result = scan.scan([str(corpus(files))], *args)
        self.assertEqual(result["disagree"], [], json.dumps(result["disagree"], indent=1))
        return result

    def test_identifiers_name_things_rather_than_state_them(self):
        self.quiet({"a.md": "Part P-005 is the plain spacer, rev F.\n",
                    "b.md": "Part P-009 is the plain spacer, rev F.\nRelease V83 of the pack.\n",
                    "c.md": "Release V80 of the pack.\n"})

    def test_dates_and_history_are_not_claims(self):
        self.quiet({"a.md": "Updated October 30, 2026 by the team.\nSince 2.1.0 there is a Team plan.\n",
                    "b.md": "Updated October 24, 2026 by the team.\nSince 2.0.0 there is a Team plan.\n"})

    def test_a_table_of_different_things_is_not_a_stale_copy(self):
        self.quiet({"a.md": "Plan seats 5 users each.\nPlan seats 10 users each.\nPlan seats 25 users each.\n",
                    "b.md": "Plan seats 50 users each.\nPlan seats 100 users each.\n"})

    def test_numbered_lists_and_code_are_not_statements(self):
        self.quiet({"a.md": "1. Install the tool\n2. Run the tool\n```\npip install acme==2.3.0\n```\n"
                            "Acme 2.4.0 is current. Use `acme==2.2.0` in old projects.\n",
                    "b.md": "1. Install the tool\n3. Run the tool\nAcme 2.4.0 is current.\n",
                    "c.html": "<p>Acme 2.4.0 is current.</p><script>var v = 'Acme 2.1.0';</script>"
                              "<pre>Acme 2.0.0 was first.</pre>"})

    def test_a_changelog_is_history_unless_asked_for(self):
        files = {"index.md": "Acme 2.4.0 is current.\n", "docs.md": "Acme 2.4.0 is current.\n",
                 "CHANGELOG.md": "Acme 2.3.0 fixed the billing page.\n"}
        self.quiet(files)
        result = scan.scan([str(corpus(files))], everything=True)
        self.assertEqual(said(result), {"acme {}": {"2.4.0": 2, "2.3.0": 1}})


class WhatAPersonReads(unittest.TestCase):
    def test_a_page_is_read_as_sentences_across_its_inline_tags_and_its_alt_text(self):
        lines, _ = scan.read_markup('<p>Pro is <b>$49</b> per <em>month</em>.</p>'
                                    '<img alt="Uptime of 99.9% guaranteed"><script>x = "$1 per month"</script>')
        text = [t for _, t in lines]
        self.assertIn("Pro is $49 per month .", text)
        self.assertIn("Uptime of 99.9% guaranteed", text)
        self.assertFalse(any("$1" in t for t in text))

    def test_a_drawing_is_read_by_its_words_alone(self):
        lines, _ = scan.read_markup('<svg><style>.a{width:400px}</style><text x="10">Blade '
                                    '<tspan>216 mm</tspan></text><path d="M 0 0 L 10 10"/></svg>', svg=True)
        self.assertEqual([t for _, t in lines], ["Blade", "216 mm"])


class ALiveSite(unittest.TestCase):
    def test_a_site_is_read_page_by_page_on_its_own_host_only(self):
        root = corpus({
            "index.html": '<p>Start your 14-day free trial today.</p><a href="/pricing.html">Pricing</a>'
                          '<a href="https://example.com/elsewhere.html">Elsewhere</a>',
            "pricing.html": '<p>Start your 14-day free trial now.</p><a href="/help.html">Help</a>',
            "help.html": "<p>Start your 30-day free trial, no card needed.</p>",
        })
        handler = functools.partial(_Quiet, directory=str(root))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/index.html"
            result = scan.scan([url])
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(result["sources"], 3)
        self.assertEqual(said(result), {"start your {} day free": {"14": 2, "30": 1}})
        self.assertFalse(any("example.com" in u for u in result["unread"]))


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class TheLine(unittest.TestCase):
    def test_nothing_to_scan_and_flags_it_does_not_take_are_refused(self):
        root = corpus({"a.md": "x\n"})
        self.assertEqual(run(root)[0], 2)
        code, out = run(root, ".", "--kep")
        self.assertEqual(code, 2, out)
        self.assertIn("does not take --kep", out)
        code, out = run(root, "nowhere")
        self.assertEqual(code, 2, out)
        self.assertIn("nothing here to read", out)

    def test_help_says_how_and_needs_no_corpus(self):
        code, out = run(corpus({"a.md": "x\n"}), "--help")
        self.assertEqual(code, 0, out)
        self.assertIn("usage: wherefore scan", out)


if __name__ == "__main__":
    unittest.main()
