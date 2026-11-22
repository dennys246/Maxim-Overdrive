extends Node
## The stick-stability check's frames (docs/design/client_objects.md §7.2; the parameters are step 8's checklist's):
## the lone 20 mm stick (fuel fixture fuel_stick) in the fuel-ID view, at 72 and 30 px/m on the rig and laptop tiers,
## each at 8 camera offsets of k/8 output px on both screen axes. Writes stab-<tier>-<px per m>-<k>.png and
## stability.json (each frame's projected stick ends, and its drawn width) into the directory after ``--out=``;
## scripts/golden_run.py judges them with scripts/golden_stability.py. Needs a display (Xvfb in CI).
## Engine why: the root is a plain Node because it only orchestrates; the drawing happens in the RenderStage.

const OUT_FLAG: String = "--out="
const WIDTH: int = 1280
const HEIGHT: int = 720
const FIXTURE: String = "fuel_stick"
const RECIPES: MaterialPalette = preload("res://game/recipe_palette.tres")
const TIERS: Array[String] = ["rig", "laptop"]
## 120 px/m (owner, 2026-11-22): at 30-90 the stick is floored to a whole 2 px, where even a hard edge barely crawls
## on the rig tier (2.01-2.12x the ideal); at 120 it is 2.4 px, and a hard edge fails there (2.55x) while the shipped
## edge holds (1.07x). Chosen from that survey of the deletion, before the shipped shader was judged at it.
const PX_PER_M: Array[float] = [72.0, 30.0, 120.0]
const OFFSETS: int = 8

var _stage: RenderStage = RenderStage.new()


func _ready() -> void:
	if DisplayServer.get_name() == "headless":
		_fail("--headless draws nothing; run under a display (Xvfb in CI)")
		return
	var out: String = _arg(OUT_FLAG)
	if out.is_empty():
		_fail("pass the output directory after --: -- %s<dir>" % OUT_FLAG)
		return
	var fixture: FuelFixture = FuelFixture.named(FIXTURE)
	if not fixture.problems.is_empty():
		_fail("fuel fixture: " + "; ".join(fixture.problems))
		return
	_stage.size = Vector2i(WIDTH, HEIGHT)
	add_child(_stage)
	_stage.volume.visible = false  # the stick alone: no wall can cut into what is measured
	var refused: Array[String] = _stage.show_fuel(fixture.snapshot, fixture.region_names, RECIPES)
	if not refused.is_empty():
		_fail("fuel: " + "; ".join(refused))
		return
	_stage.use_pass(CellVolume.Pass.OCCLUDER, false)
	_stage.use_fuel_view(FuelPass.View.FUEL_ID, false)
	var meta: Dictionary[String, Dictionary] = {}
	for tier_name: String in TIERS:
		_stage.use_tier(load("res://game/tiers/%s.tres" % tier_name) as RenderTier)
		for px_per_m: float in PX_PER_M:
			var key: String = "%s-%d" % [tier_name, int(px_per_m)]
			var entry: Dictionary = await _frames(out, key, fixture.snapshot, px_per_m)
			if entry.is_empty():
				return
			meta[key] = entry
	var file: FileAccess = FileAccess.open(out.path_join("stability.json"), FileAccess.WRITE)
	if file == null or not file.store_string(JSON.stringify(meta)):
		_fail("cannot write stability.json")
		return
	file.close()
	print("stability: wrote %d frames" % (TIERS.size() * PX_PER_M.size() * OFFSETS))
	get_tree().quit(0)


## One zoom's OFFSETS frames; returns {ends, drawn_px}, or {} after failing.
func _frames(out: String, key: String, snap: FuelSnapshot, px_per_m: float) -> Dictionary:
	var origin: Vector3 = _rod_point(snap, 0.0)
	var end: Vector3 = _rod_point(snap, 1.0)
	var pixel_m: float = 1.0 / px_per_m
	var ends: Array[Array] = []
	for k: int in OFFSETS:
		_stage.aim((origin + end) * 0.5, IsoCamera.step_yaw(0), HEIGHT * pixel_m)
		var camera: Camera3D = _stage.camera
		camera.transform.origin += (camera.transform.basis.x + camera.transform.basis.y) * (float(k) / OFFSETS) * pixel_m
		var image: Image = await _stage.capture()
		if image == null or image.save_png(out.path_join("stab-%s-%d.png" % [key, k])) != OK:
			_fail("cannot draw or save %s offset %d" % [key, k])
			return {}
		var a: Vector2 = camera.unproject_position(IsoCamera.to_godot(origin))
		var b: Vector2 = camera.unproject_position(IsoCamera.to_godot(end))
		ends.append([a.x, a.y, b.x, b.y])
	var radius: float = snap.column("rods", "radius_m").decode_float(0)
	return {"ends": ends, "drawn_px": 2.0 * FuelPass.drawn_half_m(radius, pixel_m) / pixel_m}


## The stick's axis at fraction ``f`` of its length, in world metres.
func _rod_point(snap: FuelSnapshot, f: float) -> Vector3:
	var origin: Vector3 = Vector3(snap.column("rods", "origin_x_m").decode_float(0),
		snap.column("rods", "origin_y_m").decode_float(0), snap.column("rods", "origin_z_m").decode_float(0))
	var axis: Vector3 = Vector3(snap.column("rods", "axis_x").decode_float(0),
		snap.column("rods", "axis_y").decode_float(0), snap.column("rods", "axis_z").decode_float(0))
	return origin + axis * snap.column("rods", "length_m").decode_float(0) * f


func _arg(flag: String) -> String:
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with(flag):
			return arg.substr(flag.length())
	return ""


func _fail(why: String) -> void:
	push_error("stability: " + why)
	get_tree().quit(1)
