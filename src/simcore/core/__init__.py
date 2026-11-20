"""The sealed core: everything that runs on the simulation lane (boundaries §3).

It imports no layer above it, no ``maxim``, and none of the banned modules (clocks, entropy, the OS, file IO,
concurrency); ``pyproject.toml``'s import contracts hold it to that, and ``tests/test_determinism.py`` scans it.
Loaded tables arrive as required parameters.
"""
