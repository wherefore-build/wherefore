"""`wherefore report`: feedback for the engine's makers - a bug, a question, a request - in one command.

A DEVELOPER TELLS THEIR AGENT TO PING US, AND THIS IS WHAT THE AGENT RUNS. It
writes the report a maintainer needs and nothing private: a title; the words,
as the body; the release, Python and the platform; the shape of the corpus -
its name and how many generators, rules, captured groups and sources it
declares, never their contents; and the output of the command that went
wrong, if it is given with --from. It prints the whole report before anything
leaves the machine. Then, if `gh` is installed and signed in, it opens the
issue on wherefore-build/wherefore; if not, it prints a link that opens the
issue filled in, which GitHub serves with no token. `--show` prints the report
and sends nothing; `--link` prints it and the link, and sends nothing even
when `gh` is signed in, so the person can read it and send it themselves.

    wherefore report --title "The gate refuses a captured group" "What I did, and what it said." --from gate.log --show
    wherefore report --title "Scan two repositories at once" "Point it at a site and an app together." --link

THERE IS NO KIND. Whether a thing is a bug or a missing feature depends on
what the engine was meant to do, which is the maintainers' judgment; it is
made in triage, where the issue is labelled (wherefore-build/wherefore#15).
One report says one thing: several things are several reports.

THE WORDS ARE THE PERSON'S, OR THEIR AGENT'S AND APPROVED BY THEM. An agent may
draft the title and the words from what the person said; the person reads the
report, and it is sent only when they say so - by the agent with `gh`, or by
the person through the link. WHAT IT NEVER DOES: read a file it was not given,
send without printing, or name a path on the machine it runs on.
"""
import pathlib
import platform
import shutil
import subprocess
import urllib.parse

from . import __version__

REPO = "wherefore-build/wherefore"
USAGE = "usage: wherefore report --title TITLE WORDS ... [--from FILE] [--show | --link]"
TITLE_MAX = 100        # a title is a line in a list of issues; the rest is the words
LINK_MAX = 8000        # GitHub refuses a longer address; past it, the link would open nothing


def shape():
    """The corpus's shape, in counts; never a file's name, a value in one, or a path on this machine."""
    from . import config
    try:
        config.find_root()
    except SystemExit:                           # a ConfigError: nothing here or above, or WHEREFORE_ROOT points nowhere
        return "no corpus here"
    try:
        cfg = config.load()
    except (Exception, SystemExit):              # the error names the file and the directory; the report says neither
        return "a wherefore.json the engine refuses (add its error with --from, if it helps)"
    d = cfg.doc
    inv = d.get("inventory", {})
    parts = [f"{len(d.get('generators', []))} generators", f"{len(d.get('sources', {}))} sources",
             f"{len(inv.get('authored', {}).get('rules', []))} authored rules",
             f"{len(inv.get('captured', {}).get('groups', {}))} captured groups"]
    if "entry" in d:
        parts.append("configured in Python (`entry`)")
    if "palette" in d:
        parts.append("a palette declared" if "none" not in d["palette"] else "no palette, by declaration")
    return f"{cfg.name}: " + ", ".join(parts)


def body(title, words, output=None):
    """The report, as Markdown, in the order a maintainer reads it: what, then where, then what it printed."""
    lines = [f"# {title}", "", words.strip(), "",
             f"**Engine:** wherefore {__version__} · Python {platform.python_version()} · {platform.system()} {platform.machine()}",
             f"**The corpus:** {shape()}", ""]
    if output is not None:
        lines += ["**What it printed:**", "", "```", output.rstrip("\n"), "```", ""]
    lines += ["_Written by `wherefore report`: a title, the words, the release, the corpus's shape in counts "
              "and the output given with --from. No file's contents._"]
    return "\n".join(lines) + "\n"


def link(title, text):
    q = urllib.parse.urlencode({"title": title, "body": text})
    return f"https://github.com/{REPO}/issues/new?{q}"


