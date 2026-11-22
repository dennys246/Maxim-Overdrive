// Rods (docs/design/client_objects.md §4): what the rod's two passes share. A unit cylinder per instance, its axis
// along local y, scaled by the instance transform to the rod's length and radius. The vertex shader widens a thin rod
// to the 2 px floor plus one rendered pixel; the fragment shader finds its own segment, drops a burnt-through one (per
// pixel, never per vertex, §4.2), and computes its coverage: its distance from the drawn silhouette in rendered
// pixels, 0.5 on the silhouette itself.
//
// Analytic edge coverage, not MSAA (owner ruling 3, 2026-11-22, measured in docs/design/research/fuel_antialiasing.md).
// Two passes, because a blended edge can't both write depth and fade (review C-S1): Compatibility's prepass for a
// blended material keeps only fragments at alpha 1, so a floored stick on the laptop tier, whose fade spans its whole
// width, wrote no depth, and crossing sticks occluded each other by instance order. The depth pass (fuel_rod.gdshader)
// writes depth, and no colour, over the drawn silhouette (coverage 0.5 and up); the colour (fuel_rod_fringe.gdshader,
// its next passes) blends the whole coverage ramp, depth-tested against every silhouette: every rod's core, then every
// rod's fade outside it, so a front fade lands on a rear rod. The cost: inside the front rod's silhouette the rear rod
// is hidden, so the front rod's inner fade blends over what is behind both (D1's inner half).
//
// Why view space: the camera is orthographic, so view-space x and y are screen-aligned metres, and a fragment's
// distance from the rod's projected axis is a 2-D distance there. A perspective camera would need the projection
// (B40 (3): no perspective path is drawn yet).

#define FUEL_INSTANCE
#include "res://addons/engine/render/fuel_object.gdshaderinc"

// Metres one rendered pixel spans: the fade's width. 0 until set, which draws hard edges.
uniform float render_pixel_m = 0.0;

varying float v_s;
varying vec3 v_normal_world;
varying vec3 v_view;
varying flat vec2 v_axis_a;
varying flat vec2 v_axis_b;
varying flat float v_drawn_m;

void vertex() {
	Instance inst = instance_at(INSTANCE_ID);
	v_instance = instance_fields(inst);
	v_segment_m = inst.segment_m;
	float length_m = length(MODEL_MATRIX[1].xyz);
	float radius_m = length(MODEL_MATRIX[0].xyz);
	v_s = (VERTEX.y + 0.5) * length_m;
	v_drawn_m = max(radius_m, floor_half_m);  // FuelPass.drawn_half_m, the rule's GDScript copy for the checks
	VERTEX.xz *= (v_drawn_m + render_pixel_m) / max(radius_m, 1e-6);
	mat4 to_view = VIEW_MATRIX * MODEL_MATRIX;
	v_view = (to_view * vec4(VERTEX, 1.0)).xyz;
	v_axis_a = (to_view * vec4(0.0, -0.5, 0.0, 1.0)).xy;
	v_axis_b = (to_view * vec4(0.0, 0.5, 0.0, 1.0)).xy;
	v_normal_world = godot_to_world(normalize(MODEL_NORMAL_MATRIX * NORMAL));
}

// The distance in view-space metres from ``p`` to the segment a-b: the rod's projected axis, its caps included.
float axis_distance(vec2 p, vec2 a, vec2 b) {
	vec2 ab = b - a;
	float t = clamp(dot(p - a, ab) / max(dot(ab, ab), 1e-12), 0.0, 1.0);
	return length(p - (a + ab * t));
}

// This fragment's coverage, or -1 when its segment is burnt through; ``row`` is the segment row it reads.
float rod_coverage(out int row) {
	Instance inst = fuel_instance_from_varyings();
	row = segment_row(inst, clamp(v_s, 0.0, inst.segment_m * float(inst.count)));
	if (burnt_through(row)) {
		return -1.0;
	}
	float fade = max(render_pixel_m, 1e-6);
	return clamp((v_drawn_m - axis_distance(v_view.xy, v_axis_a, v_axis_b)) / fade + 0.5, 0.0, 1.0);
}

vec3 rod_albedo(int row) {
	return fuel_debug == 0 ? fuel_colour(fuel_instance_from_varyings(), row, normalize(v_normal_world))
		: vec3(fuel_debug == 1 ? 1.0 : 0.0);
}
