"""Does anything, anywhere, still claim a number the product has retired?

IN WHEREFORE. Moved from chaotic-pendulums-co's checks/no_stale_numbers.py.
The register - what the product used to be - stays in the client's source,
where wherefore.json `retired.register` points. Where a person reads is a
surface the client declares; so is what counts as a number being ASSERTED
(`assertion_patterns`), because that is a corpus's grammar - "210 mm", "⌀4.5",
"$79" - and not a law; and so are the lines that carry a retired value as
another quantity (`exemptions`, each keyed by the file, the value and text on
that line, each with its reason). The readers, the phrase matcher, the
register's rules and every message are as they were. The arms that read the
pendulum's own spec schema and derivation library - a parameter's provenance,
derived numbers quoted in prose, retired part numbers - stay with the
pendulum, which runs this sweep and then its own.

Every other check in this repo compares one surface with itself. brand-drift
proves a generator reproduces its own output. engineering-drift proves the same
for the pack. drawn_dimensions proves a drawing's label matches its own line.
All of them pass on a file that is internally perfect and three revisions out
of date, which is how a fork became 216 while

    the sketches went on printing "210 mm"
    the hero's inlined DRAFT SHEETS went on showing a 210 fork
    a 234 KB copy of the hero at the repo root went on being a 210 fork

This asks the other question. spec.retired records what the product USED to be;
this fails if any of it still appears where a PERSON would read it - a
drawing's own text, a DXF note, a document, a page. Not in code: a literal in a
generator is a different problem, and binding the generators is how that one
gets fixed.

NUMBERS AND SENTENCES. spec.retired.values catches "210 mm". It could not catch
the DXF note that still read "drilled through" after the tap became blind, or
the BOM that went on ordering BEAD BLAST after the part drawings moved to
"Brushed both faces, grain lengthwise ... Clean and deox only - NO MATTE ETCH" -
two supplier documents, shipped in the same folder, instructing opposite
operations. A dimension goes stale as a number and a process goes stale as a
sentence, and the same person reads both, so spec.retired.phrases is scanned
the same way and reported beside the values.

Change a dimension, add a row to spec.retired, and this tells you every file
that has not caught up. That is the harness - "did it propagate" becomes a
question the repo answers, not one you have to ask.

AND A THIRD KIND OF STALE, which is not about the past at all. A hand-written
sentence in the spec can quote a number that is DERIVED - the clamp column, a
seat's web, the fork gap - and derivations move without prose. Four of those
were found and fixed one at a time, so the arm at the bottom of this file asks
the question generally: does tools/stack.py work this number out, does it move
when the spec moves, and is it not a value the spec holds? See derived_prose()
for what it will and will not swear to.

Usage:  wherefore check retired
"""
import json
import io
import re
import subprocess
import sys
import tokenize

SVG_TEXT = re.compile(r">([^<>]{0,400}?)</text>")
DXF_TEXT = re.compile(r"\n1\n([^\n]*)")
# A script's comments: the block kind, and the line kind where it starts a
# comment rather than sitting inside a URL or a string. The code itself is the
# other problem - see the note on SCAN.
JS_COMMENT = re.compile(r"/\*.*?\*/|(?<![:\"'\\])//[^\n]*", re.S)


def py_prose(src):
    """A Python file's comments and docstrings, and nothing else.

    Read as TOKENS rather than swept with a pattern, for the reason
    brand/code/uncomment.py gives about JavaScript: a `#` inside a string is not
    a comment, and a hand-rolled stripper that thinks it is would read this
    repository's own quoted examples - `"210 mm"`, "D6 H7" - as claims. A
    docstring is a string token standing alone as a statement, which is exactly
    what the tokenizer already knows and a pattern cannot.
    """
    out, prev = [], tokenize.INDENT
    for t in tokenize.generate_tokens(io.StringIO(src).readline):
        if t.type == tokenize.COMMENT:
            out += t.string.lstrip("#").splitlines()
        elif t.type == tokenize.STRING and prev in (
                tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE, tokenize.NL):
            out += t.string.splitlines()
        if t.type not in (tokenize.NL, tokenize.COMMENT):
            prev = t.type
    return out

