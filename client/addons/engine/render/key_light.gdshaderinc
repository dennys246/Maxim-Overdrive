// The fixed key light and night ambient (client_rendering.md §5.3), shared by the cell and fuel passes so both are lit
// by one light. Half-Lambert (0.5 + 0.5 n.L, squared): faces turned away from the light don't go black.

// World axes (x east, y north, z up): from the south-south-west, high.
const vec3 KEY_DIR_WORLD = vec3(-0.30, -0.45, 0.84);
const vec3 KEY_COLOUR = vec3(1.25, 1.18, 1.05);
const vec3 AMBIENT_COLOUR = vec3(0.13, 0.15, 0.22);

vec3 face_lit(vec3 albedo, vec3 n_world, float ao) {
	float s = 0.5 + 0.5 * dot(n_world, normalize(KEY_DIR_WORLD));
	return albedo * (AMBIENT_COLOUR + KEY_COLOUR * s * s) * ao;
}
