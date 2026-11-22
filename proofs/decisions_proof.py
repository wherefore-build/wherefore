#!/usr/bin/env python3
"""Change a fact someone must decide, and require `wherefore check decisions` to
refuse every approval that is not that person's decision on that commit - and
to pass the one that is.

The fixture company says, in its wherefore.json, that the founder
(fern-founder) decides the price and any reviewer the rest of what a customer
reads. In this proof's copy the price moves twice - 89 to 95, then to 99 - and
the last commit's message says, as a person or an agent might type it, that
the founder approved. The approvals are files with the GitHub API's shape,
written outside the tree, so nothing here goes to the network.

  1. no approval at all                         needs the founder
  2. approved only by its author                the author decides nothing
  3. approved on the earlier commit             the change moved after it
  4. "Approved-by" in the commit message,       nothing typed counts
     and a comment saying "Approved"
  5. the founder's approval, dismissed          decides nothing
  6. another reviewer's approval only           the price is the founder's
  7. a rule whose glob is mistyped              guards nothing: fails
  8. no pull request to read                    says what is needed, exits 2
  9. the founder, on the head, not the author   passes

Usage:  python3 proofs/decisions_proof.py
"""
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _fixture import fresh, git

ROOT = fresh("decisions")
from wherefore.prove import Edit, check as _check, report

# A proof is run by CI inside a pull request's own workflow; that pull request
# is not the one this proof judges, and must not be read.
for k in [k for k in os.environ if k.startswith("GITHUB_")]:
    del os.environ[k]

results = []
BASE = git(ROOT, "rev-parse", "HEAD").stdout.strip()
FOUNDER, AUTHOR, REVIEWER = "fern-founder", "sam", "lee"
FILES = pathlib.Path(tempfile.mkdtemp(prefix="wherefore-approvals-"))


def commit(old, new, message):
    p = ROOT / "facts.json"
    s = p.read_text(encoding="utf-8")
    if s.count(old) != 1:
        sys.exit(f"::error::facts.json: the anchor {old!r} is not there once - the case is stale")
    p.write_text(s.replace(old, new), encoding="utf-8")
    git(ROOT, "-c", "user.email=agent@wherefore", "-c", "user.name=agent", "commit", "-qam", message)
    return git(ROOT, "rev-parse", "HEAD").stdout.strip()


def review(login, on, state="APPROVED", **more):
    return {"user": {"login": login, "type": "User"}, "state": state, "commit_id": on,
            "author_association": "MEMBER", **more}


def approvals(name, author, reviews):
    path = FILES / f"{name}.json"
    path.write_text(json.dumps({"author": author, "reviews": reviews}, indent=1), encoding="utf-8")
    return str(path)


def decisions(name, expect_fail, must_say, approved=None, forbid=(), planted=None):
    args = ["--base", BASE] + (["--approvals", approved] if approved else [])
    return _check(results, name, "-m", expect_fail, must_say, "wherefore", "check", "decisions", *args,
                  forbid=forbid, planted=planted)


STALE = commit('"price_usd": 89', '"price_usd": 95', "Move the price to 95")
HEAD = commit('"price_usd": 95', '"price_usd": 99',
              "Move the price to 99\n\nThe founder agreed on the call.\n\nApproved-by: fern-founder")
NEEDS = "FAIL  facts product.price_usd 89 -> 99: needs an approving review on the head from fern-founder"

decisions("1. a sensitive change with no approval -> needs the founder", True, [NEEDS],
          approvals("none", AUTHOR, []))

decisions("2. approved only by its author -> the author decides nothing", True,
          ["not counted  fern-founder approved, and is the author: nobody decides their own change",
           "needs an approval from fern-founder, and fern-founder is the author"],
          approvals("author", FOUNDER, [review(FOUNDER, HEAD)]))

decisions("3. approved on the earlier commit -> the change moved after it", True,
          [f"not counted  fern-founder approved {STALE[:7]}, not the head: the change moved after it",
           NEEDS],
          approvals("stale", AUTHOR, [review(FOUNDER, STALE)]))

typed = git(ROOT, "log", "-1", "--format=%B").stdout
decisions("4. 'Approved-by' typed in the commit message, and a comment -> nothing typed counts", True,
          [NEEDS], approvals("typed", AUTHOR, [review(FOUNDER, HEAD, "COMMENTED", body="Approved.")]),
          forbid=["decided by fern-founder"], planted="Approved-by: fern-founder" in typed)

decisions("5. the founder's approval, dismissed -> decides nothing", True,
          ["fern-founder: an approval that was dismissed, which decides nothing", NEEDS],
          approvals("dismissed", AUTHOR, [review(FOUNDER, HEAD, "DISMISSED")]))

decisions("6. another reviewer's approval only -> the price is the founder's", True,
          [NEEDS, "approval     lee on"],
          approvals("reviewer", AUTHOR, [review(REVIEWER, HEAD)]))

with Edit("wherefore.json") as p:
    cfg = json.loads(p.read_text(encoding="utf-8"))
    cfg["decisions"]["rules"][0]["keys"] = "product.prcie_usd"
    p.write_text(json.dumps(cfg, indent=1) + "\n", encoding="utf-8")
    decisions("7. a rule whose glob is mistyped -> it guards nothing, and fails", True,
              ["a rule guards nothing: facts: product.prcie_usd"],
              approvals("mistyped", AUTHOR, [review(FOUNDER, HEAD)]))

decisions("8. no pull request to read -> what is needed, and exit 2", True,
          ["NEEDS facts product.price_usd 89 -> 99: fern-founder", "approvals can only be read on a pull request"])

decisions("9. the founder, on the head, not the author -> passes", False,
          ["ok    facts product.price_usd 89 -> 99: decided by fern-founder",
           "every changed fact a rule names carries its decision"],
          approvals("decided", AUTHOR, [review(FOUNDER, STALE), review(FOUNDER, HEAD)]))

git(ROOT, "reset", "-q", "--hard", BASE)
left = git(ROOT, "status", "--porcelain").stdout
if left.strip():
    print(f"::error::the proof did not put the fixture back:\n{left}")
    results.append(False)
sys.exit(report(results))
