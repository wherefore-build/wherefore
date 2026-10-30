# Contributing

Wherefore holds other people's builds to a rule, so it holds itself to the
same one: every check is shown to fail before it is trusted, and a change that
leaves anything stale is refused.

## Working on the engine

```
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[pictures,xlsx]'
python -m unittest discover -s tests
for p in proofs/*_proof.py; do python "$p" || exit 1; done
```

- **A new check comes with its proof:** a script that breaks the fixture
  company (`tests/fixture/`) the way the check exists to catch, and requires the
  check to fail in the right words. Then break the check itself, and watch the
  proof report a miss.
- **A command is said once,** in `src/wherefore/commands.json`. The CLI's help,
  the README and the skill all read it, and `corpus/commands_named.py` fails a
  document that names a command the CLI does not have.
- **The version moves whenever `src/` does** (`corpus/version_moves.py`), with
  an entry in `CHANGELOG.md`. Merging to `main` tags and publishes the release
  from that entry.
- **The README is generated** from `docs/README.template.md`
  (`corpus/readme.py`); edit the template, never the README.

## Contributions from outside

Not accepted yet. Issues are welcome once the repository is public; pull
requests will be, once the project has a contributor agreement in place.
