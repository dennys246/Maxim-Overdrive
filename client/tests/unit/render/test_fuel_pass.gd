extends RefCounted
## The fuel-object pass (addons/engine/render/fuel_pass.gd, fuel_geometry.gd): instances per kind from the fixture,
## the instance texture the shaders decode, transforms through the one axis mapping, rebuilds only on structural
## change, and every uniform it sets declared by both shaders. Headless, so pixels are the goldens' job; this holds
## what the shaders are given.


const REGIONS: Dictionary[int, String] = {}


func _fixture(t: TestContext) -> FuelFixture:
	var f: FuelFixture = FuelFixture.named("fuel_ramp")
	t.check(f.problems.is_empty(), "the fixture loads: %s" % [f.problems])
	return f


func _snap(t: TestContext) -> FuelSnapshot:
	return _fixture(t).snapshot


## A pass that has drawn the fixture once.
func _pass(t: TestContext, f: FuelFixture) -> FuelPass:
	var fuel: FuelPass = FuelPass.new()
	var _problems: Array[String] = fuel.use_palette(f.snapshot.recipe_ids, {1: Color.WHITE, 2: Color.WHITE})
	t.check_eq(fuel.show_fuel(f.snapshot, f.region_names), [] as Array[String], "the fixture draws")
	return fuel


## Instance ``i`` of a MultiMesh buffer as a transform. The tests read the buffers FuelGeometry hands the pass: the
## headless renderer keeps no MultiMesh data, and its get_instance_transform returns identity, which would pass any
## check that a slab's local y is up.
func _xf(buffer: PackedFloat32Array, i: int) -> Transform3D:
	var at: int = i * FuelGeometry.FLOATS
	var basis: Basis = Basis(Vector3(buffer[at], buffer[at + 4], buffer[at + 8]),
		Vector3(buffer[at + 1], buffer[at + 5], buffer[at + 9]), Vector3(buffer[at + 2], buffer[at + 6], buffer[at + 10]))
	return Transform3D(basis, Vector3(buffer[at + 3], buffer[at + 7], buffer[at + 11]))


func test_each_object_is_one_instance_of_its_kind(t: TestContext) -> void:
	var f: FuelFixture = _fixture(t)
	var fuel: FuelPass = _pass(t, f)
	t.check_eq(fuel.rods.multimesh.instance_count, 77, "rods")
	t.check_eq(fuel.slabs.multimesh.instance_count, 2, "slabs")
	fuel.free()


func test_the_instance_texture_carries_exact_rows_past_half_float(t: TestContext) -> void:
	var f: FuelFixture = _fixture(t)
	var snap: FuelSnapshot = f.snapshot
	var fuel: FuelPass = _pass(t, f)
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
	t.check_eq(bytes[at + 3], 0, "pine_rod's palette slot")
	var slab: PackedByteArray = fuel.instance_images["slabs"].get_data()
	t.check_eq(slab[3], 1, "pine_slab's palette slot, its own byte above the first row")
	fuel.free()


func test_a_rod_maps_through_the_one_axis_mapping(t: TestContext) -> void:
	var snap: FuelSnapshot = _snap(t)
	var xf: Transform3D = _xf(FuelGeometry.rod_buffer(snap), 0)
	var origin: Vector3 = Vector3(snap.column("rods", "origin_x_m").decode_float(0),
		snap.column("rods", "origin_y_m").decode_float(0), snap.column("rods", "origin_z_m").decode_float(0))
	var length: float = snap.column("rods", "length_m").decode_float(0)
	t.check(xf.origin.is_equal_approx(IsoCamera.to_godot(origin + Vector3(length * 0.5, 0.0, 0.0))), "the centre")
	t.check(is_equal_approx(xf.basis.y.length(), length), "local y spans the length")
	t.check(xf.basis.determinant() > 0.0, "right-handed, so windings survive")


