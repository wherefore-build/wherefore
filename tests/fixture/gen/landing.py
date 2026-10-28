"""site/index.html: the landing page, from the facts and the deck's edition."""
import json

from kit import COMPANY, PRODUCT, ROOT, dollars, litres, made_where

OUT = ROOT / "site/index.html"
# Written LAST, by ledger.py, and read here: so a change to the deck lands on
# this page one pass late, and the corpus takes two passes to settle.
EDITION = json.loads((ROOT / "ledger.json").read_text(encoding="utf-8"))["deck"]

html = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{PRODUCT['name']} - {COMPANY['name']}</title></head>
<body>
<h1>{PRODUCT['name']}</h1>
<p>An {PRODUCT['kind']}: {litres(PRODUCT['capacity_l'])}, boiling in {PRODUCT['boil_minutes']} minutes, for {dollars(PRODUCT['price_usd'])}.</p>
<p>{made_where()} {PRODUCT['warranty_years']}-year warranty.</p>
<footer>Deck edition {EDITION}</footer>
</body>
</html>
"""
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(html, encoding="utf-8")
