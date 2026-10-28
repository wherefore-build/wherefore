import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import lib
SRC = (lib.SRC / "checks/no_stale_numbers.py").read_text(encoding="utf-8")
DST = lib.DST / "retired.py"
def between(a, b):
    i = SRC.index(a); j = SRC.index(b, i); return SRC[i:j]
readers = between("SVG_TEXT = re.compile", "\n\n# A retired value that is NOT the retired thing")
phrase = between("def phrase_hits(phrase, chunks):", "\n\ndef old_part_numbers(")
hits_doc = between('    """A retired value, claimed.', '    v = f"{value:g}"')
docstring = between('"""Does anything, anywhere, still claim a number the product has retired?', '\nimport copy')

head = docstring.replace(
 '"""Does anything, anywhere, still claim a number the product has retired?\n',
 '"""Does anything, anywhere, still claim a number the product has retired?\n'
 '\n'
 'IN WHEREFORE. Moved from chaotic-pendulums-co\'s checks/no_stale_numbers.py.\n'
 'The register - what the product used to be - stays in the client\'s source,\n'
 'where wherefore.json `retired.register` points. Where a person reads is a\n'
 'surface the client declares; so is what counts as a number being ASSERTED\n'
 '(`assertion_patterns`), because that is a corpus\'s grammar - "210 mm", "⌀4.5",\n'
 '"$79" - and not a law; and so are the lines that carry a retired value as\n'
 'another quantity (`exemptions`, each keyed by the file, the value and text on\n'
 'that line, each with its reason). The readers, the phrase matcher, the\n'
 'register\'s rules and every message are as they were. The arms that read the\n'
 'pendulum\'s own spec schema and derivation library - a parameter\'s provenance,\n'
 'derived numbers quoted in prose, retired part numbers - stay with the\n'
 'pendulum, which runs this sweep and then its own.\n', 1)
head = head.replace("\nUsage:  python3 checks/no_stale_numbers.py\n", "\nUsage:  wherefore check retired\n")

glue = r'''


def hits(value, chunks, patterns):
''' + hits_doc + r'''    v = re.escape(f"{value:g}")
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
'''
out = (head + "\nimport json\nimport io\nimport re\nimport subprocess\nimport sys\nimport tokenize\n\n"
       + readers + "\n\n\n" + phrase + glue)
DST.write_text(out, encoding="utf-8")
print(f"retired.py: built from checks/no_stale_numbers.py")
