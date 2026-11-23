// The rod's colour (fuel_rod.gdshaderinc), in two passes drawn after every rod's depth pass: the core (coverage 0.5 and
// up, the silhouette the depth pass wrote) and then the fade outside it, each blended by its coverage, depth-tested
// against every rod's silhouette, never writing depth. Every rod's core draws before any rod's fade, so a front rod's
// fade always blends over a rod behind it, whatever their instance order (review D1, owner 2026-11-22): sorting by
// centre got only crossings whose centres line up right. Two exceptions. Rods that touch: their widened shells
// interpenetrate, so near the contact the rear rod's depth hides part of the front fade, and the rear fade draws over
// the front core (fuel_leftovers N-1; numbers in docs/plans/checklists.md step 8). Fade over fade still blends in
// instance order (N-5).
// One shader, two materials, so both halves compute the coverage the depth pass did with the same code: a fragment
// falls in exactly one of them.
shader_type spatial;
render_mode unshaded, cull_back, blend_mix, depth_draw_never;

#include "res://addons/engine/render/fuel_rod.gdshaderinc"

// false: the core pass; true: the fade pass.
uniform bool fade_half = false;

void fragment() {
	int row;
	float coverage = rod_coverage(row);
	if (coverage <= 0.0 || (coverage < 0.5) != fade_half) {
		discard;
	}
	ALBEDO = rod_albedo(row);
	ALPHA = coverage;
}
