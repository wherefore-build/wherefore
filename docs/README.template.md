# Wherefore

**Your company, compiled.**

Code has one source of truth: change it once, and everything built from it
follows. Everything else a company makes - the website, the docs, the pricing
page, the app's own words - is a copy of a copy, kept by hand, and it drifts.

Wherefore gives everything else what code has. Say each fact once. Generate
every asset from it. Anything left stale stops the change before it ships. AI
writes the rules; the build never improvises.

## A hardware company, compiled from one spec file

Wherefore was built alongside Chaotic Pendulums, a small hardware company
started to test the idea on something with more surface area than software. If
one source can hold machined parts, physics, suppliers and a storefront, it can
hold your app, website and docs. [How it is built](https://wherefore.build/#case).

## What it does

{{features}}

## The principles it enforces

{{principles}}

## Install

```
pip install wherefore-build       # Python 3.10+, standard library only
uv tool install wherefore-build   # or, as a command of its own
pipx install wherefore-build      # the same, with pipx
pip install 'wherefore-build[pictures,xlsx]'  # for picture and workbook comparison
```

It needs Python 3.10 or later and nothing else. Your project can be in any
language: Wherefore reads and checks files, whatever made them. With no Python
on the machine, `uv tool install` fetches one. A generator is a Python script
by default, or any command - a Node build, a shell script, a CAD export -
declared with `run` and held exactly as strictly.

The distribution is `wherefore-build`, because `wherefore` on PyPI is another
project's. What you import and what you type are `wherefore`.

## Use

```
pip install -e .                 # from a checkout of this repository
pip install -e '.[pictures,xlsx]' # with picture and workbook comparison

{{commands}}
```

**Start with a scan.** `wherefore scan` needs no setup and no `wherefore.json`:
point it at a built site, a docs folder or a live address, and it reports every
value the company states more than one way - "start your {} day free trial", 14
in three places and 30 in one. Each is a fact to say once, in a source, and
build every copy from; the rest of Wherefore is how.

A client describes its corpus in `wherefore.json`: its sources, its generators
in order, its inventory of authored and captured files, and every exception to
byte-identity. Every exemption carries a `why`, and the engine refuses an entry
that has none. `tests/fixture/` is a complete, fictional example.

A client that configures the engine in Python instead, in the scripts its
proofs plant faults into, names those scripts in `entry`, and each command runs
the client's own script exactly as its CI does. The engine refuses a command
that is handed over and configured in `wherefore.json` as well, because that is
one fact in two places. Chaotic Pendulums is that kind of client.

## This repository

| path | what |
|---|---|
| `src/wherefore/` | the engine |
| `tests/fixture/` | Fernhollow Kettles, a fictional company the engine proves itself against |
| `proofs/` | the engine's proofs: each breaks the fixture one way and requires the right failure, in the right words |
| `tests/` | unit tests, and `test_phase5.py`: the fixture compiled from its sources alone |
| `tools/moved/` | the exact edits that turned each pendulum original into an engine module; `verify.py` re-runs them |
| `src/wherefore/skills/wherefore/` | the skill, shipped in the package: how a coding agent works in a corpus (`SKILL.md`) and starts one (`start.md`). A corpus's own copies are generated from the release it pins, by the `wherefore.skill` generator `wherefore init` declares: `.claude/skills/wherefore/` for Claude Code and `.agents/skills/wherefore/` for Codex, the same files in the open Agent Skills format |
| `CHANGELOG.md` | every release, newest first; a client upgrades only by moving its pin |
| `src/wherefore/releases.json` | every release again, as data - version, date, a title, a sentence and a picture of it working - for the company's changelog page; `tests/test_releases.py` holds it to `CHANGELOG.md` and runs the newest picture again |
| `corpus/`, `wherefore.json` | this repository as a client of its own engine: the README's generator, the corpus's checks and their proofs |
| `docs/README.template.md` | the README's text; the README is generated from it, `src/wherefore/commands.json` and `src/wherefore/principles.json` |
| `requirements-engine.txt` | the previous release, which judges this repository's own corpus |
| `LICENSE` | Apache-2.0 |
| `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` | how to work on the engine and contribute to it, how everyone taking part behaves, and how to report a vulnerability |
| `PUBLISHING.md` | how a release reaches PyPI, and what this repository's history leaves out |

```
python3 -m unittest discover tests
for p in proofs/*_proof.py; do python3 "$p" || exit 1; done
```

## Licence

Apache-2.0 (`LICENSE`). The package is published as `wherefore-build`; what you
import and what you type are `wherefore`.
