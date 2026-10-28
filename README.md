# whereforeart

**Wherefore** is the machinery of a company that compiles. There is one source
of truth, every asset is generated from it, and every change is tested, so
nothing ships that contradicts a decision.

It was extracted from `zakholdsworth/chaotic-pendulums-co`, whose every drawing,
solid, page and parts list is generated from one spec file. That repository is
its first client.

## The principles it enforces

1. **A fact exists in exactly one place.** Everything else is generated from it or checked against it.
2. **The build is deterministic.** Nothing in the build path calls a model.
3. **Fail loudly.** A change the build cannot handle stops it; nothing improvises.
4. **A check is not trusted until it has been shown to fail.**
5. **Sources versus outputs.** Every tracked file is *generated*, *authored* or
   *captured*. Generated files are never hand-edited, and a capture is stamped
   with what it was made from.

## Use

```
pip install -e .                 # Python 3.10+, standard library only
pip install -e '.[pictures,xlsx]' # for picture and workbook comparison

wherefore init                   # a wherefore.json that declares nothing yet
wherefore gate                   # every tracked file classified, every generated one current
wherefore build                  # regenerate everything, twice, and keep the result
wherefore gate --restamp GROUP   # after re-making a capture
wherefore prove                  # run the client's proofs, one at a time, in place
wherefore list                   # run every generator once and say what each wrote
wherefore check retired         # nothing a person reads still claims a retired value or phrase
wherefore check reach           # every fact, moved one at a time, reaches what it should
wherefore check claims          # every claim says only what its rule allows
```

A client describes its corpus in `wherefore.json`: its sources, its generators
in order, its inventory of authored and captured files, and every exception to
byte-identity. Every exemption carries a `why`, and the engine refuses an entry
that has none. `tests/fixture/` is a complete, fictional example.

## This repository

| path | what |
|---|---|
| `src/wherefore/` | the engine |
| `tests/fixture/` | Fernhollow Kettles, a fictional company the engine proves itself against |
| `proofs/` | the engine's proofs: each breaks the fixture one way and requires the right failure, in the right words |
| `tests/` | unit tests, and `test_phase5.py`: the fixture compiled from its sources alone |
| `tools/moved/` | the exact edits that turned each pendulum original into an engine module; `verify.py` re-runs them |
| `ENGINE_INVENTORY.md` | what was moved from the pendulum repo, and how |
| `ARCHITECTURE_REVIEW.md` | the review the extraction follows, and the decisions taken |

```
python3 -m unittest discover tests
for p in proofs/*_proof.py; do python3 "$p" || exit 1; done
```
