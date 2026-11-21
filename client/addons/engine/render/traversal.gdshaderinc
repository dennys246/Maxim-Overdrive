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
uniform ivec3 cells = ivec3(1);
uniform float cell_m = 0.1;

// The walk ends after this many iterations: a ray crosses at most nx + ny + nz = 208 cells of the alley, and each
// brick jump replaces at least one cell step.
const int MAX_STEPS = 320;
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

// The walk state in the cell the ray reaches just after parameter t, having crossed a boundary on ``axis``. The
// crossed axis's cell is decided from the step direction, not by rounding the point, because a point exactly on a
// boundary (every brick jump lands on one, often on two at once) rounds either way in float and would skip a cell.
Walk walk_at(Ray r, float t, int axis) {
	Walk w;
	vec3 p = r.o + r.d * t;
	w.cell = ivec3(floor(p));
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

// Jump to the first cell past the 4 x 4 x 4 brick the walk is in: empty-space skipping (§5.2). An empty brick costs
// one occupancy read instead of up to ten cell steps with two texture reads each.
void skip_brick(Ray r, inout Walk w) {
	vec3 lo = vec3((w.cell / BRICK) * BRICK);
	vec3 bound = lo + vec3(greaterThan(r.d, vec3(0.0))) * float(BRICK);
	vec3 t = (bound - r.o) * r.inv;
	t = vec3(r.stp.x == 0 ? FAR : t.x, r.stp.y == 0 ? FAR : t.y, r.stp.z == 0 ? FAR : t.z);
	int axis = (t.x < t.y && t.x < t.z) ? 0 : (t.y < t.z ? 1 : 2);
	w = walk_at(r, pick(t, axis), axis);
}

// The axis of the volume's face that the point ``o`` (cell space, on the box) lies on: the entry face's axis.
int entry_axis(vec3 o) {
	vec3 to_face = min(abs(o), abs(o - vec3(cells)));
	return (to_face.x < to_face.y && to_face.x < to_face.z) ? 0 : (to_face.y < to_face.z ? 1 : 2);
}
