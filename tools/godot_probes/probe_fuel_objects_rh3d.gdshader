shader_type spatial;
render_mode unshaded;

uniform sampler3D t3d : filter_linear, repeat_disable;

void fragment() {
	// 2 x 1 x 1 texture with 0 and 1000: the midpoint between texel centres is u = 0.5.
	float v = textureLod(t3d, vec3(0.5, 0.5, 0.5), 0.0).r;
	ALBEDO = vec3(v / 1000.0);
}