func test_a_near_vertical_rod_is_built_against_east(t: TestContext) -> void:
	var snap: FuelSnapshot = _snap(t)
	for column: Array in [["rods.axis_x", 0.0], ["rods.axis_z", 1.0]]:
		var bytes: PackedByteArray = snap.columns[column[0]].duplicate()
		var value: float = column[1]
		bytes.encode_float(0, value)
		snap.columns[column[0]] = bytes
	var basis: Basis = _xf(FuelGeometry.rod_buffer(snap), 0).basis
	t.check(basis.y.normalized().is_equal_approx(IsoCamera.to_godot(Vector3(0.0, 0.0, 1.0))), "local y is the axis")
	t.check(absf(basis.x.normalized().dot(basis.y.normalized())) < 1e-6, "across is perpendicular to it")
	t.check(basis.determinant() > 0.0, "right-handed")


func test_a_slabs_segmented_face_is_on_top(t: TestContext) -> void:
	var snap: FuelSnapshot = _snap(t)
	var xf: Transform3D = _xf(FuelGeometry.slab_buffer(snap), 0)
	t.check(xf.basis.y.normalized().is_equal_approx(Vector3.UP), "the length x width normal is Godot's up")
	t.check(is_equal_approx(xf.basis.y.length(), snap.floats("slabs", "thickness_m")[0]), "local y spans the thickness")
	t.check(xf.basis.determinant() > 0.0, "right-handed")


func test_only_a_structural_change_rebuilds(t: TestContext) -> void:
	var f: FuelFixture = _fixture(t)
	var snap: FuelSnapshot = f.snapshot
	var fuel: FuelPass = _pass(t, f)
	var _second: Array[String] = fuel.show_fuel(snap, f.region_names)
	t.check_eq(fuel.rebuilds, 1, "a second frame with the same structure doesn't rebuild")
	var _same: Array[String] = fuel.use_palette(snap.recipe_ids, {1: Color.WHITE, 2: Color.WHITE})
	var _third: Array[String] = fuel.show_fuel(snap, f.region_names)
	t.check_eq(fuel.rebuilds, 1, "nor does the same palette again")
	var state: PackedByteArray = snap.column("objects", "state").duplicate()
	state[0] = 1
	snap.columns["objects.state"] = state
	var hot: PackedByteArray = snap.column("segments", "surface_temperature_c").duplicate()
	hot.encode_half(0, 900.0)
	snap.columns["segments.surface_temperature_c"] = hot
	var _burnt: Array[String] = fuel.show_fuel(snap, f.region_names)
	t.check_eq(fuel.rebuilds, 1, "a burnout and a new temperature don't either")
	var radius: PackedByteArray = snap.column("rods", "radius_m").duplicate()
	radius.encode_float(0, 0.02)
	snap.columns["rods.radius_m"] = radius
	var _grown: Array[String] = fuel.show_fuel(snap, f.region_names)
	t.check_eq(fuel.rebuilds, 2, "new geometry does")
	var renamed: Dictionary[int, String] = f.region_names.duplicate()
	renamed[999] = "annex"
	var _regions: Array[String] = fuel.show_fuel(snap, renamed)
	t.check_eq(fuel.rebuilds, 3, "and so does a new region map, which the structural check reads")
	fuel.free()


## The pass's drawn state: rebuild count, instance counts and the palette uniform, which a refused frame must not move.
func _drawn(fuel: FuelPass) -> Array:
	var material: ShaderMaterial = fuel.rods.material_override
	return [fuel.rebuilds, fuel.rods.multimesh.instance_count, fuel.flames.multimesh.instance_count,
		material.get_shader_parameter(&"recipe_colours")]


