extends RefCounted
## The fuel seam (addons/engine/render/fuel_snapshot.gd) and its fixture reader (tests/support/fuel_fixture.gd): the
## committed fixture loads, its rows sit where client_objects.md §7.1 puts them, the trigger bytes ignore state, and
## every check of §3.2 refuses a frame with a reason, so nothing draws from a malformed table.


func _loaded(t: TestContext) -> FuelFixture:
	var f: FuelFixture = FuelFixture.named("fuel_ramp")
	t.check(f.problems.is_empty(), "fuel_ramp loads: %s" % [f.problems])
	return f


func test_the_committed_fixture_loads(t: TestContext) -> void:
	var f: FuelFixture = _loaded(t)
	if f.snapshot == null:
		return
	var snap: FuelSnapshot = f.snapshot
	t.check_eq(snap.rows["objects"], 74, "objects")
	t.check_eq(snap.rows["slabs"], 1, "one slab")
	t.check_eq(snap.kind_ids, {"rod": 0, "slab": 1} as Dictionary[String, int], "the kind vocabulary")
	var first: PackedInt32Array = snap.first_rows()
	t.check(first[first.size() - 5] > 2048, "the visible objects start past half-float exactness")
	t.check_eq(first[0], 0, "the first object starts at row 0")


func test_state_never_moves_the_trigger(t: TestContext) -> void:
	var snap: FuelSnapshot = _loaded(t).snapshot
	if snap == null:
		return
	var before: PackedByteArray = snap.trigger_bytes()
	var state: PackedByteArray = snap.column("objects", "state").duplicate()
	state[0] = 1
	snap.columns["objects.state"] = state
	t.check(snap.trigger_bytes() == before, "a burnout changes no trigger byte, so it never rebuilds instances")
	var counts: PackedByteArray = snap.column("objects", "segment_count").duplicate()
	counts.encode_u16(0, counts.decode_u16(0) + 1)
	snap.columns["objects.segment_count"] = counts
	t.check(snap.trigger_bytes() != before, "a changed count does")


## A copy of the fixture's snapshot with one column's bytes changed by ``edit``.
func _with(t: TestContext, key: String, edit: Callable) -> FuelSnapshot:
	var f: FuelFixture = _loaded(t)
	var snap: FuelSnapshot = f.snapshot
	var bytes: PackedByteArray = snap.columns[key].duplicate()
	edit.call(bytes)
	snap.columns[key] = bytes
	return snap


func _refused(t: TestContext, snap: FuelSnapshot, regions: Dictionary[int, String], expect: String) -> void:
	var found: Array[String] = snap.problems(regions)
	var named: bool = found.any(func(p: String) -> bool: return p.contains(expect))
	t.check(named, "refused with '%s': %s" % [expect, found])


func test_every_structural_check_refuses(t: TestContext) -> void:
	var regions: Dictionary[int, String] = _loaded(t).region_names
	_refused(t, _with(t, "objects.recipe_id", _u16(0, 99)), regions, "recipe 99")
	_refused(t, _with(t, "objects.region_id", _u16(0, 999)), regions, "region 999")
	_refused(t, _with(t, "objects.kind", func(b: PackedByteArray) -> void: b[0] = 7), regions, "kind 7")
	_refused(t, _with(t, "objects.segment_length_m", _f32(0, -0.02)), regions, "segment length")
	_refused(t, _with(t, "objects.segment_count", _u16(0, 31)), regions, "segment counts sum")
	_refused(t, _with(t, "rods.radius_m", _f32(0, 0.0)), regions, "rod row 0")
	_refused(t, _with(t, "rods.axis_x", _f32(0, 0.9)), regions, "rod row 0")
	_refused(t, _with(t, "rods.origin_y_m", _f32(0, NAN)), regions, "rod row 0")
	_refused(t, _with(t, "slabs.thickness_m", _f32(0, 0.0)), regions, "slab row 0")
	_refused(t, _with(t, "slabs.width_axis_y", _f32(0, 1.1)), regions, "slab row 0")
	_refused(t, _with(t, "rods.object_id", func(b: PackedByteArray) -> void: b.encode_u32(0, 70000)), regions, "rods rows")


