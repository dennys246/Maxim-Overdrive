// The cut-away (client_rendering.md §2): cells of a cut region above the stump are drawn as if they were air.
// Cutaway.gd decides which regions; this only reads the uniforms, so the rule lives in one place and can be tested
// without a GPU.

uniform int cut_ids[8];
uniform int cut_count = 0;
// Cells whose top is at most this height (world z, metres) stay drawn: the stump.
uniform float stump_top_m = 0.0;

bool region_is_cut(int region) {
	for (int i = 0; i < 8; i++) {
		if (i >= cut_count) {
			break;
		}
		if (cut_ids[i] == region) {
			return true;
		}
	}
	return false;
}

// True when cell ``c`` (solid, in region ``region``) is hidden by the cut.
bool is_cut(ivec3 c, int region) {
	return region != 0 && region_is_cut(region) && float(c.z + 1) * cell_m > stump_top_m + 1e-4;
}

// A solid cell the shader draws: solid and not cut away.
bool drawn_at(ivec3 c) {
	return inside(c) && material_at(c) != 0 && !is_cut(c, region_at(c));
}

// A cell removed by the cut: the faces it exposes are hatched.
bool cut_away_at(ivec3 c) {
	return inside(c) && material_at(c) != 0 && is_cut(c, region_at(c));
}
