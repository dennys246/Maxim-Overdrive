extends Node3D
## The renderer golden (client_rendering.md §6): a fixed orthographic camera over hand-placed boxes, drawn once and
## saved as a PNG that scripts/golden_run.py judges against the committed golden. It needs a real GL context (Xvfb
## in the CI image): under --headless it refuses at once, since the capture's await would never return.
## Engine whys: Camera3D in orthographic projection keeps sizes constant with depth (§1); each MeshInstance3D draws one
## mesh; the floor is larger than the view, so the scene fills the frame; the materials are unshaded so the frame
## depends on no light; WorldEnvironment fixes the background and keeps glow off. Node3D is the root because
## everything here has a 3-D transform.

const YAW_DEG: float = 45.0
const ELEVATION_DEG: float = 40.0
const DISTANCE_M: float = 60.0
const OUT_FLAG: String = "--out="
const WIDTH: int = 1280
const HEIGHT: int = 720

@onready var _camera: Camera3D = $Camera3D
@onready var _crate: MeshInstance3D = $Crate


func _ready() -> void:
	_place_camera()
	if DisplayServer.get_name() == "headless":
		# Measured on 4.7.2: under --headless frame_post_draw never fires, so the await below would hang.
		_fail("--headless draws nothing; run under a display (Xvfb in CI)")
		return
	var out: String = _out_path()
	if out.is_empty():
		_fail("pass the output path after --: -- %s<png>" % OUT_FLAG)
		return
	# frame_post_draw fires once the frame has been drawn, so the viewport's texture holds this frame.
	await RenderingServer.frame_post_draw
	var image: Image = get_viewport().get_texture().get_image()
	if image == null:
		_fail("get_image() is null: no real renderer (--headless draws nothing)")
		return
	if image.get_width() != WIDTH or image.get_height() != HEIGHT:
		_fail("the frame is %dx%d, not %dx%d" % [image.get_width(), image.get_height(), WIDTH, HEIGHT])
		return
	var err: Error = image.save_png(out)
	if err != OK:
		_fail("save_png(%s) failed: %s" % [out, error_string(err)])
		return
	print("golden: wrote %s adapter=%s" % [out, RenderingServer.get_video_adapter_name()])
	get_tree().quit(0)


## Yaw 45°, elevation 40°, 60 m back from the crate, looking at it: client_rendering.md §1's golden camera.
func _place_camera() -> void:
	var yaw: float = deg_to_rad(YAW_DEG)
	var elevation: float = deg_to_rad(ELEVATION_DEG)
	var back: Vector3 = Vector3(cos(elevation) * sin(yaw), sin(elevation), cos(elevation) * cos(yaw))
	_camera.position = _crate.position + back * DISTANCE_M
	_camera.look_at(_crate.position, Vector3.UP)


func _out_path() -> String:
	for arg: String in OS.get_cmdline_user_args():
		if arg.begins_with(OUT_FLAG):
			return arg.substr(OUT_FLAG.length())
	return ""


func _fail(why: String) -> void:
	push_error("golden: " + why)
	get_tree().quit(1)