func _u16(row: int, value: int) -> Callable:
	return func(b: PackedByteArray) -> void: b.encode_u16(row * 2, value)


func _f32(row: int, value: float) -> Callable:
	return func(b: PackedByteArray) -> void: b.encode_float(row * 4, value)


func test_counts_that_sum_right_on_the_wrong_objects_are_refused(t: TestContext) -> void:
	var regions: Dictionary[int, String] = _loaded(t).region_names
	var swap: Callable = func(b: PackedByteArray) -> void:
		b.encode_u16(0, b.decode_u16(0) + 1)
		b.encode_u16(2, b.decode_u16(2) - 1)
	_refused(t, _with(t, "objects.segment_count", swap), regions, "keys are not the ones")


func test_a_kind_this_client_cannot_draw_is_refused(t: TestContext) -> void:
	var f: FuelFixture = _loaded(t)
	f.snapshot.kind_ids["bed"] = 2
	_refused(t, f.snapshot, f.region_names, "kind bed")


func test_a_short_column_is_refused_before_any_row_is_read(t: TestContext) -> void:
	var f: FuelFixture = _loaded(t)
	var short: PackedByteArray = f.snapshot.columns["segments.char_fraction"].slice(1)
	f.snapshot.columns["segments.char_fraction"] = short
	var found: Array[String] = f.snapshot.problems(f.region_names)
	t.check_eq(found.size(), 1, "only the shape problem: %s" % [found])


func test_a_state_other_than_live_or_burnt_out_is_refused(t: TestContext) -> void:
	var snap: FuelSnapshot = _with(t, "objects.state", func(b: PackedByteArray) -> void: b[3] = 2)
	t.check(not snap.state_problems().is_empty(), "state 2 is refused")
	t.check(_loaded(t).snapshot.state_problems().is_empty(), "the fixture's states pass")


func _header() -> Dictionary:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(FuelFixture.DIR + "/fuel_ramp.json"))
	var header: Dictionary = parsed
	return header


func test_every_malformed_header_is_refused(t: TestContext) -> void:
	var blob: PackedByteArray = FileAccess.get_file_as_bytes(FuelFixture.DIR + "/fuel_ramp.bin.gz")
	t.check(FuelFixture.parse(_header(), blob).problems.is_empty(), "the unmodified header loads")
	var cases: Dictionary[String, Array] = {
		"format": ["overdrive-client-snapshot-fixture"], "version": [1, "0"], "kinds": [[], {"rod": "0"}],
		"recipes": [3], "regions": [[], {"0": "x"}, {"7": 1}], "tables": [[], {}],
		"data_sha256": ["0"], "data_gzip_sha256": ["0"], "data_size": [0, 1e12],
	}
	for key: String in cases:
		for bad: Variant in cases[key]:
			var header: Dictionary = _header()
			header[key] = bad
			var f: FuelFixture = FuelFixture.parse(header, blob)
			t.check(f.snapshot == null and not f.problems.is_empty(), "%s = %s is refused" % [key, bad])


func test_a_column_with_the_wrong_dtype_or_span_is_refused(t: TestContext) -> void:
	var blob: PackedByteArray = FileAccess.get_file_as_bytes(FuelFixture.DIR + "/fuel_ramp.bin.gz")
	for edit: Array in [["dtype", "f32"], ["offset", 999999999], ["size", -1]]:
		var header: Dictionary = _header()
		var tables: Dictionary = header["tables"]
		var segments: Dictionary = tables["segments"]
		var cols: Dictionary = segments["columns"]
		var col: Dictionary = cols["seg"]
		col[edit[0]] = edit[1]
		var f: FuelFixture = FuelFixture.parse(header, blob)
		t.check(f.snapshot == null and not f.problems.is_empty(), "segments.seg %s = %s is refused" % edit)
