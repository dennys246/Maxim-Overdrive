// Lighting (client_rendering.md §5.3): a fixed key light, face shading, neighbour AO, a fixed night ambient. The
// shader is unshaded (Godot's lights don't touch it) and computes all of this itself: Phase 1 has no light field,
// so the night is a look, not a simulation (BF-N1), and a fixed light keeps goldens independent of any light node.
//
// Face shading: a voxel face's normal is one of six axes, so a Lambert term gives each face orientation one flat
// tone. Half-Lambert (0.5 + 0.5 n.L, squared, Valve's trick) keeps faces turned away from the light from going black
// and, with the light off every axis, gives the top and both visible sides three different tones at every yaw.

uniform int ao_taps = 4;
uniform vec3 palette[16];

// World axes (x east, y north, z up): from the south-south-west, high.
const vec3 KEY_DIR_WORLD = vec3(-0.30, -0.45, 0.84);
const vec3 KEY_COLOUR = vec3(1.25, 1.18, 1.05);
const vec3 AMBIENT_COLOUR = vec3(0.13, 0.15, 0.22);
const float CHAR_DARKEN = 0.4;
const float HATCH_PERIOD_M = 0.12;
const float HATCH_DUTY = 0.4;
const float HATCH_SHADE = 0.45;
const float FISSURE_DARKEN_PER_M = 14.0;

vec3 albedo_of(int material, float crack) {
	vec3 base = palette[clamp(material, 0, 15)];
	// Char darkens as well as carves: a burned surface is darker. The checks (§6.4) measure shape over cracked
	// cells, so this alone can't pass them.
	return base * (1.0 - CHAR_DARKEN * crack);
}

vec3 face_lit(vec3 albedo, vec3 n_world, float ao) {
	float s = 0.5 + 0.5 * dot(n_world, normalize(KEY_DIR_WORLD));
	return albedo * (AMBIENT_COLOUR + KEY_COLOUR * s * s) * ao;
}

// Darkening for a hit ``depth_m`` inside a fissure: its walls get less light the deeper they are.
float fissure_shade(float depth_m) {
	return exp(-FISSURE_DARKEN_PER_M * depth_m);
}

float occludes(ivec3 c) {
	return drawn_at(c) ? 1.0 : 0.0;
}

// Ambient occlusion from the cells next to the face: a face in a corner is darker, which is what makes voxel
// geometry read as solid. ``out_cell`` is the air cell the face looks into; u and v are the face's own axes and
// fu, fv where the point is on the face, in [0, 1]. Each solid neighbour darkens the part of the face near it.
float face_ao(ivec3 out_cell, int axis, vec3 p_cell) {
	if (ao_taps == 0) {
		return 1.0;
	}
	int ua = axis == 0 ? 1 : 0;
	int va = axis == 2 ? 1 : 2;
	ivec3 u = axis_unit(ua);
	ivec3 v = axis_unit(va);
	float fu = fract(pick(p_cell, ua));
	float fv = fract(pick(p_cell, va));
	vec4 near = vec4(max(0.0, 2.0 * fu - 1.0), max(0.0, 1.0 - 2.0 * fu), max(0.0, 2.0 * fv - 1.0), max(0.0, 1.0 - 2.0 * fv));
	near = near * near;
	float occ = occludes(out_cell + u) * near.x + occludes(out_cell - u) * near.y;
	occ += occludes(out_cell + v) * near.z + occludes(out_cell - v) * near.w;
	if (ao_taps == 8) {
		occ += 0.5 * occludes(out_cell + u + v) * near.x * near.z + 0.5 * occludes(out_cell + u - v) * near.x * near.w;
		occ += 0.5 * occludes(out_cell - u + v) * near.y * near.z + 0.5 * occludes(out_cell - u - v) * near.y * near.w;
	}
	return clamp(1.0 - 0.45 * occ, 0.45, 1.0);
}

// Hatching marks a cut face by shape (diagonal stripes in the face's own plane, in metres), so a cut wall never
// reads as burned away, whatever the viewer's colour vision (§2).
float hatch(int axis, vec3 p_cell) {
	int ua = axis == 0 ? 1 : 0;
	int va = axis == 2 ? 1 : 2;
	float s = (pick(p_cell, ua) + pick(p_cell, va)) * cell_m / HATCH_PERIOD_M;
	return fract(s) < HATCH_DUTY ? HATCH_SHADE : 1.0;
}
