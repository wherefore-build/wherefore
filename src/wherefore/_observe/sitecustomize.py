"""Record every path a generator opens for writing, into $WHEREFORE_WRITE_LOG.

IN WHEREFORE. This file was moved from chaotic-pendulums-co's
checks/_observe/sitecustomize.py with two changes and no others: the variables
it reads are WHEREFORE_WRITE_LOG, WHEREFORE_READ_LOG and WHEREFORE_UNIT, written
out literally so a guard that reads this source can find them, and the root
comes from WHEREFORE_ROOT. A client may keep an observer of its own - the
pendulum does, because its selection guard reads that file - by naming its
directory in wherefore.json `observer.dir` with the `env_prefix` it reads.

This is the mechanism the coverage gate is built on, and it is deliberately
the smallest thing that could work: Python raises an `open` audit event for
every file opened, whoever opens it, so one hook records them all without any
generator knowing it is watched.

It lives in a directory that contains NOTHING ELSE and is put on PYTHONPATH,
which is how Python finds a module called `sitecustomize` and imports it before
it runs anything. A child process inherits PYTHONPATH, so a generator that
shells out to another python is recorded too.

WHY NOT SCRAPE THE SOURCE. tools/audit_files.py does that - it greps the
generators for string literals that look like filenames - and it is the reason
this exists. buildpack.py writes `f"{d}cp-primary-{n}.svg"`, a name that is not
a literal anywhere, so the scrape misses all 53 of the marks. A list of what a
generator APPEARS to write drifts from what it DOES write, silently, and the
drift is invisible in exactly the direction that matters: a file the scrape
misses looks unclassified, and a file the scrape imagines looks covered.

WHY NOT mtime. Because a generator that skips its write when nothing changed
leaves the mtime alone, and the gate cannot tell that from a generator that was
never called. Both are the bug this catches. See the note in coverage_gate.py:
the fix was to make the generators write unconditionally, not to loosen this.

WHAT IT CANNOT SEE: a write that does not go through Python's open() - a C
extension calling write(2) on a descriptor it got elsewhere, or a rename over
a file opened under another name. Nothing in this repo does either, and the
gate's second half (byte-identical against a snapshot) would still catch the
content being wrong; only the coverage half would be fooled.

THE READ SIDE, $WHEREFORE_READ_LOG. The same event, asked the other question: not
"what did this make" but "what did this LOOK AT". checks/leaves_are_leaves.py
is built on it. A file that nothing in the heavy tier ever opens is a file a
change to cannot move the heavy tier's answer, and that is the only licence
checks/foundation.py has for letting a push skip the suite. So every open is
recorded, in every mode, with the script that made it:

    <mode>\t<script>\t<realpath>
    <mode>\t<unit>><script>\t<realpath>     when the script is not the unit

WHOSE READ IT IS, $WHEREFORE_UNIT. One job's log holds every step's reads, and a job
now runs several fingerprints: the checks under `heavy`, and a long proof under
a fingerprint of its own, so that a push that moves neither the proof nor what
it proves can skip it. Holding the proof's fingerprint to the WHOLE job's log
would make it the job's fingerprint again and the skip worth nothing, so a read
has to say which of the job's units caused it - and the script that made it is
not that: version.py is a unit of `heavy` AND the process version_proof.py
starts.

So the first watched process in a tree writes its own name into WHEREFORE_UNIT, every
child inherits it through the environment, and every line carries it. The
script stays beside it, because the script is what a message has to name to be
worth reading. checks/leaves_are_leaves.py judges each fingerprint on the lines
whose UNIT is one of its tier's declared units - and on every line whose unit
it does not recognise, because a tree that lost the variable is a tree nobody
can attribute, and the safe direction is to hold every fingerprint to it.

WHEREFORE_UNIT is set by this file and never by a workflow: checks/selection_holds.py
reads the names this module takes from the environment and fails a step that
sets any of them, so a step cannot relabel another step's reads.

Only paths inside this repository, because every import of the standard
library is an open too, and a log of those is a log nobody reads. Imports of
the repo's OWN modules are kept - io.open_code raises the same event - which is
what makes "a generator started importing a leaf" visible as well as "a
generator started reading one".

copying() is the one exemption, and it is explicit rather than inferred. The
coverage gate snapshots every tracked file before it runs anything and puts
every one back afterwards; that is a byte copy for restoring, not an
examination, and without saying so the log would claim the gate reads the
whole repository - true, and useless. Anything that wraps itself in copying()
is saying in code "I move these bytes, I do not look at them", where a reviewer
can hold it to that.
"""
import contextlib
import os
import sys

