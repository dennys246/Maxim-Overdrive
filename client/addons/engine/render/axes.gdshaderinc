// The world's axes against Godot's, in a shader (IsoCamera.to_godot is the same mapping in GDScript; nothing else maps).
// The world is z-up (x east, y north, z up); Godot is y-up. A world point (x, y, z) is the Godot point (x, z, -y): a
// rotation, not a mirror, so windings survive it.

vec3 godot_to_world(vec3 g) {
	return vec3(g.x, -g.z, g.y);
}

vec3 world_to_godot(vec3 w) {
	return vec3(w.x, w.z, -w.y);
}
