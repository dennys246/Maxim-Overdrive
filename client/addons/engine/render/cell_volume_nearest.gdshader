// The cell volume with surface_glow read nearest-filtered: each cell's face one flat glow (the laptop tier, §5.5).
// unshaded: the shader lights itself (lighting.gdshaderinc), so Godot's light pass is skipped entirely.
// cull_back: only the box's camera-facing faces start a ray; the camera is never inside the volume.
shader_type spatial;
render_mode unshaded, cull_back;

#include "res://addons/engine/render/cell_volume.gdshaderinc"