func test_a_refused_structure_draws_nothing_new(t: TestContext) -> void:
	var f: FuelFixture = _fixture(t)
	var snap: FuelSnapshot = f.snapshot
	var fuel: FuelPass = _pass(t, f)
	var before: Array = _drawn(fuel)
	var radius: PackedByteArray = snap.column("rods", "radius_m").duplicate()
	radius.encode_float(0, INF)
	snap.columns["rods.radius_m"] = radius
	var found: Array[String] = fuel.show_fuel(snap, f.region_names)
	t.check(found.any(func(p: String) -> bool: return p.contains("rod row 0")), "the structure is refused: %s" % [found])
	t.check_eq(_drawn(fuel), before, "and nothing is rebuilt or recoloured")
	fuel.free()


func test_a_refused_frame_with_a_good_structure_draws_nothing_new(t: TestContext) -> void:
	# The per-frame check runs before any rebuild (review TB2-B1): a state of 2 on an unchanged structure, and an
	# insertion whose segment columns are a row short, are each refused with nothing drawn.
	var f: FuelFixture = _fixture(t)
	var snap: FuelSnapshot = f.snapshot
	var fuel: FuelPass = _pass(t, f)
	var before: Array = _drawn(fuel)
	var state: PackedByteArray = snap.column("objects", "state").duplicate()
	state[0] = 2
	snap.columns["objects.state"] = state
	var _palette: Array[String] = fuel.use_palette(snap.recipe_ids, {1: Color.RED, 2: Color.RED})
	var found: Array[String] = fuel.show_fuel(snap, f.region_names)
	t.check_eq(found, ["object row 0 has state 2; only 0 and 1 are defined"] as Array[String], "a bad state")
	t.check_eq(_drawn(fuel), before, "draws nothing new, the palette included (review TB2-S3)")
	state[0] = 0
	snap.columns["objects.state"] = state
	var counts: PackedByteArray = snap.column("objects", "segment_count").duplicate()
	counts.encode_u16(0, counts.decode_u16(0) + 1)
	snap.columns["objects.segment_count"] = counts
	snap.rows["segments"] += 1
	var grown: Array[String] = fuel.show_fuel(snap, f.region_names)
	t.check(grown.size() == 1 and grown[0].begins_with("segments.surface_temperature_c"), "a short column: %s" % [grown])
	t.check_eq(_drawn(fuel), before, "an insertion refused per frame rebuilds nothing")
	fuel.free()


func test_a_structural_column_edited_in_place_is_checked_again(t: TestContext) -> void:
	# The pass keeps a copy of the structure it drew, not the snapshot's arrays (review TB2-S1).
	var f: FuelFixture = _fixture(t)
	var snap: FuelSnapshot = f.snapshot
	var fuel: FuelPass = _pass(t, f)
	var radius: PackedByteArray = snap.columns["rods.radius_m"]
	radius.encode_float(0, INF)
	snap.columns["rods.radius_m"] = radius
	var found: Array[String] = fuel.show_fuel(snap, f.region_names)
	t.check(found.any(func(p: String) -> bool: return p.contains("rod row 0")), "refused: %s" % [found])
	fuel.free()


func test_every_uniform_the_pass_sets_is_one_both_shaders_declare(t: TestContext) -> void:
	var f: FuelFixture = _fixture(t)
	var fuel: FuelPass = _pass(t, f)
	t.check(fuel.use_pixel_metres(0.01, 1.0).is_empty(), "a positive pixel size and scale are taken")
	fuel.use_flicker(0.0)
	fuel.use_view(FuelPass.View.SHADED)
	# Each shader declares every name but the other kinds' own: the rods' edge fade and the flames' own three.
	var flame_only: Array = [&"flame_flicker", &"flame_height_m", &"segment_object_tex"]
	var not_on: Dictionary[Shader, Array] = {
		FuelPass.ROD_SHADER: flame_only,
		FuelPass.ROD_FRINGE_SHADER: flame_only,
		FuelPass.SLAB_SHADER: flame_only + [&"render_pixel_m"],
		FuelPass.FLAME_SHADER: [&"render_pixel_m"],
	}
	for shader: Shader in not_on:
		var declared: Array[String] = []
		for u: Dictionary in shader.get_shader_uniform_list():
			var uniform_name: String = u["name"]
			declared.append(uniform_name)
		for set_name: StringName in fuel.uniform_names():
			if not_on[shader].has(set_name):
				continue
			t.check(declared.has(String(set_name)), "%s is declared by %s" % [set_name, shader.resource_path])
	t.check_eq(fuel.uniform_names().size(), 13, "all thirteen were set")
	var source: String = FileAccess.get_file_as_string("res://addons/engine/render/fuel_object.gdshaderinc")
	t.check(source.contains("const int ROW_WIDTH = %d;" % FuelPass.ROW_WIDTH), "the row width agrees")
	t.check(source.contains("uniform vec3 recipe_colours[%d];" % FuelPass.PALETTE_SIZE), "the palette size agrees")
	fuel.free()


