extends SceneTree
## The fuel pass's CPU cost at fire_solid §1.3's world limits (docs/design/client_objects.md §4.1): 1,800 rods and 200
## slabs, ten segments each (2,000 objects, 2x10^4 segment rows). Prints the minimum and median of 15 runs for an
## insertion (check, rebuild and uploads), the structural check alone, a steady frame, and the rebuild's parts.
##   godot --headless --path client -s <abs path>/tools/fuel_aa/rebuild_time.gd

const RUNS: int = 15
const RODS: int = 1800
const SLABS: int = 200
const PER: int = 10


func _column(n: int, dtype: String, value: float) -> PackedByteArray:
	var b: PackedByteArray = PackedByteArray()
	var _e: int = b.resize(n * FuelSnapshot.DTYPE_BYTES[dtype])
	for i: int in n:
		match dtype:
			"f32":
				b.encode_float(i * 4, value)
			"f16":
				b.encode_half(i * 2, value)
			"u16":
				b.encode_u16(i * 2, int(value))
			"u32":
				b.encode_u32(i * 4, int(value))
			_:
				b[i] = int(value)
	return b


func _limits() -> FuelSnapshot:
	var s: FuelSnapshot = FuelSnapshot.new()
	var n: int = RODS + SLABS
	s.rows = {"objects": n, "rods": RODS, "slabs": SLABS, "segments": n * PER}
	s.kind_ids = {"rod": 0, "slab": 1}
	s.recipe_ids = {"pine_rod": 1, "pine_slab": 2}
	var tables: Dictionary[String, Dictionary] = FuelSnapshot.tables()
	for table: String in tables:
		var spec: Dictionary = tables[table]
		for name: String in spec:
			var dtype: String = spec[name]
			s.columns["%s.%s" % [table, name]] = _column(s.rows[table], dtype, 0.0)
	var oid: PackedByteArray = _column(n, "u32", 0.0)
	var kind: PackedByteArray = _column(n, "u8", 0.0)
	var rod_id: PackedByteArray = _column(RODS, "u32", 0.0)
	var slab_id: PackedByteArray = _column(SLABS, "u32", 0.0)
	for i: int in n:
		oid.encode_u32(i * 4, i + 1)
		if i < RODS:
			rod_id.encode_u32(i * 4, i + 1)
		else:
			kind[i] = 1
			slab_id.encode_u32((i - RODS) * 4, i + 1)
	s.columns["objects.object_id"] = oid
	s.columns["objects.kind"] = kind
	s.columns["rods.object_id"] = rod_id
	s.columns["slabs.object_id"] = slab_id
	s.columns["objects.recipe_id"] = _column(n, "u16", 1.0)
	s.columns["objects.region_id"] = _column(n, "u16", 7.0)
	s.columns["objects.segment_count"] = _column(n, "u16", PER)
	s.columns["objects.segment_length_m"] = _column(n, "f32", 0.02)
	s.columns["rods.length_m"] = _column(RODS, "f32", 0.2)
	s.columns["rods.radius_m"] = _column(RODS, "f32", 0.01)
	s.columns["rods.axis_x"] = _column(RODS, "f32", 1.0)
	s.columns["slabs.length_m"] = _column(SLABS, "f32", 0.2)
	s.columns["slabs.width_m"] = _column(SLABS, "f32", 0.1)
	s.columns["slabs.thickness_m"] = _column(SLABS, "f32", 0.02)
	s.columns["slabs.length_axis_x"] = _column(SLABS, "f32", 1.0)
	s.columns["slabs.width_axis_y"] = _column(SLABS, "f32", 1.0)
	var seg_oid: PackedByteArray = _column(n * PER, "u32", 0.0)
	var seg: PackedByteArray = _column(n * PER, "u16", 0.0)
	for i: int in n * PER:
		seg_oid.encode_u32(i * 4, floori(i / float(PER)) + 1)
		seg.encode_u16(i * 2, i % PER)
	s.columns["segments.object_id"] = seg_oid
	s.columns["segments.seg"] = seg
	s.columns["segments.thickness_fraction"] = _column(n * PER, "u8", 255.0)
	return s


func _time(step: Callable) -> String:
	var times: Array[float] = []
	for run: int in RUNS:
		var t0: int = Time.get_ticks_usec()
		step.call()
		times.append((Time.get_ticks_usec() - t0) / 1000.0)
	times.sort()
	return "min %.2f ms, median %.2f ms" % [times[0], times[floori(times.size() / 2.0)]]


func _initialize() -> void:
	var regions: Dictionary[int, String] = {7: "pile"}
	var snap: FuelSnapshot = _limits()
	var refused: Array[String] = snap.problems(regions)
	if not refused.is_empty():
		push_error("rebuild_time: the limits snapshot is refused: %s" % [refused.slice(0, 3)])
		quit(1)
		return
	var insertion: Callable = func() -> void:
		var fuel: FuelPass = FuelPass.new()
		var _r: Array[String] = fuel.show_fuel(snap, regions)
		fuel.free()
	var steady_pass: FuelPass = FuelPass.new()
	var _first: Array[String] = steady_pass.show_fuel(snap, regions)
	var steps: Dictionary[String, Callable] = {
		"insertion (check, rebuild, uploads)": insertion,
		"structural check": func() -> void: var _p: Array[String] = snap.problems(regions),
		"steady frame": func() -> void: var _s: Array[String] = steady_pass.show_fuel(snap, regions),
		"rod buffer": func() -> void: var _b: PackedFloat32Array = FuelGeometry.rod_buffer(snap),
		"flame buffer": func() -> void: var _f: PackedFloat32Array = FuelGeometry.flame_buffer(snap),
	}
	for name: String in steps:
		print("rebuild_time: %s: %s" % [name, _time(steps[name])])
	if steady_pass.rebuilds != 1:
		push_error("rebuild_time: a steady frame rebuilt")
	steady_pass.free()
	quit(0)
