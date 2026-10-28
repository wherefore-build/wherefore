"""A fact out of a source, by name.

Two adapters, because two shapes of source exist:

  params   the shape the repository this was extracted from keeps its spec in:
           `family.group.name` names spec[family][group]["params"][name], whose
           value is its `nominal`, or its `value` where it has no band
  leaves   any JSON: a dotted path through objects and arrays (an array index
           is a number), and the value is whatever is there

A source's adapter is declared beside it in wherefore.json `sources`; `leaves`
is the default, because it assumes nothing about the source's shape.
"""


def value(doc, dotted, adapter="leaves"):
    if adapter == "params":
        family, group, name = dotted.split(".")
        p = doc[family][group]["params"][name]
        return p.get("nominal", p.get("value"))
    node = doc
    for part in dotted.split("."):
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


def leaves(doc, prefix=()):
    """(dotted path, value) for every scalar in a JSON document, in order."""
    if isinstance(doc, dict):
        for k, v in doc.items():
            yield from leaves(v, prefix + (str(k),))
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            yield from leaves(v, prefix + (str(i),))
    else:
        yield ".".join(prefix), doc
