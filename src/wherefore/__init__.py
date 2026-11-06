"""Wherefore: a company that compiles.

One source of truth, every asset generated from it, every change tested - so
nothing ships that contradicts a decision. This package is the machinery that
enforces it; a client's wherefore.json says what its corpus is.

Kept free of imports on purpose: the observer is loaded into every process a
generator starts, and nothing it does should cost a generator anything.
"""
__version__ = "0.14.0"
