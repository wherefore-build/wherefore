---
name: wherefore
description: Set up or work in a repository whose documents are compiled from one source of truth by Wherefore - a wherefore.json at the root, generators that write every asset, a coverage gate that proves every tracked file is generated, authored or captured. Use when starting Wherefore in a repository (read start.md), changing a fact, adding a generator, adding or fixing a check, or when the gate, a retired-facts sweep, the source-reach probe or a claim rule fails.
---

# Working in a corpus that compiles

**Starting from nothing?** If there is no `wherefore.json`, or it declares
nothing but the generator that writes this skill, read `start.md` beside this
file first: it takes a repository from its first interview with the owner to
one fact compiled and held.

A Wherefore repository has one source of truth and generates everything else
from it. Your job is never to make a document say the right thing. It is to
make the **source** say the right thing, and let the generators carry it.

## The five rules

1. **A fact exists in exactly one place.** If a number, a name or a phrase
   appears in two files, one of them is generated from the other or checked
   against it. If you find a second copy, that is the bug.
2. **The build is deterministic.** Nothing in the build path calls a model,
   reads the clock, or depends on the machine beyond what a declared
   comparator tolerates. You may help *write* generators and checks; you never
   become one.
3. **Fail loudly.** When something does not fit, stop and say what does not
   fit. Never improvise a value, widen a tolerance, add an exemption or skip a
   check to get green.
4. **A check is not trusted until it has been shown to fail.**
5. **Sources versus outputs.** Every tracked file is *generated* (written by a
   generator during the gate's run), *authored* (a source a person edits,
   matched by a rule in the inventory) or *captured* (hand-made, and stamped
   with what it was made from). Generated files are never edited by hand.

## Find your bearings

```
cat wherefore.json          # sources, generators in order, inventory, comparators, checks
wherefore list              # what each generator writes, right now
wherefore gate              # is every tracked file classified and current?
wherefore graph             # what builds what: which script makes each file, from what
wherefore check palette     # every colour anywhere is one the brand's source holds, or excused with why
```

`wherefore graph` is for seeing the chain before you change it: which sources a
script reads, which files it makes, and what else moves with a fact. It runs
every generator once, writes `wherefore-graph.html` (and JSON with `--json`),
and puts every file back exactly as it was - it changes nothing, so run it
whenever the shape of the corpus is the question. A command generator (`run`)
shows what it wrote but not what it read: its reads are not observed.

A corpus may publish its own map: a `run` generator that is
`wherefore graph --html site/map/index.html`, committed like any generated
file. The gate runs it; `wherefore graph` credits it with that file rather than
running it, so the map never maps itself without end. Give it
`--theme site/brand.css` (or any stylesheet that sets the page's custom
properties) and the map is drawn in the corpus's own colours, with no palette
of the engine's left in it.

A brand is a fact like a price. Declare `palette` in wherefore.json - `source`,
the JSON file the colours live in - and `wherefore check palette` fails a
colour said anywhere else that the source does not hold, unless the file is in
`not_ours` with why. A corpus with no brand declines it: `{"none": why}`. The
gate says when colours are said in several of the files the build made and
nothing is declared, reading nothing for it that it did not read to judge.

`wherefore.json` and any file a section includes are where every exemption
lives, and **every exemption carries a `why`**. The engine refuses an entry
without one. Read the reasons before changing anything near them.

If `wherefore.json` declares `entry`, the corpus configures the engine in
Python: each command runs the script named there, and **that script** is where
the generator list, the comparators and the exemptions live, with their
reasons. Edit them there. Do not copy them into `wherefore.json`, which refuses
them anyway, because that would be one fact in two places.

## Changing a fact

1. Edit the source named in `sources`, and only the source.
2. If the old value or wording should never be seen again, add a row to the
   retired register, with what it was, what superseded it and why. Do it in the
   same change: the harness must arrive before the change it catches.
3. Run `wherefore build`. It regenerates everything, twice, and keeps the
   result. A "not a fixed point" message on the first run after a change is
   normal when a generator reads something a later one writes. Run it again.
   If the corpus still does not settle, that is a real fault.
4. Read what moved. Every moved file should be explained by your change. A
   file that moved and should not have is a generator reading something it
   should not.
5. `wherefore check retired`, `check reach` and `check claims`.
6. **Commit the source and every document it moved in one commit.** A
   document and the fact it prints belong together.

If a captured file depends on the fact, the gate names it: "THESE NEED
RE-MAKING". You cannot make a photograph current. Say so, leave it failing,
and let a person re-make it and run `wherefore gate --restamp '<group>'`.
Never restamp a capture you did not re-make.

## Adding a generator