# A page is not only its inlined drawings. .html used to be read with SVG_TEXT
# alone, which meant this check opened web/prototype/template.html - the live
# marketing site - and took ZERO chunks out of it, and took only the 65 drawing
# labels out of the supplier's hand-over page. Both were selling and quoting
# "6082-T6" in prose at the time, in a paragraph and a stock line, and neither
# was ever a candidate to be named. A check that reads a file and finds nothing
# in it is worse than one that does not open it: it counts towards the total it
# prints. Comments, <script> and <style> stay out - a literal in code is the
# other problem, and binding the generators is how that one gets fixed.
HTML_DEAD = re.compile(r"<!--.*?-->|<(script|style)\b[^>]*>.*?</\1\s*>",
                       re.S | re.I)
HTML_TAG = re.compile(r"<[^>]*>", re.S)



LFS_HINT = ("this is a git-lfs POINTER, not the file. The job that read it "
            "checked out without lfs:true - add it, rather than teaching the "
            "check to skip what it cannot read.")


def _not_a_pointer(path):
    head = path.open("rb").read(64)
    if head.startswith(b"version https://git-lfs"):
        raise SystemExit(f"{path.name}: {LFS_HINT}")


def readable(path):
    """Only what a person actually reads out of this file."""
    _not_a_pointer(path)
    if path.suffix == ".xlsx":
        # The BOM went on describing a "38 x 6 x 114" plate for three revisions
        # because this check could not open a workbook. A cell is text a person
        # reads, and a supplier quotes from it.
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True)
        return [str(c.value) for ws in wb for row in ws.iter_rows()
                for c in row if isinstance(c.value, str)]
    src = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".dxf":
        return DXF_TEXT.findall(src)
    if path.suffix == ".svg":
        return SVG_TEXT.findall(src)
    if path.suffix == ".py":
        return py_prose(src)
    if path.suffix == ".js":
        return [line for c in JS_COMMENT.findall(src)
                for line in c.strip("/*").splitlines()]
    if path.suffix == ".html":
        # Text nodes, one chunk each, entities resolved - "368 &times; 38 mm"
        # is read as a person reads it, so an `a x b x c` envelope written in
        # entities is still an envelope. Inlined <text> falls out of this for
        # free, so nothing that used to be seen stops being seen.
        import html as _html
        return [_html.unescape(c)
                for c in HTML_TAG.split(HTML_DEAD.sub(" ", src)) if c.strip()]
    return src.splitlines()



def phrase_hits(phrase, chunks):
    """A retired phrase, still asserted.

    Whitespace-insensitive and case-insensitive, so "Bead blast", "bead-blast"
    and "bead  blast" are all the same claim, and bounded at both ends so a
    phrase inside a longer word is not a hit.

    A SIZE IS A PHRASE TOO, and two things follow from letting one in. The bar's
    SECTION went stale - "38 x 6", the profiled width by the thickness - and it
    could not be registered as a value: 6 is the shoulder screw's shoulder, the
    626's bore and its width, the flanged spacer's bore and the M5's thread
    length, and a sweep for a bare 6 fires on thirty-nine live lines of this
    corpus. It is only stale as the PAIR, which is a phrase, so it is registered
    as one - and then the matcher has to read a size the way the documents write
    one:

      the sign is `x` OR `×`, because both are typed here and they are the same
      claim - brand/SPEC.md's table writes one and sideview.py's docstring the
      other, of the same bar;

      and a number does not end where a decimal carries on. "38 x 6.35" is the
      bar this product HAS, and the boundary that asks only for a non-word
      character let it through as "38 x 6" - the successor reported as the thing
      it superseded, which is the one false alarm that would make this useless.

    WHAT IT CANNOT SEE: a negation. The drawings say "DO NOT TAP THROUGH", and
    a scan for "tap through" would call that stale when it is the opposite - it
    is the instruction that the phrase is retired. That is why "tap through" is
    NOT in spec.retired.phrases: a phrase whose retirement is enforced by a
    sentence containing it cannot be swept this way, and pretending otherwise
    would add a false alarm to a check whose whole value is that its alarms
    are real.
    """
    words = [r"[x\u00d7]" if w in ("x", "×") else re.escape(w)
             for w in phrase.split()]
    rx = re.compile(r"(?<![\w-])" + r"[\s\-]+".join(words)
                    + r"(?![\w-])(?!\.\d)", re.I)
    return [c.strip() for c in chunks if rx.search(c)]



