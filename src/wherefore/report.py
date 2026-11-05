"""`wherefore report`: a bug, a question or a feature request, written for the engine's makers.

A DEVELOPER TELLS THEIR AGENT TO PING US, AND THIS IS WHAT THE AGENT RUNS. It
writes the report a maintainer needs and nothing private: the release, Python
and the platform; the shape of the corpus - its name and how many generators,
rules, captured groups and sources it declares, never their contents; the
output of the command that went wrong, if it is given with --from; and the
person's words. It prints the whole report before anything leaves the machine.
Then, if `gh` is installed and signed in, it opens the issue on
wherefore-build/wherefore with the kind as its label; if not, it prints a link
that opens the issue prefilled, which GitHub serves with no token. `--show`
prints the report and sends nothing: the skill tells an agent to run that
first and show the person.

    wherefore report bug "the gate says X and I did Y" --from gate.log
    wherefore report ask "can a captured group name two upstreams?"
    wherefore report feature "scan two repositories at once" --show

WHAT IT NEVER DOES: read a file it was not given, send without printing, or
put words in the person's mouth. The words after the kind are the report's
and come from the person.
"""
import json
import pathlib
import platform
import shutil
import subprocess
import sys
import urllib.parse

from . import __version__

REPO = "wherefore-build/wherefore"
KINDS = {"bug": ("bug", "bug"), "ask": ("question", "question"), "feature": ("feature request", "enhancement")}
USAGE = "usage: wherefore report bug|ask|feature WORDS ... [--from FILE] [--show]"  # one usage line per kind in commands.json


def shape():
    """The corpus's shape, in counts; never a name of a file or a value in one."""
    try:
        from . import config
        cfg = config.load()
    except (Exception, SystemExit) as e:         # no corpus, or one the engine refuses (a ConfigError exits)
        return f"no corpus here, or one the engine refuses: {str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__}"
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


def body(kind, words, output=None):
    """The report, as Markdown, in the order a maintainer reads it."""
    kind_words = KINDS[kind][0]
    lines = [f"# {kind_words}: {words}", "",
             f"**Engine:** wherefore {__version__} · Python {platform.python_version()} · {platform.system()} {platform.machine()}",
             f"**The corpus:** {shape()}", ""]
    if output is not None:
        lines += ["**What it printed:**", "", "```", output.rstrip("\n"), "```", ""]
    lines += [f"_Written by `wherefore report`: the release, the corpus's shape in counts, the output given "
              f"with --from, and the person's words. No file's contents._"]
    return "\n".join(lines) + "\n"


def link(kind, title, text):
    q = urllib.parse.urlencode({"title": title, "labels": KINDS[kind][1], "body": text})
    return f"https://github.com/{REPO}/issues/new?{q}"


def gh_signed_in():
    gh = shutil.which("gh")
    if not gh:
        return None
    r = subprocess.run([gh, "auth", "status"], capture_output=True, text=True)
    return gh if r.returncode == 0 else None


def parse(args):
    out = {"kind": None, "words": [], "from": None, "show": False}
    it = iter(args)
    for a in it:
        if a in ("-h", "--help"):
            print(USAGE + "\n\n" + __doc__.split("\n\n")[1])
            return 0
        if a == "--show":
            out["show"] = True
        elif a == "--from":
            out["from"] = next(it, None)
            if out["from"] is None:
                print(f"::error::--from takes a file, the output of the command that went wrong\n{USAGE}")
                return 2
        elif out["kind"] is None:
            if a not in KINDS:
                print(f"::error::wherefore report takes bug, ask or feature first, not {a!r}\n{USAGE}")
                return 2
            out["kind"] = a
        else:
            out["words"].append(a)
    if out["kind"] is None:
        print(f"::error::say what kind of report: bug, ask or feature\n{USAGE}")
        return 2
    if not out["words"]:
        print(f"::error::say it in words after the kind - the person's words, not an agent's\n{USAGE}")
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
    words = " ".join(opts["words"])
    text = body(opts["kind"], words, output)
    title = f"{KINDS[opts['kind']][0]}: {words}"[:120]
    print(text)
    if opts["show"]:
        print("--show: nothing was sent. Run it again without --show to open the issue.")
        return 0
    gh = gh_signed_in()
    if gh:
        r = subprocess.run([gh, "issue", "create", "--repo", REPO, "--title", title,
                            "--label", KINDS[opts["kind"]][1], "--body", text],
                           capture_output=True, text=True)
        if r.returncode == 0:
            print(f"opened: {r.stdout.strip()}")
            return 0
        print(f"::error::gh could not open the issue:\n{r.stderr.strip()}\nOpen it yourself: {link(opts['kind'], title, text)}")
        return 1
    print("gh is not here, or not signed in, so nothing was sent. This link opens the issue, filled in, "
          "for the person to send:\n" + link(opts["kind"], title, text))
    return 0
