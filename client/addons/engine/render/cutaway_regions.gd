class_name CutawayRegions
extends Resource
## The regions the cut-away may cut, by name (client_rendering.md §2, DC-N4): walls, never the crate or any other
## prop, so the fire stays visible from everywhere. Client data, not world state: the server never hears of it.

@export var regions: PackedStringArray = []