def hits(value, chunks, patterns):
    """A retired value, claimed. Bare in a drawing's text, or with a unit in prose.

    The context matters: 210 is also a steel yield in MPa and 4.5 is a drill
    size in a note about something else. What is being looked for is the number
    ASSERTED - standing alone in a label, or carrying mm, or inside an
    `a x b x c` envelope.
    """
    v = re.escape(f"{value:g}")
    pats = [re.compile(p.replace("{v}", v)) for p in patterns]
    return [c.strip() for c in chunks
            if c.strip() and any(p.search(c) for p in pats)]


def files(root, include, skip, tracked):
    """Every tracked file a surface names: (dir, glob) pairs, recursive below
    each dir, and only the top level for "."."""
    out = []
    for sub, pat in include:
        base = root / sub
        if not base.exists():
            continue
        it = base.rglob(pat) if sub != "." else base.glob(pat)
        for f in it:
            rel = str(f.relative_to(root))
            if any(s in rel for s in skip):
                continue
            if f not in tracked:
                continue
            out.append(f)
    return sorted(set(out))


def excuse(exemptions, kind):
    """{(file, value or phrase, text on the line): why}, from the declared list."""
    out = {}
    for e in exemptions:
        if kind in e:
            key = float(e[kind]) if kind == "value" else e[kind]
            out[(e["file"], key, e["says"])] = e["why"]
    return out


def sweep(root, register, include, skip, archive, patterns, numbers_excused,
          phrases_excused, read=None, register_name="the register", item="value"):
    """Every retired value and phrase, against every file a person reads.

    Returns the number of places still claiming one. Prints as it goes, in the
    words the repository this came from has always printed, so a client that
    adds arms of its own can run this first and add its count to theirs.
    """
    read = read or readable
    retired = register.get("values", [])
    if not retired:
        # Armed, and nothing superseded yet. That is the right order: the harness
        # lands before the change it exists to catch.
        print(f"{register_name} is empty - no {item} has been superseded yet\n")
    if retired and not patterns:
        sys.exit("::error::the register retires values, and wherefore.json `retired` "
                 "declares no assertion_patterns - nothing says what a value being "
                 "CLAIMED looks like in this corpus, and a sweep for a bare number "
                 "fires on every other quantity that shares its digits")

    # ONLY WHAT GIT TRACKS. A document a person reads is one this repository
    # keeps; a build artefact is a copy of one, and fixing the copy is not a
    # thing anybody can do.
    tracked = {
        (root / line) for line in subprocess.run(
            ["git", "-C", str(root), "ls-files"],
            capture_output=True, text=True, check=True,
        ).stdout.splitlines() if line
    }
    found_files = files(root, include, skip, tracked)

    def is_archive(rel):
        return any(a in rel for a in archive)

    def not_that_number(rel, value, line):
        return next((why for (f, v, says), why in numbers_excused.items()
                     if f == rel and v == value and says in line), None)

    def not_that_phrase(rel, phrase, line):
        return next((why for (f, ph, says), why in phrases_excused.items()
                     if f == rel and ph == phrase and says in line), None)

    # A REGISTER APPLIED TWICE IS NOT A REGISTER. Every row here is one
    # supersession, so a value or a phrase may appear at most once: two rows for
    # the same number are either the same fact written twice - in which case the
    # sweep reports every hit twice and a reader counts the corpus wrong - or
    # two DIFFERENT successors for one retired value, which is a register that
    # cannot say what the product carries now.
    for what, rows, key in (("value", retired, "value"),
                            ("phrase", register.get("phrases", []), "phrase")):
        seen = {}
        for row in rows:
            seen.setdefault(row[key], []).append(row)
        twice = {k: v for k, v in seen.items() if len(v) > 1}
        if twice:
            for k, v in twice.items():
                nexts = sorted({str(x.get("superseded_by")) for x in v})
                print(f"::error::{register_name} lists the {what} {k!r} {len(v)} times, "
                      f"superseded by {' and '.join(nexts)}")
            sys.exit("a retired register with a repeated row has been applied twice; "
                     "each supersession is one row")

    # A VALUE THAT CAME BACK IS NOT STALE. `resumed_at_v` is the release from
    # which the product carries the old value AGAIN. The entry stays - the files
    # between the two releases still carry the successor - and the value itself
    # stops being swept from the release it resumed at.
    resumed = [r for r in retired if r.get("resumed_at_v")]
    for r in resumed:
        print(f"  --   {r['value']:>6g} came back at V{r['resumed_at_v']}: "
              f"{r.get('resumed', '').split('.')[0]}")
    if resumed:
        print()
    retired = [r for r in retired if not r.get("resumed_at_v")]

    print(f"{len(retired)} retired values, against {len(found_files)} files a person reads\n")
    fails = 0
    for r in retired:
        found, excused = [], []
        for f in found_files:
            rel = str(f.relative_to(root))
            if is_archive(rel):
                continue
            for text in hits(r["value"], read(f), patterns):
                why = not_that_number(rel, float(r["value"]), text)
                (excused if why else found).append((f.relative_to(root), text))
        for rel_, _t in excused[:1]:
            print(f"  --   {r['value']:>6g} in {rel_} is not that number")
        mark = "ok  " if not found else "FAIL"
        print(f"  {mark} {r['value']:>6g} -> {r['superseded_by']:<6g} {r['was']}")
        for rel, text in found[:8]:
            print(f"          {rel}   says {text!r}")
            fails += 1
        if len(found) > 8:
            print(f"          ... and {len(found)-8} more")
            fails += len(found) - 8

    phrases = register.get("phrases", [])
    for ph in phrases:
        if ph.get("resumed_at_v"):
            print(f"  --   {ph['phrase']!r} came back at V{ph['resumed_at_v']}: "
                  f"{ph.get('resumed', '').split('.')[0]}")
    phrases = [ph for ph in phrases if not ph.get("resumed_at_v")]
    print(f"\n{len(phrases)} retired phrases, against the same files"
          f" (the design history excepted)\n")
    for ph in phrases:
        found, excused = [], []
        for f in found_files:
            rel = str(f.relative_to(root))
            if is_archive(rel):
                continue
            for text in phrase_hits(ph["phrase"], read(f)):
                why = not_that_phrase(rel, ph["phrase"], text)
                (excused if why else found).append((f.relative_to(root), text))
        for rel_, _t in excused[:1]:
            print(f"  --   {ph['phrase']!r} in {rel_} is a record, not a claim")
        mark = "ok  " if not found else "FAIL"
        print(f"  {mark} {ph['phrase']!r} -> {ph['superseded_by']!r}")
        for rel, text in found[:8]:
            print(f"          {rel}   says {text[:90]!r}")
            fails += 1
        if len(found) > 8:
            print(f"          ... and {len(found)-8} more")
            fails += len(found) - 8
    return fails


