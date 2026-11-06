"""`wherefore check published`: a page nobody here builds still states the source's facts.

Each test serves a stand-in for the hosted site from this machine, so the
check is exercised end to end - fetched, read as a person reads it, compared
with the source - with no network.
"""
import functools
import http.server
import json
import threading
import unittest

from _util import repo, wherefore

PRICING = ('<html><head><style>.x{color:#fff}</style></head><body><h1>Plans</h1>'
           '<p>Start your <b>14</b>-day free trial today. Pro is <span>$49</span> per month.</p>'
           '<ul><li>Unlimited projects</li><li>Priority support</li></ul>'
           '<script>var trial = 30;</script></body></html>')


class Site:
    def __init__(self, pages):
        site = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                status, body = pages.get(self.path, (404, "not here"))
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body.encode())

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


FACTS = {"plans": {"pro": {"trial_days": 14, "price": 49, "features": ["Unlimited projects", "Priority support"]}}}


def corpus(site, states, unreachable=None, facts=FACTS, url="/pricing"):
    page = {"url": site + url, "why": "the public site, on a hosted CMS marketing edits", "states": states}
    if unreachable:
        page["unreachable"] = unreachable
    return repo({"wherefore.json": {"wherefore": 1, "name": "fern",
                                    "sources": {"facts": {"path": "facts.json", "why": "the source"}},
                                    "published": {"pricing": page}},
                 "facts.json": facts})


class HeldByReading(unittest.TestCase):
    def setUp(self):
        self.site = Site({"/pricing": (200, PRICING)})
        self.addCleanup(self.site.close)

    def test_a_page_that_says_what_the_source_says_passes_by_template_bare_value_and_each(self):
        root = corpus(self.site.base, [
            {"fact": "plans.pro.trial_days", "as": ["{} day free trial", "{}-day free trial"]},
            {"fact": "plans.pro.price", "as": "${} per month"},
            {"fact": "plans.pro.trial_days"},
            {"fact": "plans.pro.features", "each": True},
        ])
        code, out = wherefore(root, "check", "published")
        self.assertEqual(code, 0, out)
        self.assertIn("ok   pricing: " + self.site.base + "/pricing says '14-day free trial', as plans.pro.trial_days does", out)
        self.assertIn("says '$49 per month', as plans.pro.price does", out)
        self.assertIn("says 'Priority support', as plans.pro.features[1] does", out)
        self.assertIn("5 statements on 1 published page still say what the source says", out)
        self.assertIn("A published page is a copy until it is built from the source", out)

    def test_a_page_that_says_otherwise_fails_and_quotes_the_page(self):
        root = corpus(self.site.base, [{"fact": "plans.pro.trial_days", "as": "{}-day free trial"}],
                      facts={"plans": {"pro": {"trial_days": 30}}})
        code, out = wherefore(root, "check", "published")
        self.assertEqual(code, 1, out)
        self.assertIn("SAYS OTHERWISE pricing: " + self.site.base + "/pricing says '14-day free trial', and "
                      "plans.pro.trial_days is '30'", out)
        self.assertIn("change it there, or the source", out)
        self.assertIn("::error::1 of 1 statements on 1 published page no longer hold", out)

    def test_a_statement_the_page_no_longer_makes_is_not_said(self):
        root = corpus(self.site.base, [{"fact": "plans.pro.trial_days", "as": "{} months of free hosting"}])
        code, out = wherefore(root, "check", "published")
        self.assertEqual(code, 1, out)
        self.assertIn("NOT SAID pricing: " + self.site.base + "/pricing does not state plans.pro.trial_days as "
                      "'{} months of free hosting': the page changed shape, or the template is wrong", out)

    def test_script_and_style_are_not_what_a_person_reads(self):
        root = corpus(self.site.base, [{"fact": "plans.pro.trial_days", "as": "trial = {}"}],
                      facts={"plans": {"pro": {"trial_days": 30}}})
        code, out = wherefore(root, "check", "published")
        self.assertEqual(code, 1, out)
        self.assertIn("NOT SAID", out, "the 30 in the script is not on the page")

    def test_a_page_that_does_not_answer_fails_unless_the_corpus_says_why_not(self):
        gone = "http://127.0.0.1:9"
        root = corpus(gone, [{"fact": "plans.pro.trial_days", "as": "{} day free trial"}])
        code, out = wherefore(root, "check", "published")
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL pricing: http://127.0.0.1:9/pricing did not answer", out)
        root = corpus(gone, [{"fact": "plans.pro.trial_days", "as": "{} day free trial"}],
                      unreachable="the CMS being down is not the page moving")
        code, out = wherefore(root, "check", "published")
        self.assertEqual(code, 0, out)
        self.assertIn("--   pricing: http://127.0.0.1:9/pricing did not answer", out)
        self.assertIn("Passed, because the CMS being down is not the page moving", out)
        self.assertIn("1 page did not answer, and passed for the reason each gives", out)

    def test_nothing_published_is_said_and_passes(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "fern"}})
        code, out = wherefore(root, "check", "published")
        self.assertEqual(code, 0, out)
        self.assertIn("nothing here is published without being built", out)


