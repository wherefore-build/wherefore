"""`wherefore check decisions`: a change to a fact carries the approval of someone allowed to give it.

THE RECORD OF WHO DECIDED A FACT WAS A QUOTE. A price moved, and the commit
message said the founder had agreed - in words anyone can type, the agent that
made the change included. That is fine for one team that knows each other's
voices, and it is nothing at all once many people and their agents change
facts at once (docs/scale.md, Stage 2). So a repository declares which facts
need whom, and this check reads the decision from where it is verified: a
pull request's approving reviews, whose author is GitHub's account, not a
typed name.

    "decisions": {
     "rules": [
      {"source": "facts", "keys": "plans.*.price_usd", "decides": ["dana", "lee"],
       "why": "a price is a promise to every customer: the founders set it"},
      {"source": "facts", "keys": "*", "decides": "reviewer",
       "why": "every fact a customer reads is checked by a second person"}
     ]
    }

`source` is a source wherefore.json declares; `keys` a glob over its dotted
leaf keys, or a list of them - the same globs `reach` takes, so `*` matches
dots too; `decides` is "reviewer", anyone with review rights here who is not
the change's author, or a list of GitHub logins, any one of whom decides.

WHAT IT JUDGES. Each source a rule names is read at the base and at HEAD, as
committed - never the working tree, since an approval is given to a commit -
and every leaf key that was added, removed or given another value is a
changed fact. A changed fact needs a decision from EVERY rule whose glob
names it, so a catch-all rule listed before a narrow one can never quietly
cover it. A key no rule names needs nothing, and is listed as such. A glob
that names no key at either end fails: a mistyped glob guards nothing.

WHAT COUNTS AS A DECISION. A review, read from GitHub, that is

  - the reviewer's latest that is not a comment: a later request for changes,
    or the approval being dismissed, takes it back;
  - APPROVED;
  - by someone other than the pull request's author;
  - on the head commit being judged. An approval on an earlier commit does
    not count: the change moved after it.

and for "reviewer", by an account GitHub says has review rights here (its
association is OWNER, MEMBER or COLLABORATOR) and that is not a bot. A named
login counts whatever its association: it is named.

WHAT NEVER COUNTS: anything typed. A commit message, a trailer, the pull
request's body, a comment that says "approved". None of it is read.

WHERE IT RUNS. On a pull request, in GitHub Actions, it reads the pull request
from the event, and its reviews from the REST API with GITHUB_TOKEN. `--pr N`
names one from anywhere GITHUB_TOKEN and GITHUB_REPOSITORY are set.
`--approvals FILE` is a stand-in with the API's shape - {"author", "reviews":
[...], and optionally "head"} - for tests and proofs. With none of them it
prints what the change would need and exits 2: approvals can only be read on a
pull request, and a check that cannot read them must not pass.

WHAT IT CANNOT SEE. Who pushed which commit: a reviewer who pushes a fact
change to someone else's pull request and then approves it decides their own
change. GitHub's "require approval of the most recent reviewable push" is the
guard for that. And who the author is: the account that opened the pull
request. An agent that opens pull requests with its owner's credentials makes
the owner the author, who then cannot approve - see the commands page, "Who
the author is".
"""
import fnmatch
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

from . import __version__, sources

FIELDS = ("rules",)
RULE_FIELDS = ("source", "keys", "decides", "why")
REVIEWER = "reviewer"
LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})(?:\[bot\])?$")
REVIEW_RIGHTS = ("OWNER", "MEMBER", "COLLABORATOR")
API = "https://api.github.com"
TIMEOUT = 30
PAGE = 100
SHOWN = 40
NO_CONTEXT = 2


class Unread(Exception):
    """Something this check needs and could not read: a base, a source, the approvals."""


# ── the section ─────────────────────────────────────────────────────────────

