import pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib import SRC, DST
s = (SRC / "checks/generators.py").read_text(encoding="utf-8")

def once(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new)

def cut(start, end, new):
    """Replace from `start` (inclusive) to `end` (exclusive)."""
    global s
    i = s.index(start); j = s.index(end, i)
    assert s.count(start) == 1
    s = s[:i] + new + s[j:]

once('"""Every generator this repo runs, and a way to run them all while watching.\n',
     '"""Every generator this repo runs, and a way to run them all while watching.\n'
     '\n'
     'IN WHEREFORE. Moved from chaotic-pendulums-co\'s checks/generators.py, with its\n'
     'docstring and comments kept as they were: the stories are that repository\'s,\n'
     'and they are the reason each line is the way it is. What changed is only\n'
     'where the lists come from. ROOT, GENERATORS, NOT_A_GENERATOR, the observer and\n'
     'the names it reads are the CLIENT\'s now, set by configure() - from\n'
     'wherefore.json, or by a client that keeps its generator list in code, which\n'
     'is how the pendulum keeps the text its proofs plant faults into where it is.\n'
     'Each process the runner starts is also told the root, in WHEREFORE_ROOT, for\n'
     'an observer that does not live inside the client\'s tree. And roll() runs\n'
     'whichever gate the client names, rather than one path in one repository.\n')
once('ROOT = pathlib.Path(__file__).resolve().parents[1]\nOBSERVER = ROOT / "checks/_observe"\n',
     '# The client\'s, set by configure(). See the module docstring.\n'
     'ROOT = None\n'
     'OBSERVER = pathlib.Path(__file__).resolve().parent / "_observe"\n'
     'ENV_PREFIX = "WHEREFORE_"\n'
     'TEMP_PREFIX = "wherefore-"\n'
     'GATE_ARGV = [sys.executable, "-m", "wherefore", "gate", "--keep"]\n'
     'GATE_NAME = "`wherefore gate`"\n')
cut("GENERATORS = [\n", "\n# Scripts that write into the repo and are NOT generators",
    "GENERATORS = []\n")
cut("NOT_A_GENERATOR = {\n", "\n\ndef run_all(",
    "NOT_A_GENERATOR = {}\n"
    "\n"
    "\n"
    "def configure(root, generators, not_a_generator=None, observer=None,\n"
    "              env_prefix=\"WHEREFORE_\", temp_prefix=\"wherefore-\",\n"
    "              gate_argv=None, gate_name=None):\n"
    "    \"\"\"Say whose corpus this is. Every function below reads these.\"\"\"\n"
    "    global ROOT, OBSERVER, ENV_PREFIX, TEMP_PREFIX, GATE_ARGV, GATE_NAME\n"
    "    ROOT = pathlib.Path(root).resolve()\n"
    "    GENERATORS[:] = list(generators)\n"
    "    NOT_A_GENERATOR.clear()\n"
    "    NOT_A_GENERATOR.update(not_a_generator or {})\n"
    "    if observer is not None:\n"
    "        OBSERVER = pathlib.Path(observer)\n"
    "    ENV_PREFIX, TEMP_PREFIX = env_prefix, temp_prefix\n"
    "    if gate_argv is not None:\n"
    "        GATE_ARGV, GATE_NAME = list(gate_argv), gate_name\n"
    "\n"
    "\n"
    "def configure_from(cfg):\n"
    "    \"\"\"configure() from a loaded wherefore.json.\"\"\"\n"
    "    configure(cfg.root, cfg.generators, cfg.not_a_generator, cfg.observer_dir,\n"
    "              cfg.env_prefix, cfg.temp_prefix)\n")
once('        [str(OBSERVER)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))\n',
     '        [str(OBSERVER)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))\n'
     '    env["WHEREFORE_ROOT"] = str(ROOT)\n')
once('tempfile.mkdtemp(prefix="cp-coverage-")', 'tempfile.mkdtemp(prefix=f"{TEMP_PREFIX}coverage-")')
once('            env["CP_WRITE_LOG"] = str(log)\n', '            env[f"{ENV_PREFIX}WRITE_LOG"] = str(log)\n')
once('    gate = ROOT / "checks/coverage_gate.py"\n', '')
once('"is committed.\\nThis is checks/coverage_gate.py - it is the one thing "',
     'f"is committed.\\nThis is {GATE_NAME} - it is the one thing "')
once('    r = subprocess.run([sys.executable, str(gate), "--keep"], cwd=ROOT)\n',
     '    r = subprocess.run(GATE_ARGV, cwd=ROOT)\n')
(DST / "generators.py").write_text(s, encoding="utf-8")
print("generators.py: built from checks/generators.py")