1. Write it as a pure function of the sources. It reads the source files and
   writes its outputs **unconditionally**, every run. A generator that skips
   the write when nothing changed looks exactly like one nobody called, and
   the gate will fail its files as unclassified. That is correct, and the fix
   goes in the generator.
2. A Python generator is the default, declared by `script`, and writes through
   Python's `open()`: the observer sees nothing else, so a shell redirect or a
   subprocess that is not Python, started from a `script`, writes files nobody
   covers. A generator that is another program - node, a shell script, a CAD
   export - is declared by `run`, its command as a list of words
   (`["node", "gen/site.mjs"]`), run as given with no shell between; what it
   writes is seen by comparing the tree before and after it, so it may write
   any way it likes and is held exactly as strictly. A generator that prints
   its product declares `stdout_to`.
3. Add it to `generators` in order: after everything it reads, before
   everything that reads it. Give it a `makes`. If it must skip the probe or
   the second pass, give a `why` that a skeptic would accept.
4. Run `wherefore gate`. Every file it writes is now *generated*. Every new
   file it does not account for is a decision: generated (a generator should
   write it), authored (add a narrow inventory rule, with its reason) or
   captured (a group, with what it was made from). A file a generator writes
   and a rule also claims is a contradiction, and one of the two is wrong.
5. Track the outputs. A generated file git does not track is held to
   nothing. Either commit it or say in `.gitignore` that it is a build output.

## Writing a check, then proving it fails

A check documents itself: what it asks, what it cannot see, and the bug that
caused it to be written. Then prove it with a proof script, beside it:

```python
from wherefore.prove import Edit, check, report

results = []
with Edit("site/index.html") as p:                       # break one thing
    p.write_text(p.read_text().replace("$89", "$79"))
    check(results, "the old price, back on the page", "-m", True,   # it must FAIL
          ["79 -> 89", "site/index.html   says"],                    # and say so
          "wherefore", "check", "retired")
check(results, "nothing broken", "-m", False, ["nothing anywhere"],
      "wherefore", "check", "retired")
raise SystemExit(report(results))
```

- `Edit` puts the file back byte for byte, even if the check throws, and
  refuses a block that changed nothing. That means your anchor moved, so fix
  the case.
- `check` requires the exit code **and** the words. A check that fails for the
  wrong reason has caught nothing.
- Include a case that must **not** fire. A check that cries wolf gets ignored.
- **Then break the check itself** and watch the proof report MISS. Only then
  is the proof worth anything.
- Proofs plant into the working tree. Run them one at a time per checkout:
  `wherefore prove`.

## When something fails

| It says | It means | Do |
|---|---|---|
| `X is unclassified` | nothing wrote X and nothing declares it | a generator stopped writing it (fix the generator), or X is a source or a capture (add the rule, with the reason) |
| `X regenerated DIFFERENT` | X is not what its generator makes today | the source moved and X was not rebuilt (`wherefore build`), or X was edited by hand (undo it and change the source) |
| `the corpus is not a fixed point` | a second pass changed files | build again; if it persists, find the generator reading a file that changes after it |
| `X is a generated file git doesn't track` | an output outside the corpus | track it, or `.gitignore` it as a build output |
| `NEED RE-MAKING` | a capture's source moved | a person re-makes it; you do not restamp |
| `NOTHING ... changed` (reach) | a fact reaches no output | a generator holds its own copy; make it read the source. Or the fact is dead; remove it. Exempt it only with a reason that survives review |
| `says ...` (retired) | a retired value or phrase is still claimed | fix the source or generator that writes it, never the output |
| a claim rule fails | copy says what nobody justified | change the copy at its source. Add to `may_say` only with a true, written reason |
| `MOVED` (upstream) | something this corpus copied from elsewhere has changed where it was taken from | take the copy again from the source as it is now - re-copy the file, re-count the numbers - and record the new version or commit and the day in the same change; then `wherefore gate`. Never move the recorded value alone |
| `no longer says` (upstream) | the source answered, but not in the shape `read` expects | look at the source. If it moved, take the copy again; if only its shape changed, change `read` - and say which in the commit |
| `did not answer` (upstream) | the source is down, or the address is wrong | check the address. Add `unreachable` only with the reason a source being down should not stop this corpus |

**Never** fix a failure by:

- editing a generated file;
- loosening a tolerance;
- exempting without a reason someone else would accept;
- deleting a test, or skipping or disabling one;
- restamping a capture nobody re-made;
- moving the version an upstream copy records without taking the copy again.

The cheap direction and the expensive one are not symmetric here, and the
check is usually right.

## Releases are a person's

If the repository versions what it ships (drafts, releases, a write-once
archive), you may work inside a draft freely. You never promote a draft, cut a
release or tag one unless the owner has authorized *that* release. If a change
seems to require one, stop and lay out the options.
