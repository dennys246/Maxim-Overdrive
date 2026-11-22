extends SceneTree
## The fuel pass's frame time (docs/design/research/fuel_antialiasing.md, rerun at a Godot upgrade or a fuel shader
## change): the golden view with the cell volume and 2,000 rods (2x10^4 segments, the world limits), per mode, the
## minimum and median of 150 process-frame intervals after 30 warm-up frames, drawn straight to the window:
##   AA_MODE=shipped|noflame|off godot --rendering-driver opengl3 --rendering-method gl_compatibility \
##     --resolution 1280x720 --disable-vsync --path client -s <abs path>/tools/fuel_aa/frame_time.gd
## shipped draws the pass as it ships, flames on; noflame hides the flames; off hides the pass, the baseline. The
## comparison's MSAA and hard-edge modes are gone with the candidates they measured.

var _mode: String
var _frames: int = 0
var _last: int = 0
var _intervals: Array[int] = []

func _initialize() -> void:
	_mode = OS.get_environment("AA_MODE")
	_setup.call_deferred()

func _put(s: FuelSnapshot, key: String, dtype: String, n: int, value: Callable) -> void:
	var b: PackedByteArray = PackedByteArray()
	var _e: int = b.resize(n * FuelSnapshot.DTYPE_BYTES[dtype])
	for i: int in n:
		var v: float = value.call(i)
		if dtype == "u8":
			b[i] = int(v)
		elif dtype == "u16":
			b.encode_u16(i * 2, int(v))
		elif dtype == "u32":
			b.encode_u32(i * 4, int(v))
		elif dtype == "f16":
			b.encode_half(i * 2, v)
		else:
			b.encode_float(i * 4, v)
	s.columns[key] = b

func _many() -> FuelSnapshot:
	var s: FuelSnapshot = FuelSnapshot.new()
	s.kind_ids = {"rod": 0, "slab": 1}
	s.recipe_ids = {"pine_rod": 1}
	var n: int = 2000
	var per: int = 10
	s.rows = {"objects": n, "rods": n, "slabs": 0, "segments": n * per}
	_put(s, "objects.object_id", "u32", n, func(i: int) -> float: return i + 1)
	_put(s, "objects.recipe_id", "u16", n, func(_i: int) -> float: return 1)
	_put(s, "objects.region_id", "u16", n, func(_i: int) -> float: return 7)
	_put(s, "objects.kind", "u8", n, func(_i: int) -> float: return 0)
	_put(s, "objects.state", "u8", n, func(_i: int) -> float: return 0)
	_put(s, "objects.segment_count", "u16", n, func(_i: int) -> float: return per)
	_put(s, "objects.segment_length_m", "f32", n, func(_i: int) -> float: return 0.02)
	_put(s, "rods.object_id", "u32", n, func(i: int) -> float: return i + 1)
	_put(s, "rods.origin_x_m", "f32", n, func(i: int) -> float: return 2.0 + 0.25 * (i % 32))
	_put(s, "rods.origin_y_m", "f32", n, func(i: int) -> float: return 0.6 + 0.045 * floori(i / 32.0))
	_put(s, "rods.origin_z_m", "f32", n, func(_i: int) -> float: return 0.41)
	_put(s, "rods.axis_x", "f32", n, func(_i: int) -> float: return 1.0)
	_put(s, "rods.axis_y", "f32", n, func(_i: int) -> float: return 0.0)
	_put(s, "rods.axis_z", "f32", n, func(_i: int) -> float: return 0.0)
	_put(s, "rods.length_m", "f32", n, func(_i: int) -> float: return 0.2)
	_put(s, "rods.radius_m", "f32", n, func(_i: int) -> float: return 0.01)
	_put(s, "segments.object_id", "u32", n * per, func(i: int) -> float: return floori(i / float(per)) + 1)
	_put(s, "segments.seg", "u16", n * per, func(i: int) -> float: return i % per)
	_put(s, "segments.surface_temperature_c", "f16", n * per, func(i: int) -> float: return 300.0 + (i % 997))
	_put(s, "segments.ignited_fraction", "u8", n * per, func(i: int) -> float: return 255 if i % 7 == 0 else 0)
	_put(s, "segments.thickness_fraction", "u8", n * per, func(_i: int) -> float: return 255)
	_put(s, "segments.char_fraction", "u8", n * per, func(i: int) -> float: return i % 256)
	for c: String in FuelSnapshot.SLABS:
		s.columns["slabs." + c] = PackedByteArray()
	return s

func _setup() -> void:
	if not _mode in ["shipped", "noflame", "off"]:
		push_error("frame_time: AA_MODE must be shipped, noflame or off, not '%s'" % _mode)
		quit(1)
		return
	var env: Environment = Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color.BLACK
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	env.glow_enabled = true
	env.glow_hdr_threshold = 1.0
	var we: WorldEnvironment = WorldEnvironment.new()
	we.environment = env
	root.add_child(we)
	var cam: Camera3D = Camera3D.new()
	root.add_child(cam)
	cam.current = true
	IsoCamera.place(cam, Vector3(6.3, 2.9, 0.7), IsoCamera.step_yaw(0), 10.0)
	var volume: CellVolume = CellVolume.new()
	root.add_child(volume)
	var cells: CellSnapshot = SnapshotFixture.named("alley_fire").snapshot
	volume.show_snapshot(cells)
	var palette: MaterialPalette = load("res://game/palette.tres") as MaterialPalette
	var _p: Array[String] = volume.use_palette(cells.material_ids, palette.by_id(cells.material_ids))
	var _q: String = volume.use_pixel_metres(10.0 / 720.0)
	var fuel: FuelPass = FuelPass.new()
	root.add_child(fuel)
	var snap: FuelSnapshot = _many()
	var _r: Array[String] = fuel.use_palette(snap.recipe_ids, {1: Color(0.5, 0.35, 0.2)})
	var _s: String = fuel.use_pixel_metres(10.0 / 720.0, 1.0)
	var refused: Array[String] = fuel.show_fuel(snap, {7: "x"} as Dictionary[int, String])
	if not refused.is_empty():
		push_error("frame_time: the limits snapshot is refused: %s" % [refused])
	fuel.flames.visible = _mode == "shipped"
	fuel.visible = _mode != "off"
	_last = Time.get_ticks_usec()

func _process(_delta: float) -> bool:
	var now: int = Time.get_ticks_usec()
	_frames += 1
	if _frames > 30:
		_intervals.append(now - _last)
	_last = now
	if _frames >= 180:
		_intervals.sort()
		print("mode %s min_us %d median_us %d" % [_mode, _intervals[0], _intervals[floori(_intervals.size() / 2.0)]])
		return true
	return false
