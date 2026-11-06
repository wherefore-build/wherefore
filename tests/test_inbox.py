"""corpus/inbox.py: the ledger, written back onto the issues, once each.

The script goes to GitHub; these run it with --show, which sends nothing, and
hold what it would say to the ledger: every shipped item that answers issues
gets a closing note with the release, the feature, the plan and the line an
agent reads; every open item with issues gets its plan; each carries the marker
that keeps it to once.
"""
import os
import re
import subprocess
import sys
import unittest

from _util import ENGINE
import json


def run(*args):
    env = dict(os.environ)
    env.pop("GITHUB_TOKEN", None)
    r = subprocess.run([sys.executable, str(ENGINE / "corpus/inbox.py"), *args], capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


class WrittenBack(unittest.TestCase):
    def setUp(self):
        self.items = json.loads((ENGINE / "roadmap.json").read_text(encoding="utf-8"))["items"]

    def test_every_shipped_item_with_issues_is_told_what_shipped_with_the_line_an_agent_reads(self):
        code, out = run("--shipped", "--show")
        self.assertEqual(code, 0, out)
        for it in self.items:
            if it["state"] != "shipped" or not it.get("issues"):
                continue
            for url in it["issues"]:
                n = url.rsplit("/", 1)[1]
                self.assertIn(f"would say on #{n}, if not said, and close it: shipped {it['id']} in {it['since']}", out)
            self.assertIn(f"wherefore-inbox: shipped version={it['since']} feature={it['feature']}", out)
            self.assertIn(f"<!-- wherefore-inbox shipped {it['id']} -->", out)
            self.assertIn(it["plan"][:60], out, "the plan is on the closing note")
            # the clip plays on the issue: the site's poster, linking the clip's page, above the Watch line
            page = f"https://wherefore.build/motion/{it['feature']}/"
            self.assertIn(f", in motion]({page}poster.svg)]({page})", out, "the closing note plays the clip")
            self.assertIn(f"**Watch:** {page}", out)

    def test_every_open_item_with_issues_is_told_its_plan(self):
        code, out = run("--planned", "--show")
        self.assertEqual(code, 0, out)
        for it in self.items:
            if it["state"] == "shipped" or not it.get("issues"):
                continue
            for url in it["issues"]:
                self.assertIn(f"would say on #{url.rsplit('/', 1)[1]}, if not said: the plan for {it['id']}", out)
            self.assertIn(it["plan"][:60], out)
            self.assertIn(f"<!-- wherefore-inbox planned {it['id']} -->", out)
        self.assertNotIn("shipped", out.split("would say")[0], "nothing is sent, and nothing shipped is on the planned pass")

    def test_without_a_token_it_refuses_to_send_and_says_how_to_look(self):
        code, out = run("--shipped")
        self.assertEqual(code, 1, out)
        self.assertIn("GITHUB_TOKEN is not set; --show says what would be done", out)


if __name__ == "__main__":
    unittest.main()