func test_a_rods_colour_core_then_fade_follow_its_depth_and_get_every_uniform(t: TestContext) -> void:
	var f: FuelFixture = _fixture(t)
	var fuel: FuelPass = _pass(t, f)
	t.check(fuel.use_pixel_metres(0.01, 0.5).is_empty(), "a pixel size")
	var depth: ShaderMaterial = fuel.rods.material_override
	var core: ShaderMaterial = depth.next_pass
	var fade: ShaderMaterial = core.next_pass if core != null else null
	t.check(core != null and core.shader == FuelPass.ROD_FRINGE_SHADER, "the colour's core draws after the depth")
	t.check(fade != null and fade.shader == FuelPass.ROD_FRINGE_SHADER, "and its fade after the core")
	if fade == null:
		fuel.free()
		return
	t.check_eq([core.get_shader_parameter(&"fade_half"), fade.get_shader_parameter(&"fade_half")], [null, true],
		"the core draws coverage 0.5 and up (the shader's default), the fade below it")
	# Every core before any fade, and flames last (review D1, C-S2): priorities, since all of them blend.
	var priorities: Array[int] = [depth.render_priority, core.render_priority, fade.render_priority,
		(fuel.flames.material_override as ShaderMaterial).render_priority]
	t.check_eq(priorities, [0, 1, 2, 3] as Array[int], "depth, core, fade, flames")
	for u: Dictionary in FuelPass.ROD_SHADER.get_shader_uniform_list():
		var uniform_name: StringName = u["name"]
		for colour: ShaderMaterial in [core, fade]:
			t.check_eq(colour.get_shader_parameter(uniform_name), depth.get_shader_parameter(uniform_name),
				"%s is the same on every pass" % uniform_name)
	t.check_eq(fade.get_shader_parameter(&"render_pixel_m"), 0.02, "the fade is one rendered pixel")
	fuel.free()


func test_the_segment_textures_are_the_columns_in_whole_rows(t: TestContext) -> void:
	var f: FuelFixture = _fixture(t)
	var snap: FuelSnapshot = f.snapshot
	var fuel: FuelPass = _pass(t, f)
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
		t.check(not fuel.use_pixel_metres(bad, 1.0).is_empty(), "pixel size %s is refused" % bad)
		t.check(not fuel.use_pixel_metres(0.01, bad).is_empty(), "render scale %s is refused" % bad)
	var problems: Array[String] = fuel.use_palette(snap.recipe_ids, {1: Color.WHITE})
	t.check(problems.any(func(p: String) -> bool: return p.contains("pine_slab")), "a recipe without a colour: %s" % [problems])
	fuel.free()


