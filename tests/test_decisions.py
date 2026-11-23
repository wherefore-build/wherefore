"""`wherefore check decisions`: a change to a fact carries the approval of someone allowed to give it.

What can go wrong: a sensitive fact passing on anyone's approval; the author
deciding their own change; an approval on an earlier commit standing for a
later one; a dismissed approval, or one taken back, still counting; something
typed - a commit message - counting; an added or removed key read as no
change; a rule that guards nothing passing; a malformed section read as
something; and, outside a pull request, a check that cannot read approvals
passing. None of it goes to the network: approvals come from a file, or from
a reader handed in for the one function that would.
"""
import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
import urllib.error

from _util import SRC, git, repo
from wherefore import config, decisions, status

FOUNDER, SAM, LEE = "fern-founder", "sam", "lee"
RULES = [{"source": "facts", "keys": "product.price_usd", "decides": [FOUNDER],
          "why": "the price is a promise to every customer: the founder sets it"},
         {"source": "facts", "keys": ["company.*", "product.*"], "decides": "reviewer",
          "why": "every fact a customer reads is checked by a second person"}]
FACTS = {"company": {"name": "Fernhollow Kettles", "city": "Porto"},
         "product": {"price_usd": 89, "boil_minutes": 3},
         "notes": {"internal": "nobody decides this"}}


def config_doc(rules=RULES):
    return {"wherefore": 1, "name": "kettles",
            "sources": {"facts": {"path": "facts.json", "why": "the source"}},
            "decisions": {"rules": rules}}


def corpus(rules=RULES):
    """A committed corpus; the commit it starts at is the base."""
    root = repo({"wherefore.json": config_doc(rules), "facts.json": FACTS})
    return root, head(root)


def head(root):
    return git(root, "rev-parse", "HEAD").stdout.strip()


