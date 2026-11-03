"""`wherefore check upstream`: a copy taken from elsewhere, held to where it was taken from.

Each test serves a stand-in for the other site from this machine, so the check
is exercised end to end - fetched over HTTP, read, compared - with no network.
"""
import base64
import functools
import http.server
import json
import threading
import unittest

from _util import repo, wherefore

MODEL = "<p>the model, as it was copied</p>\n"


class Site:
    """A stand-in for another company's site: {path: (status, body)}.

    A body that is a function answers the request itself, given the handler -
    for an answer no well-behaved server would give.
    """

    def __init__(self, pages):
        self.pages = pages
        site = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                status, body = site.pages.get(self.path, (404, "not here"))
                if callable(body):
                    return body(self)
                self.send_response(status)
                self.end_headers()
                self.wfile.write(body.encode() if isinstance(body, str) else body)

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def corpus(upstream, files=None):
    """A committed corpus with one captured group, `taken`, whose upstream is `upstream`."""
    group = {"files": ["taken/model.html"], "no_stamp": "taken from another site, which the gate does not read",
             "why": "a copy of another site's file", "upstream": upstream}
    config = {"wherefore": 1, "inventory": {"authored": {"rules": [["wherefore.json", "the corpus"],
                                                   ["facts.json", "what this corpus records"]]},
                            "captured": {"groups": {"taken": group}}}}
    tree = {"wherefore.json": config, "taken/model.html": MODEL, "facts.json": {"taken": {"version": "83"}}}
    tree.update(files or {})
    return repo(tree)


class TheCopyIsHeldToItsSource(unittest.TestCase):
    def setUp(self):
        page = (f'<html><head><meta name="pack-version" content="83"></head>'
                f'<script>var MODEL="{base64.b64encode(MODEL.encode()).decode()}";</script></html>')
        self.site = Site({"/": (200, page), "/model.html": (200, MODEL),
                          "/release.json": (200, json.dumps({"release": {"version": "83"}}))})
        self.addCleanup(self.site.close)

    def check(self, upstream):
        return wherefore(corpus(upstream), "check", "upstream")

    def test_a_copy_that_is_still_what_it_was_taken_from_passes(self):
        code, out = self.check({"url": self.site.url + "/model.html", "matches": "bytes"})
        self.assertEqual(code, 0, out)
        self.assertIn("ok   taken: taken/model.html is what", out)

    def test_a_copy_read_out_of_a_page_by_pattern_and_base64_passes(self):
        code, out = self.check({"url": self.site.url + "/", "matches": "bytes",
                                "read": {"pattern": 'var MODEL="([A-Za-z0-9+/=]+)"', "decode": "base64"}})
        self.assertEqual(code, 0, out)

    def test_the_source_moved_and_the_copy_did_not(self):
        self.site.pages["/model.html"] = (200, "<p>the model, made again</p>\n")
        code, out = self.check({"url": self.site.url + "/model.html", "matches": "bytes"})
        self.assertEqual(code, 1, out)
        self.assertIn("MOVED taken:", out)
        self.assertIn("Take the copy again", out)

    def test_a_recorded_version_read_from_json_and_from_a_meta_tag(self):
        for read in ({"json": "/release/version"}, {"meta": "pack-version"}):
            url = self.site.url + ("/release.json" if "json" in read else "/")
            code, out = self.check({"url": url, "read": read, "matches": {"file": "facts.json", "at": "taken.version"}})
            self.assertEqual(code, 0, out)
            self.assertIn("says 83, as facts.json taken.version records", out)

    def test_a_new_version_upstream_fails_and_names_what_to_take_again(self):
        self.site.pages["/release.json"] = (200, json.dumps({"release": {"version": "84"}}))
        code, out = self.check({"url": self.site.url + "/release.json", "read": {"json": "/release/version"},
                                "matches": {"file": "facts.json", "at": "taken.version"}})
        self.assertEqual(code, 1, out)
        self.assertIn("says 84, and facts.json taken.version records 83", out)
        self.assertIn("Take taken/model.html again", out)
        self.assertIn("never the number alone", out)

    def test_a_source_that_changed_shape_is_a_change(self):
        code, out = self.check({"url": self.site.url + "/", "matches": "bytes",
                                "read": {"pattern": 'var HERO="([A-Za-z0-9+/=]+)"', "decode": "base64"}})
        self.assertEqual(code, 1, out)
        self.assertIn("no longer says what `read` looks for", out)

    def test_a_source_that_does_not_answer_fails_unless_the_corpus_says_why_not(self):
        upstream = {"url": self.site.url + "/gone.html", "matches": "bytes"}
        code, out = self.check(upstream)
        self.assertEqual(code, 1, out)
        self.assertIn("did not answer", out)
        upstream["unreachable"] = "a host being down is not the source moving"
        code, out = self.check(upstream)
        self.assertEqual(code, 0, out)
        self.assertIn("Passed, because a host being down is not the source moving", out)
        self.assertIn("0 of 1 copies taken from elsewhere still match", out)
        self.assertIn("not checked is not matching", out)


