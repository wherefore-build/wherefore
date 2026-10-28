# Changelog

Every release of the engine, newest first. A client pins one commit (its
`requirements-engine.txt`), and moving that pin is a pull request its own full
suite judges, so a release reaches no client by itself.

The version is stated in `pyproject.toml`, in `wherefore.__version__` and here,
and `tests/test_version.py` holds the three together until they are one fact
(DIRECTIONS.md §12, §13).

## 0.1.0 (2026-10-28)

The first release: the machinery extracted from chaotic-pendulums-co, moved
rather than rewritten, with the pendulum as its first client.

- **Moved, byte for byte but for recorded edits** (`tools/moved/`): the
  generator runner and the roll, the write observer, the coverage gate, the
  comparators (pictures, numbers, workbook cells, inlined pictures), the proof
  harness, the retired-facts sweep and the source-reach probe.
- **New:**
  - `wherefore.json`, with includes and a required `why` for every
    exemption;
  - `entry`, for a client that configures the engine in Python;
  - the CLI: `init`, `list`, `build`, `gate`, `prove`, `check retired`,
    `check reach`, `check claims` and `hook install`;
  - two source adapters (`params`, `leaves`);
  - the claim rule.
- **Proved** against a fictional client, `tests/fixture/`. Each proof breaks it
  one way and requires the right failure, in the right words.
