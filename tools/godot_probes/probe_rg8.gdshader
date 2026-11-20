shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled;

uniform highp sampler3D ids : filter_nearest;

void vertex() {
	POSITION = vec4(VERTEX.xy * 2.0, 0.0, 1.0);
}

void fragment() {
	ivec2 p = ivec2(FRAGCOORD.xy);
	int index = p.y * 256 + p.x;
	vec2 rg = texelFetch(ids, ivec3(index % 256, (index / 256) % 16, index / 4096), 0).rg;
	int id = int(round(rg.r * 255.0)) + 256 * int(round(rg.g * 255.0));
	ALBEDO = id == index ? vec3(1.0) : vec3(1.0, 0.0, 0.0);
}
