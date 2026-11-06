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


    def serve(self, pages):
        """A site from {path: (status, headers, body)}, and the paths asked for, in order."""
        asked = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                asked.append(self.path)
                status, headers, body = pages.get(self.path, (404, {}, "not here"))
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(body.encode())

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_port}", asked

    def test_every_fetch_counts_toward_the_limit_not_only_pages(self):
        links = "".join(f'<a href="/file{i}.zip">file {i}</a>' for i in range(300))
        pages = {"/": (200, {"Content-Type": "text/html"}, f"<p>Downloads.</p>{links}")}
        pages.update({f"/file{i}.zip": (200, {"Content-Type": "application/zip"}, "PK")
                      for i in range(300)})
        base, asked = self.serve(pages)
        result = scan.scan([base + "/"], max_pages=5)
        self.assertEqual(len(asked), 5, asked)
        self.assertEqual(result["sources"], 1)

    def test_an_answer_that_is_not_html_is_not_read(self):
        base, _ = self.serve({"/big.bin": (200, {"Content-Type": "application/octet-stream"}, "x" * 1000)})
        self.assertEqual(scan._fetch(base + "/big.bin"), ("application/octet-stream", None))

    def test_a_redirect_to_another_host_is_refused_and_said(self):
        elsewhere, asked_there = self.serve({"/": (200, {"Content-Type": "text/html"},
                                                   "<p>Start your 30-day free trial elsewhere.</p>")})
        base, _ = self.serve({
            "/": (200, {"Content-Type": "text/html"},
                  '<p>Start your 14-day free trial today.</p><a href="/away">Away</a>'),
            "/away": (302, {"Location": elsewhere + "/"}, ""),
        })
        result = scan.scan([base + "/"])
        self.assertEqual(asked_there, [])
        self.assertEqual(result["sources"], 1)
        self.assertEqual([u for u in result["unread"] if "another host" in u],
                         [f"{base}/away: redirected to {elsewhere[len('http://'):]}, another host, "
                          f"which a scan does not read"])

    def test_a_redirect_on_the_same_host_is_followed(self):
        base, asked = self.serve({
            "/": (302, {"Location": "/home"}, ""),
            "/home": (200, {"Content-Type": "text/html"}, "<p>Start your 14-day free trial today.</p>"),
        })
        result = scan.scan([base + "/"])
        self.assertEqual(asked, ["/", "/home"])
        self.assertEqual((result["sources"], result["unread"]), (1, []))


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