def gh_signed_in():
    gh = shutil.which("gh")
    if not gh:
        return None
    r = subprocess.run([gh, "auth", "status"], capture_output=True, text=True)
    return gh if r.returncode == 0 else None


def parse(args):
    out = {"title": None, "words": [], "from": None, "show": False, "link": False}
    it = iter(args)
    for a in it:
        if a in ("-h", "--help"):
            print(USAGE + "\n\n" + __doc__.split("\n\n")[1])
            return 0
        if a == "--show":
            out["show"] = True
        elif a == "--link":
            out["link"] = True
        elif a in ("--title", "--from"):
            v = next(it, None)
            if v is None:
                what = "a title, one line" if a == "--title" else "a file, the output of the command that went wrong"
                print(f"::error::{a} takes {what}\n{USAGE}")
                return 2
            out[a[2:]] = v
        else:
            out["words"].append(a)
    if out["show"] and out["link"]:
        print(f"::error::--show or --link, not both: --show prints the report, --link prints it and the link\n{USAGE}")
        return 2
    if out["title"] is None:
        if out["words"] and out["words"][0] in ("bug", "ask", "feature"):
            print("::error::wherefore report no longer takes bug, ask or feature: the maintainers label each issue "
                  "in triage. Give it a title and the words:\n"
                  f"  wherefore report --title \"one line\" \"the rest\"\n{USAGE}")
        else:
            print(f"::error::give the report a title, one line, with --title; the words after it are the body\n{USAGE}")
        return 2
    title = " ".join(out["title"].split())
    if not title:
        print(f"::error::--title is empty: say in one line what the report is about\n{USAGE}")
        return 2
    if len(title) > TITLE_MAX:
        print(f"::error::the title is {len(title)} characters; keep it to {TITLE_MAX}, a line in a list, "
              f"and say the rest in the words\n{USAGE}")
        return 2
    out["title"] = title
    if not " ".join(out["words"]).strip():
        print(f"::error::say it in words after the title: what happened, what you wanted, or what you asked\n{USAGE}")
        return 2
    return out


def main(args):
    opts = parse(args)
    if isinstance(opts, int):
        return opts
    output = None
    if opts["from"]:
        p = pathlib.Path(opts["from"])
        if not p.is_file():
            print(f"::error::--from {opts['from']}: no such file")
            return 2
        output = p.read_text(encoding="utf-8", errors="replace")
    title = opts["title"]
    text = body(title, " ".join(opts["words"]), output)
    print(text)
    if opts["show"]:
        print("--show: nothing was sent. Show the person; send it only when they say.")
        return 0
    url = link(title, text)
    fits = len(url) <= LINK_MAX
    if opts["link"]:
        if not fits:
            print(f"::error::the report is too long for a link ({len(url)} characters; GitHub opens at most "
                  f"about {LINK_MAX}). Give --from less of the output, or send it with gh, signed in.")
            return 1
        print("--link: nothing was sent. This link opens the issue, filled in, for the person to read and send:\n" + url)
        return 0
    gh = gh_signed_in()
    if gh:
        r = subprocess.run([gh, "issue", "create", "--repo", REPO, "--title", title, "--body", text],
                           capture_output=True, text=True)
        if r.returncode == 0:
            print(f"opened: {r.stdout.strip()}")
            return 0
        print(f"::error::gh could not open the issue:\n{r.stderr.strip()}")
        if fits:
            print(f"Open it yourself: {url}")
        return 1
    if not fits:
        print(f"::error::gh is not here, or not signed in, and the report is too long for a link ({len(url)} "
              f"characters; GitHub opens at most about {LINK_MAX}). Nothing was sent. Give --from less of the "
              "output, or sign in to gh.")
        return 1
    print("gh is not here, or not signed in, so nothing was sent. This link opens the issue, filled in, "
          "for the person to send:\n" + url)
    return 0
