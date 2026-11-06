"""Every colour comes from one source, unless a file says, with why, that its colours are another's.

A BRAND IS A FACT LIKE A PRICE. A company that holds its colours in one file
and builds its pages from it still ends up with a colour typed somewhere: a
stylesheet, a generator, a page another tool drew. It looks right until the
accent changes, and then it is the one thing that did not - the company's own
site found the engine's map carrying the brand's accent typed a second time,
inside the engine. So this reads every tracked text file and fails a colour
literal - #hex, rgb(), hsl() and their kin, or a named colour on a colour
property - that is not one of the values the palette's source holds, naming
the file and the line.

THE PALETTE IS DECLARED, OR DECLINED, IN wherefore.json:

    "palette": {
     "source": "brand/tokens.json",
     "read": ["gen/**", "site/**"],
     "not_ours": {"site/pendulum/index.html": "another company's page, framed; its own suite holds its brand"}
    }

`source` is a JSON file: every string in it that is a #RRGGBB (or #RGB, or
with alpha) colour is one of the brand's values, wherever it sits. `read`, if
given, limits the files read to those globs; without it every tracked text file
is read, the source itself aside. `not_ours` names files whose colours are
somebody else's, each with the reason, and they are skipped and counted. A
corpus with no brand says so, once, with why:

    "palette": {"none": "a shop's parts list: nothing here is coloured"}

ON BY DEFAULT. A corpus that declares neither fails this check in words, and the
gate, which never fails for it, says when colours are said in more than one of
the files the build made and no palette is declared - so the drift is caught
before anybody thinks to ask for it. The gate reads only the generated files
for this, which it wrote and compared anyway: a courtesy must not widen what
the gate opens, because a client may hold its gate to exactly that.

WHAT IT CANNOT SEE: a colour built at run time from parts, a colour inside a
picture, and a literal smuggled through an interpolation. A page that takes its
colours from the brand as var(--…) passes; the brand's own values, written out
by a generator from the source, pass because they are the source's.
"""
import fnmatch
import json
import pathlib
import re

from .retired import tracked_files

HEX = re.compile(r"(?<![\w&])#(?:[0-9A-Fa-f]{8}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3,4})\b")
FUNC = re.compile(r"\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(", re.I)
NAMED = re.compile(r"\b(?:color|background(?:-color)?|border(?:-[a-z]+)*|outline(?:-color)?|fill|stroke|"
                   r"text-decoration-color|caret-color)\s*:[^;{}\"']*?\b(white|black|red|green|blue|gray|grey|"
                   r"orange|yellow|purple|pink|brown|silver|navy|teal|lime)\b", re.I)
TEXT = {".css", ".scss", ".less", ".html", ".htm", ".svg", ".xml", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx",
        ".vue", ".py", ".rb", ".go", ".rs", ".java", ".kt", ".swift", ".json", ".jsonc", ".yml", ".yaml", ".toml",
        ".md", ".txt", ".sh", ".env"}
NOTICE_FROM = 2          # files with colours in them before the gate says something


def values_in(doc):
    """Every colour value a JSON document holds, wherever it sits, upper-cased."""
    out = set()
    if isinstance(doc, dict):
        for v in doc.values():
            out |= values_in(v)
    elif isinstance(doc, list):
        for v in doc:
            out |= values_in(v)
    elif isinstance(doc, str) and HEX.fullmatch(doc.strip()):
        out.add(doc.strip().upper())
    return out


# Where a colour is quoted, not painted: a page's <pre> and <code>, Markdown's
# fences and backticks. The scan's own output, shown on a page, names the greys
# it found; that is text a visitor reads, not a colour they receive.
QUOTED = re.compile(r"<(pre|code)\b[^>]*>.*?</\1\s*>|```.*?```|~~~.*?~~~|`[^`\n]*`", re.S | re.I)


