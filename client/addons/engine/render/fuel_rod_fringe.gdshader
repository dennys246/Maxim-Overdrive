// The rod's colour pass (fuel_rod.gdshaderinc), drawn after every rod's depth pass as its next pass: the rod's colour,
// blended by its coverage over the whole widened rod, depth-tested against every rod's silhouette, never writing depth.
// Inside its own silhouette it meets its own depth and passes; behind another rod's silhouette it is hidden.
shader_type spatial;
render_mode unshaded, cull_back, blend_mix, depth_draw_never;

#include "res://addons/engine/render/fuel_rod.gdshaderinc"

void fragment() {
	int row;
	float coverage = rod_coverage(row);
	if (coverage <= 0.0) {
		discard;
	}
	ALBEDO = rod_albedo(row);
	ALPHA = coverage;
}
