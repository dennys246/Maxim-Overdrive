"""The engine's adapters to the outside world: file gates (``loaders``) and the Maxim SEM membrane (``sem``).

Adapters import the core, never the protocol layer or the game. Only ``simcore.adapters.sem`` may import ``maxim``.
"""
