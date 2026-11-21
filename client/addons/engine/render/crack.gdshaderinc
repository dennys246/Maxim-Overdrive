// Crack changes shape (client_rendering.md §5.4; EX-S10, CR-S4): a cracked cell is carved, not just darkened.
//
// The pattern is a 3-D Voronoi diagram, the cells of nearest feature point, whose boundaries look like the polygonal
// fissures of drying or heat-cracked material. Each cell carries one feature point, jittered by an integer hash of
// the cell's index (a lattice twice as fine drew polygons 3.6 px across at the golden zoom: all groove, no face).
// The pattern is fixed to the world (it never swims as the camera turns) and runs on across cell boundaries. Points within w of a boundary are empty when the cell's crack c > 0, with
// w = max(0.02 m * c, the metres 0.75 px spans): a groove 2w wide is never narrower than 1.5 px, so it can't
// shimmer in and out between pixels as the camera moves.

uniform sampler3D crack_tex : filter_nearest, repeat_disable;
// Metres one rendered pixel spans at the current zoom and render scale (IsoCamera.pixel_metres).
uniform float pixel_m = 0.01;
uniform int crack_substeps = 4;

const float CRACK_MAX_HALF_WIDTH_M = 0.02;
const float CRACK_MIN_HALF_WIDTH_PX = 0.75;

float crack_at(ivec3 c) {
	return texelFetch(crack_tex, c, 0).r;
}

float groove_half_width_m(float c) {
	return max(CRACK_MAX_HALF_WIDTH_M * c, CRACK_MIN_HALF_WIDTH_PX * pixel_m);
}

// A well-mixed integer hash of a lattice index, three values in [0, 1]. Integer arithmetic, so every GPU (and the
// CPU) gets the same pattern; a sin-based float hash differs between drivers.
vec3 lattice_hash(ivec3 p) {
	uvec3 v = uvec3(p) * 1664525u + 1013904223u;
	v.x += v.y * v.z;
	v.y += v.z * v.x;
	v.z += v.x * v.y;
	v = v ^ (v >> 16u);
	v.x += v.y * v.z;
	v.y += v.z * v.x;
	v.z += v.x * v.y;
	return vec3(v & uvec3(65535u)) / 65535.0;
}

// The distance in metres from world point ``p_m`` to the nearest Voronoi boundary, and the unit vector (world axes)
// pointing from that boundary into the polygon ``p_m`` is in.
float crack_edge(vec3 p_m, out vec3 away) {
	float spacing = cell_m;
	vec3 q = p_m / spacing;
	ivec3 base = ivec3(floor(q));
	float d1 = FAR;
	float d2 = FAR;
	vec3 f1 = vec3(0.0);
	vec3 f2 = vec3(0.0);
	for (int z = -1; z <= 1; z++) {
		for (int y = -1; y <= 1; y++) {
			for (int x = -1; x <= 1; x++) {
				ivec3 n = base + ivec3(x, y, z);
				vec3 f = vec3(n) + 0.15 + 0.7 * lattice_hash(n);
				float dd = dot(f - q, f - q);
				if (dd < d1) {
					d2 = d1;
					f2 = f1;
					d1 = dd;
					f1 = f;
				} else if (dd < d2) {
					d2 = dd;
					f2 = f;
				}
			}
		}
	}
	// The boundary between the two nearest points is their bisecting plane; q's distance to it is exact for that
	// pair and a close bound for the true boundary.
	vec3 across = normalize(f2 - f1);
	away = -across;
	return dot((f1 + f2) * 0.5 - q, across) * spacing;
}

// The result of carving one cracked cell along the ray.
struct Carve {
	bool solid;   // the ray met material inside this cell
	float t;      // where (cell space ray parameter)
	vec3 away;    // the fissure wall's normal (world axes), when the hit is inside a groove
	float edge_m; // the distance from the boundary at the hit
	int k;        // the substep it hit at: 0 is the cell's face
};

// March ``crack_substeps`` steps into the cell from where the walk entered it until a point outside every groove.
Carve carve(Ray r, Walk w, float c) {
	Carve out_c;
	out_c.solid = false;
	float half_w = groove_half_width_m(c);
	float exit_t = cell_exit_t(w);
	for (int k = 0; k < 16; k++) {
		if (k >= crack_substeps) {
			break;
		}
		float t = mix(w.t, exit_t, float(k) / float(crack_substeps));
		vec3 away;
		float e = crack_edge((r.o + r.d * t) * cell_m, away);
		if (e > half_w) {
			out_c.solid = true;
			out_c.t = t;
			out_c.away = away;
			out_c.edge_m = e;
			out_c.k = k;
			return out_c;
		}
	}
	return out_c;
}
