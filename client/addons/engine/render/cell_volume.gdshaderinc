// The one shader (client_rendering.md §5): a voxel raymarch over the snapshot's channels.
//
// How it draws: the mesh is just a box over the volume. The GPU rasterises the box's camera-facing faces, and for
// each pixel they cover, fragment() walks the ray from that pixel through the cell grid until it meets a drawn cell.
// The pixel then shows that cell's face, and the shader writes the face's depth, so bodies and other meshes hide
// behind cells, and in front of them, correctly (§5.3). The geometry is the data: when a cell changes, the next
// frame shows it after one texture upload, with no mesh to rebuild.
//
// Why a fragment shader on a box (not a compute pass or a mesh per cell): it runs on the Compatibility renderer
// (OpenGL 3.3, T8), which has no compute shaders, and it costs one draw call.
//
// The top-level .gdshader files set the render mode and GLOW_LINEAR, then include this.

#include "res://addons/engine/render/traversal.gdshaderinc"
#include "res://addons/engine/render/cutaway.gdshaderinc"
#include "res://addons/engine/render/crack.gdshaderinc"
#include "res://addons/engine/render/lighting.gdshaderinc"
#include "res://addons/engine/render/emission.gdshaderinc"
#include "res://addons/engine/render/debug.gdshaderinc"

// The box's centre in the volume's Godot frame (whose origin is the world's origin): a mesh vertex v is the volume
// point v + centre_godot.
uniform vec3 centre_godot = vec3(0.0);

varying vec3 v_local;
varying vec3 v_camera_local;
varying vec3 v_forward_local;

void vertex() {
	v_local = VERTEX;
	mat4 to_local = inverse(MODEL_MATRIX);
	v_camera_local = (to_local * vec4(CAMERA_POSITION_WORLD, 1.0)).xyz;
	v_forward_local = normalize(mat3(to_local) * -INV_VIEW_MATRIX[2].xyz);
}

// What the walk found.
struct Hit {
	ivec3 cell;
	float t;
	int axis;
	bool in_groove;   // the hit is a fissure wall inside this cell
	vec3 away;        // the Voronoi direction at the hit (world axes)
	float edge_m;     // the distance from the nearest crack boundary, metres
	float depth_m;    // how far below the surface the ray had gone through grooves
	bool cracked;
};

bool find_hit(Ray r, out Hit h) {
	Walk w = walk_at(r, 0.0, entry_axis(r.o));
	float groove_t0 = -1.0;
	for (int i = 0; i < MAX_STEPS; i++) {
		if (!inside(w.cell)) {
			return false;
		}
		if (brick_empty(w.cell)) {
			skip_brick(r, w);
			continue;
		}
		if (drawn_at(w.cell)) {
			float c = crack_at(w.cell);
			h.cell = w.cell;
			h.axis = w.axis;
			h.t = w.t;
			h.in_groove = false;
			h.away = vec3(0.0);
			h.edge_m = FAR;
			h.cracked = c > 0.0;
			if (h.cracked && debug_carves()) {
				Carve cv = carve(r, w, c);
				if (!cv.solid) {
					groove_t0 = groove_t0 < 0.0 ? w.t : groove_t0;
					advance(r, w);
					continue;
				}
				h.t = cv.t;
				h.in_groove = cv.k > 0;
				h.away = cv.away;
				h.edge_m = cv.edge_m;
			}
			float surface_t = groove_t0 >= 0.0 ? groove_t0 : w.t;
			h.depth_m = (h.t - surface_t) * cell_m;
			return true;
		}
		advance(r, w);
	}
	return false;
}

// The shading normal in world axes: the crossed face's, a fissure wall's, or the face's tilted towards a groove at
// its lip (§5.4), which shades the groove's edge as a bevel.
vec3 hit_normal(Ray r, Hit h) {
	if (h.in_groove) {
		return -h.away;
	}
	vec3 face = -vec3(axis_unit(h.axis)) * float(pick_i(r.stp, h.axis));
	if (!h.cracked) {
		return face;
	}
	float half_w = groove_half_width_m(crack_at(h.cell));
	float lip = clamp(1.0 - (h.edge_m - half_w) / half_w, 0.0, 1.0);
	return normalize(face - 0.8 * lip * h.away);
}

vec3 shade(Ray r, Hit h, vec3 p, float time) {
	vec3 face = -vec3(axis_unit(h.axis)) * float(pick_i(r.stp, h.axis));
	ivec3 out_cell = h.cell - axis_unit(h.axis) * pick_i(r.stp, h.axis);
	float g = glow_count(h.cell, p, face);
	if (debug_mode != PASS_SHADED) {
		return debug_colour(h.cell, g);
	}
	bool on_face = !h.in_groove && h.depth_m <= 0.0;
	float ao = on_face ? face_ao(out_cell, h.axis, p) : 1.0;
	float hatched = on_face && cut_away_at(out_cell) ? hatch(h.axis, p) : 1.0;
	vec3 albedo = albedo_of(material_at(h.cell), crack_at(h.cell));
	vec3 lit = face_lit(albedo, hit_normal(r, h), ao) * hatched * fissure_shade(h.depth_m);
	return lit + glow_emission(g) + flame_emission(h.cell, time);
}

void fragment() {
	bool ortho = PROJECTION_MATRIX[3][3] == 1.0;
	vec3 dir_local = ortho ? v_forward_local : normalize(v_local - v_camera_local);
	vec3 origin = godot_to_world(v_local + centre_godot) / cell_m;
	Ray r = make_ray(clamp(origin, vec3(0.0), vec3(cells)), normalize(godot_to_world(dir_local)));
	Hit h;
	if (!find_hit(r, h)) {
		discard;
	}
	vec3 p = r.o + r.d * h.t;
	ALBEDO = shade(r, h, p, TIME);
	// Depth of the hit, not of the box face (§5.3): project it and map NDC z to the depth buffer's range, which on
	// the Compatibility renderer (OpenGL) is [0, 1] from [-1, 1]; Forward+ uses reversed Z with NDC z as is.
	vec4 clip = PROJECTION_MATRIX * VIEW_MATRIX * MODEL_MATRIX * vec4(world_to_godot(p * cell_m) - centre_godot, 1.0);
	vec3 ndc = clip.xyz / clip.w;
#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	DEPTH = ndc.z * 0.5 + 0.5;
#else
	DEPTH = ndc.z;
#endif
}
