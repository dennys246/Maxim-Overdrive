extends RefCounted
## The volume node (render/cell_volume.gd) and the client data it reads: a snapshot sizes the box and sets every
## uniform the shader reads, a tier picks the shader variant, and the tier and palette files load as specified
## (client_rendering.md §5.5).


func test_a_snapshot_sizes_the_box_and_sets_the_uniforms(t: TestContext) -> void:
	var snap: CellSnapshot = SnapshotFixture.named("alley_fire").snapshot
	var volume: CellVolume = CellVolume.new()
	volume.show_snapshot(snap)
	var box: BoxMesh = volume.mesh
	t.check(box.size.is_equal_approx(Vector3(12.0, 4.8, 4.0)), "box: %s (x, height, depth)" % [box.size])
	t.check(volume.position.is_equal_approx(Vector3(6.0, 2.4, -2.0)), "centred over the world box: %s" % [volume.position])
	t.check_eq(volume.uniform(&"cells"), Vector3i(120, 40, 48), "cells")
	t.check(volume.uniform(&"glow_scale_c") is float, "the glow calibration is set")
	for texture: StringName in [&"material_tex", &"region_tex", &"crack_tex", &"glow_tex", &"burning_tex", &"bricks_tex"]:
		t.check(volume.uniform(texture) is ImageTexture3D, "%s is a 3-D texture" % texture)
	volume.use_cut(PackedInt32Array([2, 4]), 0.7)
	t.check_eq(volume.uniform(&"cut_ids"), PackedInt32Array([2, 4, 0, 0, 0, 0, 0, 0]), "cut ids padded to 8")
	t.check_eq(volume.uniform(&"cut_count"), 2, "cut count")
	volume.use_pass(CellVolume.Pass.GLOW_MASK)
	t.check_eq(volume.uniform(&"debug_mode"), 3, "the pass number the shader's debug include reads")
	volume.free()


func test_a_second_snapshot_updates_the_textures_in_place(t: TestContext) -> void:
	var volume: CellVolume = CellVolume.new()
	volume.show_snapshot(SnapshotFixture.named("alley_cold").snapshot)
	var crack_tex: ImageTexture3D = volume.uniform(&"crack_tex")
	var bricks_tex: ImageTexture3D = volume.uniform(&"bricks_tex")
	volume.show_snapshot(SnapshotFixture.named("alley_fire").snapshot)
	var crack_again: ImageTexture3D = volume.uniform(&"crack_tex")
	var bricks_again: ImageTexture3D = volume.uniform(&"bricks_tex")
	t.check(crack_again == crack_tex, "the same shape reuses the crack texture")
	t.check(bricks_again == bricks_tex, "and the bricks texture")
	volume.show_snapshot(_tiny())
	var resized: ImageTexture3D = volume.uniform(&"crack_tex")
	t.check(resized != crack_tex, "a new shape allocates a new texture")
	t.check_eq([resized.get_width(), resized.get_height(), resized.get_depth()], [2, 3, 4], "at the new shape")
	volume.free()


## A drawable 2 x 3 x 4 snapshot of air.
func _tiny() -> CellSnapshot:
	var snap: CellSnapshot = CellSnapshot.new()
	snap.nx = 2
	snap.ny = 3
	snap.nz = 4
	snap.cell_m = 0.1
	snap.glow_scale_c_per_count = 1.0
	snap.material_ids = {"air": 0}
	for channel: String in CellSnapshot.CHANNEL_BYTES:
		var bytes: PackedByteArray = PackedByteArray()
		var _ok: int = bytes.resize(snap.cells() * CellSnapshot.CHANNEL_BYTES[channel])
		snap.channels[channel] = bytes
	return snap


func test_the_crack_octave_keeps_polygons_wide_and_holds_at_a_boundary(t: TestContext) -> void:
	# 12 px of 0.01389 m (the golden view) is 0.167 m: one octave up from a 0.1 m cell.
	t.check_eq(CellVolume.crack_octave(0.1, 10.0 / 720.0, -1), 1, "the golden view")
	t.check_eq(CellVolume.crack_octave(0.1, 10.0 / 360.0, -1), 2, "the laptop tier's half resolution")
	t.check_eq(CellVolume.crack_octave(0.1, 0.005, -1), 0, "zoomed in: one polygon per cell")
	# The default 12 m view at 720 px is exactly 2 octaves: rounding must not flip it, whichever side it lands.
	for current: int in [1, 2]:
		t.check_eq(CellVolume.crack_octave(0.1, 12.0 / 720.0, current), current, "holds %d on the boundary" % current)
	t.check_eq(CellVolume.crack_octave(0.1, 12.0 / 720.0 * 1.2, 1), 2, "moves on once well past it")
	var volume: CellVolume = CellVolume.new()
	volume.show_snapshot(SnapshotFixture.named("alley_cold").snapshot)
	volume.use_pixel_metres(10.0 / 720.0)
	var spacing: float = volume.uniform(&"crack_spacing_m")
	t.check(is_equal_approx(spacing, 0.2), "the uniform carries the spacing: %s" % spacing)
	volume.free()