def change(root, edit, message="a change"):
    """Edit facts.json, commit it, and return the new head."""
    facts = json.loads((root / "facts.json").read_text(encoding="utf-8"))
    edit(facts)
    (root / "facts.json").write_text(json.dumps(facts, indent=1) + "\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "-c", "user.email=t@wherefore", "-c", "user.name=t", "commit", "-qm", message)
    return head(root)


def review(login, on, state="APPROVED", association="MEMBER", kind="User"):
    return {"user": {"login": login, "type": kind}, "state": state, "commit_id": on,
            "author_association": association}


def approvals(root, author, reviews, **extra):
    path = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-approvals-")) / "approvals.json"
    path.write_text(json.dumps({"author": author, "reviews": reviews, **extra}), encoding="utf-8")
    return str(path)


def bare_env():
    """This process's environment with nothing of GitHub's: CI runs these tests
    inside a pull request's workflow, and the check must not read that one."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GITHUB_")}


def check(root, *args):
    env = dict(bare_env(), PYTHONPATH=str(SRC), WHEREFORE_ROOT=str(root))
    r = subprocess.run([sys.executable, "-m", "wherefore", "check", "decisions", *args], cwd=root,
                       env=env, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def in_process(root, args, env, read):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = decisions.main(config.load(root), args, env=env, read=read)
    return code, out.getvalue()


def price(to):
    return lambda f: f["product"].__setitem__("price_usd", to)


class WhoDecides(unittest.TestCase):
    def test_a_sensitive_fact_approved_by_someone_named_passes(self):
        root, base = corpus()
        h = change(root, price(99))
        code, out = check(root, "--base", base, "--approvals", approvals(root, SAM, [review(FOUNDER, h)]))
        self.assertEqual(code, 0, out)
        self.assertIn("ok    facts product.price_usd 89 -> 99: decided by fern-founder (facts: product.price_usd); "
                      "and fern-founder (facts: company.*, product.*)", out)
        self.assertIn("every changed fact a rule names carries its decision: 1 decided, by fern-founder", out)

    def test_a_sensitive_fact_approved_only_by_another_reviewer_fails(self):
        root, base = corpus()
        h = change(root, price(99))
        code, out = check(root, "--base", base, "--approvals", approvals(root, SAM, [review(LEE, h)]))
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL  facts product.price_usd 89 -> 99: needs an approving review on the head from "
                      "fern-founder (facts: product.price_usd)", out)
        fail = next(l for l in out.splitlines() if "FAIL" in l)
        self.assertNotIn("company.*", fail, "the reviewer rule is met by lee, and is not asked for again")

    def test_a_routine_fact_needs_any_reviewer_who_is_not_the_author(self):
        root, base = corpus()
        h = change(root, lambda f: f["product"].__setitem__("boil_minutes", 4))
        code, out = check(root, "--base", base, "--approvals", approvals(root, SAM, []))
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL  facts product.boil_minutes 3 -> 4: needs an approving review on the head from someone "
                      "with review rights here who is not sam", out)
        code, out = check(root, "--base", base, "--approvals", approvals(root, SAM, [review(LEE, h)]))
        self.assertEqual(code, 0, out)
        self.assertIn("ok    facts product.boil_minutes 3 -> 4: decided by lee", out)

    def test_the_authors_own_approval_does_not_count(self):
        root, base = corpus()
        h = change(root, price(99))
        code, out = check(root, "--base", base, "--approvals", approvals(root, FOUNDER, [review(FOUNDER, h)]))
        self.assertEqual(code, 1, out)
        self.assertIn("not counted  fern-founder approved, and is the author: nobody decides their own change", out)
        self.assertIn("needs an approval from fern-founder, and fern-founder is the author", out)

    def test_an_approval_on_an_older_commit_does_not_count(self):
        root, base = corpus()
        first = change(root, price(95))
        h = change(root, price(99))
        code, out = check(root, "--base", base, "--approvals", approvals(root, SAM, [review(FOUNDER, first)]))
        self.assertEqual(code, 1, out)
        self.assertIn(f"not counted  fern-founder approved {first[:7]}, not the head: the change moved after it", out)
        # Approved again on the head, it counts.
        code, out = check(root, "--base", base, "--approvals",
                          approvals(root, SAM, [review(FOUNDER, first), review(FOUNDER, h)]))
        self.assertEqual(code, 0, out)

    def test_a_dismissed_approval_or_one_taken_back_does_not_count(self):
        root, base = corpus()
        h = change(root, price(99))
        code, out = check(root, "--base", base, "--approvals",
                          approvals(root, SAM, [review(FOUNDER, h, "DISMISSED")]))
        self.assertEqual(code, 1, out)
        self.assertIn("fern-founder: an approval that was dismissed, which decides nothing", out)
        code, out = check(root, "--base", base, "--approvals", approvals(root, SAM, [
            review(FOUNDER, h), review(FOUNDER, h, "CHANGES_REQUESTED")]))
        self.assertEqual(code, 1, out)
        self.assertIn("fern-founder: a request for changes", out)
        # A comment after an approval takes nothing back.
        code, out = check(root, "--base", base, "--approvals", approvals(root, SAM, [
            review(FOUNDER, h), review(FOUNDER, h, "COMMENTED")]))
        self.assertEqual(code, 0, out)

    def test_nothing_typed_counts(self):
        root, base = corpus()
        h = change(root, price(99), message="Move the price\n\nApproved-by: fern-founder\napproved by fern-founder")
        comment = dict(review(FOUNDER, h, "COMMENTED"), body="Approved.")
        code, out = check(root, "--base", base, "--approvals", approvals(root, SAM, [comment]))
        self.assertEqual(code, 1, out)
        self.assertIn("needs an approving review on", out)

    def test_review_rights_and_bots(self):
        root, base = corpus()
        h = change(root, lambda f: f["company"].__setitem__("city", "Braga"))
        for who in (review("drive-by", h, association="CONTRIBUTOR"),
                    review("helper[bot]", h, association="NONE", kind="Bot")):
            code, out = check(root, "--base", base, "--approvals", approvals(root, SAM, [who]))
            self.assertEqual(code, 1, out)
            self.assertIn("so it counts only where it is named", out)
        # Named, a login counts whatever GitHub says of it.
        named = [dict(RULES[1], keys="company.*", decides=["drive-by"])]
        root, base = corpus(named)
        h = change(root, lambda f: f["company"].__setitem__("city", "Braga"))
        code, out = check(root, "--base", base, "--approvals",
                          approvals(root, SAM, [review("drive-by", h, association="CONTRIBUTOR")]))
        self.assertEqual(code, 0, out)


class WhatChanged(unittest.TestCase):
    def test_an_unchanged_fact_needs_nothing(self):
        root, base = corpus()
        change(root, lambda f: f["notes"].__setitem__("internal", "still nobody's"))
        code, out = check(root, "--base", base)          # no approvals at all: none are needed
        self.assertEqual(code, 0, out)
        self.assertIn("--    facts notes.internal", out)
        self.assertIn("no rule names it, so it needs no decision", out)
        self.assertIn("no changed fact needs a decision", out)
        code, out = check(root, "--base", "HEAD")
        self.assertEqual(code, 0, out)
        self.assertIn("no fact changed since HEAD: nothing waits on a decision", out)

    def test_added_and_removed_keys_are_changes(self):
        root, base = corpus()
        change(root, lambda f: (f["product"].__setitem__("warranty_years", 2), f["company"].pop("city")))
        code, out = check(root, "--base", base)
        self.assertEqual(code, 2, out)
        self.assertIn("NEEDS facts product.warranty_years added, 2", out)
        self.assertIn('NEEDS facts company.city removed, was "Porto"', out)
        self.assertIn("2 facts changed since", out)

    def test_a_number_said_another_way_is_the_same_fact_and_true_is_not_one(self):
        self.assertEqual(decisions.changes({"a": 89, "b": 1}, {"a": 89.0, "b": True}),
                         [("b", "changed", 1, True)])

    def test_a_rule_that_names_no_fact_fails(self):
        root, base = corpus([dict(RULES[0], keys="product.prcie_usd")])
        change(root, price(99))
        code, out = check(root, "--base", base)
        self.assertEqual(code, 1, out)
        self.assertIn("a rule guards nothing: facts: product.prcie_usd - 'product.prcie_usd' names no fact", out)


class WhereItRuns(unittest.TestCase):
    def test_with_no_pull_request_it_says_what_is_needed_and_exits_2(self):
        root, base = corpus()
        change(root, price(99))
        code, out = check(root, "--base", base)
        self.assertEqual(code, 2, out)
        self.assertIn("NEEDS facts product.price_usd 89 -> 99: fern-founder (facts: product.price_usd); and any "
                      "reviewer who is not the author (facts: company.*, product.*)", out)
        self.assertIn("approvals can only be read on a pull request", out)
        code, out = check(root)
        self.assertEqual(code, 2, out)
        self.assertIn("no base to judge the change against", out)

    def test_a_malformed_section_is_refused(self):
        for rules, says in (
                ([dict(RULES[0], why="")], "says no `why`"),
                ([dict(RULES[0], source="prices")], "decisions.rules[0].source is 'prices'"),
                ([dict(RULES[0], decides="anyone")], "decisions.rules[0].decides is \"reviewer\""),
                ([dict(RULES[0], decides=["not a login"])], "names 'not a login', which is not a GitHub login"),
                ([dict(RULES[0], keys=[])], "decisions.rules[0].keys is a glob"),
                ([dict(RULES[0], approves="x")], "has approves, which it does not take"),
                ([], "`decisions` is an object")):
            root, _ = corpus(rules)
            code, out = check(root, "--base", "HEAD")
            self.assertEqual(code, 1, f"{says}: {out}")
            self.assertIn(says, out)

    def test_approvals_for_another_commit_are_refused(self):
        root, base = corpus()
        h = change(root, price(99))
        code, out = check(root, "--base", base, "--approvals",
                          approvals(root, SAM, [review(FOUNDER, base)], head=base))
        self.assertEqual(code, 2, out)
        self.assertIn(f"the approvals are for {base[:12]}, and this checkout is {h[:12]}", out)

    def test_githubs_merge_commit_is_judged_against_the_base_it_merges_onto(self):
        root, base = corpus()
        git(root, "checkout", "-qb", "pr")
        h = change(root, price(99))
        git(root, "checkout", "-q", base)
        moved = change(root, lambda f: f["company"].__setitem__("name", "Fernhollow"))   # main moved on
        git(root, "-c", "user.email=t@wherefore", "-c", "user.name=t", "merge", "-q", "--no-ff", "-m", "merge", h)
        code, out = check(root, "--approvals", approvals(root, SAM, [review(FOUNDER, h)], head=h))
        self.assertEqual(code, 0, out)
        self.assertIn(f"1 fact changed since the base this pull request merges onto, {moved[:7]}", out)
        env = dict(bare_env(), GITHUB_ACTIONS="true", GITHUB_EVENT_PATH=self.event(base, h, 7))
        code, out = in_process(root, ["--approvals", approvals(root, SAM, [review(FOUNDER, h)], head=h)],
                               env, read=None)
        self.assertEqual(code, 0, out)
        self.assertIn(f"1 fact changed since the base this pull request merges onto, {moved[:7]}", out)
        self.assertNotIn("company.name", out, "main's own change is not this pull request's")

    def event(self, base, h, number):
        path = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-event-")) / "event.json"
        path.write_text(json.dumps({"pull_request": {"number": number, "base": {"sha": base},
                                                     "head": {"sha": h}}}), encoding="utf-8")
        return str(path)

    def test_in_a_workflow_the_reviews_are_read_for_the_events_pull_request(self):
        root, base = corpus()
        h = change(root, price(99))
        asked = []

        def read(repo_name, number, token):
            asked.append((repo_name, number, token))
            return {"number": number, "author": SAM, "head": h, "base": base, "reviews": [review(FOUNDER, h)]}

        env = dict(bare_env(), GITHUB_ACTIONS="true", GITHUB_EVENT_PATH=self.event(base, h, 12),
                   GITHUB_REPOSITORY="fern/site", GITHUB_TOKEN="not-a-token")
        code, out = in_process(root, [], env, read)
        self.assertEqual(code, 0, out)
        self.assertEqual(asked, [("fern/site", 12, "not-a-token")])
        self.assertIn(f"pull request #12 by sam, judged at its head {h[:7]}", out)
        self.assertNotIn("not-a-token", out)
        # Without a token, it cannot read them, and says so.
        del env["GITHUB_TOKEN"]
        code, out = in_process(root, [], env, read)
        self.assertEqual(code, 2, out)
        self.assertIn("GITHUB_TOKEN is not set", out)

    def test_pr_names_one_from_anywhere(self):
        root, base = corpus()
        h = change(root, price(99))

        def read(repo_name, number, token):
            return {"number": number, "author": SAM, "head": h, "base": base, "reviews": [review(LEE, h)]}

        env = dict(bare_env(), GITHUB_REPOSITORY="fern/site", GITHUB_TOKEN="not-a-token")
        code, out = in_process(root, ["--pr", "3"], env, read)
        self.assertEqual(code, 1, out)
        self.assertIn("pull request #3 by sam", out)
        self.assertIn(f"1 fact changed since the pull request's base, {base[:7]}", out)


class ReadingGitHub(unittest.TestCase):
    """The one function that goes to the network, given an opener that does not."""

    class Answer:
        def __init__(self, body):
            self.body = json.dumps(body).encode()

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return self.body

    def test_the_pull_request_and_every_page_of_its_reviews(self):
        seen = []
        many = [review(f"r{i}", "abc") for i in range(decisions.PAGE + 1)]

        def opener(req, timeout):
            seen.append((req.full_url, req.get_header("Authorization")))
            if req.full_url.endswith("/pulls/5"):
                return self.Answer({"user": {"login": SAM}, "head": {"sha": "abc"}, "base": {"sha": "def"}})
            page = int(req.full_url.rsplit("page=", 1)[1])
            return self.Answer(many[(page - 1) * decisions.PAGE: page * decisions.PAGE])

        got = decisions.read_pull("fern/site", 5, "tkn", api="https://api.example", opener=opener)
        self.assertEqual((got["author"], got["head"], got["base"], len(got["reviews"])), (SAM, "abc", "def", 101))
        self.assertEqual([u for u, _ in seen], [
            "https://api.example/repos/fern/site/pulls/5",
            "https://api.example/repos/fern/site/pulls/5/reviews?per_page=100&page=1",
            "https://api.example/repos/fern/site/pulls/5/reviews?per_page=100&page=2"])
        self.assertTrue(all(a == "Bearer tkn" for _, a in seen))

    def test_a_refusal_is_said_without_the_token(self):
        def opener(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)

        with self.assertRaises(decisions.Unread) as e:
            decisions.read_pull("fern/site", 5, "tkn", api="https://api.example", opener=opener)
        self.assertIn("GitHub answered 403", str(e.exception))
        self.assertNotIn("tkn", str(e.exception))


class Status(unittest.TestCase):
    def test_status_says_how_many_facts_a_rule_covers(self):
        root, _ = corpus()
        doc = status.find(root)
        self.assertEqual(doc["decisions"], {"rules": 2, "facts": 5, "covered": 4, "named": 1})
        self.assertIn("  decisions 4 of 5 facts need an approval to change, by 2 rules; 1 from someone named",
                      status.lines(doc))

    def test_no_section_no_line(self):
        root = repo({"wherefore.json": {"wherefore": 1, "name": "k"}})
        self.assertNotIn("decisions", status.find(root))


if __name__ == "__main__":
    unittest.main()
