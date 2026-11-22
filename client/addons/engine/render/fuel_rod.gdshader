// The rod's depth pass (fuel_rod.gdshaderinc): invisible (blended at alpha 0), writing depth over exactly the drawn
// silhouette, coverage 0.5 and up, the 2 px floor included. Its next passes, fuel_rod_fringe.gdshader, draw the colour.
// Depth only, because an opaque core showing its colour put a hard step in the edge's ramp at coverage 0.5, which
// crawled on the laptop tier (2.55-2.62x the ideal line against the 2.0x bar, measured 2026-11-22).
shader_type spatial;
render_mode unshaded, cull_back, blend_mix, depth_draw_always;

#include "res://addons/engine/render/fuel_rod.gdshaderinc"

void fragment() {
	int row;
	if (rod_coverage(row) < 0.5) {
		discard;
	}
	ALBEDO = vec3(0.0);
	ALPHA = 0.0;
}
