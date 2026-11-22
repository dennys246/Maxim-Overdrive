extends Node
## The renderer goldens and the never-colour-alone frames (client_rendering.md §6), drawn from snapshot fixtures,
## never a live server. Each ``--shot=<fixture>:<tier>:<pass>:<png>`` after ``--`` draws one frame at the golden
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

var _stage: RenderStage = RenderStage.new()
var _fixtures: Dictionary[String, SnapshotFixture] = {}


func _ready() -> void:
	if DisplayServer.get_name() == "headless":
		# Measured on 4.7.2: under --headless frame_post_draw never fires, so the capture would hang.
		_fail("--headless draws nothing; run under a display (Xvfb in CI)")
		return
	var shots: Array[String] = _shots()
	if shots.is_empty():
		_fail("pass the shots after --: -- %s<fixture>:<tier>:<pass>:<png> ..." % SHOT_FLAG)
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
	_stage.show_snapshot(fixture.snapshot, PALETTE)
	_stage.use_tier(tier)
	var yaw: float = IsoCamera.step_yaw(0)
	_stage.aim(_stage.volume_bounds_m("crate").get_center(), yaw, SIZE_M)
	_stage.cut_for(fixture.actors[PLAYER], yaw, WALLS)
	var feet: Array[Vector3] = []
	feet.assign(fixture.actors.values())
	_stage.place_bodies(feet)
	_stage.use_pass(shot.pass_kind, tier.bloom)
	var image: Image = await _stage.capture()
	if image == null or image.get_width() != WIDTH or image.get_height() != HEIGHT:
		return "no %dx%d frame" % [WIDTH, HEIGHT]
	var err: Error = image.save_png(shot.png)
	if err != OK:
		return "save_png failed: %s" % error_string(err)
	print("golden: wrote %s adapter=%s" % [shot.png, RenderingServer.get_video_adapter_name()])
	return ""


## Each fixture is read once per run, so its snapshot object, and the region bounds the stage keeps for it, are
## shared by every shot that draws it.
func _fixture(fixture_name: String) -> SnapshotFixture:
	if not _fixtures.has(fixture_name):
		_fixtures[fixture_name] = SnapshotFixture.named(fixture_name)
	return _fixtures[fixture_name]


func _shots() -> Array[String]:
	var out: Array[String] = []
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with(SHOT_FLAG):
			out.append(arg.substr(SHOT_FLAG.length()))
	return out


func _fail(why: String) -> void:
	push_error("golden: " + why)
	get_tree().quit(1)
