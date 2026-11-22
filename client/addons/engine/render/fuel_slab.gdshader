// Slabs (docs/design/client_objects.md §4): a unit box per instance, length along local x, thickness along local y
// (the segmented face's normal, fire_solid §1.1), width along local z. The vertex shader widens a thin slab to 2
// output pixels of projected thickness (§4.2: the floor applies to what the screen shows, not the world thickness);
// the fragment shader finds its segment along the length and drops a burnt-through one.
shader_type spatial;
render_mode unshaded, cull_back;

#include "res://addons/engine/render/fuel_object.gdshaderinc"

// Below this, a slab seen edge-on stops growing: its face, not its edge, is then what shows.
const float MIN_EDGE_SINE = 0.25;

varying float v_s;
varying flat int v_instance;
varying vec3 v_normal_world;

void vertex() {
	v_instance = INSTANCE_ID;
	float length_m = length(MODEL_MATRIX[0].xyz);
	float thickness_m = length(MODEL_MATRIX[1].xyz);
	v_s = (VERTEX.x + 0.5) * length_m;
	vec3 normal_godot = normalize(MODEL_MATRIX[1].xyz);
	vec3 forward = normalize(-INV_VIEW_MATRIX[2].xyz);
	float cosine = dot(normal_godot, forward);
	float edge_sine = max(sqrt(max(1.0 - cosine * cosine, 0.0)), MIN_EDGE_SINE);
	VERTEX.y *= max(1.0, 2.0 * floor_half_m / max(thickness_m * edge_sine, 1e-6));
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
