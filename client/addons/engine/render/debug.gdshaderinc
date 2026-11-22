// Debug passes (client_rendering.md §6.4): masks the checks read instead of the shaded frame. Each writes pure 0 or 1,
// which every tonemap and sRGB conversion keeps exact, so a check can threshold the PNG at 0.5.

// 0: shaded. 1: occluder, every drawn cell black (the player's ID pass: what hides the body). 2: crack mask, white
// where the first drawn cell has crack > 0. 3: glow mask, white where its surface_glow > 0. Masks don't carve, so a
// mask pixel is the cell a cold frame shows there.
uniform int debug_mode = 0;

const int PASS_SHADED = 0;
const int PASS_OCCLUDER = 1;
const int PASS_CRACK_MASK = 2;
const int PASS_GLOW_MASK = 3;

bool debug_carves() {
	return debug_mode == PASS_SHADED;
}

vec3 debug_colour(ivec3 cell, float g) {
	if (debug_mode == PASS_CRACK_MASK) {
		return crack_at(cell) > 0.0 ? vec3(1.0) : vec3(0.0);
	}
	if (debug_mode == PASS_GLOW_MASK) {
		return g > 0.0 ? vec3(1.0) : vec3(0.0);
	}
	return vec3(0.0);
}
