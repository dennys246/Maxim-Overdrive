// One grey-box voxel. Per-instance data from the MultiMesh: COLOR is the material's shade, INSTANCE_CUSTOM is
// (glow, crack, heat, unused) in 0..1. State never shows by colour alone (CLAUDE.md, client standards): glow adds
// emitted brightness, crack darkens the cube (and voxels.gd shrinks it, a change of shape), heat tints only in the
// H debug view.
shader_type spatial;

uniform bool show_heat = false;

varying vec4 v_custom;

void vertex() {
	v_custom = INSTANCE_CUSTOM;
}

void fragment() {
	float glow = v_custom.x;
	float crack = v_custom.y;
	float heat = v_custom.z;
	vec3 base = COLOR.rgb * (1.0 - 0.55 * crack);
	if (show_heat) {
		base = mix(base, vec3(1.0, 0.25, 0.05), heat * 0.85);
	}
	ALBEDO = base;
	ROUGHNESS = 0.9;
	EMISSION = vec3(1.0, 0.35, 0.08) * glow * 4.0;
}
