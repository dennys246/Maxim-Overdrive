// Rods (docs/design/client_objects.md §4): a unit cylinder per instance, its axis along local y, scaled by the
// instance transform to the rod's length and radius. The vertex shader only widens a thin rod to the 2 px floor; the
// fragment shader finds its own segment and drops a burnt-through one, decided per pixel, never per vertex (§4.2).
shader_type spatial;
render_mode unshaded, cull_back;

#include "res://addons/engine/render/fuel_object.gdshaderinc"

varying float v_s;
varying flat int v_instance;
varying vec3 v_normal_world;

void vertex() {
	v_instance = INSTANCE_ID;
	float length_m = length(MODEL_MATRIX[1].xyz);
	float radius_m = length(MODEL_MATRIX[0].xyz);
	v_s = (VERTEX.y + 0.5) * length_m;
	VERTEX.xz *= max(1.0, floor_half_m / max(radius_m, 1e-6));
	v_normal_world = godot_to_world(normalize(MODEL_NORMAL_MATRIX * NORMAL));
}

void fragment() {
	Instance inst = instance_at(v_instance);
	int row = segment_row(inst, v_s);
	if (burnt_through(row)) {
		discard;
	}
	ALBEDO = fuel_colour(inst, row, normalize(v_normal_world));
}
