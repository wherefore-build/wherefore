"""The docs, shipped with each release as data, so a client renders the docs of the release it pins.

A PAGE A PERSON READS TO USE WHEREFORE, held to the release it describes.
Each page is Markdown in docs/ beside this module, authored by the engine's
makers and held by the engine's tests: every command has its section in the
commands page and every section is a command; every section of wherefore.json
the engine reads has its section in the configuration page; every `wherefore`
command a page names exists; and every example - a fenced block that begins
`$ wherefore ...` - is run again on the example company, and must print what
the page says, in order. The start page is the skill's own start guide, so
the person and their agent read one text.

The company's site reads `pages()` from the release it pins and renders them
at /docs/; a release that adds a page the site has no place for stops the
site's build, the way a feature without words does.
"""
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
PAGES = [
    ("start", "Start", "skills/wherefore/start.md"),
    ("commands", "Commands", "docs/commands.md"),
    ("configuration", "Configuration", "docs/configuration.md"),
    ("checks", "Checks and proofs", "docs/checks.md"),
    ("reporting", "Reporting", "docs/reporting.md"),
]
# Every section of wherefore.json the engine reads; tests/test_docs.py holds the
# configuration page to this list, and this list to config.py by hand.
CONFIG_SECTIONS = ("wherefore", "name", "sources", "generators", "not_a_generator", "inventory", "compare",
                   "surfaces", "retired", "reach", "claims", "palette", "published", "proofs", "hook",
                   "entry", "messages", "observer", "temp_prefix", "units", "drift", "launch")
EXAMPLE = re.compile(r"^```\n\$ (wherefore [^\n]*)\n(.*?)^```", re.M | re.S)


def pages():
    """[(id, title, markdown)] in reading order."""
    return [(pid, title, (HERE / rel).read_text(encoding="utf-8")) for pid, title, rel in PAGES]


def examples(markdown):
    """[(command, [lines])] for every example a page runs: the command typed
    after `$`, and the lines it must print, in order; `…` stands for lines
    left out."""
    return [(m.group(1).strip(), [l for l in m.group(2).splitlines() if l.strip()])
            for m in EXAMPLE.finditer(markdown)]


def sections(markdown):
    """The `## ` headings of a page, in order."""
    return re.findall(r"^## (.+)$", markdown, re.M)