_LOG = os.environ.get("WHEREFORE_WRITE_LOG")
_READS = os.environ.get("WHEREFORE_READ_LOG")
# The client's root, from the runner that put this file on PYTHONPATH. In the
# repository this was extracted from the observer lived three directories below
# the root, and that is still the fallback - but installed with the engine it
# lives in site-packages, where three directories up is nobody's repository, so
# an unset WHEREFORE_ROOT filters every read out and the leaf judge fails on an
# empty log: loud, and in the right direction.
_ROOT = os.path.realpath(os.environ.get("WHEREFORE_ROOT") or os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
_COPYING = [0]


@contextlib.contextmanager
def copying():
    """Opens inside this block are byte copies, not reads. See the docstring."""
    _COPYING[0] += 1
    try:
        yield
    finally:
        _COPYING[0] -= 1


if _READS:
    _rh = open(_READS, "a", buffering=1, encoding="utf-8", errors="replace")
    _roots = tuple({_ROOT + os.sep, os.path.abspath(_ROOT) + os.sep})
    _who = os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else "python"

    def _unit(who):
        """The name of the outermost watched process in this tree.

        Set once, here, and inherited by every child through the environment.
        A process that starts before its own name is knowable ("python", while
        site runs) does not claim the tree: it is left unset, and the log line
        says the script alone, which the leaf check reads as unattributed and
        holds every fingerprint to.
        """
        was = os.environ.get("WHEREFORE_UNIT")
        if was:
            return was
        if who and who != "python":
            os.environ["WHEREFORE_UNIT"] = who
        return who

    def _read(event, args):
        if event != "open" or _COPYING[0]:
            return
        path, mode = args[0], args[1]
        if path is None or isinstance(path, int):
            return
        try:
            p = os.fspath(path)
            if isinstance(p, bytes):
                p = os.fsdecode(p)
            a = os.path.abspath(p)
            # AN IMPORT OPENS THE CACHE, NOT THE SOURCE, once the cache is warm:
            # brand/code/__pycache__/tokens.cpython-312.pyc, or - under a Python
            # that sets sys.pycache_prefix, as Apple's does - the same name under
            # ~/Library/Caches with the source's whole path inside it. Either is
            # recorded as the .py it was compiled from, or the second import of
            # a leaf module would be invisible, and the gate runs every
            # generator twice. The proof found the second spelling by missing it.
            if a.endswith(".pyc"):
                pre = getattr(sys, "pycache_prefix", None)
                d, name = os.path.split(a)
                if pre and a.startswith(os.path.abspath(pre) + os.sep):
                    d = d[len(os.path.abspath(pre)):] or os.sep
                elif os.path.basename(d) == "__pycache__":
                    d = os.path.dirname(d)
                a = os.path.join(d, name.split(".")[0] + ".py")
            # The cheap test first: this runs for every import of every module
            # in every process, and almost none of them are in the repo.
            if not a.startswith(_roots):
                return
            real = os.path.realpath(a)
            if mode is None:                  # os.open(): the mode is in flags
                flags = args[2] or 0
                mode = ("w" if flags & os.O_TRUNC else "r+") \
                    if flags & (os.O_WRONLY | os.O_RDWR) else "r"
            # sys.argv is not set yet while site runs, so the name is looked up
            # per event rather than trusted from import time.
            who = os.path.basename(sys.argv[0]) if getattr(sys, "argv", None) \
                and sys.argv[0] else _who
            unit = _unit(who)
            _rh.write(f"{mode}\t{who if unit == who else f'{unit}>{who}'}\t{real}\n")
        except Exception:
            # As below: a hook that raises kills what it watches. A read that
            # cannot be recorded is a gap, and the docstring of
            # leaves_are_leaves.py lists the gaps it has.
            pass

    sys.addaudithook(_read)

    # WHAT A BROWSER LOADS. Chromium and WebKit are not Python, so the hook
    # above never sees the page print_layout.py prints, the hero hero_stills.py
    # renders, or the video the walkthrough's page plays. Playwright is, and
    # every page it drives lives in a context it made. So when Playwright's own
    # Browser and BrowserType modules are imported, the two calls that make a
    # context are wrapped, and each new context reports every request it sends:
    #
    #     browser\t<script>\t<realpath>      a file:// request
    #     browser-url\t<script>\t<url>       anything else a page asked for
    #     playwright\t<script>\tpatched <module> | PATCH-FAILED <module>: <why>
    #
    # Browser.new_page makes its context through new_context, so it is covered
    # too. A Playwright that renames these internals cannot be patched; that
    # is written down as PATCH-FAILED, and checks/leaves_are_leaves.py fails a
    # log that says it, rather than taking an empty request log as a clean one.
    _PW = {"playwright._impl._browser": ("Browser", "new_context"),
           "playwright._impl._browser_type": ("BrowserType", "launch_persistent_context")}

    def _who_now():
        who = os.path.basename(sys.argv[0]) if getattr(sys, "argv", None) \
            and sys.argv[0] else _who
        unit = _unit(who)
        return who if unit == who else f"{unit}>{who}"

    def _request(url):
        try:
            if url.startswith("file:"):
                from urllib.parse import unquote, urlparse
                p = os.path.realpath(unquote(urlparse(url).path))
                _rh.write(f"browser\t{_who_now()}\t{p}\n")
            elif not url.startswith(("data:", "about:", "blob:")):
                _rh.write(f"browser-url\t{_who_now()}\t{url}\n")
        except Exception:
            pass

    def _wrap(module, name):
        cls_name, meth = _PW[name]
        cls = getattr(module, cls_name)
        orig = getattr(cls, meth)

        async def made_a_context(self, *a, **k):
            ctx = await orig(self, *a, **k)
            try:
                ctx.on("request", lambda req: _request(req.url))
            except Exception as e:
                _rh.write(f"playwright\t{_who_now()}\tPATCH-FAILED {name}: on('request') {e}\n")
            return ctx
        made_a_context.__wrapped__ = orig
        setattr(cls, meth, made_a_context)

    class _PlaywrightWatch:
        """A meta-path finder that finds nothing itself: it lets the real
        finder find Playwright's two modules, and wraps their loading."""

        def find_spec(self, name, path=None, target=None):
            if name not in _PW:
                return None
            for finder in sys.meta_path:
                if finder is self or not hasattr(finder, "find_spec"):
                    continue
                spec = finder.find_spec(name, path, target)
                if spec is not None:
                    break
            else:
                return None
            loader = spec.loader
            run = getattr(loader, "exec_module", None)
            if run is None:
                return spec

            class Loader:
                def create_module(self, s):
                    return loader.create_module(s)

                def exec_module(self, module):
                    run(module)
                    try:
                        _wrap(module, name)
                        _rh.write(f"playwright\t{_who_now()}\tpatched {name}\n")
                    except Exception as e:
                        _rh.write(f"playwright\t{_who_now()}\tPATCH-FAILED {name}: {e}\n")

                def __getattr__(self, attr):
                    return getattr(loader, attr)
            spec.loader = Loader()
            return spec

    sys.meta_path.insert(0, _PlaywrightWatch())

if _LOG:
    _fh = open(_LOG, "a", buffering=1, encoding="utf-8", errors="replace")
    # The open() above is itself an open, and it happens before the hook is
    # installed, so it cannot record itself. Anything after this point can.

    def _record(event, args):
        if event != "open":
            return
        path, mode = args[0], args[1]
        # mode is None for os.open(); its flags are args[2]. A directory
        # listing and a read both reach here too, hence the mode test.
        if path is None or mode is None:
            return
        if not any(c in mode for c in "wxa+"):
            return
        try:
            _fh.write(os.path.realpath(os.fspath(path)) + "\n")
        except Exception:
            # A hook that raises kills the generator it is watching. An
            # unrecordable path is a gap in coverage, which the gate reports
            # as an unclassified file - loud, and in the right place.
            pass

    sys.addaudithook(_record)