func test_a_recipe_past_the_palette_draws_magenta_never_a_real_colour(t: TestContext) -> void:
	var f: FuelFixture = _fixture(t)
	var snap: FuelSnapshot = f.snapshot
	var ids: Dictionary[String, int] = {}
	var colours: Dictionary[int, Color] = {}
	for i: int in FuelPass.UNCOLOURED_SLOT:
		ids["filler_%d" % i] = 100 + i
		colours[100 + i] = Color.WHITE
	ids["pine_rod"] = snap.recipe_ids["pine_rod"]
	ids["pine_slab"] = snap.recipe_ids["pine_slab"]
	colours[ids["pine_rod"]] = Color.WHITE  # coloured, so only the reserved slot can draw them magenta
	colours[ids["pine_slab"]] = Color.WHITE
	var fuel: FuelPass = FuelPass.new()
	var problems: Array[String] = fuel.use_palette(ids, colours)
	t.check_eq(problems.size(), 2, "both recipes past the %d real slots are reported: %s" % [FuelPass.UNCOLOURED_SLOT, problems])
	t.check(problems.all(func(p: String) -> bool: return p.contains("past the shader")), "as past the palette")
	t.check_eq(fuel.show_fuel(snap, f.region_names), [] as Array[String], "the frame still draws")
	t.check_eq(fuel.instance_images["rods"].get_data()[3], FuelPass.UNCOLOURED_SLOT, "in the magenta slot")
	var material: ShaderMaterial = fuel.rods.material_override
	var palette: Array = material.get_shader_parameter(&"recipe_colours")
	var magenta: Vector3 = Vector3(FuelPass.UNCOLOURED.r, FuelPass.UNCOLOURED.g, FuelPass.UNCOLOURED.b)
	t.check_eq(palette[FuelPass.UNCOLOURED_SLOT], magenta, "which no recipe's colour takes")
	fuel.free()


func test_each_segment_row_gets_a_flame_at_its_top(t: TestContext) -> void:
	var f: FuelFixture = _fixture(t)
	var snap: FuelSnapshot = f.snapshot
	var fuel: FuelPass = _pass(t, f)
	t.check_eq(fuel.flames.multimesh.instance_count, snap.rows["segments"], "one flame quad per segment row")
	var tops: PackedFloat32Array = FuelGeometry.flame_buffer(snap)
	var top: Transform3D = _xf(tops, 0)
	var origin: Vector3 = Vector3(snap.column("rods", "origin_x_m").decode_float(0),
		snap.column("rods", "origin_y_m").decode_float(0), snap.column("rods", "origin_z_m").decode_float(0))
	var radius: float = snap.column("rods", "radius_m").decode_float(0)
	var want: Vector3 = IsoCamera.to_godot(origin + Vector3(0.01, 0.0, radius))
	t.check(top.origin.is_equal_approx(want), "segment 0's top, half a segment along: %s" % top.origin)
	t.check(is_equal_approx(top.basis.x.length(), FuelGeometry.MIN_ROD_FLAME_M), "a thin stick's flame's least width")
	var slab_row: int = snap.geometry_rows("slab")[0]
	var slab_first: int = snap.first_rows()[slab_row]
	var on_slab: Transform3D = _xf(tops, slab_first)
	t.check(is_equal_approx(on_slab.basis.x.length(), snap.floats("slabs", "width_m")[0]), "a slab's flame spans its width")
	fuel.free()


func test_each_flame_knows_its_object_row(t: TestContext) -> void:
	var snap: FuelSnapshot = _snap(t)
	var rows: PackedFloat32Array = FuelGeometry.segment_objects(snap)
	var first: PackedInt32Array = snap.first_rows()
	t.check_eq(rows.size(), snap.rows["segments"], "one per segment row")
	for row: int in snap.rows["objects"]:
		t.check_eq(int(rows[first[row]]), row, "object %d's first segment" % row)
	t.check_eq(int(rows[rows.size() - 1]), snap.rows["objects"] - 1, "the last segment is the last object's")


