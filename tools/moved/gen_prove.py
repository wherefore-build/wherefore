import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib import move
move("checks/_prove.py", "prove.py", [
 ('"""The harness the proof scripts share: break one thing, run a check, put it back.\n',
  '"""The harness the proof scripts share: break one thing, run a check, put it back.\n'
  '\n'
  'IN WHEREFORE. Moved from chaotic-pendulums-co\'s checks/_prove.py, its words\n'
  'kept. Two things changed. ROOT is the client\'s: WHEREFORE_ROOT if it is set,\n'
  'else the nearest directory holding wherefore.json at or above the working\n'
  'directory, else the working directory - and set_root() for a client whose\n'
  'proofs import this through a module of their own. And the copy of the tree\n'
  'Tree takes is named with the client\'s TEMP_PREFIX.\n'),
 ('ROOT = pathlib.Path(__file__).resolve().parents[1]\n',
  'def _root():\n'
  '    env = os.environ.get("WHEREFORE_ROOT")\n'
  '    if env:\n'
  '        return pathlib.Path(env).resolve()\n'
  '    here = pathlib.Path.cwd().resolve()\n'
  '    for d in (here, *here.parents):\n'
  '        if (d / "wherefore.json").is_file():\n'
  '            return d\n'
  '    return here\n'
  '\n'
  '\n'
  'ROOT = _root()\n'
  'TEMP_PREFIX = "wherefore-"\n'
  '\n'
  '\n'
  'def set_root(root, temp_prefix=None):\n'
  '    """Prove against this tree. Edit, Tree and run all resolve against it."""\n'
  '    global ROOT, TEMP_PREFIX\n'
  '    ROOT = pathlib.Path(root).resolve()\n'
  '    if temp_prefix is not None:\n'
  '        TEMP_PREFIX = temp_prefix\n'),
 ('tempfile.mkdtemp(prefix="cp-tree-")', 'tempfile.mkdtemp(prefix=f"{TEMP_PREFIX}tree-")'),
])
