extends Node
## The renderer goldens and the never-colour-alone frames (client_rendering.md §6), drawn from snapshot fixtures,
## never a live server. Each ``--shot=`` after ``--`` (GoldenShot states the grammar) draws one frame at the golden
## camera (§1: yaw 45, size 10 m, centred on the crate, 1280 x 720) and saves it; scripts/golden_run.py names the
## shots and judges them. The cut is the one the fixture's player (actor 1) would see. Flicker, particles and
## cross-fade are off (§6.1). It needs a real GL context (Xvfb in CI): under --headless it refuses at once, since
## the capture's await would never return.
## Engine why: the root is a plain Node because it only orchestrates; the drawing happens in the RenderStage, a
## SubViewport.

const SHOT_FLAG: String = "--shot="
const WIDTH: int = 1280
const HEIGHT: int = 720
const SIZE_M: float = 10.0
const PLAYER: int = 1
const PALETTE: MaterialPalette = preload("res://game/palette.tres")
const WALLS: CutawayRegions = preload("res://game/cutaway.tres")
const RECIPES: MaterialPalette = preload("res://game/recipe_palette.tres")

var _stage: RenderStage = RenderStage.new()
var _fixtures: Dictionary[String, SnapshotFixture] = {}
var _fuel_fixtures: Dictionary[String, FuelFixture] = {}


func _ready() -> void:
	if DisplayServer.get_name() == "headless":
		# Measured on 4.7.2: under --headless frame_post_draw never fires, so the capture would hang.
		_fail("--headless draws nothing; run under a display (Xvfb in CI)")
		return
	var shots: Array[String] = _shots()
	if shots.is_empty():
		_fail("pass the shots after --: -- %s<shot> ..., each as GoldenShot parses" % SHOT_FLAG)
		return
	_stage.size = Vector2i(WIDTH, HEIGHT)
	add_child(_stage)
	for shot: String in shots:
		var why: String = await _draw(shot)
		if not why.is_empty():
			_fail("%s: %s" % [shot, why])
			return
	get_tree().quit(0)


## Draws one shot; returns why it failed, or "".
func _draw(text: String) -> String:
	var shot: GoldenShot = GoldenShot.parse(text)
	if not shot.problem.is_empty():
		return shot.problem
	var fixture: SnapshotFixture = _fixture(shot.fixture)
	var tier: RenderTier = load("res://game/tiers/%s.tres" % shot.tier) as RenderTier
	var why: String = GoldenShot.usable(fixture, tier, PLAYER)
	if not why.is_empty():
		return why
	var fuel: FuelFixture = null
	if not shot.fuel.is_empty():
		fuel = _fuel_fixture(shot.fuel)
		why = GoldenShot.fuel_usable(fuel)
		if not why.is_empty():
			return why
	_stage.show_snapshot(fixture.snapshot, PALETTE)
	var fuel_regions: Dictionary[int, String] = {}
	if fuel != null:
		fuel_regions = fuel.region_names
	var refused: Array[String] = _stage.show_fuel(fuel.snapshot if fuel != null else null, fuel_regions, RECIPES)
	if not refused.is_empty():
		return "fuel: " + "; ".join(refused)
	_stage.use_fuel_view(shot.fuel_view, shot.flames)
	_stage.use_tier(tier)
	var yaw: float = IsoCamera.step_yaw(0)
	_stage.aim(_stage.volume_bounds_m("crate").get_center(), yaw, SIZE_M)
	_stage.cut_for(fixture.actors[PLAYER], yaw, WALLS)
	var feet: Array[Vector3] = []
	feet.assign(fixture.actors.values())
	_stage.place_bodies(feet)
	_stage.use_pass(shot.pass_kind, tier.bloom)
	if shot.update:
		why = await _show_next(shot.fuel)
		if not why.is_empty():
			return why
	var image: Image = await _stage.capture()
	if image == null or image.get_width() != WIDTH or image.get_height() != HEIGHT:
		return "no %dx%d frame" % [WIDTH, HEIGHT]
	var err: Error = image.save_png(shot.png)
	if err != OK:
		return "save_png failed: %s" % error_string(err)
	if fuel != null:
		why = _write_footprints(fuel.snapshot, shot.png)
		if not why.is_empty():
			return why
	print("golden: wrote %s adapter=%s" % [shot.png, RenderingServer.get_video_adapter_name()])
	return ""


## The update pass: the frame drawn so far renders, then the fuel fixture's next frame replaces it, which must reach
## the pass as a steady frame (no rebuild), so what is captured next shows the in-place segment upload.
func _show_next(fuel_name: String) -> String:
	var _first: Image = await _stage.capture()
	var next: FuelFixture = _fuel_fixture(fuel_name + GoldenShot.NEXT_SUFFIX)
	var why: String = GoldenShot.fuel_usable(next)
	if not why.is_empty():
		return why
	var show: Callable = func() -> Array[String]: return _stage.show_fuel(next.snapshot, next.region_names, RECIPES)
	return GoldenShot.show_steady(_stage.fuel, show)


## Each fixture is read once per run, so its snapshot object, and the region bounds the stage keeps for it, are
## shared by every shot that draws it.
func _fixture(fixture_name: String) -> SnapshotFixture:
	if not _fixtures.has(fixture_name):
		_fixtures[fixture_name] = SnapshotFixture.named(fixture_name)
	return _fixtures[fixture_name]


func _fuel_fixture(fixture_name: String) -> FuelFixture:
	if not _fuel_fixtures.has(fixture_name):
		_fuel_fixtures[fixture_name] = FuelFixture.named(fixture_name)
	return _fuel_fixtures[fixture_name]


## Each segment's footprint, projected by the camera that drew the frame, beside the PNG: <png>.segments.json.
func _write_footprints(snap: FuelSnapshot, png: String) -> String:
	var rows: Array[Array] = FuelFootprints.of(snap, _stage.camera, SIZE_M / HEIGHT)
	var file: FileAccess = FileAccess.open(png.get_basename() + ".segments.json", FileAccess.WRITE)
	if file == null:
		return "cannot write the footprints: %s" % error_string(FileAccess.get_open_error())
	if not file.store_string(JSON.stringify(rows)):
		return "the footprints didn't write"
	file.close()
	return ""


func _shots() -> Array[String]:
	var out: Array[String] = []
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with(SHOT_FLAG):
			out.append(arg.substr(SHOT_FLAG.length()))
	return out


func _fail(why: String) -> void:
	push_error("golden: " + why)
	get_tree().quit(1)
