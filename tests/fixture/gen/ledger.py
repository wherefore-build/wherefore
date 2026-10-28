"""ledger.json: the edition of each document, worked out from the document itself.

It runs LAST, because it can only say what the deck is once the deck is
current - and the landing page, which runs first, prints it. That is the cycle
the gate's second pass exists for.
"""
import hashlib
import json

from kit import ROOT

deck = (ROOT / "deck/one-pager.svg").read_bytes()
ledger = {"deck": hashlib.sha256(deck).hexdigest()[:12]}
(ROOT / "ledger.json").write_text(json.dumps(ledger, indent=1) + "\n", encoding="utf-8")
