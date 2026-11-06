# Reporting

A developer tells their agent to ping us, and this is what the agent runs.

## One command

```
wherefore report --title TITLE WORDS ... [--from FILE] [--show | --link]
```

There is no kind to choose. Whether a thing is a bug, a question or a
missing feature is the makers' judgment, made in triage; the reporter gives
one line and the words. One report says one thing: several things are
several reports.

## What a report carries

- the title, one line, at most a hundred characters, never cut;
- the words, as the body, with their paragraphs;
- the release, the Python and the platform;
- the corpus's shape in counts - how many generators, sources, authored rules
  and captured groups it declares, and whether a brand is declared - never a
  file's name, a value in one, or a path on the machine;
- the output of the command that went wrong, when given with `--from`.

It prints the whole report before anything leaves the machine.

## Sending it

- `--show` prints the report and sends nothing. Run this first and show the
  person.
- `--link` prints the report and a link that opens the issue filled in, and
  sends nothing, even with `gh` signed in. The person reads it there and sends
  it themselves, which is the approval.
- With neither, the report is opened as an issue on wherefore-build/wherefore
  with `gh`, signed in; without `gh`, the link is printed.

An agent may draft the title and the words from what the person said. The
person approves them, by saying so before the agent sends, or by sending the
link.

## What becomes of it

The issue is the inbox. When the makers take a report on, a comment on the
issue gives the plan and names the roadmap item; the roadmap is a file
beside the engine's code, and the company's site shows it. When it ships, a
comment says the release and the feature, with a line an agent reads -

```
wherefore-inbox: shipped version=0.16.0 feature=scan-read
```

- and the issue is closed. The engine's own tests hold the chain: a release
that answers an issue says so in its ledger, the feature names the issue, and
a changelog entry that names an issue the ledger does not have fails. When
the person asks what became of a report, read the issue, tell them, and move
the pin to that release when they say.