func test_the_tiers_load_as_specified(t: TestContext) -> void:
	var want: Dictionary[String, Array] = {
		"laptop": [0.5, 2, false, false, 0, 64], "rig": [1.0, 4, true, true, 4, 256], "max": [1.0, 8, true, true, 8, 1024],
	}
	var volume: CellVolume = CellVolume.new()
	for tier_name: String in want:
		var tier: RenderTier = load("res://game/tiers/%s.tres" % tier_name) as RenderTier
		t.check(tier != null and tier.problems().is_empty(), "%s loads cleanly" % tier_name)
		if tier == null:
			continue
		var got: Array = [tier.scaling_3d_scale, tier.crack_substeps, tier.glow_linear, tier.bloom, tier.ao_taps, tier.flame_particles]
		t.check_eq(got, want[tier_name], tier_name)
		volume.use_tier(tier)
		var variant: Shader = CellVolume.SHADER_LINEAR if tier.glow_linear else CellVolume.SHADER_NEAREST
		t.check(volume.shader() == variant, "%s draws with its glow sampler variant" % tier_name)
	volume.free()


func test_a_bad_tier_is_refused(t: TestContext) -> void:
	var tier: RenderTier = RenderTier.new()
	t.check_eq(str(tier.problems()), str(["no tier_name"]), "a nameless tier")
	tier.tier_name = "bad"
	tier.scaling_3d_scale = 0.0
	tier.crack_substeps = 0
	tier.ao_taps = 6
	tier.flame_particles = -1
	t.check_eq(tier.problems().size(), 4, "each bad field: %s" % [tier.problems()])


func test_every_uniform_the_node_sets_is_one_the_shader_declares(t: TestContext) -> void:
	# set_shader_parameter caches any name, so reading a value back proves nothing; the shader's own list does.
	var volume: CellVolume = CellVolume.new()
	volume.show_snapshot(SnapshotFixture.named("alley_fire").snapshot)
	volume.use_tier(load("res://game/tiers/max.tres") as RenderTier)
	volume.use_palette({"air": 0}, {})
	volume.use_cut(PackedInt32Array(), 0.7)
	volume.use_pixel_metres(0.01)
	volume.use_pass(CellVolume.Pass.SHADED)
	volume.use_flicker(0.0)
	for variant: Shader in [CellVolume.SHADER_LINEAR, CellVolume.SHADER_NEAREST]:
		var declared: Dictionary[String, String] = {}
		for u: Dictionary in variant.get_shader_uniform_list():
			var uniform_name: String = u["name"]
			var hint: String = u["hint_string"]
			declared[uniform_name] = hint
		t.check(declared.size() >= 20, "the uniform list is readable headless: %d" % declared.size())
		for set_name: StringName in volume.uniform_names():
			t.check(declared.has(String(set_name)), "%s is declared by %s" % [set_name, variant.resource_path])
	var source: String = FileAccess.get_file_as_string("res://addons/engine/render/lighting.gdshaderinc")
	t.check(source.contains("uniform vec3 palette[%d];" % CellVolume.PALETTE_SIZE), "the palette size agrees")
	t.check(source.contains("clamp(material, 0, %d)" % (CellVolume.PALETTE_SIZE - 1)), "the palette clamp agrees")
	var cut_source: String = FileAccess.get_file_as_string("res://addons/engine/render/cutaway.gdshaderinc")
	t.check(cut_source.contains("uniform int cut_ids[%d];" % Cutaway.MAX_CUT), "the cut list size agrees")
	t.check(cut_source.contains("i < %d; i++" % Cutaway.MAX_CUT), "the cut loop bound agrees")
	var walk: String = FileAccess.get_file_as_string("res://addons/engine/render/traversal.gdshaderinc")
	t.check(walk.contains("const int BRICK = %d;" % VolumeTextures.BRICK), "the brick size agrees")
	volume.free()


func test_the_palette_and_the_cut_list_load(t: TestContext) -> void:
	var palette: MaterialPalette = load("res://game/palette.tres") as MaterialPalette
	var by_id: Dictionary[int, Color] = palette.by_id({"air": 0, "concrete": 1, "wood": 4})
	t.check_eq(str(by_id.keys()), str([1, 4]), "air has no colour; concrete and wood do")
	t.check(by_id[4].is_equal_approx(Color(0.55, 0.37, 0.22).srgb_to_linear()), "colours become linear")
	var walls: CutawayRegions = load("res://game/cutaway.tres") as CutawayRegions
	t.check_eq(walls.regions, PackedStringArray(["wall_south", "wall_north", "wall_end"]), "the walls, and never the crate")
	var volume: CellVolume = CellVolume.new()
	volume.use_palette({"air": 0, "concrete": 1, "wood": 4}, by_id)
	var colours: PackedVector3Array = volume.uniform(&"palette")
	t.check(colours[4].is_equal_approx(Vector3(by_id[4].r, by_id[4].g, by_id[4].b)), "wood's colour at id 4")
	t.check_eq(colours[2], Vector3(1, 0, 1), "an id outside the vocabulary draws magenta, never black")
	volume.free()
