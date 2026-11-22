// Fuel objects (docs/design/client_objects.md §4–§5): what the rod and slab shaders share. An object is one MultiMesh
// instance; its segments' state lives in data textures, and each fragment looks up its own segment (§4.1).
//
// Why textures and not per-instance data: Compatibility keeps MultiMesh custom data at half float, exact only to
// 2,048 (§2), so an index travels in RGBA8 bytes instead, which are exact.

#include "res://addons/engine/render/axes.gdshaderinc"
#include "res://addons/engine/render/key_light.gdshaderinc"
#include "res://addons/engine/render/glow_curve.gdshaderinc"
#include "res://addons/engine/render/flame_colour.gdshaderinc"

// Three RGBA8 texels per instance, at x = 0, 1, 2 and y = INSTANCE_ID (FuelPass writes them on a rebuild):
//   0: first segment row (3 bytes, little-endian), the recipe's palette index;
//   1: segment count (2 bytes), the object's row in the objects table (2 bytes);
//   2: the segment length's f32 bits.
uniform sampler2D instance_tex : filter_nearest, repeat_disable;
// Segment columns, row i at (i mod 256, i div 256), uploaded from the frame's bytes as they arrive.
uniform sampler2D temperature_tex : filter_nearest, repeat_disable;
uniform sampler2D ignited_tex : filter_nearest, repeat_disable;
uniform sampler2D thickness_tex : filter_nearest, repeat_disable;
uniform sampler2D char_tex : filter_nearest, repeat_disable;
// The objects' state column (0 live, 1 burnt out), row i at (i mod 256, i div 256).
uniform sampler2D state_tex : filter_nearest, repeat_disable;
uniform vec3 recipe_colours[16];
// Metres one output pixel spans: half the 2 px floor (§4.2). 0 until set, which floors nothing.
uniform float floor_half_m = 0.0;
// FuelPass.View: 0 shaded; 1 the fuel-ID mask (fuel white, flames black); 2 the flame-ID mask (flames white, fuel
// black). §7.2's checks read both, unlit.
uniform int fuel_debug = 0;

const int ROW_WIDTH = 256;
// §3.3's clip of surface_temperature_c, applied here too; FuelSnapshot refuses a frame outside it (owner ruling 9).
// Unseen in the goldens: +inf drew as 6,000 °C's white on llvmpipe with the linear tonemapper (ruling 6).
const float FUEL_MIN_C = -273.0;
const float FUEL_MAX_C = 6000.0;
// §5.1: the glow's start and span are client constants now that the input is degrees C.
const float FUEL_GLOW_START_C = 525.0;
const float FUEL_GLOW_SPAN_C = 975.0;
// §5.2: a flaming surface is brighter than a hot one at the same temperature, in the cell pass's flame colour.
const float BURN_GAIN = 1.2;
// §5.2: char darkens the albedo, a luminance change the char check measures.
const float FUEL_CHAR_DARKEN = 0.7;

struct Instance {
	int first;
	int count;
	int object_row;
	int recipe;
	float segment_m;
};

uint byte_of(float unorm) {
	return uint(round(unorm * 255.0));
}

Instance instance_at(int id) {
	vec4 a = texelFetch(instance_tex, ivec2(0, id), 0);
	vec4 b = texelFetch(instance_tex, ivec2(1, id), 0);
	vec4 c = texelFetch(instance_tex, ivec2(2, id), 0);
	Instance inst;
	inst.first = int(byte_of(a.r) | (byte_of(a.g) << 8u) | (byte_of(a.b) << 16u));
	inst.recipe = int(byte_of(a.a));
	inst.count = int(byte_of(b.r) | (byte_of(b.g) << 8u));
	inst.object_row = int(byte_of(b.b) | (byte_of(b.a) << 8u));
	inst.segment_m = uintBitsToFloat(byte_of(c.r) | (byte_of(c.g) << 8u) | (byte_of(c.b) << 16u) | (byte_of(c.a) << 24u));
	return inst;
}

#ifdef FUEL_INSTANCE
// The instance's fields, fetched once per vertex instead of per fragment (review P-N2), as flat varyings: x first
// row, y count, z object row, w palette slot.
varying flat ivec4 v_instance;
varying flat float v_segment_m;

// Each vertex() sets them from instance_at(INSTANCE_ID): Godot lets only vertex() itself assign a varying.
ivec4 instance_fields(Instance inst) {
	return ivec4(inst.first, inst.count, inst.object_row, inst.recipe);
}

Instance fuel_instance_from_varyings() {
	Instance inst;
	inst.first = v_instance.x;
	inst.count = v_instance.y;
	inst.object_row = v_instance.z;
	inst.recipe = v_instance.w;
	inst.segment_m = v_segment_m;
	return inst;
}
#endif

ivec2 row_at(int row) {
	return ivec2(row % ROW_WIDTH, row / ROW_WIDTH);
}

// The segment row a fragment ``s`` metres along its object reads, clamped to the object's own segments so an end cap
// at s = L never reads the next object's first row (§4.1).
int segment_row(Instance inst, float s) {
	int k = clamp(int(floor(s / inst.segment_m)), 0, inst.count - 1);
	return inst.first + k;
}

bool burnt_out(int object_row) {
	return byte_of(texelFetch(state_tex, row_at(object_row), 0).r) == 1u;
}

bool burnt_through(int row) {
	return texelFetch(thickness_tex, row_at(row), 0).r <= 0.0;
}

// A segment's colour: lit albedo darkened by char, plus glow and the burning term, both off once the object is burnt
// out (§4.3). Glow and burning are HDR, so above 1.0 they drive bloom: brightness, never hue alone (§5).
vec3 fuel_colour(Instance inst, int row, vec3 n_world) {
	float t_c = clamp(texelFetch(temperature_tex, row_at(row), 0).r, FUEL_MIN_C, FUEL_MAX_C);
	float ignited = texelFetch(ignited_tex, row_at(row), 0).r;
	float charred = texelFetch(char_tex, row_at(row), 0).r;
	vec3 albedo = recipe_colours[clamp(inst.recipe, 0, 15)] * (1.0 - FUEL_CHAR_DARKEN * charred);
	vec3 colour = face_lit(albedo, n_world, 1.0);
	if (burnt_out(inst.object_row)) {
		return colour;
	}
	if (t_c > FUEL_GLOW_START_C) {
		colour += glow_curve(t_c, FUEL_GLOW_START_C, clamp((t_c - FUEL_GLOW_START_C) / FUEL_GLOW_SPAN_C, 0.0, 1.0));
	}
	return colour + FLAME_COLOUR * BURN_GAIN * ignited;
}
