# Starting a corpus

Read this when the repository has no `wherefore.json` yet, or has one that
declares nothing but this skill. The goal of the first session is small and
complete: **one fact, said once, compiled into one asset, held by the gate.**
Everything after that is the same move, repeated.

## Ask before you write anything

Interview the owner. One question at a time, and write the answers down:
they become the `why` beside each source and each rule.

1. **What does the company say in more than one place?** Names (the product,
   its features, its plans), numbers (limits, dimensions, versions), claims
   (where it is made, what it is certified for) and statuses (what has
   shipped, what is in beta, what was retired).
2. **Where is each one said?** The site, the docs, the deck, the emails, the
   app's own strings, a video's script. Which of those live in this
   repository, and which only in someone's drive?
3. **Does a system already own any of it?** Billing owns prices, feature flags
   own what is live, a CMS may own the copy. That system stays the source of
   truth. Do not copy its values into a facts file by hand and call the copy
   the source: tell the owner, and leave that fact for later.
4. **Who decides, and who releases?** You may work inside a draft. You never
   cut, tag or publish a release unless the owner has authorized that one.

## Count before you change anything

Start with **`wherefore scan`** over what the company publishes - the built
site, the docs folder, exported notes, or a live site's address. It needs no
setup, and it reports every statement whose copies disagree ("start your {}
day free trial": 14 in three places, 30 in one), which is the count in its
plainest form.

Then, for each fact the owner named, search the repository for every place it
is stated - every spelling, and every old value they remember. Report it
plainly, before proposing anything:

> The product name appears in 41 files, spelled three ways. Two pages still
> give the old upload limit.

That count is the reason to do any of this. It is also how you choose where
to start: **the fact with the most copies, in the asset people read most.**

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

4. **Write the generator.** A Python script that reads the source and writes
   the asset, every run, through `open()`. It holds no fact of its own:

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
the corpus records once. `wherefore check upstream` reads it, before a deploy
and on a schedule, and fails when the source has moved, until the copy is taken
again. The gate never reads it: the gate stays offline, so the same tree always
gives the same answer.

So a feature that ships reaches every page that tells people about the
product, or that page's build stops, and the pull request that moves the pin
is where the page catches up. Prove it the way every check is proved: remove
one feature's words and require the build to fail, naming it.

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
