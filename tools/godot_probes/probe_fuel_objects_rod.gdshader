shader_type spatial;
render_mode unshaded;

// Per-segment state as data textures, 256 rows wide: row i at (i % 256, i / 256).
uniform sampler2D thickness_tex : filter_nearest, repeat_disable;  // R8, fraction of initial thickness
uniform sampler2D temp_tex : filter_nearest, repeat_disable;       // RH, degrees C
uniform float floor_radius_m = 0.0;  // the pixel floor as a radius in metres

varying float v_seg_row;
varying float v_thick;

ivec2 at(int row) { return ivec2(row % 256, row / 256); }

void vertex() {
	// CylinderMesh: height 1 along local y from -0.5 to 0.5, radius 1. INSTANCE_CUSTOM.r = first row, .g = segment count.
	int first = int(INSTANCE_CUSTOM.r + 0.5);
	int count = int(INSTANCE_CUSTOM.g + 0.5);
	float s = clamp(VERTEX.y + 0.5, 0.0, 0.9999);
	int seg = int(floor(s * float(count)));
	v_seg_row = float(first + seg);
	float th = texelFetch(thickness_tex, at(first + seg), 0).r;
	v_thick = th;
	// Radius in instance units is scaled by the transform (radius r along x and z); floor applied in world metres.
	float r_world = length(MODEL_MATRIX[0].xyz);
	float want = max(r_world * th, th > 0.0 ? floor_radius_m : 0.0);
	VERTEX.xz *= want / max(r_world, 1e-6);
}

void fragment() {
	int row = int(v_seg_row + 0.5);
	float t = texelFetch(temp_tex, at(row), 0).r;
	if (v_thick <= 0.0) { discard; }
	ALBEDO = vec3(clamp(t / 1000.0, 0.0, 1.0), 0.2, 0.2);
}
