extends SceneTree
## §9 probe: can the client read GPU time on Compatibility? Draws a box for 120 frames with render-time measuring on,
## then prints the viewport's measured GPU and CPU times and the minimum frame interval. Windowed:
## godot --rendering-driver opengl3 --rendering-method gl_compatibility --disable-vsync
##       --path tools/godot_probes -s res://probe_gpu_time.gd

const FRAMES: int = 120

var _frames: int = 0
var _last_usec: int = 0
var _min_interval_usec: int = 1 << 62
var _gpu_max_ms: float = 0.0


func _initialize() -> void:
	var camera: Camera3D = Camera3D.new()
	camera.position = Vector3(0, 0, 3)
	var box: MeshInstance3D = MeshInstance3D.new()
	box.mesh = BoxMesh.new()
	root.add_child(camera)
	root.add_child(box)
	RenderingServer.viewport_set_measure_render_time(root.get_viewport_rid(), true)


func _process(_delta: float) -> bool:
	var now: int = Time.get_ticks_usec()
	if _last_usec > 0:
		_min_interval_usec = mini(_min_interval_usec, now - _last_usec)
	_last_usec = now
	var rid: RID = root.get_viewport_rid()
	_gpu_max_ms = maxf(_gpu_max_ms, RenderingServer.viewport_get_measured_render_time_gpu(rid))
	_frames += 1
	if _frames < FRAMES:
		return false
	print("probe gpu: max measured GPU %.4f ms, last CPU %.4f ms, min frame interval %d us, adapter=%s" % [
		_gpu_max_ms, RenderingServer.viewport_get_measured_render_time_cpu(rid), _min_interval_usec,
		RenderingServer.get_video_adapter_name()])
	return true