def validate(doc):
    """Refuse what cannot be meant, before anything runs."""
    from .config import ConfigError
    d = doc.get("decisions")
    if d is None:
        return
    shape = ("`decisions` is an object, {\"rules\": [...]}: each rule a `source`, a glob of its "
             "`keys`, who `decides` them - \"reviewer\" or a list of GitHub logins - and `why`")
    if not isinstance(d, dict):
        raise ConfigError(shape)
    unknown = set(d) - set(FIELDS)
    if unknown:
        raise ConfigError(f"`decisions` has {', '.join(sorted(unknown))}, which it does not take: rules")
    rules = d.get("rules")
    if not (isinstance(rules, list) and rules):
        raise ConfigError(shape)
    declared = doc.get("sources") or {}
    for i, rule in enumerate(rules):
        where = f"decisions.rules[{i}]"
        if not isinstance(rule, dict):
            raise ConfigError(f"{where} is an object: source, keys, decides, why")
        unknown = set(rule) - set(RULE_FIELDS)
        if unknown:
            raise ConfigError(f"{where} has {', '.join(sorted(unknown))}, which it does not take: "
                              f"{', '.join(RULE_FIELDS)}")
        src = rule.get("source")
        if not (isinstance(src, str) and src in declared):
            have = ", ".join(map(repr, declared)) or "none"
            raise ConfigError(f"{where}.source is {src!r}, and the sources wherefore.json declares "
                              f"are {have}: a rule names the facts of a declared source")
        keys = rule.get("keys")
        globs = keys if isinstance(keys, list) else [keys]
        if not (globs and all(isinstance(g, str) and g.strip() for g in globs)):
            raise ConfigError(f"{where}.keys is a glob over {src}'s dotted keys - \"plans.*.price_usd\" "
                              f"- or a list of them")
        who = rule.get("decides")
        if who != REVIEWER:
            if not (isinstance(who, list) and who):
                raise ConfigError(f"{where}.decides is \"reviewer\" - anyone with review rights who is "
                                  f"not the author - or a list of the GitHub logins who may decide, "
                                  f"and not {who!r}")
            for login in who:
                if not (isinstance(login, str) and LOGIN.match(login)):
                    raise ConfigError(f"{where}.decides names {login!r}, which is not a GitHub login")
            lowered = [w.lower() for w in who]
            if len(set(lowered)) != len(lowered):
                raise ConfigError(f"{where}.decides names someone twice")
        why = rule.get("why")
        if not (isinstance(why, str) and why.strip()):
            raise ConfigError(f"{where} says no `why`. Who decides a fact is a rule somebody has to "
                              f"stand behind: say why these facts need them")


def rules(cfg):
    out = []
    for rule in (cfg.doc.get("decisions") or {}).get("rules", []):
        globs = rule["keys"] if isinstance(rule["keys"], list) else [rule["keys"]]
        out.append({"source": rule["source"], "globs": globs, "decides": rule["decides"], "why": rule["why"],
                    "label": f"{rule['source']}: {', '.join(globs)}"})
    return out


def names(rule, key):
    return any(fnmatch.fnmatchcase(key, g) for g in rule["globs"])


def who(rule):
    """Who a rule asks for, as a person reads it."""
    if rule["decides"] == REVIEWER:
        return "any reviewer who is not the author"
    return " or ".join(rule["decides"])


# ── the facts, at two commits ───────────────────────────────────────────────

def _git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def resolve(root, ref):
    """The full name of a commit (or tree) here, or None."""
    r = _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{tree}}")
    if r.returncode:
        return None
    r = _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return r.stdout.strip() if r.returncode == 0 else _git(root, "rev-parse", ref).stdout.strip()


