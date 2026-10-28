"""What every Fernhollow generator shares: the facts, read once, and how to say them."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FACTS = json.loads((ROOT / "facts.json").read_text(encoding="utf-8"))
PRODUCT = FACTS["product"]
COMPANY = FACTS["company"]


def litres(x):
    return f"{x:g} litres"


def dollars(x):
    return f"${x:,}"


def made_where():
    """The one origin sentence, from the activities the facts say happen there."""
    acts = FACTS["origin"]["activities"]
    said = acts[0] if len(acts) == 1 else ", ".join(acts[:-1]) + " and " + acts[-1]
    return f"{said.capitalize()} in {COMPANY['country']}."
