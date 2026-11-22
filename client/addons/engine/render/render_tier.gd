class_name RenderTier
extends Resource
## One rendering tier (client_rendering.md §5.5, D20): how much detail a machine draws. Never physics: every tier
## receives the same 0.1 m channels and draws the same world, so a tier changes precision, not what is shown.
## A Resource so each tier is a .tres file of client data (client/game/tiers/), editable without code, and typed, so a
## misspelt field fails to load instead of being ignored.

@export var tier_name: String = ""
## The 3-D viewport's render scale: 0.5 draws a quarter of the pixels and upscales (the cheapest knob a GPU has).
@export var scaling_3d_scale: float = 1.0
## How many steps the crack march takes into a cracked cell (§5.4): more steps, finer fissure floors.
@export var crack_substeps: int = 4
## Read surface_glow with linear filtering (smooth across cells) or nearest (each cell flat). A sampler's filter is
## fixed when the shader compiles in Godot, so this picks one of two shader variants, not a uniform.
@export var glow_linear: bool = true
## Bloom: the WorldEnvironment's glow post-process, which bleeds HDR emission above 1.0 into its surroundings.
@export var bloom: bool = true
## Neighbour ambient occlusion per face: 0 (off), 4 (the face's four edge neighbours) or 8 (edges and corners). Only
## the neighbours on the shaded point's side can darken it, so the shader reads 2 or 3 of them (lighting.gdshaderinc).
@export var ao_taps: int = 4
## Flame particle budget (§5.3). Particles aren't built yet; the field is here so the tier files are complete.
@export var flame_particles: int = 0


## Every reason this tier can't be used; empty when it can.
func problems() -> Array[String]:
	var out: Array[String] = []
	if tier_name.is_empty():
		out.append("no tier_name")
	if not (scaling_3d_scale > 0.0 and scaling_3d_scale <= 1.0):
		out.append("scaling_3d_scale %s is not in (0, 1]" % scaling_3d_scale)
	if crack_substeps < 1 or crack_substeps > 16:
		out.append("crack_substeps %d is not in 1..16" % crack_substeps)
	if ao_taps not in [0, 4, 8]:
		out.append("ao_taps %d is not 0, 4 or 8" % ao_taps)
	if flame_particles < 0:
		out.append("flame_particles %d is negative" % flame_particles)
	return out
