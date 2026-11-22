// Phase 1 flames (docs/design/client_objects.md §5.3): a client-drawn flame over each flaming segment, a purely visual
// effect driven by the segment's ignited_fraction (CLAUDE.md, "may add purely visual effects"). One camera-facing quad
// per segment row (INSTANCE_ID is the row), placed by FuelPass at the segment's top edge on a rebuild; a segment that
// isn't flaming collapses to zero area here, so only flaming segments cost any fill.
//
// Engine why: a flame is gas, with no surface for the raymarch or the fuel meshes to hit, so it is drawn as an emissive
// billboard over them, blended additively (it can only brighten what is behind it), after opaque geometry, testing
// depth but never writing it. Its height is a stylisation `[engineering]`; Phase 2's flame table replaces it.
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled;

#include "res://addons/engine/render/fuel_object.gdshaderinc"

// The flame's height at full ignition, metres: FuelPass.FLAME_HEIGHT_M, which also sizes the flames' culling box.
uniform float flame_height_m = 0.0;
// Each segment row's object row (FuelGeometry.segment_objects), as exact floats: a flame honours its object's burnout.
uniform sampler2D segment_object_tex : filter_nearest, repeat_disable;
const vec3 FLAME_BASE = vec3(1.0, 0.36, 0.06);
const vec3 FLAME_TIP = vec3(1.0, 0.78, 0.32);
const float FLAME_GAIN = 2.2;
// 0 in goldens (animation off, client_rendering.md §6.1); 1 in play.
uniform float flame_flicker = 0.0;

varying vec2 v_uv;
varying float v_ignited;

void vertex() {
	int object_row = int(texelFetch(segment_object_tex, row_at(INSTANCE_ID), 0).r);
	// §4.3: a burnt-out object draws no flame, and a burnt-through segment has no surface to burn from.
	bool dead = burnt_out(object_row) || burnt_through(INSTANCE_ID);
	float ignited = dead ? 0.0 : texelFetch(ignited_tex, row_at(INSTANCE_ID), 0).r;
	v_ignited = ignited;
	v_uv = UV;
	float width_m = length(MODEL_MATRIX[0].xyz);
	float phase = float(INSTANCE_ID) * 0.618;
	// 0.2: FuelPass.FLICKER_HEIGHT, which the flames' culling box allows for.
	float height_m = flame_height_m * sqrt(ignited) * (1.0 + flame_flicker * 0.2 * sin(TIME * 7.0 + phase * 6.283));
	// Camera-facing: the quad spans the camera's right and up, rising from the instance origin (the segment's top).
	vec3 right = normalize(INV_VIEW_MATRIX[0].xyz);
	vec3 up = normalize(INV_VIEW_MATRIX[1].xyz);
	vec3 base = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	vec3 world = base + right * (UV.x - 0.5) * max(width_m, floor_half_m * 4.0) + up * (1.0 - UV.y) * height_m;
	if (ignited <= 0.0) {
		world = base;  // zero area: rasterises nothing
	}
	POSITION = PROJECTION_MATRIX * VIEW_MATRIX * vec4(world, 1.0);
}

void fragment() {
	// A tongue: widest at the base, narrowing to the tip, fading at its edges.
	float rise = 1.0 - v_uv.y;
	float half_width = 0.5 * (1.0 - rise * rise);
	float across = abs(v_uv.x - 0.5);
	float body = clamp((half_width - across) / max(half_width, 1e-3), 0.0, 1.0);
	float shape = body * (1.0 - rise);
	if (fuel_debug == 2) {
		ALBEDO = shape > 0.05 ? vec3(1.0) : vec3(0.0);
	} else if (fuel_debug == 1) {
		ALBEDO = vec3(0.0);
	} else {
		ALBEDO = mix(FLAME_BASE, FLAME_TIP, rise) * FLAME_GAIN * shape * v_ignited;
	}
}
