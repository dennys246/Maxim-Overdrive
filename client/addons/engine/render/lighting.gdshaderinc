// Lighting (client_rendering.md §5.3): a fixed key light, face shading, neighbour AO, a fixed night ambient. The
// shader is unshaded (Godot's lights don't touch it) and computes all of this itself: Phase 1 has no light field,
// so the night is a look, not a simulation (BF-N1), and a fixed light keeps goldens independent of any light node.
//
// Face shading: a voxel face's normal is one of six axes, so a Lambert term gives each face orientation one flat
// tone. Half-Lambert (0.5 + 0.5 n.L, squared, Valve's trick) keeps faces turned away from the light from going black
// and, with the light off every axis, gives the top and both visible sides three different tones at every yaw.

uniform int ao_taps = 4;
uniform vec3 palette[16];

const float CHAR_DARKEN = 0.4;
const float HATCH_PERIOD_M = 0.12;
const float HATCH_MIN_PERIOD_PX = 8.0;
const float HATCH_DUTY = 0.4;
const float HATCH_SHADE = 0.45;
const float FISSURE_DARKEN_PER_M = 14.0;

vec3 albedo_of(int material, float crack) {
	vec3 base = palette[clamp(material, 0, 15)];
	// Char darkens as well as carves: a burned surface is darker. The checks (§6.4) measure shape over cracked
	// cells, so this alone can't pass them.
	return base * (1.0 - CHAR_DARKEN * crack);
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
// fu, fv where the point is on the face, in [0, 1]. Only the neighbours on the point's own side of each axis can
// darken it, so only those are read: 2 edge taps, plus 1 corner tap at ao_taps 8 (a far-side tap always weighed 0).
float face_ao(ivec3 out_cell, int axis, vec3 p_cell) {
	if (ao_taps == 0) {
		return 1.0;
	}
	int ua = axis == 0 ? 1 : 0;
	int va = axis == 2 ? 1 : 2;
	float fu = fract(pick(p_cell, ua)) * 2.0 - 1.0;
	float fv = fract(pick(p_cell, va)) * 2.0 - 1.0;
	ivec3 u = axis_unit(ua) * (fu < 0.0 ? -1 : 1);
	ivec3 v = axis_unit(va) * (fv < 0.0 ? -1 : 1);
	float wu = fu * fu;
	float wv = fv * fv;
	float occ = occludes(out_cell + u) * wu + occludes(out_cell + v) * wv;
	if (ao_taps == 8) {
		occ += 0.5 * occludes(out_cell + u + v) * wu * wv;
	}
	return clamp(1.0 - 0.45 * occ, 0.45, 1.0);
}

// Hatching marks a cut face by shape (diagonal stripes in the face's own plane, in metres), so a cut wall never
// reads as burned away, whatever the viewer's colour vision (§2).
float hatch(int axis, vec3 p_cell) {
	int ua = axis == 0 ? 1 : 0;
	int va = axis == 2 ? 1 : 2;
	// At least HATCH_MIN_PERIOD_PX pixels a stripe pair, or at half resolution the stripes alias into a checkerboard.
	float period = max(HATCH_PERIOD_M, HATCH_MIN_PERIOD_PX * pixel_m);
	float s = (pick(p_cell, ua) + pick(p_cell, va)) * cell_m / period;
	return fract(s) < HATCH_DUTY ? HATCH_SHADE : 1.0;
}