def leaves_at(root, ref, path):
    """{dotted key: value} of the JSON at `path` in `ref`; {} where `ref` has no such file."""
    r = subprocess.run(["git", "show", f"{ref}:./{path}"], cwd=root, capture_output=True)
    if r.returncode:
        return {}
    try:
        doc = json.loads(r.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise Unread(f"{path} at {ref[:12]} is not JSON ({e}): a rule names facts by their dotted keys, "
                     f"so the source it names must be JSON")
    return dict(sources.leaves(doc))


def _same(a, b):
    """One value: 89 and 89.0 are, true and 1 are not."""
    return isinstance(a, bool) == isinstance(b, bool) and a == b


def changes(before, after):
    """[(key, how, was, now)] for every key added, removed or changed, in the order the files hold them."""
    out = []
    for key, now in after.items():
        if key not in before:
            out.append((key, "added", None, now))
        elif not _same(before[key], now):
            out.append((key, "changed", before[key], now))
    for key, was in before.items():
        if key not in after:
            out.append((key, "removed", was, None))
    return out


def shown(value):
    s = json.dumps(value, ensure_ascii=False)
    return s if len(s) <= SHOWN else s[:SHOWN - 1] + "…"


def said(how, was, now):
    if how == "added":
        return f"added, {shown(now)}"
    if how == "removed":
        return f"removed, was {shown(was)}"
    return f"{shown(was)} -> {shown(now)}"


# ── the approvals ───────────────────────────────────────────────────────────

def read_pull(repo, number, token, api=None, opener=None):
    """{number, author, head, base, reviews} for pull request `number` of `repo`, from the GitHub REST API.

    The one function here that goes to the network, kept thin so the rest is
    judged offline: the pull request, for its author and its head and base
    commits, and every page of its reviews, oldest first, as GitHub lists them.
    """
    api = (api or os.environ.get("GITHUB_API_URL") or API).rstrip("/")
    opener = opener or urllib.request.urlopen

    def get(path):
        req = urllib.request.Request(api + path, headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": f"wherefore/{__version__} (check decisions)"})
        try:
            with opener(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise Unread(f"GitHub answered {e.code} for {path}: the token cannot read this pull request's "
                         f"reviews (the workflow needs `pull-requests: read`), or it does not exist")
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise Unread(f"GitHub could not be read for {path}: {getattr(e, 'reason', None) or e}")

    pr = get(f"/repos/{repo}/pulls/{number}")
    reviews, page = [], 1
    while True:
        got = get(f"/repos/{repo}/pulls/{number}/reviews?per_page={PAGE}&page={page}")
        if not isinstance(got, list):
            raise Unread(f"GitHub's reviews for #{number} are not a list")
        reviews += got
        if len(got) < PAGE:
            break
        page += 1
    try:
        return {"number": number, "author": pr["user"]["login"], "head": pr["head"]["sha"],
                "base": pr["base"]["sha"], "reviews": reviews}
    except (KeyError, TypeError):
        raise Unread(f"GitHub's answer for #{number} is not a pull request")


def read_file(path):
    """The --approvals stand-in: {"author": login, "reviews": [the API's review objects], "head": optional sha}."""
    try:
        doc = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Unread(f"--approvals {path} cannot be read as JSON: {e}")
    shape = (f"--approvals {path} is {{\"author\": the pull request's author, \"reviews\": [its reviews, "
             f"as GitHub's API lists them]}}, and optionally \"head\", the commit they judge")
    if not (isinstance(doc, dict) and isinstance(doc.get("author"), str) and doc["author"]
            and isinstance(doc.get("reviews"), list)):
        raise Unread(shape)
    if "head" in doc and not (isinstance(doc["head"], str) and doc["head"]):
        raise Unread(shape)
    return {"number": doc.get("number"), "author": doc["author"], "head": doc.get("head"),
            "base": None, "reviews": doc["reviews"]}


def tally(pull, head):
    """({login lowered: approval}, [lines for the reviews that do not count]).

    Each reviewer's latest review that is not a comment says where they stand;
    it counts when it is APPROVED, by someone who is not the author, on `head`.
    """
    author = pull["author"].lower()
    latest = {}
    for rv in pull["reviews"]:
        if not isinstance(rv, dict):
            continue
        login = (rv.get("user") or {}).get("login")
        if not login or rv.get("state") in ("COMMENTED", "PENDING"):
            continue
        latest[login.lower()] = rv
    counted, not_counted = {}, []
    for key, rv in latest.items():
        login, state, on = rv["user"]["login"], rv.get("state"), rv.get("commit_id") or ""
        if state != "APPROVED":
            what = {"DISMISSED": "an approval that was dismissed",
                    "CHANGES_REQUESTED": "a request for changes"}.get(state, f"a review that is {state}")
            not_counted.append(f"{login}: {what}, which decides nothing")
        elif key == author:
            not_counted.append(f"{login} approved, and is the author: nobody decides their own change")
        elif on != head:
            not_counted.append(f"{login} approved {on[:7] or 'no commit'}, not the head: "
                               f"the change moved after it")
        else:
            assoc = rv.get("author_association") or "NONE"
            bot = (rv["user"].get("type") == "Bot") or login.endswith("[bot]")
            counted[key] = {"login": login, "rights": assoc in REVIEW_RIGHTS and not bot,
                            "association": assoc, "bot": bot}
    return counted, not_counted


def decided_by(rule, counted):
    """The logins whose approval decides for `rule`."""
    if rule["decides"] == REVIEWER:
        return [a["login"] for a in counted.values() if a["rights"]]
    named = {n.lower() for n in rule["decides"]}
    return [a["login"] for k, a in counted.items() if k in named]


def wanting(rule, author):
    """What is missing for `rule`, in words."""
    if rule["decides"] == REVIEWER:
        return f"an approving review on the head from someone with review rights here who is not {author}"
    others = [n for n in rule["decides"] if n.lower() != author.lower()]
    if not others:
        return (f"an approval from {' or '.join(rule['decides'])}, and {author} is the author: "
                f"someone else named must make the change, or be named")
    tail = f" ({author} is named, and is the author)" if len(others) < len(rule["decides"]) else ""
    return f"an approving review on the head from {' or '.join(others)}{tail}"


# ── where it runs ───────────────────────────────────────────────────────────

def _event(env):
    """The pull request GitHub Actions is running for, from its event, or None."""
    if env.get("GITHUB_ACTIONS") != "true" or not env.get("GITHUB_EVENT_PATH"):
        return None
    try:
        event = json.loads(pathlib.Path(env["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    pr = event.get("pull_request") if isinstance(event, dict) else None
    return pr if isinstance(pr, dict) and pr.get("number") else None


def _usage():
    return "usage: wherefore check decisions [--base REF] [--pr N | --approvals FILE]"


def _args(args):
    base = pr = approvals = None
    rest = list(args)
    while rest:
        a = rest.pop(0)
        if a in ("-h", "--help"):
            return "help"
        if a in ("--base", "--pr", "--approvals") and rest:
            v = rest.pop(0)
            if a == "--base":
                base = v
            elif a == "--pr":
                if not v.isdigit():
                    return f"--pr takes a pull request's number, not {v!r}"
                pr = int(v)
            else:
                approvals = v
        else:
            return f"wherefore check decisions does not take {a!r}"
    if pr is not None and approvals is not None:
        return "--pr reads the approvals from GitHub and --approvals from a file: one or the other"
    return base, pr, approvals


def main(cfg, args, env=None, read=read_pull):
    env = os.environ if env is None else env
    parsed = _args(args)
    if parsed == "help":
        print(_usage())
        return 0
    if isinstance(parsed, str):
        print(f"::error::{parsed}\n{_usage()}")
        return 2
    base_ref, pr_number, approvals_file = parsed
    validate(cfg.doc)
    ruled = rules(cfg)
    if not ruled:
        print("no `decisions` in wherefore.json: no fact here waits on anyone's approval. Declare which "
              "facts need whom - a source, a glob of its keys, \"reviewer\" or named people, and why")
        return 0
    root = cfg.root
    try:
        return _judge(cfg, root, ruled, base_ref, pr_number, approvals_file, env, read)
    except Unread as e:
        print(f"::error::{e}")
        return 2


def _judge(cfg, root, ruled, base_ref, pr_number, approvals_file, env, read):
    event = _event(env) if pr_number is None else None
    number = pr_number if pr_number is not None else (event or {}).get("number")
    pull = read_file(approvals_file) if approvals_file is not None else None

    def from_github():
        repo, token = env.get("GITHUB_REPOSITORY"), env.get("GITHUB_TOKEN")
        unset = [n for n, v in (("GITHUB_TOKEN", token), ("GITHUB_REPOSITORY", repo)) if not v]
        if unset:
            raise Unread(f"pull request #{number}'s reviews are read from GitHub with GITHUB_TOKEN, for "
                         f"GITHUB_REPOSITORY, and {' and '.join(unset)} {'is' if len(unset) == 1 else 'are'} "
                         f"not set. In a workflow, give the step env: GITHUB_TOKEN: "
                         f"${{{{ secrets.GITHUB_TOKEN }}}}")
        return read(repo, number, token)

    here = resolve(root, "HEAD")
    if here is None:
        raise Unread("there is no commit here to judge")
    parents = _git(root, "rev-list", "--parents", "-n", "1", here).stdout.split()[1:]
    if base_ref is None and len(parents) == 2 and parents[1] in (
            ((event or {}).get("head") or {}).get("sha"), (pull or {}).get("head")):
        # GitHub's checkout of a pull request: its head merged onto its base.
        # What the change brings is what the merge adds to its first parent.
        base, base_said = parents[0], f"the base this pull request merges onto, {parents[0][:7]}"
    elif base_ref is None:
        pr_base = ((event or {}).get("base") or {}).get("sha")
        if not pr_base and pull is None and number is not None:
            pull = from_github()                  # --pr, outside a workflow: the base is the pull request's
        pr_base = pr_base or (pull or {}).get("base")
        if not pr_base:
            raise Unread("no base to judge the change against: --base REF, or run on a pull request, "
                         "whose base it is")
        if resolve(root, pr_base) is None:
            raise Unread(f"the pull request's base, {pr_base[:12]}, is not in this clone: check out with "
                         f"fetch-depth: 0, so the facts can be read where the change began")
        # Where the change left the base, as GitHub's own diff reads it: a base
        # that moved on since must not read as this change undoing it.
        mb = _git(root, "merge-base", pr_base, "HEAD")
        base = mb.stdout.strip() if mb.returncode == 0 else pr_base
        base_said = f"the pull request's base, {base[:7]}"
    else:
        base = resolve(root, base_ref)
        if base is None:
            raise Unread(f"--base {base_ref} is not a commit here: name the commit this change is "
                         f"judged against - in a pull request, its base")
        base_said = base_ref[:7] if re.fullmatch(r"[0-9a-f]{40}", base_ref) else base_ref

    # Every changed fact, and what each needs.
    by_source = {}
    for r in ruled:
        by_source.setdefault(r["source"], []).append(r)
    found, idle = [], []
    for name, rs in by_source.items():
        path = cfg.doc["sources"][name]["path"]
        before, after = leaves_at(root, base, path), leaves_at(root, here, path)
        for r in rs:
            for g in r["globs"]:
                if not any(fnmatch.fnmatchcase(k, g) for k in (*before, *after)):
                    idle.append(f"{r['label']} - {g!r} names no fact in {path} at {base_said} or at HEAD")
        for key, how, was, now in changes(before, after):
            found.append((name, key, how, was, now, [r for r in rs if names(r, key)]))
        if _git(root, "diff", "--quiet", "HEAD", "--", path).returncode == 1:
            print(f"note: {path} has changes not committed; they are not judged - an approval is given to a commit")
    if idle:
        for line in idle:
            print(f"::error::a rule guards nothing: {line}. A mistyped glob would leave the facts it "
                  f"meant unguarded, so it fails")
        return 1
    for r in ruled:
        print(f"  rule  {r['label']} - {who(r)} decides")
    needing = [f for f in found if f[5]]
    if found:
        print(f"{len(found)} fact{'s' if len(found) != 1 else ''} changed since {base_said}; "
              f"{len(needing)} need{'s' if len(needing) == 1 else ''} a decision")
    for name, key, how, was, now, rs in found:
        if not rs:
            print(f"  --    {name} {key} {said(how, was, now)}: no rule names it, so it needs no decision")
    if not needing:
        print("no changed fact needs a decision" if found else
              f"no fact changed since {base_said}: nothing waits on a decision")
        return 0

    if pull is None and number is not None:
        pull = from_github()                      # read only when a fact needs it
    if pull is None:
        for name, key, how, was, now, rs in needing:
            print(f"  NEEDS {name} {key} {said(how, was, now)}: "
                  + "; and ".join(f"{who(r)} ({r['label']})" for r in rs))
        print(f"\n::error::{len(needing)} changed fact{'s' if len(needing) != 1 else ''} need a decision, and "
              f"approvals can only be read on a pull request: run this in GitHub Actions on pull_request "
              f"and pull_request_review, or give --pr N with GITHUB_TOKEN and GITHUB_REPOSITORY. Nothing "
              f"typed - a commit message, a pull request's body - is a decision")
        return NO_CONTEXT

    head = pull.get("head") or here
    if head != here and not (len(parents) == 2 and parents[1] == head):
        raise Unread(f"the approvals are for {head[:12]}, and this checkout is {here[:12]}: an approval "
                     f"speaks for the commit it was given on. When the pull request has moved on, the "
                     f"run for its newest push is the one that judges it")
    counted, not_counted = tally(pull, head)
    number = f"pull request #{pull['number']}" if pull.get("number") else "the change"
    print(f"{number} by {pull['author']}, judged at its head {head[:7]}")
    for a in counted.values():
        rights = "" if a["rights"] else (" - a bot, so it counts only where it is named" if a["bot"] else
                                         f" - no review rights here ({a['association']}), so it counts only "
                                         f"where it is named")
        print(f"  approval     {a['login']} on {head[:7]}{rights}")
    for line in not_counted:
        print(f"  not counted  {line}")

    lacking, deciders = 0, set()
    for name, key, how, was, now, rs in needing:
        got, missing = [], []
        for r in rs:
            by = decided_by(r, counted)
            if by:
                got.append(f"{', '.join(by)} ({r['label']})")
                deciders.update(by)
            else:
                missing.append(f"{wanting(r, pull['author'])} ({r['label']})")
        if missing:
            lacking += 1
            print(f"  FAIL  {name} {key} {said(how, was, now)}: needs " + "; and ".join(missing))
        else:
            print(f"  ok    {name} {key} {said(how, was, now)}: decided by " + "; and ".join(got))
    if lacking:
        print(f"\n::error::{lacking} of the {len(needing)} changed fact{'s' if len(needing) != 1 else ''} "
              f"needing a decision {'lacks' if lacking == 1 else 'lack'} one. A decision is an approving review on the head commit by someone the "
              f"rule allows; nothing typed - a commit message, the pull request's body, a comment - counts")
        return 1
    print(f"\nevery changed fact a rule names carries its decision: {len(needing)} decided, by "
          f"{', '.join(sorted(deciders, key=str.lower))}")
    return 0


# ── for `wherefore status` ──────────────────────────────────────────────────

def coverage(cfg):
    """{rules, facts, covered, named}: how many facts, as the working tree holds them, a rule covers."""
    ruled = rules(cfg)
    facts = covered = named = 0
    for name, src in (cfg.doc.get("sources") or {}).items():
        try:
            doc = json.loads((cfg.root / src["path"]).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for key, _ in sources.leaves(doc):
            facts += 1
            rs = [r for r in ruled if r["source"] == name and names(r, key)]
            covered += bool(rs)
            named += any(r["decides"] != REVIEWER for r in rs)
    return {"rules": len(ruled), "facts": facts, "covered": covered, "named": named}


if __name__ == "__main__":                       # pragma: no cover - the CLI is the way in
    from . import config
    sys.exit(main(config.load(), sys.argv[1:]))
