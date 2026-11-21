extends RefCounted
## The fixture reader (tests/support/snapshot_fixture.gd): both committed fixtures load into drawable snapshots, and
## every malformed field is refused with a reason and no snapshot, so no check ever draws from half a fixture.


func test_the_committed_fixtures_load(t: TestContext) -> void:
	for fixture_name: String in ["alley_cold", "alley_fire"]:
		var f: SnapshotFixture = SnapshotFixture.named(fixture_name)
		t.check(f.problems.is_empty(), "%s: %s" % [fixture_name, f.problems])
		if f.snapshot == null:
			continue
		t.check_eq([f.snapshot.nx, f.snapshot.ny, f.snapshot.nz], [120, 40, 48], "%s shape (nx, ny, nz)" % fixture_name)
		t.check_eq(f.snapshot.cell_m, 0.1, "cell_m")
		t.check_eq(f.snapshot.region_id("crate"), 5, "the crate's id")
		t.check_eq(f.snapshot.material_ids["wood"], 4, "wood's id, on the seam")
		t.check(is_equal_approx(f.snapshot.glow_scale_c_per_count, 975.0 / 255.0), "glow scale 975/255")
		t.check_eq(f.actors[1], Vector3(5.5, 2.925, 0.4), "the player's feet in metres")


func test_the_cells_are_the_alley(t: TestContext) -> void:
	var snap: CellSnapshot = SnapshotFixture.named("alley_fire").snapshot
	if snap == null:
		t.check(false, "the fixture loads")
		return
	var material: PackedByteArray = snap.channels["material"]
	t.check_eq(material[snap.index(0, 0, 0)], 1, "floor concrete at the origin")
	t.check_eq(material[snap.index(5, 20, 5)], 0, "air above the pavement")
	t.check_eq(material[snap.index(62, 28, 6)], 4, "wood in the crate")
	t.check_eq(material[snap.index(30, 2, 20)], 1, "wall_south at y 0.2 m")
	var crack: PackedByteArray = snap.channels["crack"]
	t.check(crack[snap.index(60, 28, 6)] < crack[snap.index(65, 28, 6)], "the crack ramps up eastward over the crate")
	var bounds: Dictionary[int, AABB] = snap.region_cell_bounds()
	t.check_eq(bounds[snap.region_id("crate")], AABB(Vector3(60, 26, 4), Vector3(6, 6, 6)), "the crate's cell box")


func _header() -> Dictionary:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(SnapshotFixture.DIR + "/alley_cold.json"))
	var header: Dictionary = parsed
	return header


func _blob() -> PackedByteArray:
	return FileAccess.get_file_as_bytes(SnapshotFixture.DIR + "/alley_cold.bin.gz")


func _refused(t: TestContext, header: Dictionary, blob: PackedByteArray, why: String) -> void:
	var f: SnapshotFixture = SnapshotFixture.parse(header, blob)
	t.check(f.snapshot == null, "%s: no snapshot" % why)
	t.check(not f.problems.is_empty(), "%s: a reason is given" % why)


func test_every_malformed_header_is_refused(t: TestContext) -> void:
	var good: Dictionary = _header()
	t.check(SnapshotFixture.parse(good, _blob()).problems.is_empty(), "the unmodified header loads")
	var cases: Dictionary[String, Array] = {
		"format": ["wire-frame"], "version": [1, 0.5, "0"], "shape": [[48, 40], [48, 40, -1.5], "x"],
		"cell_m": ["0.1", 0.0], "regions": [[], {"0": "floor"}, {"x": "floor"}, {"1": 3}],
		"materials": ["wood", {"wood": "4"}], "glow": [{}, {"offset_c": 525, "scale_num": 975, "scale_den": 0}],
		"actors": [{}, [{"id": 1}], [{"id": 1, "pos_mm": [1, 2]}], [{"id": 1, "pos_mm": [1, 2, 3]}, {"id": 1, "pos_mm": [4, 5, 6]}]],
		"data_size": [0, -1, 1e12, 230400],
		"data_sha256": ["00"], "data_gzip_sha256": ["00", 3], "channels": [[], {}],
	}
	for key: String in cases:
		for bad: Variant in cases[key]:
			var header: Dictionary = good.duplicate(true)
			header[key] = bad
			_refused(t, header, _blob(), "%s = %s" % [key, bad])


func test_a_bad_channel_spec_or_corrupt_data_is_refused(t: TestContext) -> void:
	var good: Dictionary = _header()
	var channels: Dictionary = good["channels"]
	for change: Dictionary in [{"dtype": "u16"}, {"offset": -1}, {"size": 999999999}, {"offset": 1e300}]:
		var header: Dictionary = good.duplicate(true)
		var listed: Dictionary = header["channels"]
		var spec: Dictionary = listed["crack"]
		spec.merge(change, true)
		_refused(t, header, _blob(), "crack %s" % change)
	var short: Dictionary = good.duplicate(true)
	var short_channels: Dictionary = short["channels"]
	var crack: Dictionary = short_channels["crack"]
	crack["size"] = 1000
	_refused(t, short, _blob(), "a channel shorter than the cells")
	_refused(t, good, PackedByteArray([1, 2, 3]), "data that isn't gzip")
	var tampered: PackedByteArray = _blob()
	tampered[tampered.size() >> 1] ^= 0x55
	_refused(t, good, tampered, "data whose bytes changed")
	t.check(channels.has("crack"), "the header lists crack")


func test_a_missing_or_unreadable_fixture_is_refused(t: TestContext) -> void:
	var missing: SnapshotFixture = SnapshotFixture.named("no_such_fixture")
	t.check(missing.snapshot == null and not missing.problems.is_empty(), "a missing fixture")
	t.check_eq(SnapshotFixture.whole_of(2.5), -1, "2.5 is not whole")
	t.check_eq(SnapshotFixture.whole_of(9007199254740994.0), -1, "above 2^53 is not whole")
	t.check_eq(SnapshotFixture.whole_of(7.0), 7, "7.0 is whole")
	t.check(not SnapshotFixture.is_whole(INF), "infinity is not whole")
