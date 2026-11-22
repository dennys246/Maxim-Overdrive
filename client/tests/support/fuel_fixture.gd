class_name FuelFixture
extends RefCounted
## A committed fuel fixture (client/tests/fixtures/fuel/, made by scripts/fuel_fixtures.py): a JSON header and
## gzip-compressed columns, read into the FuelSnapshot the object pass draws. A test fixture reader, not the protocol
## decoder: steps 6.0b and 7 aren't built, so this reads only the fixture container, whose tables follow
## docs/design/client_objects.md §3 column for column. It lives under tests/ so nothing shipped depends on it.
##
## Every field is checked before any column is used; a fixture with any problem yields no snapshot and says why.

const DIR: String = "res://tests/fixtures/fuel"
const FORMAT: String = "overdrive-client-fuel-fixture"
const VERSION: int = 0
## Far above the world limits' 356,000 bytes of fuel tables (client_objects.md §3.5).
const MAX_DATA_BYTES: int = 1024 * 1024

## Null when the fixture has problems.
var snapshot: FuelSnapshot = null
## The fuel objects' regions, id -> name, which come after the cell fixture's.
var region_names: Dictionary[int, String] = {}
var problems: Array[String] = []


static func named(fixture_name: String) -> FuelFixture:
	var header_path: String = DIR.path_join(fixture_name + ".json")
	var text: String = FileAccess.get_file_as_string(header_path)
	if text.is_empty():
		return failed("cannot read %s: %s" % [header_path, error_string(FileAccess.get_open_error())])
	var parsed: Variant = JSON.parse_string(text)
	if not parsed is Dictionary:
		return failed("%s is not a JSON object" % header_path)
	var header: Dictionary = parsed
	var data_name: String = SnapshotFixture.text_of(header.get("data"))
	if data_name.is_empty() or data_name.get_file() != data_name:
		return failed("%s: data must be a file name beside it" % header_path)
	return parse(header, FileAccess.get_file_as_bytes(DIR.path_join(data_name)))


static func failed(why: String) -> FuelFixture:
	var out: FuelFixture = FuelFixture.new()
	out.problems.append(why)
	return out


static func parse(header: Dictionary, compressed: PackedByteArray) -> FuelFixture:
	var out: FuelFixture = FuelFixture.new()
	out._read(header, compressed)
	if not out.problems.is_empty():
		out.snapshot = null
	return out


func _read(header: Dictionary, compressed: PackedByteArray) -> void:
	if SnapshotFixture.text_of(header.get("format")) != FORMAT:
		problems.append("format is %s, not %s" % [header.get("format"), FORMAT])
		return
	var version: Variant = header.get("version")
	if not SnapshotFixture.is_whole(version) or SnapshotFixture.whole_of(version) != VERSION:
		problems.append("version %s is not %d; this reader knows only %d" % [version, VERSION, VERSION])
		return
	var snap: FuelSnapshot = FuelSnapshot.new()
	snap.kind_ids = _ids(header, "kinds")
	snap.recipe_ids = _ids(header, "recipes")
	_read_regions(header)
	if not problems.is_empty():
		return
	var data: PackedByteArray = SnapshotFixture.inflate(header, compressed, MAX_DATA_BYTES, problems)
	if problems.is_empty():
		_read_tables(header, data, snap)
	if problems.is_empty():
		problems.append_array(snap.problems(region_names))
		problems.append_array(snap.frame_problems())
	snapshot = snap


## A name -> id vocabulary (welcome's kinds or recipes).
func _ids(header: Dictionary, key: String) -> Dictionary[String, int]:
	var out: Dictionary[String, int] = {}
	var listed: Variant = header.get(key)
	if not listed is Dictionary:
		problems.append("%s must be an object" % key)
		return out
	var vocabulary: Dictionary = listed
	for name: Variant in vocabulary:
		var text: String = SnapshotFixture.text_of(name)
		if text.is_empty() or not SnapshotFixture.is_whole(vocabulary[name]):
			problems.append("%s: %s -> %s is not a name and an id" % [key, name, vocabulary[name]])
			return out
		out[text] = SnapshotFixture.whole_of(vocabulary[name])
	return out


func _read_regions(header: Dictionary) -> void:
	var listed: Variant = header.get("regions")
	if not listed is Dictionary:
		problems.append("regions must be an object")
		return
	var regions: Dictionary = listed
	for key: Variant in regions:
		var id_text: String = SnapshotFixture.text_of(key)
		var region_name: String = SnapshotFixture.text_of(regions[key])
		if not (id_text.is_valid_int() and id_text.to_int() > 0 and not region_name.is_empty()):
			problems.append("regions: %s -> %s is not a positive id and a name" % [key, regions[key]])
			return
		region_names[id_text.to_int()] = region_name


func _read_tables(header: Dictionary, data: PackedByteArray, snap: FuelSnapshot) -> void:
	var listed: Variant = header.get("tables")
	if not listed is Dictionary:
		problems.append("tables must be an object")
		return
	var tables: Dictionary = listed
	var specs: Dictionary[String, Dictionary] = FuelSnapshot.tables()
	for table: String in specs:
		if not tables.get(table) is Dictionary:
			problems.append("no %s table" % table)
			continue
		var entry: Dictionary = tables[table]
		if not SnapshotFixture.is_whole(entry.get("rows")) or SnapshotFixture.whole_of(entry.get("rows")) < 0:
			problems.append("%s: rows must be a whole number" % table)
			continue
		snap.rows[table] = SnapshotFixture.whole_of(entry.get("rows"))
		_read_columns(table, entry.get("columns"), specs[table], data, snap)


func _read_columns(table: String, listed: Variant, spec: Dictionary, data: PackedByteArray, snap: FuelSnapshot) -> void:
	if not listed is Dictionary:
		problems.append("%s: columns must be an object" % table)
		return
	var cols: Dictionary = listed
	for name: String in spec:
		if not cols.get(name) is Dictionary:
			problems.append("%s.%s is missing" % [table, name])
			continue
		var col: Dictionary = cols[name]
		var dtype: String = spec[name]
		if SnapshotFixture.text_of(col.get("dtype")) != dtype:
			problems.append("%s.%s is %s, not %s" % [table, name, col.get("dtype"), dtype])
			continue
		var offset: int = SnapshotFixture.whole_of(col.get("offset"))
		var size: int = SnapshotFixture.whole_of(col.get("size"))
		if offset < 0 or size < 0 or offset + size > data.size():
			problems.append("%s.%s spans %s..%s, outside the data" % [table, name, col.get("offset"), col.get("size")])
			continue
		snap.columns["%s.%s" % [table, name]] = data.slice(offset, offset + size)
