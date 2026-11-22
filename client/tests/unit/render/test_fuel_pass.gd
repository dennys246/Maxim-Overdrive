extends RefCounted
## The fuel-object pass (addons/engine/render/fuel_pass.gd, fuel_geometry.gd): instances per kind from the fixture,
## the instance texture the shaders decode, transforms through the one axis mapping, rebuilds only on structural
## change, and every uniform it sets declared by both shaders. Headless, so pixels are the goldens' job; this holds
## what the shaders are given.


func _snap(t: TestContext) -> FuelSnapshot:
	var f: FuelFixture = FuelFixture.named("fuel_ramp")
	t.check(f.problems.is_empty(), "the fixture loads: %s" % [f.problems])
	return f.snapshot


func _pass(snap: FuelSnapshot) -> FuelPass:
	var fuel: FuelPass = FuelPass.new()
	var _problems: Array[String] = fuel.use_palette(snap.recipe_ids, {1: Color.WHITE, 2: Color.WHITE})
	fuel.show_fuel(snap)
	return fuel


func test_each_object_is_one_instance_of_its_kind(t: TestContext) -> void:
	var snap: FuelSnapshot = _snap(t)
	var fuel: FuelPass = _pass(snap)
	t.check_eq(fuel.rods.multimesh.instance_count, 73, "rods")
	t.check_eq(fuel.slabs.multimesh.instance_count, 1, "slabs")
	fuel.free()


func test_the_instance_texture_carries_exact_rows_past_half_float(t: TestContext) -> void:
	var snap: FuelSnapshot = _snap(t)
	var fuel: FuelPass = _pass(snap)
	var image: Image = fuel.instance_images["rods"]
	var bytes: PackedByteArray = image.get_data()
	var first: PackedInt32Array = snap.first_rows()
	var last: int = fuel.rods.multimesh.instance_count - 1
	var at: int = last * FuelPass.INSTANCE_TEXELS * 4
	var object_row: int = bytes.decode_u16(at + 6)
	t.check_eq(image.get_width(), FuelPass.INSTANCE_TEXELS, "three texels per instance")
	t.check_eq(bytes[at] | (bytes[at + 1] << 8) | (bytes[at + 2] << 16), first[object_row], "the first row, exact")
	t.check(first[object_row] > 2048, "a row past where half float is exact")
	t.check_eq(bytes.decode_u16(at + 4), snap.column("objects", "segment_count").decode_u16(object_row * 2), "count")
	t.check(is_equal_approx(bytes.decode_float(at + 8), 0.02), "the segment length's f32 bits")
	fuel.free()


func test_a_rod_maps_through_the_one_axis_mapping(t: TestContext) -> void:
	var snap: FuelSnapshot = _snap(t)
	var xf: Transform3D = FuelGeometry.transform(snap, "rods", 0)
	var origin: Vector3 = Vector3(snap.column("rods", "origin_x_m").decode_float(0),
		snap.column("rods", "origin_y_m").decode_float(0), snap.column("rods", "origin_z_m").decode_float(0))
	var length: float = snap.column("rods", "length_m").decode_float(0)
	t.check(xf.origin.is_equal_approx(IsoCamera.to_godot(origin + Vector3(length * 0.5, 0.0, 0.0))), "the centre")
	t.check(is_equal_approx(xf.basis.y.length(), length), "local y spans the length")
	t.check(xf.basis.determinant() > 0.0, "right-handed, so windings survive")


func test_a_slabs_segmented_face_is_on_top(t: TestContext) -> void:
	var snap: FuelSnapshot = _snap(t)
	var xf: Transform3D = FuelGeometry.transform(snap, "slabs", 0)
	t.check(xf.basis.y.normalized().is_equal_approx(Vector3.UP), "the length x width normal is Godot's up")
	t.check(xf.basis.determinant() > 0.0, "right-handed")


func test_only_a_structural_change_rebuilds(t: TestContext) -> void:
	var snap: FuelSnapshot = _snap(t)
	var fuel: FuelPass = _pass(snap)
	fuel.show_fuel(snap)
	t.check_eq(fuel.rebuilds, 1, "a second frame with the same structure doesn't rebuild")
	var state: PackedByteArray = snap.column("objects", "state").duplicate()
	state[0] = 1
	snap.columns["objects.state"] = state
	var hot: PackedByteArray = snap.column("segments", "surface_temperature_c").duplicate()
	hot.encode_half(0, 900.0)
	snap.columns["segments.surface_temperature_c"] = hot
	fuel.show_fuel(snap)
	t.check_eq(fuel.rebuilds, 1, "a burnout and a new temperature don't either")
	var radius: PackedByteArray = snap.column("rods", "radius_m").duplicate()
	radius.encode_float(0, 0.02)
	snap.columns["rods.radius_m"] = radius
	fuel.show_fuel(snap)
	t.check_eq(fuel.rebuilds, 2, "new geometry does")
	fuel.free()


func test_every_uniform_the_pass_sets_is_one_both_shaders_declare(t: TestContext) -> void:
	var snap: FuelSnapshot = _snap(t)
	var fuel: FuelPass = _pass(snap)
	t.check(fuel.use_pixel_metres(0.01).is_empty(), "a positive pixel size is taken")
	for shader: Shader in [FuelPass.ROD_SHADER, FuelPass.SLAB_SHADER]:
		var declared: Array[String] = []
		for u: Dictionary in shader.get_shader_uniform_list():
			var uniform_name: String = u["name"]
			declared.append(uniform_name)
		for set_name: StringName in fuel.uniform_names():
			t.check(declared.has(String(set_name)), "%s is declared by %s" % [set_name, shader.resource_path])
	t.check_eq(fuel.uniform_names().size(), 8, "all eight were set")
	var source: String = FileAccess.get_file_as_string("res://addons/engine/render/fuel_object.gdshaderinc")
	t.check(source.contains("const int ROW_WIDTH = %d;" % FuelPass.ROW_WIDTH), "the row width agrees")
	t.check(source.contains("uniform vec3 recipe_colours[%d];" % FuelPass.PALETTE_SIZE), "the palette size agrees")
	fuel.free()


func test_the_segment_textures_are_the_columns_in_whole_rows(t: TestContext) -> void:
	var snap: FuelSnapshot = _snap(t)
	var fuel: FuelPass = _pass(snap)
	var material: ShaderMaterial = fuel.rods.material_override
	var temperature: ImageTexture = material.get_shader_parameter(&"temperature_tex")
	t.check_eq(temperature.get_format(), Image.FORMAT_RH, "half floats, as the column arrives")
	t.check_eq(temperature.get_height(), ceili(snap.rows["segments"] / float(FuelPass.ROW_WIDTH)), "whole rows")
	t.check_eq(temperature.get_width(), FuelPass.ROW_WIDTH, "row width")
	fuel.free()


func test_a_bad_pixel_size_and_a_missing_colour_are_reported(t: TestContext) -> void:
	var snap: FuelSnapshot = _snap(t)
	var fuel: FuelPass = FuelPass.new()
	for bad: float in [0.0, -1.0, NAN, INF]:
		t.check(not fuel.use_pixel_metres(bad).is_empty(), "pixel size %s is refused" % bad)
	var problems: Array[String] = fuel.use_palette(snap.recipe_ids, {1: Color.WHITE})
	t.check(problems.any(func(p: String) -> bool: return p.contains("pine_slab")), "a recipe without a colour: %s" % [problems])
	fuel.free()