func test_culling_boxes_hold_what_the_shaders_draw(t: TestContext) -> void:
	var f: FuelFixture = _fixture(t)
	var snap: FuelSnapshot = f.snapshot
	var fuel: FuelPass = _pass(t, f)
	t.check(fuel.use_pixel_metres(0.01, 0.5).is_empty(), "a pixel size")
	var rods: AABB = fuel.boxes()["rod"]
	var xf: Transform3D = _xf(FuelGeometry.rod_buffer(snap), 0)
	var radius: float = snap.floats("rods", "radius_m")[0]
	for end: float in [-0.5, 0.5]:
		var tip: Vector3 = xf * Vector3(0.0, end, 0.0)
		t.check(rods.grow(1e-6).has_point(tip + xf.basis.x.normalized() * radius), "rod 0's surface at %s is inside" % end)
	t.check(rods.size.length() < 10.0 and rods.has_volume(), "the box is the pile's, not a default: %s" % rods)
	t.check(fuel.rods.custom_aabb.encloses(rods.grow(0.029)), "rods grow by the floor and a two-pixel fade")
	t.check(fuel.use_pixel_metres(0.01, 0.25).is_empty(), "a quarter-scale tier")
	t.check(fuel.rods.custom_aabb.encloses(rods.grow(0.049)), "rods grow by the floor and a four-pixel fade there")
	t.check(fuel.slabs.custom_aabb.encloses(fuel.boxes()["slab"].grow(0.079)), "slabs by their floor")
	var flames: AABB = fuel.flames.custom_aabb
	var tops: PackedFloat32Array = FuelGeometry.flame_buffer(snap)
	for i: int in snap.rows["segments"]:
		var top: Transform3D = _xf(tops, i)
		var reach: float = FuelPass.FLAME_HEIGHT_M * (1.0 + FuelPass.FLICKER_HEIGHT) + 0.5 * top.basis.x.length()
		if not flames.encloses(AABB(top.origin, Vector3.ZERO).grow(reach - 1e-4)):
			t.check(false, "flame %d's quad, a flame's height and half its width round its base, is inside" % i)
			break
	var all: AABB = fuel.boxes()["rod"].merge(fuel.boxes()["slab"])
	t.check(all.grow(1.0).encloses(flames), "and the box is the scene's, not ±1000 m: %s" % flames)
	fuel.free()


func test_flicker_is_bounded_and_its_height_agrees_with_the_shader(t: TestContext) -> void:
	var fuel: FuelPass = FuelPass.new()
	fuel.use_flicker(5.0)
	var material: ShaderMaterial = fuel.flames.material_override
	t.check_eq(material.get_shader_parameter(&"flame_flicker"), 1.0, "an amount past 1 is clamped")
	var source: String = FileAccess.get_file_as_string("res://addons/engine/render/fuel_flame.gdshader")
	t.check(source.contains("flame_flicker * %.1f * sin" % FuelPass.FLICKER_HEIGHT), "the shader's flicker height agrees")
	fuel.free()


func test_bounds_hold_a_turned_unit_box(t: TestContext) -> void:
	var basis: Basis = Basis(Vector3(1.0, 2.0, 0.5).normalized(), 0.7).scaled(Vector3(0.3, 1.5, 0.2))
	var xf: Transform3D = Transform3D(basis, Vector3(4.0, -1.0, 2.0))
	var buffer: PackedFloat32Array = PackedFloat32Array([
		basis.x.x, basis.y.x, basis.z.x, xf.origin.x, basis.x.y, basis.y.y, basis.z.y, xf.origin.y,
		basis.x.z, basis.y.z, basis.z.z, xf.origin.z,
	])
	var half: Vector3 = Vector3(1.0, 0.5, 1.0)
	var want: AABB = AABB(xf.origin, Vector3.ZERO)
	for corner: int in 8:
		var local: Vector3 = Vector3(half.x if corner & 1 else -half.x, half.y if corner & 2 else -half.y,
			half.z if corner & 4 else -half.z)
		want = want.expand(xf * local)
	var got: AABB = FuelGeometry.bounds(buffer, half)
	t.check(got.position.is_equal_approx(want.position) and got.size.is_equal_approx(want.size),
		"the box of a turned, scaled unit box's corners: %s, want %s" % [got, want])
	t.check_eq(FuelGeometry.bounds(PackedFloat32Array(), half), AABB(), "no instances, no box")
