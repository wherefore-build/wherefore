"""A claim may say only what someone has justified in writing.

NEW IN WHEREFORE, not moved. The repository this was extracted from enforces
one claim - where its product is made - with a check of its own
(checks/brand_integrity.py), whose grammar is about that claim and stays there.
What generalises is the shape of the rule: a claim has a TRIGGER ("in the USA",
"in Portugal", "clinically proven"), the things it may be said of, each with
the reason it is true, and the things it must never be said of, each with the
reason it is not. A sentence that triggers the claim and names anything else
fails, and says which word and why.

HOW A SENTENCE IS READ. Text comes from the same readers the retired-facts
check uses, so a claim is found wherever a person reads one - a page's text
nodes, a drawing's labels, a workbook's cells, a document's lines - and never in
code. Each trigger is matched the way a retired phrase is: whitespace- and
case-insensitive, bounded at both ends. What it is said OF is the run of words
right before it, joined by commas, "and", "or" or "&": "Assembled, tested and
boxed in Portugal" says assembled, tested and boxed.

A SENTENCE THAT STATES THE RULE IS NOT A CLAIM. 'It is never "made in
Portugal"' is the instruction, and the run right after a negation - allowing a
copula or a verb of saying between them - is read as stated, not claimed. A
negation anywhere else does not excuse it: "Made in Portugal - not negotiable"
makes the claim.

WHAT IT CANNOT SEE. A claim split across two sentences. A claim made with no
word before its trigger at all ("Portugal's finest") - add that form as its own
trigger. And it is strict on purpose: a word it does not know before the
trigger fails, because an affirmative claim nobody has justified is the one
this exists to stop. The fix is a line in `may_say`, with its reason.
"""
import re

from .retired import phrase_hits, readable

CONNECT = {",", "and", "&", "or", "then"}
NEGATION = {"never", "not", "no", "cannot", "avoid", "without"}
CARRIES = {"is", "are", "was", "were", "be", "been", "being", "say", "says", "said",
           "call", "called", "write", "written", "label", "labelled", "labeled"}
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
TOKEN = re.compile(r"[A-Za-z][\w'-]*|[,&]")


def trigger_rx(trigger):
    words = [re.escape(w) for w in trigger.split()]
    return re.compile(r"(?<![\w-])" + r"[\s\-]+".join(words) + r"(?![\w-])", re.I)


def said_of(prefix):
    """(the words a claim is said of, whether a negation governs them)."""
    toks = [t.lower() for t in TOKEN.findall(prefix)]
    if not toks or toks[-1] in CONNECT:
        return [], False
    run, i = [toks[-1]], len(toks) - 2
    while i >= 0 and toks[i] in CONNECT:
        while i >= 0 and toks[i] in CONNECT:      # ", and" is one join
            i -= 1
        if i < 0:
            break
        run.append(toks[i])
        i -= 1
    before = toks[:i + 1]
    while before and before[-1] in CARRIES:
        before.pop()
    return run[::-1], bool(before) and before[-1] in NEGATION


def faults(claim, text):
    """[(the sentence, the word, why it fails)] for one chunk of readable text."""
    rx = trigger_rx(claim["trigger"])
    out = []
    for sentence in SENTENCE.split(text):
        for m in rx.finditer(sentence):
            words, negated = said_of(sentence[:m.start()])
            if negated:
                continue
            if not words:
                out.append((sentence.strip(), "", f"says {claim['trigger']!r} of nothing "
                            f"a rule can read - name what happens there"))
            for w in words:
                if w in claim.get("never", {}):
                    out.append((sentence.strip(), w, claim["never"][w]))
                elif w not in claim.get("may_say", {}):
                    out.append((sentence.strip(), w, f"nothing in may_say justifies "
                                f"{w!r} {claim['trigger']}"))
    return out


def main(cfg, argv=()):
    """`wherefore check claims`: every declared claim, against its surface."""
    import subprocess
    from .retired import files
    claims = cfg.doc.get("claims", [])
    if not claims:
        print("no claims are declared - nothing here may only be said with a reason")
        return 0
    tracked = {cfg.root / line for line in subprocess.run(
        ["git", "-C", str(cfg.root), "ls-files"], capture_output=True, text=True,
        check=True).stdout.splitlines() if line}
    total = 0
    for c in claims:
        for key in ("name", "trigger", "surface", "why"):
            if not str(c.get(key, "")).strip():
                print(f"::error::a claim in wherefore.json has no `{key}`")
                return 1
        for book in ("may_say", "never"):
            for w, why in c.get(book, {}).items():
                if not str(why).strip():
                    print(f"::error::{c['name']}: {book} {w!r} carries no reason. Saying a "
                          f"claim is true, or that it is not, is a statement somebody has "
                          f"to be able to stand behind")
                    return 1
        surface = cfg.doc.get("surfaces", {}).get(c["surface"])
        if surface is None:
            print(f"::error::{c['name']} names the surface {c['surface']!r}, which "
                  f"wherefore.json `surfaces` does not declare")
            return 1
        found = []
        for f in files(cfg.root, surface.get("include", []), surface.get("skip", []), tracked):
            rel = str(f.relative_to(cfg.root))
            if any(a in rel for a in surface.get("archive", [])):
                continue
            for chunk in readable(f):
                if not phrase_hits(c["trigger"], [chunk]):
                    continue
                found += [(rel, *x) for x in faults(c, chunk)]
        print(f"  {'ok  ' if not found else 'FAIL'} {c['name']}: {c['trigger']!r} may be "
              f"said of {', '.join(c.get('may_say', {})) or 'nothing'}")
        for rel, sentence, word, why in found[:12]:
            print(f"          {rel} says {sentence[:90]!r}")
            print(f"              {word + ': ' if word else ''}{why}")
        total += len(found)
    if total:
        print(f"\n::error::{total} claim(s) say something nobody has justified in writing")
        return 1
    print("\nevery claim says only what its rule allows")
    return 0
