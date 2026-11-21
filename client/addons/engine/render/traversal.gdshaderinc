// The cell grid and the walk through it (client_rendering.md §5.1, §5.2).
//
// Amanatides and Woo (1987), "A Fast Voxel Traversal Algorithm": a ray through a regular grid visits cells in
// order by always stepping across whichever cell boundary it reaches first. Per axis it keeps tmax, the ray
// parameter where it next crosses a boundary on that axis, and tdelta, how far apart those crossings are. Each step
// is a compare and an add, and no cell is skipped or visited twice, which a fixed-step march can't promise.
//
// Space: "cell space" is the volume in cell units, x east, y north, z up (the world's axes), with cell (i, j, k)
// covering [i, i + 1) x [j, j + 1) x [k, k + 1). The mesh is a box over the whole volume, centred on its node.

uniform sampler3D material_tex : filter_nearest, repeat_disable;
uniform sampler3D region_tex : filter_nearest, repeat_disable;
uniform sampler3D bricks_tex : filter_nearest, repeat_disable;
// Sentinel defaults: a volume whose uniforms were never set draws nothing (cell_m 0 sends every ray out of bounds),
// rather than drawing plausibly with a stale value. CellVolume sets both from the snapshot.
uniform ivec3 cells = ivec3(0);
uniform float cell_m = 0.0;

const int BRICK = 4;
const float FAR = 1e30;

struct Ray {
	vec3 o;      // origin, cell space
	vec3 d;      // direction, cell space (unit length in cells)
	vec3 inv;    // 1 / d, FAR where d is 0
	ivec3 stp;   // the sign of d per axis
};

struct Walk {
	ivec3 cell;
	vec3 tmax;   // the ray parameter of the next boundary on each axis
	float t;     // the ray parameter where the walk entered this cell
	int axis;    // the axis of the boundary it crossed to enter
};

// The world (x, y, z) is Godot's (x, z, -y), so a Godot vector (x, y, z) is the world's (x, -z, y): the same map
// as IsoCamera.to_godot and to_world.
vec3 godot_to_world(vec3 g) {
	return vec3(g.x, -g.z, g.y);
}

vec3 world_to_godot(vec3 w) {
	return vec3(w.x, w.z, -w.y);
}

int material_at(ivec3 c) {
	return int(round(texelFetch(material_tex, c, 0).r * 255.0));
}

// The u16 region id, uploaded as RG8: low byte in r, high byte in g.
int region_at(ivec3 c) {
	vec2 rg = texelFetch(region_tex, c, 0).rg;
	return int(round(rg.r * 255.0)) + 256 * int(round(rg.g * 255.0));
}

bool inside(ivec3 c) {
	return c.x >= 0 && c.y >= 0 && c.z >= 0 && c.x < cells.x && c.y < cells.y && c.z < cells.z;
}

bool brick_empty(ivec3 c) {
	return texelFetch(bricks_tex, c / BRICK, 0).r < 0.5;
}

ivec3 axis_unit(int axis) {
	return axis == 0 ? ivec3(1, 0, 0) : (axis == 1 ? ivec3(0, 1, 0) : ivec3(0, 0, 1));
}

float pick(vec3 v, int axis) {
	return axis == 0 ? v.x : (axis == 1 ? v.y : v.z);
}

int pick_i(ivec3 v, int axis) {
	return axis == 0 ? v.x : (axis == 1 ? v.y : v.z);
}

Ray make_ray(vec3 o, vec3 d) {
	Ray r;
	r.o = o;
	r.d = d;
	r.stp = ivec3(sign(d));
	r.inv = vec3(d.x != 0.0 ? 1.0 / d.x : FAR, d.y != 0.0 ? 1.0 / d.y : FAR, d.z != 0.0 ? 1.0 / d.z : FAR);
	return r;
}

float boundary_t(Ray r, ivec3 cell, int axis) {
	int s = pick_i(r.stp, axis);
	if (s == 0) {
		return FAR;
	}
	float edge = float(pick_i(cell, axis) + (s > 0 ? 1 : 0));
	return (edge - pick(r.o, axis)) * pick(r.inv, axis);
}

// The walk state at the ray's entry into the volume (t = 0), through a face on ``axis``. The entry axis's cell is
// decided from the step direction, not by rounding the point, which lies exactly on that face. This is the only
// place the walk is set from a position: every later cell comes from exact steps (advance), so float rounding,
// which differs between a GPU and llvmpipe, can never place the walk on the wrong side of a boundary.
Walk walk_at(Ray r, float t, int axis) {
	Walk w;
	vec3 p = r.o + r.d * t;
	w.cell = clamp(ivec3(floor(p)), ivec3(0), cells - ivec3(1));
	int s = pick_i(r.stp, axis);
	int crossed = int(round(pick(p, axis))) - (s < 0 ? 1 : 0);
	w.cell = axis == 0 ? ivec3(crossed, w.cell.y, w.cell.z) : (axis == 1 ? ivec3(w.cell.x, crossed, w.cell.z) : ivec3(w.cell.x, w.cell.y, crossed));
	w.t = t;
	w.axis = axis;
	w.tmax = vec3(boundary_t(r, w.cell, 0), boundary_t(r, w.cell, 1), boundary_t(r, w.cell, 2));
	return w;
}

// Cross the nearest boundary into the next cell.
void advance(Ray r, inout Walk w) {
	if (w.tmax.x < w.tmax.y && w.tmax.x < w.tmax.z) {
		w.t = w.tmax.x;
		w.cell.x += r.stp.x;
		w.tmax.x += abs(r.inv.x);
		w.axis = 0;
	} else if (w.tmax.y < w.tmax.z) {
		w.t = w.tmax.y;
		w.cell.y += r.stp.y;
		w.tmax.y += abs(r.inv.y);
		w.axis = 1;
	} else {
		w.t = w.tmax.z;
		w.cell.z += r.stp.z;
		w.tmax.z += abs(r.inv.z);
		w.axis = 2;
	}
}

// Where the ray leaves the current cell (the nearest of its three boundaries).
float cell_exit_t(Walk w) {
	return min(w.tmax.x, min(w.tmax.y, w.tmax.z));
}

// A ray crosses at most nx + ny + nz cells in all, and each outer iteration moves it at least one cell (a brick
// skip moves it out of a brick), so this bounds every walk through the volume, whatever its shape.
int max_steps() {
	return cells.x + cells.y + cells.z + BRICK;
}

// Leave the empty 4 x 4 x 4 brick the walk is in: empty-space skipping (§5.2). The walk takes its ordinary exact
// steps, but reads no texture until it is in another brick: an empty brick costs one occupancy read instead of two
// reads per cell. Earlier versions jumped to the brick's exit and re-derived the cell from the float position there;
// on llvmpipe that cycled one ray between two bricks, and the cure for that shaded floor tops as side faces (wrong
// entry axis) along brick edges. Exact steps can do neither. A ray crosses at most 3 * BRICK cells of one brick.
void skip_brick(Ray r, inout Walk w) {
	ivec3 brick = w.cell / BRICK;
	for (int k = 0; k < 3 * BRICK; k++) {
		advance(r, w);
		if (!inside(w.cell) || any(notEqual(w.cell / BRICK, brick))) {
			return;
		}
	}
}

// The axis of the box face the ray entered through, from that face's normal (world axes). The normal is exact per
// face, where guessing from the point's distance to each face picks the wrong axis within float error of an edge.
int entry_axis(vec3 face_normal) {
	vec3 n = abs(face_normal);
	return (n.x > n.y && n.x > n.z) ? 0 : (n.y > n.z ? 1 : 2);
}
