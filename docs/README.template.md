# whereforeart

**Wherefore** is the machinery of a company that compiles. There is one source
of truth, every asset is generated from it, and every change is tested, so
nothing ships that contradicts a decision.

It was extracted from `zakholdsworth/chaotic-pendulums-co`, whose every drawing,
solid, page and parts list is generated from one spec file. That repository is
its first client.

## The principles it enforces

{{principles}}

## Use

```
pip install -e .                 # Python 3.10+, standard library only
pip install -e '.[pictures,xlsx]' # for picture and workbook comparison

{{commands}}
```

A client describes its corpus in `wherefore.json`: its sources, its generators
in order, its inventory of authored and captured files, and every exception to
byte-identity. Every exemption carries a `why`, and the engine refuses an entry
that has none. `tests/fixture/` is a complete, fictional example.

A client that configures the engine in Python instead, in the scripts its
proofs plant faults into, names those scripts in `entry`, and each command runs
the client's own script exactly as its CI does. The engine refuses a command
that is handed over and configured in `wherefore.json` as well, because that is
one fact in two places. `chaotic-pendulums-co` is that kind of client; see
`integration/chaotic-pendulums-co/`.

## This repository

| path | what |
|---|---|
| `src/wherefore/` | the engine |
| `tests/fixture/` | Fernhollow Kettles, a fictional company the engine proves itself against |
| `proofs/` | the engine's proofs: each breaks the fixture one way and requires the right failure, in the right words |
| `tests/` | unit tests, and `test_phase5.py`: the fixture compiled from its sources alone |
| `tools/moved/` | the exact edits that turned each pendulum original into an engine module; `verify.py` re-runs them |
| `src/wherefore/skills/wherefore/` | the skill, shipped in the package: how a coding agent works in a corpus (`SKILL.md`) and starts one (`start.md`). A corpus's own copy is generated from the release it pins, by the `wherefore.skill` generator `wherefore init` declares |
| `integration/chaotic-pendulums-co/` | the pendulum as the first client: a patch series, what it waits on, and what was checked |
| `ENGINE_INVENTORY.md` | what was moved from the pendulum repo, and how |
| `ARCHITECTURE_REVIEW.md` | the review the extraction follows, and the decisions taken |
| `VERSIONING_SHAPE.md` | the next extraction's questions, with recommendations, waiting on the owner |
| `CHANGELOG.md` | every release, newest first; a client upgrades only by moving its pin |
| `corpus/`, `wherefore.json` | this repository as a client of its own engine: the README's generator, the corpus's checks and their proofs |
| `docs/README.template.md` | the README's text; the README is generated from it, `src/wherefore/commands.json` and `src/wherefore/principles.json` |
| `requirements-engine.txt` | the previous release, which judges this repository's own corpus |
| `DIRECTIONS.md` | where it could go: obligations, sign-off, agents in the loop, onboarding; none of it built |

```
python3 -m unittest discover tests
for p in proofs/*_proof.py; do python3 "$p" || exit 1; done
```