def main(cfg, argv=()):
    """`wherefore check retired`, from wherefore.json `retired` and its surface."""
    from . import sources as S
    conf = cfg.doc.get("retired")
    if not conf:
        print("::error::wherefore.json declares no `retired` section")
        return 1
    reg = conf.get("register", {})
    name, src = cfg.source(reg.get("source"))
    doc = json.loads((cfg.root / src["path"]).read_text(encoding="utf-8"))
    register = S.value(doc, reg["at"]) if reg.get("at") else doc
    surface = cfg.doc.get("surfaces", {}).get(conf.get("surface"))
    if surface is None:
        print(f"::error::retired names the surface {conf.get('surface')!r}, which "
              f"wherefore.json `surfaces` does not declare")
        return 1
    for e in conf.get("exemptions", []):
        if not str(e.get("why", "")).strip():
            print(f"::error::the exemption for {e.get('file')!r} carries no reason. An "
                  f"exemption is a justification, not a silence")
            return 1
    fails = sweep(cfg.root, register, surface.get("include", []), surface.get("skip", []),
                  surface.get("archive", []), conf.get("assertion_patterns", []),
                  excuse(conf.get("exemptions", []), "value"),
                  excuse(conf.get("exemptions", []), "phrase"))
    if fails:
        print(f"\n::error::{fails} places still claim a value or a phrase this "
              f"product does not have")
        print("\nEvery one of these files is internally consistent and regenerates")
        print("itself perfectly. That is exactly why nothing else catches them.")
        return 1
    print("\nnothing anywhere still claims a retired value or a retired phrase")
    return 0
