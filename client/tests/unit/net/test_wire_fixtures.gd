extends RefCounted
## The client's wire decoders against the golden fixtures the server's decoders read (client/tests/fixtures/wire/,
## made by scripts/wire_fixtures.py; tests/test_wire.py is the Python side): every fixture of the sets naming
## "godot" as a reader reaches the outcome its manifest names, with the same refusal code.

const DIR: String = "res://tests/fixtures/wire"


func _manifest() -> Dictionary:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(DIR.path_join("manifest.json")))
	var manifest: Dictionary = parsed if parsed is Dictionary else {}
	return manifest


func _entries(manifest: Dictionary, set_name: String) -> Array:
	var wire_set: Dictionary = manifest[set_name]
	var entries: Array = wire_set["fixtures"]
	return entries


## The JSON readers' value as an int: every manifest number parses to a float.
func _int(value: Variant) -> int:
	var number: float = value
	return int(number)


func _readers(manifest: Dictionary, set_name: String) -> Array:
	var wire_set: Dictionary = manifest.get(set_name, {})
	var readers: Array = wire_set.get("readers", [])
	return readers


func _catalogue(manifest: Dictionary) -> String:
	var catalogue: String = manifest["catalogue"]
	return catalogue


func test_godot_reads_the_frames_and_json_sets_and_not_the_client_messages(t: TestContext) -> void:
	var manifest: Dictionary = _manifest()
	t.check(manifest.has("frames"), "the manifest loads")
	t.check(_readers(manifest, "frames").has("godot"), "frames")
	t.check(_readers(manifest, "json").has("godot"), "json")
	t.check(not _readers(manifest, "client").has("godot"), "client messages are the server's")


func test_every_frame_reaches_its_manifest_outcome(t: TestContext) -> void:
	var manifest: Dictionary = _manifest()
	var cap: int = _int(manifest["frame_cap"])
	for entry: Dictionary in _entries(manifest, "frames"):
		var file: String = entry["file"]
		var catalogue: String = entry["catalogue"]
		var data: PackedByteArray = FileAccess.get_file_as_bytes(DIR.path_join(file))
		var read: WireRead = FrameDecoder.decode(data, WireCatalogue.v0(), catalogue, _int(entry.get("max_bytes", cap)))
		var got: String = "accepted" if read.ok else "refused " + read.code
		t.check_eq(got, _want(entry), "%s (%s)" % [file, read.reason])
		if read.ok and got == _want(entry):
			var frame: WireFrame = read.value
			_check_accepted(t, entry, frame)


func _want(entry: Dictionary) -> String:
	var outcome: String = entry["outcome"]
	return "accepted" if outcome == "accepted" else "refused %s" % entry["code"]


func _check_accepted(t: TestContext, entry: Dictionary, frame: WireFrame) -> void:
	var name: String = entry["file"]
	var ignored: Array = entry.get("ignored", [])
	t.check_eq(frame.ignored, Array(ignored, TYPE_STRING, "", null), name + ": ignored")
	var shape: Array = entry.get("shape", [2, 2, 2])
	t.check_eq([frame.nz, frame.ny, frame.nx], [_int(shape[0]), _int(shape[1]), _int(shape[2])], name + ": shape")
	t.check_eq(frame.tick, _int(entry.get("tick", 5)), name + ": tick")
	var channels: Array[String] = ["material", "region", "crack", "temperature_c"]
	t.check_eq(frame.channels.keys(), channels, name + ": channels")
	var probes: Array = entry.get("probes", [])
	for probe: Dictionary in probes:
		var zyx: Array = probe["zyx"]
		var i: int = frame.index(_int(zyx[0]), _int(zyx[1]), _int(zyx[2]))
		var channel: String = probe["channel"]
		var bytes: PackedByteArray = frame.channels[channel]
		var value: int = bytes.decode_u16(i * 2) if channel == "region" else bytes.decode_u8(i)
		t.check_eq(value, _int(probe["value"]), "%s: %s at %s" % [name, channel, zyx])


func test_every_json_text_reaches_its_manifest_outcome(t: TestContext) -> void:
	for entry: Dictionary in _entries(_manifest(), "json"):
		var file: String = entry["file"]
		var text: String = FileAccess.get_file_as_string(DIR.path_join(file))
		var read: WireRead = WireJson.parse(text, _int(entry.get("max_bytes", 1 << 20)))
		var got: String = "accepted" if read.ok else "refused " + read.code
		t.check_eq(got, _want(entry), "%s (%s)" % [file, read.reason])


func test_the_client_catalogue_hashes_to_the_server_s(t: TestContext) -> void:
	t.check_eq(WireCatalogue.catalogue_hash(WireCatalogue.v0()), _catalogue(_manifest()), "v0's catalogue hash")


func test_the_asymmetric_frame_reads_x_fastest(t: TestContext) -> void:
	var data: PackedByteArray = FileAccess.get_file_as_bytes(DIR.path_join("frames/asymmetric.bin"))
	var read: WireRead = FrameDecoder.decode(data, WireCatalogue.v0(), _catalogue(_manifest()), 1 << 22)
	t.check(read.ok, "the asymmetric frame decodes")
	if not read.ok:
		return
	var frame: WireFrame = read.value
	var material: PackedByteArray = frame.channels["material"]
	t.check_eq(material.decode_u8(3), 2, "[z=0, y=0, x=3]: x varies fastest")
	t.check_eq(material.decode_u8(12), 5, "[z=1, y=0, x=0]")
	t.check_eq(frame.origin_um, [-1000, 2000, 400] as Array[int], "the grid's origin")


func test_a_number_written_as_a_float_is_listed_by_its_key(t: TestContext) -> void:
	var read: WireRead = WireJson.parse("{\"a\":5.0,\"b\":[1e3,2],\"c\":7}", 100)
	t.check(read.ok, "the text parses")
	t.check_eq(read.non_integer_keys, ["a", ""] as Array[String], "5.0 under a, 1e3 in an array")
