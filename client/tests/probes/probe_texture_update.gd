extends SceneTree
## §9 probe: can one slice of a 3-D texture be updated alone, and what does a whole update cost? Lists every
## texture-update method the engine has, then times ImageTexture3D.update at the tile's shape (120 × 40 × 48, R8),
## the minimum of 50 updates. Windowed (the dummy renderer of --headless does no uploads):
## godot --rendering-driver opengl3 --rendering-method gl_compatibility --path client
##       -s res://tests/probes/probe_texture_update.gd

const NX: int = 120
const NY: int = 40
const NZ: int = 48
const RUNS: int = 50

var _frames: int = 0


func _initialize() -> void:
	for cls: String in ["ImageTexture3D", "Texture3D", "RenderingServer"]:
		for method: Dictionary in ClassDB.class_get_method_list(cls, true):
			var method_name: String = method["name"]
			if method_name.contains("update"):
				print("probe texture: %s.%s" % [cls, method_name])


func _process(_delta: float) -> bool:
	_frames += 1
	if _frames < 3:
		return false
	var slices: Array[Image] = []
	for z: int in NZ:
		slices.append(Image.create(NX, NY, false, Image.FORMAT_R8))
	var texture: ImageTexture3D = ImageTexture3D.new()
	var err: Error = texture.create(Image.FORMAT_R8, NX, NY, NZ, false, slices)
	print("probe texture: create -> %s" % error_string(err))
	var best: int = 1 << 62
	var first: int = -1
	for run: int in RUNS:
		slices[run % NZ].set_pixel(run % NX, 0, Color(1, 0, 0))
		var start: int = Time.get_ticks_usec()
		texture.update(slices)
		var took: int = Time.get_ticks_usec() - start
		if first < 0:
			first = took
		best = mini(best, took)
	print("probe texture: whole update of %d slices: first %d us, min of %d %d us, adapter=%s" % [
		NZ, first, RUNS, best, RenderingServer.get_video_adapter_name()])
	return true