def cut_short(handler):
    """Promise a longer body than is sent, then close: the server went away mid-answer."""
    handler.send_response(200)
    handler.send_header("Content-Length", "1000")
    handler.end_headers()
    handler.wfile.write(b"<p>the model, as it")
    handler.wfile.flush()
    handler.close_connection = True


class WhatTheSourceSaysIsReadCarefully(unittest.TestCase):
    def setUp(self):
        self.site = Site({})
        self.addCleanup(self.site.close)

    def check(self, upstream, facts=None):
        files = {"facts.json": facts} if facts is not None else None
        return wherefore(corpus(upstream, files), "check", "upstream")

    def test_an_answer_cut_short_did_not_answer_and_is_no_traceback(self):
        self.site.pages["/model.html"] = (200, cut_short)
        code, out = self.check({"url": self.site.url + "/model.html", "matches": "bytes"})
        self.assertEqual(code, 1, out)
        self.assertIn("did not answer", out)
        self.assertNotIn("Traceback", out)

    def test_a_true_said_and_recorded_is_the_same_value(self):
        self.site.pages["/release.json"] = (200, json.dumps({"beta": True}))
        code, out = self.check({"url": self.site.url + "/release.json", "read": {"json": "/beta"},
                                "matches": {"file": "facts.json", "at": "beta"}}, facts={"beta": True})
        self.assertEqual(code, 0, out)
        self.assertIn("says true, as facts.json beta records", out)

    def test_an_answer_too_large_to_read_is_refused_in_words(self):
        self.site.pages["/model.html"] = (200, b"x" * (10 * 1024 * 1024 + 1))
        code, out = self.check({"url": self.site.url + "/model.html", "matches": "bytes"})
        self.assertEqual(code, 1, out)
        self.assertIn("more than 10 MB", out)
        self.assertNotIn("Traceback", out)

    def test_a_long_value_is_cut_short_in_a_moved_line(self):
        long = "v" * 500
        self.site.pages["/release.json"] = (200, json.dumps({"version": long}))
        code, out = self.check({"url": self.site.url + "/release.json", "read": {"json": "/version"},
                                "matches": {"file": "facts.json", "at": "version"}}, facts={"version": "83"})
        self.assertEqual(code, 1, out)
        self.assertIn("MOVED taken:", out)
        self.assertNotIn(long, out)
        self.assertIn("v" * 77 + "...", out)


class AnUpstreamThatCannotBeCheckedIsRefused(unittest.TestCase):
    def refused(self, upstream, said):
        code, out = wherefore(corpus(upstream), "check", "upstream")
        self.assertNotEqual(code, 0, out)
        self.assertIn(said, out)
        self.assertNotIn("Traceback", out)

    def test_no_address(self):
        self.refused({"matches": "bytes"}, "`upstream.url` is the address the copy was taken from")

    def test_two_ways_of_reading(self):
        self.refused({"url": "https://example.com/", "matches": "bytes", "read": {"json": "/a", "meta": "b"}},
                     "`upstream.read` takes one of")

    def test_a_json_pointer_that_is_not_one(self):
        self.refused({"url": "https://example.com/", "read": {"json": "release/version"},
                      "matches": {"file": "facts.json", "at": "taken.version"}},
                     "`upstream.read.json` is a JSON pointer")

    def test_nothing_to_match(self):
        self.refused({"url": "https://example.com/"}, "`upstream.matches` is \"bytes\"")

    def test_a_recorded_value_the_corpus_does_not_say(self):
        self.refused({"url": "https://example.com/", "read": {"json": "/v"},
                      "matches": {"file": "facts.json", "at": "taken.release"}}, "which does not say it")


class TheGateStaysOffline(unittest.TestCase):
    def test_the_gate_never_reads_an_upstream(self):
        # Nothing answers at this address; the gate passes because it never asks.
        root = corpus({"url": "http://127.0.0.1:9/nothing-here", "matches": "bytes"})
        code, out = wherefore(root, "gate")
        self.assertEqual(code, 0, out)
        self.assertNotIn("upstream", out)


if __name__ == "__main__":
    unittest.main()
