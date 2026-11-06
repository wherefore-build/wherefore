# Starting a corpus

Read this when the repository has no `wherefore.json` yet, or has one that
declares nothing but this skill. The goal of the first session is small and
complete: **one fact, said once, compiled into one asset, held by the gate.**
Everything after that is the same move, repeated.

## Count before you ask anything

Start with **`wherefore scan`**, before the interview and before you write
anything. It needs no setup and writes nothing, and it answers the first
question an owner is usually asked and cannot answer from memory - what does
the company say in more than one place? Point it at what the company
publishes: the built site, the docs folder, exported deck notes, or a live
address. Where there are several places - the site, the app, the backend,
the docs, the deck - point it at all of them at once:

```
wherefore scan https://www.example.com app backend docs
```

Read in one place, it reports every value stated in words more than one way:
"start your {} day free trial": 14 in three places, 30 in one. Read in two,
it also says what the places state in common, which of those any two of
them disagree on (`DIFFER`), and which they all agree on. That is the count in its plainest
form, and the reason to do any of this.

**Show the person what it found before you ask them anything.** The interview
is better for it: instead of listing facts from memory, they answer about the
ones in front of them - which value is true, and who decides it.

### What the scan cannot see

The scan reports a number that has words on both sides of it within one
block of text, read from pages, Markdown and plain text. Know what that
leaves out, and look there by other means:

- **Names, lists and wording.** A plan's feature list with one item swapped
  for another is a disagreement the scan cannot see. Read the pages that
  state the same thing side by side.
- **A value alone on its line** - a price on a pricing card with no words to
  its left - has no statement to match. Read the cards.
- **What an app assembles at run time.** The scan reads the string literals
  out of source code in the common languages - what a program says to a
  person, typed whole - but not a message built from pieces, or a value
  that arrives from a database or a billing system. Read the module that
  builds the message.
- **Pages nothing links to.** A live address is crawled by its links, at
  most `--max-pages` of them.

### Read each finding where it was found

A finding is a claim to check, not a result to report. Two values said in
exactly the same files - a pricing table's two columns, on every page that
has the table - are two things, and the scan sets them apart as tied, under
"a table, not a stale copy". Two customers' results are two customers. Open
the page, find the statement, and say what it is before you count it. Report
only what you have read.

### "0 things in common" is not agreement

When several places are read together and the scan says they state nothing in
common, read the `read` lines under the first line before believing it: for
each place, how many files of each kind were read, and the kinds seen and
not read. A checkout whose readable files were icons and vendored packages'
READMEs contributed nothing of the company's. The scan reads source code for
its strings, so an app's words count; a kind it names as not read - a
spreadsheet, a database dump, a format of its own - is where to look by
other means. Until every side has been read, there is no count.

### The colours, which nobody can list

A site states its brand in colours as it states its prices in numbers, and
the scan counts them: how many distinct colours its stylesheets, style
blocks and drawings state, and which are within a shade of one another -
the greys that were meant to be one grey. That is drift nobody listed and
everybody can see. Show it with the rest; declaring the brand once, and
holding every colour to it, is `wherefore check palette`, later.

## Ask, starting from what the scan found

Interview the owner. One question at a time, and write the answers down:
they become the `why` beside each source and each rule. Begin with the
findings, then widen:

1. **Of what the scan found, which value is true, and who decides it?** A
   finding with two values has an owner somewhere; the answer names them.
2. **What did the scan miss?** Names (the product, its features, its plans),
   numbers it cannot see (a price alone on a card), claims (where it is made,
   what it is certified for) and statuses (what has shipped, what is in beta,
   what was retired). Where else is each said - the site, the docs, the deck,
   the emails, the app's own strings, a video's script? Which of those live
   in a repository, and which only in someone's drive?
3. **Does a system already own any of it?** Billing owns prices, feature
   flags own what is live, a CMS may own the copy. That system stays the
   source of truth. Do not copy its values into a facts file by hand and call
   the copy the source: tell the owner, and leave that fact for later.
4. **Who decides, and who releases?** You may work inside a draft. You never
   cut, tag or publish a release unless the owner has authorized that one.

## Find where each fact is decided before choosing the repository

The repository you were opened in may only be a reader. An app that shows the
company's plans may decide none of them: it reads prices at run time from the
billing system and holds its own copy of the plans' features, typed from
somewhere else. Starting the corpus there compiles a copy.

So, before the interview ends and before anything is written, for each fact
the scan found: **search for where it is decided.** One search across the
organisation's repositories for the phrases the scan found - the feature's
name, the trial's wording - names the repository that holds the plans, and
the billing code that holds the prices. Then:

- the corpus starts in the repository that decides the fact, and the
  readers pin it from there (see "Every surface that describes the
  product", below);
- a fact decided by a system (billing, flags, a CMS) is read from that
  system at run time, never copied into a facts file;
- the repository you were opened in gets its corpus when its turn comes, as
  a reader of the ones that decide.

Say which repository decides what, and get the owner's yes, before the first
fact.

Then, for each fact the owner named, search the repository for every place it
is stated - every spelling, and every old value they remember. Report it
plainly, before proposing anything:

> The product name appears in 41 files, spelled three ways. Two pages still
> give the old upload limit.

That is how you choose where to start: **the fact with the most copies, in
the asset people read most.**

## One fact, end to end

Get one asset compiling before you touch a second.

1. **`wherefore init`** writes `wherefore.json`, and this skill where Claude
   Code and Codex read it - `.claude/skills/wherefore/` and
   `.agents/skills/wherefore/`. Commit them. `wherefore.json` declares one
   generator already, the one that writes the skill: from the first build on,
   the skill is the one the pinned release ships, and the gate says so when it
   is not.

2. **Write the source.** A JSON file that says each fact once, shaped the way
   the owner talks about it:

   ```json
   {
    "product": {
     "name": "Northwind",
     "upload_limit_mb": 250
    }
   }
   ```

   Declare it in `sources`, with what it is:

   ```json
   "sources": {
    "facts": {"path": "facts.json", "adapter": "leaves",
              "why": "THE SOURCE: every fact the company states, once"}
   }
   ```

3. **`wherefore gate`** names every tracked file nobody has accounted for.
   Classify each one in `inventory.authored.rules`, as `[pattern, why]`, with a
   reason someone else would accept. Keep patterns narrow: `*.py` for the code
   is a reason; `**` is never one. A file you cannot classify is a question for
   the owner, not a guess.

4. **Write the generator.** By default a Python script that reads the source
   and writes the asset, every run, through `open()`. It holds no fact of its
   own:

   ```python
   import json, pathlib
   ROOT = pathlib.Path(__file__).resolve().parents[1]
   facts = json.loads((ROOT / "facts.json").read_text(encoding="utf-8"))
   p = facts["product"]
   (ROOT / "site").mkdir(exist_ok=True)
   (ROOT / "site/index.html").write_text(
       f"<h1>{p['name']}</h1><p>Uploads up to {p['upload_limit_mb']} MB.</p>\n",
       encoding="utf-8")
   ```

   Declare it, after everything it reads:

   ```json
   "generators": [
    {"script": "site.py", "cwd": "gen", "makes": "site/index.html, the landing page"}
   ]
   ```

   If the repository's own tooling is another language, the generator can be
   that instead: `{"run": ["node", "site.mjs"], "cwd": "gen", "makes": ...}`
   runs the command as given, with no shell, and the gate sees what it wrote
   by comparing the tree before and after. Use it where a Python wrapper
   would only call the real tool.

   Run `wherefore build`. Read the asset's diff: every line that moved should
   be explained by the source. Commit the source, the generator and the asset
   together.

5. **Prove the fact reaches the asset.** `reach` moves each fact, one at a
   time, and requires what it names to change:

   ```json
   "reach": {
    "facts": {"source": "facts", "include": ["product.*"], "exclude": [],
              "why": "every fact the page states"},
    "watched": ["site"],
    "probes": [
     {"name": "the upload limit", "fact": "product.upload_limit_mb",
      "reaches": "the landing page", "files": ["site/index.html"]}
    ],
    "audience": "a customer"
   }
   ```

   Then `wherefore check reach`. A fact that moves nothing is either dead or
   held by a generator's own copy; find out which.

6. **If a value is being replaced,** add it to the retired register in the
   same change - what it was, what replaced it, why - and run
   `wherefore check retired`. The register lives in the source; the `retired`
   section of `wherefore.json` says where, and which files a person reads.

7. **Hold it.** `wherefore hook install` refuses a push that leaves anything
   stale. Then the same in CI, on every push:

   ```yaml
   name: corpus
   on: [push]
   jobs:
     corpus:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v7
         - run: python3 -m pip install -r requirements-engine.txt
         - run: wherefore gate
         - run: wherefore check reach
   ```

   `requirements-engine.txt` names the one release of the engine this
   repository is built and judged by. Moving it is a change like any other.

Then the next asset, and the next, one at a time, with the gate green after
each. Never convert a repository in one change: a corpus that is half compiled
and green is worth more than one that is fully compiled and failing.

## Every surface that describes the product

Once one fact compiles, ask the owner where else the product is described:
the marketing site, the docs, the app's own strings, a changelog, a deck.
Often each lives in its own repository. Write the answers down:

1. **Which repository decides each fact?** The product's own repository
   decides what the product does - its features, its commands, its releases.
   The company's repository decides its name, its prices, its brand. Each fact
   has exactly one home, and the others read it from there.
2. **Which may read from which?** A public repository can read from a private
   one only what it is willing to publish. Say which facts cross, and keep
   everything else where it was decided.

Then set up every other surface the same way:

- **It pins the source** - a release, a commit, or a captured snapshot with
  its stamp - and never copies it by hand. Moving the pin is a pull request,
  judged by that surface's own gate.
- **It reads what the source ships as data** - the list of features, the
  releases, the commands - rather than typing its own list. If the source has
  no such list yet, that list is the first thing to add to it.
- **Its build fails on what it does not say.** A feature the source ships and
  the page has no words for stops the generator, naming the feature. So does a
  release missing from the changelog. A deliberate omission is written down
  with its reason, like any exemption, and words for a feature the source no
  longer has fail too.

Some surfaces copy what they cannot pin: another company's published file, or
counts taken from another product's public site, at one of its versions. Make
that a captured group, and give it an `upstream` - the address it was taken
from, what to read there, and what must still match: its bytes, or a version
the corpus records once. `wherefore check upstream` reads it whenever the
corpus is compiled for a deploy, and fails when the source has moved, until the copy is taken
again. The gate never reads it: the gate stays offline, so the same tree always
gives the same answer.

So a feature that ships reaches every page that tells people about the
product, or that page's build stops, and the pull request that moves the pin
is where the page catches up. Prove it the way every check is proved: remove
one feature's words and require the build to fail, naming it.

## Facts that live in application code

Every example above is a script writing a document. An app is different: its
copy of a fact is typed in its own language - a module with the plans' names
and feature lists, an upload-limit message typed beside each of a dozen size
constants - and generating that source from a JSON file is rarely the right
move. Three cases, in order:

1. **Something owns the fact already.** Billing owns the prices, a flag
   service owns what is live. The app reads it from there at run time, and
   its own copy goes. Nothing to generate; the corpus holds the pages, and the
   app reads the owner.
2. **Nothing owns it, and the app is where it lives.** Keep it once, in the
   language's own terms: one module that states the limit and builds each
   message from it, so the number is typed once and the messages cannot
   disagree with it. The corpus holds that module as authored - with its
   `why` - and the retired register and a claim rule hold what the app says
   against it (`wherefore check retired`, `wherefore check claims`).
3. **Generate source only when neither works:** when the fact is decided
   outside the app and nothing serves it at run time. Then a generator writes
   the module from the source, like any asset, and the gate holds it.

Where an app decides a fact that other surfaces state - its features, its
limits - it is the source for them: it ships the list as data, and the site
and the docs read that list, as "Every surface that describes the product"
says. The app is the one place; the others are readers.

## A page you publish but cannot build

Some surfaces the company publishes are built by nobody: a public site on a
hosted CMS that marketing edits in a form, a listing on someone else's
marketplace. The owner may rule out changing how it is made, for now. It
still states the company's own facts - the same plan features the app
states - and it drifts like any copy, edited where it is published.

This is the opposite of `upstream`. An upstream is a copy the corpus took
from elsewhere, held to the place it was taken from. Here the corpus is the
source and the page is the copy. Declare it, with the facts it states and how
each appears there:

```json
"published": {
 "pricing": {
  "url": "https://www.example.com/pricing",
  "why": "the public site, on a hosted CMS marketing edits; it states the plans the app decides",
  "states": [
   {"fact": "plans.pro.trial_days", "as": ["{} day free trial", "{}-day free trial"]},
   {"fact": "plans.pro.price", "as": "${} per month"},
   {"fact": "plans.pro.features", "each": true}
  ],
  "unreachable": "the CMS being down is not the page moving; a deploy goes ahead and says so"
 }
}
```

`as` is a template with the value in the braces - a page says "14-day free
trial" and the fact is 14 - or several; `each` holds every item of a list. Do
not write the page's sentence out whole: that is a copy of the page, which is
the thing not to keep.

**`wherefore check published`** reads each page live, as a person reads it,
and fails when the page says otherwise, quoting it: "says '30 day free trial',
and plans.pro.trial_days is '14'". A person edits the page where it is
published, because that is the only way that page changes. It goes to the
network, so it is never part of the gate or the hook: run it before every
deploy, beside `check upstream`. The drift it catches happens on the other
side, when nobody is deploying - marketing edits the CMS on a Tuesday - so
offer the owner a scheduled run as well, and let them choose:

```yaml
on:
  push:
  schedule:
    - cron: "17 6 * * *"   # the owner's choice: the page moves when nobody deploys
```

`reach` counts a fact named here as reaching that page, by declaration, and
says so; a fact stated nowhere the corpus builds and on no published page is
still dead. Prove the entries the way every check is proved: change the
source's value and require the check to fail, quoting the page.

**This is the step before building the page, not instead of it.** A
published page is a copy until it is built from the source, and the check
says so each time it runs. When the owner is ready - a CMS that reads a
feed, a page the corpus writes and someone uploads, a site moved to a
repository - the entry comes out of `published` and the page becomes a
generated asset like any other. Keep the goal in the `why`.

## What stays written by hand

Some assets are better written by a person: a help article, an essay, the
footage in a demo video. Do not generate them to tick a box. Hold them
instead:

- the **retired register** catches an old value or phrase anywhere a person
  reads (`wherefore check retired`);
- a **claim rule** says what may be claimed, of what, and why, and fails the
  rest (`wherefore check claims`).

A hand-written file that states a fact is held by those two, or it is a copy
nobody is watching.

## Stop and ask the owner

- which system is the source of truth for a fact;
- a file you cannot classify, or one made by hand from a source (a capture,
  which a person re-makes and restamps - never you);
- anything that would cut, tag or publish a release;
- anything the engine cannot express. Say what the corpus needs and why. Do
  not work around the engine with a second config, a script the gate cannot
  see, or a check that is never shown to fail.