class WhatCannotBeMeant(unittest.TestCase):
    """The gate refuses the section offline, with the reason, and reads no page."""

    def refused(self, page, facts=FACTS):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "fern",
                                        "sources": {"facts": {"path": "facts.json", "why": "the source"}},
                                        "published": {"pricing": page}}, "facts.json": facts})
        code, out = wherefore(root, "gate")
        self.assertEqual(code, 1, out)
        return out

    def test_a_page_without_why_a_template_without_braces_and_an_unknown_key(self):
        base = {"url": "https://example.com/p", "why": "marketing's", "states": [{"fact": "plans.pro.price"}]}
        self.assertIn("published['pricing'].why carries no reason", self.refused({**base, "why": " "}))
        self.assertIn("published['pricing'].states[0].as is a template with the value in braces",
                      self.refused({**base, "states": [{"fact": "plans.pro.price", "as": "per month"}]}))
        self.assertIn("published['pricing'] has schedule, which it does not take", self.refused({**base, "schedule": "daily"}))
        self.assertIn("published['pricing'].url is the page's address", self.refused({**base, "url": "example.com/p"}))

    def test_a_fact_the_source_does_not_hold_is_refused_before_any_page_is_read(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "fern",
                                        "sources": {"facts": {"path": "facts.json", "why": "the source"}},
                                        "published": {"pricing": {"url": "http://127.0.0.1:9/p", "why": "marketing's",
                                                                  "states": [{"fact": "plans.gold.price"}]}}},
                     "facts.json": FACTS})
        code, out = wherefore(root, "check", "published")
        self.assertEqual(code, 1, out)
        self.assertIn("states plans.gold.price, which facts does not hold", out)


class ReachByDeclaration(unittest.TestCase):
    def test_a_fact_stated_only_on_a_published_page_is_not_dead(self):
        gen = ("import json, pathlib\n"
               "R = pathlib.Path(__file__).resolve().parent\n"
               "f = json.loads((R / 'facts.json').read_text())\n"
               "(R / 'site').mkdir(exist_ok=True)\n"
               "(R / 'site/index.html').write_text(f\"<p>Start your {f['trial']} day free trial.</p>\\n\")\n")
        files = {"wherefore.json": {"wherefore": 1, "name": "fern",
                                    "sources": {"facts": {"path": "facts.json", "why": "the source"}},
                                    "generators": [{"script": "gen.py", "cwd": ".", "makes": "site/index.html"}],
                                    "inventory": {"authored": {"rules": [["gen.py", "the generator"]]}},
                                    "reach": {"facts": {"source": "facts", "include": ["*"], "exclude": [],
                                                        "why": "every fact"},
                                              "watched": ["site"], "probes": [], "audience": "a visitor"}},
                 "facts.json": {"trial": 14, "price": 49}, "gen.py": gen}
        root = repo(files)
        wherefore(root, "build")
        code, out = wherefore(root, "check", "reach")
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL price", out)
        cfg = json.loads((root / "wherefore.json").read_text(encoding="utf-8"))
        cfg["published"] = {"pricing": {"url": "https://www.example.com/pricing", "why": "the public site, on a CMS",
                                        "states": [{"fact": "price", "as": "${} per month"}]}}
        (root / "wherefore.json").write_text(json.dumps(cfg, indent=1) + "\n", encoding="utf-8")
        code, out = wherefore(root, "check", "reach")
        self.assertEqual(code, 0, out)
        self.assertIn("pub  price", out)
        self.assertIn("stated on the published page pricing, which nothing here builds: held by `wherefore check published`", out)
        self.assertIn("ok   trial", out)


if __name__ == "__main__":
    unittest.main()
