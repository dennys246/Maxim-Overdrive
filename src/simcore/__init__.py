"""simcore: the engine. A material-cell world simulation, its adapters to the outside, and its client protocol.

Layers, lowest first; each imports only those below it (``pyproject.toml``, ``[tool.importlinter]``; boundaries O24):

- ``simcore.core``: the sealed core. Cells, scenes, laws, the turn loop, imagined objects, action limits. No IO, no
  clock, no Maxim.
- ``simcore.adapters``: the engine's edges to the outside: file gates (``loaders``) and the Maxim SEM membrane
  (``sem``), the only engine code that imports ``maxim``.
- ``simcore.protocol``: what the client receives: rendering tiers and display encoding today, the wire protocol
  later.

The game (``maxim_overdrive``) sits above all three. A layer splits when a module passes the 500-line tripwire
(boundaries §2.2 maps where the splits are expected to fall).
"""

__version__ = "0.0.1"
