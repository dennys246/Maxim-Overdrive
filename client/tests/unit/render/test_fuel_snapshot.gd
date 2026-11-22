extends RefCounted
## The fuel seam (addons/engine/render/fuel_snapshot.gd) and its fixture reader (tests/support/fuel_fixture.gd): the
## committed fixture loads, its rows sit where client_objects.md §7.1 puts them, the structure ignores the per-frame
## columns, and every check of §3.2 refuses a frame with a reason, so nothing draws from a malformed table.


func _loaded(t: TestContext) -> FuelFixture:
	var f: FuelFixture = FuelFixture.named("fuel_ramp")
	t.check(f.problems.is_empty(), "fuel_ramp loads: %s" % [f.problems])
	return f


func test_the_committed_fixture_loads(t: TestContext) -> void:
	var f: FuelFixture = _loaded(t)
	if f.snapshot == null:
		return
	var snap: FuelSnapshot = f.snapshot
	t.check_eq(snap.rows["objects"], 77, "objects")
	t.check_eq(snap.rows["slabs"], 1, "one slab")
	t.check_eq(snap.kind_ids, {"rod": 0, "slab": 1} as Dictionary[String, int], "the kind vocabulary")
	var first: PackedInt32Array = snap.first_rows()
	t.check(first[first.size() - 8] > 2048, "the visible objects start past half-float exactness")
	t.check_eq(first[0], 0, "the first object starts at row 0")


func test_only_structural_columns_move_the_structure(t: TestContext) -> void:
	var snap: FuelSnapshot = _loaded(t).snapshot
	if snap == null:
		return
	var before: Dictionary = snap.structure()
	for key: String in FuelSnapshot.FRAME_COLUMNS:
		var bytes: PackedByteArray = snap.columns[key].duplicate()
		bytes[0] = 1
		snap.columns[key] = bytes
	t.check(snap.structure() == before, "a burnout or new segment state leaves the structure, so it never rebuilds")
	var counts: PackedByteArray = snap.column("objects", "segment_count").duplicate()
	counts.encode_u16(0, counts.decode_u16(0) + 1)
	snap.columns["objects.segment_count"] = counts
	t.check(snap.structure() != before, "a changed count moves it")
	snap.columns["objects.segment_count"] = before["objects.segment_count"]
	t.check(snap.structure() == before, "and restoring it restores the structure")
	snap.rows["segments"] += 1
	t.check(snap.structure() != before, "so does a row count")
	snap.rows["segments"] -= 1
	snap.recipe_ids["oak_rod"] = 9
	t.check(snap.structure() != before, "and a vocabulary")


func test_each_kind_has_its_own_geometry_rows(t: TestContext) -> void:
	var snap: FuelSnapshot = _loaded(t).snapshot
	t.check_eq(snap.geometry_rows("rod").size(), 76, "the rods")
	t.check_eq(snap.geometry_rows("slab").size(), 1, "the slab")
	t.check_eq(snap.geometry_rows("bed").size(), 0, "a kind the vocabulary doesn't name has none")


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
	for case: Array in [
		["objects.recipe_id", _u16(0, 99), "recipe 99"],
		["objects.region_id", _u16(0, 999), "region 999"],
		["objects.kind", func(b: PackedByteArray) -> void: b[0] = 7, "kind 7"],
		["objects.object_id", func(b: PackedByteArray) -> void: b.encode_u32(4, b.decode_u32(0)), "not above"],
		["objects.segment_count", _u16(0, 31), "segment counts sum"],
		["rods.object_id", func(b: PackedByteArray) -> void: b.encode_u32(0, 70000), "rods rows"],
		["rods.axis_x", _f32(0, 0.9), "rod row 0"],
		["rods.axis_y", _f32(0, NAN), "rod row 0"],
		["rods.origin_y_m", _f32(0, NAN), "rod row 0"],
		["slabs.thickness_m", _f32(0, 0.0), "slab row 0"],
		["slabs.width_axis_y", _f32(0, 1.1), "slab row 0"],
		["slabs.length_axis_x", _f32(0, 0.5), "slab row 0"],
		["slabs.origin_x_m", _f32(0, INF), "slab row 0"],
	]:
		var key: String = case[0]
		var edit: Callable = case[1]
		var expect: String = case[2]
		_refused(t, _with(t, key, edit), regions, expect)
	for bad: float in [0.0, -0.02, NAN, INF]:
		_refused(t, _with(t, "objects.segment_length_m", _f32(0, bad)), regions, "segment length")
		_refused(t, _with(t, "rods.length_m", _f32(0, bad)), regions, "rod row 0")
		_refused(t, _with(t, "rods.radius_m", _f32(0, bad)), regions, "rod row 0")
		_refused(t, _with(t, "slabs.length_m", _f32(0, bad)), regions, "slab row 0")
		_refused(t, _with(t, "slabs.width_m", _f32(0, bad)), regions, "slab row 0")


