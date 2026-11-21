extends Node
## The cut-away test's frames (client_rendering.md §2, step 8): at sampled positions along both side walls, by the end
## wall, around the crate and on the pavement, at all four yaws, the player's body is drawn in its ID colour twice in
## the occluder pass: with the cut the rule chose, and with every flagged wall cut away entirely (the crate and floor
## still drawn). scripts/golden_measures.py::cutaway_report divides the body's pixels in the first by those in the
## second and requires >= 95% at every sample: the walls the rule leaves standing must hide almost nothing. Each pair is saved as
## cut-<sample>-k<yaw step>-with.png and -without.png in the directory after ``--out=``.
## The camera follows the player as in play (centred on the body, the default 12 m zoom, §1), on the cold alley.
## Engine why: the root only orchestrates; RenderStage (a SubViewport) draws, at a resolution of its own.

const OUT_FLAG: String = "--out="
## One yaw step per run, so each Godot call draws a quarter of the frames: drawn in one call, 144 frames on llvmpipe
## under emulation crossed the job's 120 s timeout.
const YAW_FLAG: String = "--yaw="
const WIDTH: int = 960
const HEIGHT: int = 540
const SIZE_M: float = 12.0
const FIXTURE: String = "alley_cold"
const WALLS: CutawayRegions = preload("res://game/cutaway.tres")
const PALETTE: MaterialPalette = preload("res://game/palette.tres")
const TIER: RenderTier = preload("res://game/tiers/rig.tres")
## The body's axis 0.25 m from a wall's face (touching it), along both side walls, at the end wall, and at the
## crate: where the exit script kindles it from (5.5, 2.925), and against its south and east faces. Feet on the
## floor's top. Positions avoid the crates, whose 0.6 m boxes leave no room for a 0.5 m body against a wall. The
## pavement samples (x < 1.2 m, the spawn among them) are off the walls' ends, where every proxy-point rule failed;
## the two strip samples stand level with a wall's thickness, beside its end.
## scripts/golden_measures.py::CUTAWAY_SAMPLES must name the same samples; a test holds the two lists together.
const SAMPLES: Dictionary[String, Vector3] = {
	"south-2": Vector3(2.0, 0.65, 0.4), "south-4": Vector3(4.0, 0.65, 0.4),
	"south-7.5": Vector3(7.5, 0.65, 0.4), "south-10.5": Vector3(10.5, 0.65, 0.4),
	"north-2": Vector3(2.0, 3.35, 0.4), "north-4": Vector3(4.0, 3.35, 0.4),
	"north-7.5": Vector3(7.5, 3.35, 0.4), "north-10.5": Vector3(10.5, 3.35, 0.4),
	"end": Vector3(11.35, 2.0, 0.4),
	"crate-kindle": Vector3(5.5, 2.925, 0.4), "crate-south": Vector3(6.3, 2.35, 0.4),
	"crate-east": Vector3(6.85, 2.9, 0.4),
	"pavement-spawn": Vector3(0.6, 2.0, 0.4), "pavement-south": Vector3(0.9, 0.65, 0.4),
	"pavement-north": Vector3(0.9, 3.35, 0.4),
	"pavement-strip-south": Vector3(0.9, 0.3, 0.4), "pavement-strip-north": Vector3(0.9, 3.7, 0.4),
	"corner-south": Vector3(11.35, 0.65, 0.4), "corner-north": Vector3(11.35, 3.35, 0.4),
}

var _stage: RenderStage = RenderStage.new()


func _ready() -> void:
	if DisplayServer.get_name() == "headless":
		_fail("--headless draws nothing; run under a display (Xvfb in CI)")
		return
	var out: String = _arg(OUT_FLAG)
	var yaw_text: String = _arg(YAW_FLAG)
	if out.is_empty() or not (yaw_text in ["0", "1", "2", "3"]):
		_fail("pass the output directory and a yaw step after --: -- %s<dir> %s<0-3>" % [OUT_FLAG, YAW_FLAG])
		return
	var k: int = yaw_text.to_int()
	var fixture: SnapshotFixture = SnapshotFixture.named(FIXTURE)
	if not fixture.problems.is_empty():
		_fail("fixture: " + "; ".join(fixture.problems))
		return
	_stage.size = Vector2i(WIDTH, HEIGHT)
	add_child(_stage)
	_stage.show_snapshot(fixture.snapshot, PALETTE)
	_stage.use_tier(TIER)
	_stage.use_pass(CellVolume.Pass.OCCLUDER, false)
	for sample: String in SAMPLES:
		var why: String = await _pair(out, sample, k)
		if not why.is_empty():
			_fail(why)
			return
	print("cutaway: wrote %d pairs at yaw step %d" % [SAMPLES.size(), k])
	get_tree().quit(0)


func _pair(out: String, sample: String, k: int) -> String:
	var feet: Vector3 = SAMPLES[sample]
	var yaw: float = IsoCamera.step_yaw(k)
	_stage.aim(feet + Vector3(0.0, 0.0, RenderStage.BODY_HEIGHT_M * 0.5), yaw, SIZE_M)
	_stage.cut_for(feet, yaw, WALLS)
	_stage.place_bodies([feet])
	for chosen: bool in [true, false]:
		if not chosen:
			_stage.cut_all(WALLS)
		var image: Image = await _stage.capture()
		if image == null:
			return "no frame for %s at step %d" % [sample, k]
		var path: String = out.path_join("cut-%s-k%d-%s.png" % [sample, k, "with" if chosen else "without"])
		var err: Error = image.save_png(path)
		if err != OK:
			return "save_png(%s) failed: %s" % [path, error_string(err)]
	return ""


func _arg(flag: String) -> String:
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with(flag):
			return arg.substr(flag.length())
	return ""


func _fail(why: String) -> void:
	push_error("cutaway: " + why)
	get_tree().quit(1)
