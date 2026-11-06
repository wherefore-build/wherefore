"""The inbox, written back: the plan onto each issue when it is planned, and what shipped when it ships.

THE LEDGER IS roadmap.json. An item that answers issues names them, who asked,
and its plan; when it ships, its state is shipped with the release and the
feature. This script carries the ledger to the issues, so the person who
asked - and the agent that filed the report for them - reads it there:

    python3 corpus/inbox.py --planned          on every push to main: for each
                                               item next or later with issues,
                                               the plan, once
    python3 corpus/inbox.py --shipped          on every release: for each shipped
                                               item, what shipped, once; then
                                               the issue is closed
    python3 corpus/inbox.py --planned --show   say what would be posted; send nothing

ONCE. Every comment carries a marker naming the item and the step, and an
issue that already has that marker is left alone - except that a shipped note
written before the feature's clips existed gains the Watch line, once - so a
re-run posts nothing twice and the first run after this script arrives catches up every issue
that was answered before it existed. The shipped comment ends with a line an
agent reads:

    wherefore-inbox: shipped version=0.16.0 feature=scan-read

GITHUB_TOKEN with issues: write is what it takes. Without one, --show still
says what would be done.
"""
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = "wherefore-build/wherefore"
SITE = "https://wherefore.build/features/"
API = "https://api.github.com"


def ledger():
    items = json.loads((ROOT / "roadmap.json").read_text(encoding="utf-8"))["items"]
    feats = {f["id"]: f for f in json.loads((ROOT / "src/wherefore/features.json").read_text(encoding="utf-8"))["features"]}
    return items, feats


def number(url):
    return int(url.rsplit("/", 1)[1])


def marker(item, step):
    return f"<!-- wherefore-inbox {step} {item['id']} -->"


def planned_comment(item):
    return (f"On the roadmap as **{item['name']}** ({item['state']}), asked for by @{item['asked_by']}.\n\n"
            f"**The plan:** {item['plan']}\n\n"
            f"The roadmap is a file beside the engine's code, https://github.com/{REPO}/blob/main/roadmap.json, "
            f"and the company's site shows it. When this ships, the release says so here and closes the issue.\n\n"
            f"{marker(item, 'planned')}")


def watch(item, feature):
    """The feature's clips, on its release (corpus/motion_render.py puts them there)."""
    base = f"https://github.com/{REPO}/releases/download/v{feature['since']}/{feature['id']}"
    return f"**Watch:** [portrait]({base}-portrait.mp4) · [landscape]({base}-landscape.mp4)"


def shipped_comment(item, feature):
    return (f"Shipped in Wherefore {item['since']} as **{feature['name']}**: {item['words']}\n\n"
            f"**What was planned, and built:** {item.get('plan', '')}\n\n"
            f"**The feature now:** {feature.get('details', '')}\n\n"
            f"{watch(item, feature)}\n\n"
            f"Install: `pip install -U wherefore-build=={item['since']}` · "
            f"Details: {SITE}#{feature['id']} · "
            f"Release notes: https://github.com/{REPO}/releases/tag/v{item['since']}\n\n"
            f"wherefore-inbox: shipped version={item['since']} feature={feature['id']}\n"
            f"{marker(item, 'shipped')}")


class GitHub:
    def __init__(self, token):
        self.token = token

    def call(self, method, path, body=None):
        req = urllib.request.Request(f"{API}{path}", method=method,
                                     headers={"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
                                              "User-Agent": "wherefore-inbox", "X-GitHub-Api-Version": "2022-11-28"},
                                     data=json.dumps(body).encode() if body is not None else None)
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode("utf-8")
        return json.loads(text) if text else None

    def comments(self, n):
        out, page = [], 1
        while True:
            got = self.call("GET", f"/repos/{REPO}/issues/{n}/comments?per_page=100&page={page}")
            out += got
            if len(got) < 100:
                return out
            page += 1

    def said(self, n, mark):
        """The comment carrying `mark`, or None."""
        return next((c for c in self.comments(n) if mark in c.get("body", "")), None)

    def comment(self, n, body):
        self.call("POST", f"/repos/{REPO}/issues/{n}/comments", {"body": body})

    def edit(self, comment_id, body):
        self.call("PATCH", f"/repos/{REPO}/issues/comments/{comment_id}", {"body": body})

    def close(self, n):
        self.call("PATCH", f"/repos/{REPO}/issues/{n}", {"state": "closed", "state_reason": "completed"})


def plan(gh, show):
    items, _ = ledger()
    done = 0
    for it in items:
        if it["state"] == "shipped" or not it.get("issues"):
            continue
        for url in it["issues"]:
            n, body = number(url), planned_comment(it)
            if show:
                print(f"would say on #{n}, if not said: the plan for {it['id']}\n" + "\n".join("  | " + l for l in body.splitlines()))
                continue
            if gh.said(n, marker(it, "planned")):
                continue
            gh.comment(n, body)
            done += 1
            print(f"said on #{n}: the plan for {it['id']}")
    return done


def ship(gh, show):
    items, feats = ledger()
    done = 0
    for it in items:
        if it["state"] != "shipped" or not it.get("issues"):
            continue
        f = feats[it["feature"]]
        for url in it["issues"]:
            n, body = number(url), shipped_comment(it, f)
            if show:
                print(f"would say on #{n}, if not said, and close it: shipped {it['id']} in {it['since']}\n"
                      + "\n".join("  | " + l for l in body.splitlines()))
                continue
            earlier = gh.said(n, marker(it, "shipped"))
            if earlier:
                # Said before the clips existed: the note gains them, once.
                if "/releases/download/" not in earlier.get("body", ""):
                    gh.edit(earlier["id"], earlier["body"].replace("\n\nInstall: ", f"\n\n{watch(it, f)}\n\nInstall: ", 1))
                    done += 1
                    print(f"added the clips to the note on #{n}: shipped {it['id']} in {it['since']} as {f['id']}")
                continue
            gh.comment(n, body)
            gh.close(n)
            done += 1
            print(f"said on #{n} and closed it: shipped {it['id']} in {it['since']} as {f['id']}")
    return done


def main(argv):
    show = "--show" in argv
    mode = [a for a in argv if a in ("--planned", "--shipped")]
    if len(mode) != 1:
        print("usage: python3 corpus/inbox.py --planned|--shipped [--show]")
        return 2
    token = os.environ.get("GITHUB_TOKEN")
    if not token and not show:
        print("::error::GITHUB_TOKEN is not set; --show says what would be done without one")
        return 1
    gh = GitHub(token) if token else None
    try:
        n = plan(gh, show) if mode[0] == "--planned" else ship(gh, show)
    except urllib.error.HTTPError as e:
        print(f"::error::GitHub answered {e.code} for {e.url}: {e.read().decode('utf-8', 'replace')[:300]}")
        return 1
    if not show:
        print(f"{n} issue{'s' if n != 1 else ''} written to; the rest already said it")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