class TwoPlacesAtOnce(unittest.TestCase):
    """More than one place: every statement they both make, and where they differ."""
    def places(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-scan2-"))
        (root / "site").mkdir(); (root / "app").mkdir()
        (root / "site/index.html").write_text("<p>Start your 14 day free trial today. Plans from 9 dollars a month. "
                                              "Ships in 2 business days to anywhere.</p>\n", encoding="utf-8")
        (root / "site/pricing.html").write_text("<p>Start your 14 day free trial today.</p>\n", encoding="utf-8")
        (root / "app/welcome.md").write_text("Start your 30 day free trial today. Plans from 9 dollars a month.\n", encoding="utf-8")
        return root

    def test_what_both_say_and_where_they_differ(self):
        root = self.places()
        code, out = run(root, "site", "app")
        self.assertEqual(code, 1, out)
        self.assertIn("2 places read together - site, app - state 2 things in common; they disagree on 1", out)
        self.assertIn('DIFFER  "start your {} day free"  site: 14 (2x) · app: 30 (1x)', out)
        self.assertIn('agree   "plans from {} dollars a"  site: 9 (1x) · app: 9 (1x)', out)
        self.assertNotIn("business days", out, "said in one place only: not in common")

    def test_json_tags_every_place_with_its_root(self):
        root = self.places()
        code, out = run(root, "site", "app", "--json")
        d = json.loads(out)
        self.assertEqual(d["roots"], ["site", "app"])
        trial = [g for g in d["shared"] if g["says"] == "start your {} day free"][0]
        self.assertFalse(trial["agree"])
        self.assertEqual(trial["roots"]["site"], [{"value": "14", "count": 2}])
        self.assertEqual(trial["roots"]["app"], [{"value": "30", "count": 1}])
        self.assertEqual({w["root"] for g in d["disagree"] for v in g["values"] for w in v["where"]}, {"site", "app"})

    def test_one_place_reads_as_before(self):
        root = self.places()
        code, out = run(root, "site", "--json")
        d = json.loads(out)
        self.assertNotIn("shared", d)
        self.assertNotIn("roots", d)
        self.assertEqual(code, 0, "the site agrees with itself")


class WhatItRead(unittest.TestCase):
    """0.16.0: the scan says what each place contributed, reads an app's own
    words out of its source, sets a table apart from a stale copy, and counts
    the colours a site states (wherefore-build/wherefore#19, #20)."""

    def places(self):
        return corpus({
            "site/index.html": '<html><head><link rel="stylesheet" href="style.css"><style>.a{color:#0b0c0e}</style></head>'
                               '<body><p style="color:#0B0C0F">Start your 14 day free trial today. Plans from 9 dollars a '
                               'month.</p><table><tr><td>Basic $10 per month for 50 members</td>'
                               '<td>Team $40 per month for 250 members</td></tr></table></body></html>\n',
            "site/pricing.html": "<p>Start your 14 day free trial today.</p><table><tr><td>Basic $10 per month for 50 "
                                 "members</td><td>Team $40 per month for 250 members</td></tr></table>\n",
            "site/style.css": "body { background: #ffffff; color: rgb(11, 12, 14); } a { color: #c3ff0f }\n"
                              ".muted { color: #5f6269 } .muted2 { color: #606370 }\n",
            "app/src/Main.elm": 'module Main exposing (..)\n\nwelcome =\n    "Start your 30 day free trial today. '
                                'Plans from 9 dollars a month."\n',
            "app/src/data.json": "{}\n",
            "app/icons/a.svg": '<svg><path fill="#0b0c0e" d="M0 0"/></svg>\n',
            "app/node_modules/x/README.md": "Start your 99 day free trial today.\n",
        })

    def test_it_says_what_each_place_contributed_and_what_it_left(self):
        root = self.places()
        code, out = run(root, "site", "app")
        self.assertIn("  read  site: 2 .html, 1 .css", out)
        self.assertIn("  read  app: 1 .svg, 1 .elm · not read: 1 .json", out)
        self.assertNotIn("node_modules", out)
        d = json.loads(run(root, "site", "app", "--json")[1])
        self.assertEqual(d["read"]["app"], {"read": {".svg": 1, ".elm": 1}, "not_read": {".json": 1}})

    def test_an_apps_own_words_are_read_out_of_its_source(self):
        root = self.places()
        code, out = run(root, "site", "app")
        self.assertEqual(code, 1, out)
        self.assertIn('DIFFER  "start your {} day free"  site: 14 (2x) · app: 30 (1x)', out)
        self.assertIn("app/src/Main.elm:4", out)

    def test_a_table_on_every_page_alike_is_set_apart_from_the_stale_copies(self):
        root = self.places()
        code, out = run(root, "site")
        self.assertEqual(code, 0, out)
        self.assertIn('1 statement says two things in the same files alike - a table, not a stale copy: '
                      '"month for {} members"', out)
        d = json.loads(run(root, "site", "--json")[1])
        self.assertEqual(d["disagree"], [])
        self.assertEqual(d["tied"][0]["values"], ["50", "250"])
        self.assertEqual(d["tied"][0]["files"], ["site/index.html", "site/pricing.html"])

    def test_the_colours_a_site_states_and_which_are_within_a_shade(self):
        root = self.places()
        code, out = run(root, "site")
        self.assertIn("6 colours stated in 2 files; 2 groups within a shade of one another", out)
        self.assertIn("  #0b0c0e · #0b0c0f   site/index.html, site/style.css", out)
        self.assertIn("  #5f6269 · #606370   site/style.css", out)
        d = json.loads(run(root, "site", "--json")[1])
        self.assertEqual(d["colours"]["distinct"], 6)
        self.assertEqual(d["colours"]["near"], [["0b0c0e", "0b0c0f"], ["5f6269", "606370"]])
        self.assertEqual(d["colours"]["where"]["0b0c0e"], ["site/index.html", "site/style.css"])

    def test_a_word_in_prose_is_not_a_colour(self):
        root = corpus({"a.md": "The #bad idea and the #cafe at #10.\n", "b.html": "<p>#face</p>"})
        d = json.loads(run(root, ".", "--json")[1])
        self.assertNotIn("colours", d)

    def test_colours_in_code_are_not_read_only_its_words_are(self):
        root = corpus({"app.py": 'GREY = "#5f6269"\nprint("Start your 14 day free trial today")\n'})
        d = json.loads(run(root, ".", "--json")[1])
        self.assertNotIn("colours", d)
        self.assertEqual(d["stated"], 1)


class ALiveSitesColours(unittest.TestCase):
    def serve(self, pages):
        asked = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                asked.append(self.path)
                status, headers, body = pages.get(self.path, (404, {}, "not here"))
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(body.encode())

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_port}", asked

    def test_a_sites_stylesheets_are_read_for_colours_and_count_toward_the_limit(self):
        pages = {
            "/": (200, {"Content-Type": "text/html"},
                  '<link rel="stylesheet" href="/a.css"><link rel="stylesheet" href="https://cdn.example/b.css">'
                  '<p style="color:#0b0c0e">Start your 14 day free trial today.</p><a href="/more.html">More</a>'),
            "/a.css": (200, {"Content-Type": "text/css"}, "a { color: #0b0c0f } b { color: #c3ff0f }"),
            "/more.html": (200, {"Content-Type": "text/html"}, "<p>Start your 14 day free trial today.</p>"),
        }
        base, asked = self.serve(pages)
        result = scan.scan([base + "/"])
        self.assertEqual(sorted(asked), ["/", "/a.css", "/more.html"])
        self.assertEqual(result["read"][base.split("//")[1]], {"read": {"pages": 2, "stylesheets": 1}, "not_read": {}})
        self.assertEqual(result["colours"]["near"], [["0b0c0e", "0b0c0f"]])
        self.assertEqual(result["sources"], 2, "a stylesheet is read for colours, not for statements")
        base, asked = self.serve(pages)
        scan.scan([base + "/"], max_pages=2)
        self.assertEqual(len(asked), 2, "a stylesheet is a fetch like any other")


if __name__ == "__main__":
    unittest.main()