def unquoted(text):
    """`text` with every quoted stretch blanked, line for line, so what is left
    is what a page paints and a line number still means the same line."""
    return QUOTED.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def literals(text):
    """(line, literal, kind) for every colour said in `text` - painted, not quoted in code."""
    for n, line in enumerate(unquoted(text).splitlines(), 1):
        for m in HEX.finditer(line):
            yield n, m.group(0), "hex"
        for m in FUNC.finditer(line):
            yield n, m.group(0) + "…)", "func"
        for m in NAMED.finditer(line):
            yield n, m.group(1), "named"


def text_files(root, read=None):
    """Every tracked file a person could type a colour into, as (path, rel)."""
    out = []
    for p in sorted(tracked_files(root)):
        rel = p.relative_to(root).as_posix()
        if p.suffix.lower() not in TEXT or not p.is_file():
            continue
        if read and not any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(rel, g.rstrip("/") + "/*") for g in read):
            continue
        out.append((p, rel))
    return out


def declared(cfg):
    """The palette section, or None."""
    return cfg.doc.get("palette")


def faults(cfg):
    """(faults, files that say a colour, files excused, how many values the source holds)."""
    doc = declared(cfg)
    src = cfg.root / doc["source"]
    if not src.is_file():
        return [f"palette.source {doc['source']!r} is not a file"], 0, 0, 0
    try:
        values = values_in(json.loads(src.read_text(encoding="utf-8")))
    except ValueError as e:
        return [f"palette.source {doc['source']!r} is not JSON: {e}"], 0, 0, 0
    if not values:
        return [f"palette.source {doc['source']!r} holds no #RRGGBB colour at all"], 0, 0, 0
    not_ours = doc.get("not_ours", {})
    found, read, excused = [], 0, 0
    src_rel = src.resolve().relative_to(cfg.root).as_posix()
    for p, rel in text_files(cfg.root, doc.get("read")):
        if rel == src_rel:
            continue
        if rel in not_ours:
            excused += 1
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        said = False
        for n, lit, kind in literals(text):
            said = True
            if kind == "hex" and lit.upper() in values:
                continue
            found.append(f"{rel}:{n}: {lit} - a colour that is not one of {doc['source']}'s")
        read += said
    return found, read, excused, len(values)


def notice(cfg, made):
    """One line for the gate when colours are said in several of `made` - the
    repo-relative files the build wrote - and no palette is declared; else None."""
    if declared(cfg) is not None:
        return None
    coloured = 0
    for rel in made:
        p = cfg.root / rel
        if p.suffix.lower() not in TEXT or not p.is_file():
            continue
        try:
            if any(True for _ in literals(p.read_text(encoding="utf-8", errors="replace"))):
                coloured += 1
        except OSError:
            continue
    if coloured < NOTICE_FROM:
        return None
    return (f"NOTICE colours are said in {coloured} files the build made and no palette is declared: "
            f"`wherefore check palette` would hold them to one source. Declare `palette` in "
            f"wherefore.json - its `source`, the JSON file the brand lives in - or decline it, "
            f"{{\"none\": why}}.")


def main(cfg, args):
    if args:
        print("::error::wherefore check palette takes nothing")
        return 2
    doc = declared(cfg)
    if doc is None:
        print("::error::no palette is declared. Say where the brand lives - `palette` in wherefore.json, "
              "with `source`, the JSON file whose colours are the brand's - or, for a corpus with no "
              "brand, decline it with why: {\"palette\": {\"none\": \"...\"}}")
        return 1
    if "none" in doc:
        print(f"ok   no palette, and why: {doc['none']}")
        return 0
    found, read, excused, n = faults(cfg)
    if found:
        print(f"::error::a colour is said that {doc['source']} does not hold - the brand, said twice:\n")
        for f in found:
            print(f"   {f}")
        return 1
    said = f"ok   every colour in {read} files is one of {doc['source']}'s {n}"
    if excused:
        said += f"; {excused} files excused, each with why"
    print(said)
    return 0
