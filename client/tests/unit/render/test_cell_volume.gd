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


func test_the_palette_and_the_cut_list_load(t: TestContext) -> void:
	var palette: MaterialPalette = load("res://game/palette.tres") as MaterialPalette
	var by_id: Dictionary[int, Color] = palette.by_id({"air": 0, "concrete": 1, "wood": 4})
	t.check_eq(str(by_id.keys()), str([1, 4]), "air has no colour; concrete and wood do")
	t.check(by_id[4].is_equal_approx(Color(0.55, 0.37, 0.22).srgb_to_linear()), "colours become linear")
	var walls: CutawayRegions = load("res://game/cutaway.tres") as CutawayRegions
	t.check_eq(walls.regions, PackedStringArray(["wall_south", "wall_north", "wall_end"]), "the walls, and never the crate")
