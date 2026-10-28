import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib import SRC, DST

s = (SRC / "checks/_observe/sitecustomize.py").read_text(encoding="utf-8")
for name in ("WRITE_LOG", "READ_LOG", "UNIT"):
    s = s.replace(f"CP_{name}", f"WHEREFORE_{name}")


def once(old, new):
    global s
    assert s.count(old) == 1, old[:80]
    s = s.replace(old, new)


once('"""Record every path a generator opens for writing, into $WHEREFORE_WRITE_LOG.\n',
     '"""Record every path a generator opens for writing, into $WHEREFORE_WRITE_LOG.\n'
     '\n'
     'IN WHEREFORE. This file was moved from chaotic-pendulums-co\'s\n'
     'checks/_observe/sitecustomize.py with two changes and no others: the variables\n'
     'it reads are WHEREFORE_WRITE_LOG, WHEREFORE_READ_LOG and WHEREFORE_UNIT, written\n'
     'out literally so a guard that reads this source can find them, and the root\n'
     'comes from WHEREFORE_ROOT. A client may keep an observer of its own - the\n'
     'pendulum does, because its selection guard reads that file - by naming its\n'
     'directory in wherefore.json `observer.dir` with the `env_prefix` it reads.\n')
once('_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))\n',
     '# The client\'s root, from the runner that put this file on PYTHONPATH. In the\n'
     '# repository this was extracted from the observer lived three directories below\n'
     '# the root, and that is still the fallback - but installed with the engine it\n'
     '# lives in site-packages, where three directories up is nobody\'s repository, so\n'
     '# an unset WHEREFORE_ROOT filters every read out and the leaf judge fails on an\n'
     '# empty log: loud, and in the right direction.\n'
     '_ROOT = os.path.realpath(os.environ.get("WHEREFORE_ROOT") or os.path.dirname(\n'
     '    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))\n')
out = DST / "_observe" / "sitecustomize.py"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(s, encoding="utf-8")
print("_observe/sitecustomize.py: built from checks/_observe/sitecustomize.py")
