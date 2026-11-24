extends RefCounted
## The golden scene's shot argument and its drawability checks (tests/support/golden_shot.gd): every refusal, tested
## headless, since the scene itself needs a display the gate's runner lacks.


func test_a_good_shot_parses(t: TestContext) -> void:
	var shot: GoldenShot = GoldenShot.parse("alley_fire:rig:crack_mask:/tmp/out/x.png")
	t.check_eq(shot.problem, "", "no problem")
	t.check_eq([shot.fixture, shot.tier, shot.png], ["alley_fire", "rig", "/tmp/out/x.png"], "fields")
	t.check_eq(shot.pass_kind, CellVolume.Pass.CRACK_MASK, "pass")


func test_every_malformed_shot_is_refused(t: TestContext) -> void:
	for bad: String in ["", "alley_fire:rig:shaded", ":rig:shaded:/x.png", "alley_fire::shaded:/x.png",
			"alley_fire:rig:shaded:", "alley_fire:rig:sepia:/x.png", "alley_fire:rig:shaded:relative.png",
			"alley_fire+:rig:shaded:/x.png", "+fuel_ramp:rig:shaded:/x.png", "a+b+c:rig:shaded:/x.png",
			"alley_fire:rig:fuel_mask:/x.png", "alley_fire:rig:shaded_noflame:/x.png"]:
		t.check(not GoldenShot.parse(bad).problem.is_empty(), "refused: '%s'" % bad)


func test_an_undrawable_fixture_or_tier_is_refused(t: TestContext) -> void:
	var good: SnapshotFixture = SnapshotFixture.named("alley_fire")
	var rig: RenderTier = load("res://game/tiers/rig.tres") as RenderTier
	t.check_eq(GoldenShot.usable(good, rig, 1), "", "the committed fixture at rig")
	t.check(GoldenShot.usable(SnapshotFixture.named("missing"), rig, 1).begins_with("fixture: "), "a missing fixture")
	t.check_eq(GoldenShot.usable(good, null, 1), "no usable tier", "an unknown tier")
	t.check(GoldenShot.usable(good, RenderTier.new(), 1) == "no usable tier", "an invalid tier")
	t.check(GoldenShot.usable(good, rig, 9).contains("no player"), "no player actor")
	var renamed: SnapshotFixture = SnapshotFixture.named("alley_fire")
	renamed.snapshot.region_names[5] = "box"
	t.check(GoldenShot.usable(renamed, rig, 1).contains("no crate region"), "no crate to centre on")


func test_a_fuel_shot_names_its_fuel_fixture_and_view(t: TestContext) -> void:
	var shot: GoldenShot = GoldenShot.parse("alley_cold+fuel_ramp:laptop:flame_mask:/tmp/f.png")
	t.check_eq(shot.problem, "", "no problem")
	t.check_eq([shot.fixture, shot.fuel, shot.fuel_view, shot.flames], ["alley_cold", "fuel_ramp", FuelPass.View.FLAME_ID, true], "fields")
	t.check_eq(shot.pass_kind, CellVolume.Pass.OCCLUDER, "the cells occlude in a mask")
	var masked: GoldenShot = GoldenShot.parse("alley_cold+fuel_ramp:rig:fuel_mask:/tmp/f.png")
	t.check_eq([masked.fuel_view, masked.flames], [FuelPass.View.FUEL_ID, false], "the fuel mask draws no flames")
	t.check_eq(GoldenShot.parse("alley_cold+fuel_ramp:rig:shaded_noflame:/tmp/f.png").flames, false, "no flames")
	t.check_eq(GoldenShot.parse("alley_fire:rig:shaded:/tmp/f.png").fuel, "", "no fuel by default")
	for cell_mask: String in GoldenShot.CELL_MASKS:
		var mixed: GoldenShot = GoldenShot.parse("alley_cold+fuel_ramp:rig:%s:/tmp/f.png" % cell_mask)
		t.check(mixed.problem.contains("measures cells"), "a fuel fixture in the %s is refused" % cell_mask)
	var update: GoldenShot = GoldenShot.parse("alley_cold+fuel_ramp:rig:shaded_update:/tmp/f.png")
	t.check_eq([update.update, update.flames, update.pass_kind], [true, false, CellVolume.Pass.SHADED], "the update pass")
	t.check(not GoldenShot.parse("alley_cold+fuel_ramp:rig:shaded:/tmp/f.png").update, "only that pass updates")
	t.check(GoldenShot.parse("alley_cold:rig:shaded_update:/tmp/f.png").problem.contains("needs a <cells>+<fuel>"),
		"the update pass needs a fuel fixture")
	t.check(GoldenShot.fuel_usable(FuelFixture.named("fuel_ramp" + GoldenShot.NEXT_SUFFIX)).is_empty(), "its next frame loads")


func test_an_undrawable_fuel_fixture_is_refused(t: TestContext) -> void:
	t.check_eq(GoldenShot.fuel_usable(FuelFixture.named("fuel_ramp")), "", "the committed fuel fixture")
	t.check(GoldenShot.fuel_usable(FuelFixture.named("missing")).begins_with("fuel fixture: "), "a missing one")


func test_the_update_frame_must_reach_the_pass_steady(t: TestContext) -> void:
	var first: FuelFixture = FuelFixture.named("fuel_ramp")
	var fuel: FuelPass = FuelPass.new()
	var _p: Array[String] = fuel.use_palette(first.snapshot.recipe_ids, {1: Color.WHITE, 2: Color.WHITE})
	t.check_eq(fuel.show_fuel(first.snapshot, first.region_names), [] as Array[String], "the first frame draws")
	var next: FuelFixture = FuelFixture.named("fuel_ramp" + GoldenShot.NEXT_SUFFIX)
	var steady: Callable = func() -> Array[String]: return fuel.show_fuel(next.snapshot, next.region_names)
	t.check_eq(GoldenShot.show_steady(fuel, steady), "", "the committed next frame is steady")
	var other: FuelFixture = FuelFixture.named("fuel_stick")
	var rebuilt: Callable = func() -> Array[String]: return fuel.show_fuel(other.snapshot, other.region_names)
	t.check_eq(GoldenShot.show_steady(fuel, rebuilt), "the next frame rebuilt the fuel pass; it must be a steady frame",
		"another structure rebuilds")
	var refused: Callable = func() -> Array[String]: return ["bad"] as Array[String]
	t.check_eq(GoldenShot.show_steady(fuel, refused), "fuel next: bad", "a refused frame")
	fuel.free()