func test_a_slab_whose_axes_are_not_perpendicular_is_refused(t: TestContext) -> void:
	# Both axes stay unit; the width axis tilts 0.1 rad towards the length axis.
	var f: FuelFixture = _loaded(t)
	var snap: FuelSnapshot = f.snapshot
	for column: Array in [["slabs.width_axis_x", sin(0.1)], ["slabs.width_axis_y", cos(0.1)]]:
		var bytes: PackedByteArray = snap.columns[column[0]].duplicate()
		var value: float = column[1]
		bytes.encode_float(0, value)
		snap.columns[column[0]] = bytes
	_refused(t, snap, f.region_names, "slab row 0")


func test_an_object_with_no_segments_is_refused(t: TestContext) -> void:
	# Count 0 would make the shader's clamp(k, 0, count - 1) read the next object's rows (review TB-B3).
	var regions: Dictionary[int, String] = _loaded(t).region_names
	var moved: Callable = func(b: PackedByteArray) -> void:
		b.encode_u16(2, b.decode_u16(2) + b.decode_u16(0))
		b.encode_u16(0, 0)
	_refused(t, _with(t, "objects.segment_count", moved), regions, "no segments")


func test_an_object_in_the_other_kinds_table_is_refused(t: TestContext) -> void:
	var f: FuelFixture = _loaded(t)
	var slab_row: int = f.snapshot.geometry_rows("slab")[0]
	var as_rod: Callable = func(b: PackedByteArray) -> void: b[slab_row] = f.snapshot.kind_ids["rod"]
	_refused(t, _with(t, "objects.kind", as_rod), f.region_names, "rods rows are not")


func test_vocabularies_with_shared_or_out_of_range_ids_are_refused(t: TestContext) -> void:
	# A shared id made the pass and the check decide an object's table by different rules (review TB-B1).
	for edit: Array in [
		["kinds", "slab", 0, "two kinds share id 0"], ["recipes", "pine_slab", 1, "two recipes share id 1"],
		["kinds", "slab", 256, "outside 0..255"], ["recipes", "pine_slab", -1, "outside 0..65535"],
	]:
		var f: FuelFixture = _loaded(t)
		var vocabulary: Dictionary[String, int] = f.snapshot.kind_ids if edit[0] == "kinds" else f.snapshot.recipe_ids
		vocabulary[edit[1]] = edit[2]
		var expect: String = edit[3]
		_refused(t, f.snapshot, f.region_names, expect)


func test_row_counts_past_the_world_limits_or_missing_are_refused(t: TestContext) -> void:
	for edit: Array in [
		["objects", FuelSnapshot.MAX_OBJECTS + 1], ["segments", FuelSnapshot.MAX_SEGMENTS + 1], ["rods", -1],
	]:
		var f: FuelFixture = _loaded(t)
		f.snapshot.rows[edit[0]] = edit[1]
		_refused(t, f.snapshot, f.region_names, "%s has %d rows" % edit)
	var g: FuelFixture = _loaded(t)
	t.check(g.snapshot.rows.erase("slabs"), "the slabs' row count is gone")
	_refused(t, g.snapshot, g.region_names, "slabs has <null> rows")


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


func test_the_per_frame_check_refuses_a_bad_state_or_a_short_column(t: TestContext) -> void:
	t.check(_loaded(t).snapshot.frame_problems().is_empty(), "the fixture's frame passes")
	var snap: FuelSnapshot = _with(t, "objects.state", func(b: PackedByteArray) -> void: b[3] = 2)
	t.check_eq(str(snap.frame_problems()), str(["object row 3 has state 2; only 0 and 1 are defined"]), "state 2")
	for key: String in FuelSnapshot.FRAME_COLUMNS:
		var drop_one: Callable = func(b: PackedByteArray) -> void:
			var err: int = b.resize(b.size() - 1)
			t.check_eq(err, OK, "the column shrinks")
		var short: FuelSnapshot = _with(t, key, drop_one)
		var found: Array[String] = short.frame_problems()
		t.check(found.size() == 1 and found[0].begins_with(key), "a short %s: %s" % [key, found])


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
