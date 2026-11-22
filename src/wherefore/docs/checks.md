# Checks and proofs

A corpus is held by checks, and a check is not trusted until it has been
shown to fail. This page says what each check holds, how it fails, and how to
prove one.

## What each check holds

- **The gate** (`wherefore gate`): every tracked file is generated during the
  gate's own run, authored under a rule with a reason, or captured and
  stamped with what it was made from; every generated file is what is
  committed; the corpus settles on a second run. It fails naming the file
  nobody wrote and nobody claimed, or the generated file that differs. With
  `--since REF` it runs only the generators a change since REF can reach, by
  the map the full gate keeps, so it holds less than the full gate: a read
  the map cannot see is skipped. The full gate on main and on a schedule is
  what holds the rest.
  A source that declares a `schema` has every fact typed by it, named by
  its identity when one is wrong; a source backed by a store has its file
  materialized at the pinned version by a generator, so a file edited by
  hand differs, and a store that moved past the pin fails it.
- **Reach** (`wherefore check reach`): every fact, moved one at a time,
  changes something a visitor receives. It fails naming the fact that moved
  nothing - dead, or copied by hand into a generator - and the probe that
  named a file which did not move.
- **Retired** (`wherefore check retired`): nothing a person reads still says
  a retired value or phrase. It fails naming the file and the line.
- **Claims** (`wherefore check claims`): no page claims more than a claim's
  rule allows. It fails naming the page and the claim.
- **Upstream** (`wherefore check upstream`): every copy taken from elsewhere
  still matches where it was taken from. It fails MOVED, NO LONGER SAYS or
  UNREACHABLE, and says what to take again.
- **Palette** (`wherefore check palette`): every colour said anywhere is one
  the brand's source holds, or excused with why. It fails by file and line.
- **Published** (`wherefore check published`): every page the company
  publishes but cannot build still states the source's facts, read live. It
  fails SAYS OTHERWISE, quoting the page, NOT SAID, or UNREACHABLE.
- **Drift** (`wherefore check drift`): no more values than the corpus
  allows are said by hand in two or more files with no source behind them.
  It fails naming each value and its files, and when fewer drift than
  allowed it asks for the allowance to come down.
- **Launch** (`wherefore check launch`): every thing with a stage has what
  its stage needs, and nothing says what may not be said before it. It
  fails naming the thing, the stage and what is missing, and for every
  other thing says what the next stage still waits on.
- **Decisions** (`wherefore check decisions`): every fact a change adds,
  removes or moves carries an approving review, on the head commit, from
  someone its rules allow - a person named, or any reviewer who is not the
  author. It fails naming each fact and what is missing from whom, and
  counts nothing typed: a commit message, a pull request's body.
- **Your own checks**: a script in the corpus that reads the tree and exits
  1 with a reason, run by CI beside the engine's. The company's site has a
  dozen: every control pressed cold on a phone, every page fitting a phone's
  width, every text colour readable on its ground.

The gate, reach, retired, claims, palette, drift and launch read nothing outside the
repository, so the same tree always gives the same answer, and they run on
every push and in the pre-push hook. Upstream and published go to the
network, so they run before a deploy, and on a schedule if the client wants
one, never in the gate.

Decisions runs on a pull request and nowhere else, because what it reads is
there: the approving reviews, whose author is GitHub's account and not a
name anybody typed. A review changes its verdict without changing the tree,
so its workflow runs on `pull_request_review` as well as `pull_request` (the
commands page shows one). Off a pull request it says what the change would
need and exits 2 rather than pass. It never runs in the gate or the
pre-push hook: a push has no approvals yet. And it can only be satisfied
when the author and the decider are different accounts - an agent that
opens pull requests as its owner makes its owner the author, who cannot then
approve; the agent needs an identity of its own.

## Writing a check

A check is a script: read what it judges, print one line per thing it finds
with the file and the reason, exit 1 if it found anything and 0 if not, with
one line saying what held. Name it for what it holds, not for what it does -
`controls_press.py`, not `check_buttons.py` - and put the reason the check
exists at the top of the file, with the day it was found wanting.

## Proving a check

A proof plants the fault the check exists to catch, runs the check, requires
it to fail naming the fault, and puts the tree back exactly. The engine's
`prove` module gives the pieces:

```python
import sys
from wherefore.prove import Edit, check, report

r = []
r += check("a page that says the old price",
           Edit("site/pricing.html", "89", "79"),
           run=["python3", "-m", "wherefore", "check", "retired"],
           wants=["site/pricing.html", "79"])
r += check("the tree as it is - must not fire",
           run=["python3", "-m", "wherefore", "check", "retired"], passes=True)
raise SystemExit(report(r))
```

`Edit` is one planted fault: a file, what to find in it, what to put there.
`check` runs the command with the fault in place, requires every string in
`wants` in the output and exit 1, and restores the file; with `passes=True`
it requires exit 0 instead, which is how a proof shows the check does not
fire on the tree as it is. `report` prints PASS or MISS per case and returns
the exit status. `wherefore prove` runs every proof the corpus declares, one
at a time, in place - two at once in one checkout would plant faults over
each other.

In a corpus whose facts are backed by a store, the source's file is
generated: a fault planted in it is overwritten by the first build. Plant in
the store - `wherefore facts set`, inside an `Edit` of the store's file so
it is put back - as the engine's `proofs/facts_proof.py` does.

A proof that passes before the check is written is a proof of nothing: write
the proof, watch it MISS, write the check, watch it PASS. Then break the
check and watch the proof MISS again.

## When a check and a person disagree

The check is usually right, and it is the one to go and fix when it is not.
Never widen a tolerance, add an exemption or skip a check to get green; say
what does not fit and why. Every exemption in `wherefore.json` carries a
`why`, and the engine refuses one without it.
