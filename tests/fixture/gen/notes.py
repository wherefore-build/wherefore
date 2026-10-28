"""The speaker notes, printed: the runner's `stdout_to` puts them in deck/speaker-notes.txt."""
from kit import COMPANY, PRODUCT, dollars, litres, made_where

print(f"{PRODUCT['name']}, from {COMPANY['name']} of {COMPANY['city']}.")
print(f"Say the size as {litres(PRODUCT['capacity_l'])} and the price as {dollars(PRODUCT['price_usd'])}.")
print(f"Say where it is made exactly as the deck does: {made_where()}")
