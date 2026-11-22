// The cell volume with surface_glow read linear-filtered: glow blends smoothly across a face's cells (the rig and
// max tiers, §5.5). Otherwise identical to cell_volume_nearest.gdshader; the filter is a compile-time choice in Godot.
shader_type spatial;
render_mode unshaded, cull_back;

#define GLOW_LINEAR
#include "res://addons/engine/render/cell_volume.gdshaderinc"
