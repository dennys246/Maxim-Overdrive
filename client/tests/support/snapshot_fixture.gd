class_name SnapshotFixture
extends RefCounted
## A committed snapshot fixture (client/tests/fixtures/snapshots/, made by scripts/client_fixtures.py): a JSON header
## and gzip-compressed channel arrays, read into the CellSnapshot the renderer draws. A test fixture reader, not the
## protocol decoder: protocol v0 (step 7) isn't frozen, so this reads only the fixture container, and FIELDS.md beside
## the fixtures names every field it assumes, for step 7 to confirm or change. It lives under tests/ so nothing on
## the shipped path can come to depend on it.
##
## Every field is checked before any array is used; a fixture with any problem yields no snapshot and says why.
## JSON values arrive as Variants (and every number as a float, §4.1); each is type-checked and then assigned to a
## typed variable, the one conversion typed GDScript accepts without an unsafe cast.

const DIR: String = "res://tests/fixtures/snapshots"
const FORMAT: String = "overdrive-client-snapshot-fixture"
const VERSION: int = 0
const DTYPES: Dictionary[String, String] = {
	"material": "u8", "region": "u16", "crack": "u8", "surface_glow": "u8", "burning": "u8",
}
## Twice the alley's 1.84 MB frame: a header can't make the reader allocate more than this.
const MAX_DATA_BYTES: int = 4 * 1024 * 1024
const MAX_WHOLE: float = 9007199254740992.0

## Null when the fixture has problems.
var snapshot: CellSnapshot = null
## Actor id -> feet position in world metres (the tick message's actor table, as far as the renderer needs it).
var actors: Dictionary[int, Vector3] = {}
var problems: Array[String] = []


## The fixture called ``fixture_name`` under DIR.
static func named(fixture_name: String) -> SnapshotFixture:
	var header_path: String = DIR.path_join(fixture_name + ".json")
	var text: String = FileAccess.get_file_as_string(header_path)
	if text.is_empty():
		return failed("cannot read %s: %s" % [header_path, error_string(FileAccess.get_open_error())])
	var parsed: Variant = JSON.parse_string(text)
	if not parsed is Dictionary:
		return failed("%s is not a JSON object" % header_path)
	var header: Dictionary = parsed
	var data_name: String = text_of(header.get("data"))
	if data_name.is_empty() or data_name.get_file() != data_name:
		return failed("%s: data must be a file name beside it" % header_path)
	return parse(header, FileAccess.get_file_as_bytes(DIR.path_join(data_name)))


static func failed(why: String) -> SnapshotFixture:
	var out: SnapshotFixture = SnapshotFixture.new()
	out.problems.append(why)
	return out


## A fixture from its parsed header and its compressed data.
static func parse(header: Dictionary, compressed: PackedByteArray) -> SnapshotFixture:
	var out: SnapshotFixture = SnapshotFixture.new()
	out._read(header, compressed)
	if not out.problems.is_empty():
		out.snapshot = null
	return out


## True when ``value`` is a JSON whole number: an int, or a float with no fraction, at most 2^53 in size.
static func is_whole(value: Variant) -> bool:
	if value is int:
		return true
	if not value is float:
		return false
	var f: float = value
	return is_finite(f) and f == floorf(f) and absf(f) <= MAX_WHOLE


## ``value`` as an int when is_whole(value), else ``fallback``.
static func whole_of(value: Variant, fallback: int = -1) -> int:
	if not is_whole(value):
		return fallback
	if value is int:
		var i: int = value
		return i
	var f: float = value
	return int(f)


static func text_of(value: Variant) -> String:
	if value is String:
		var s: String = value
		return s
	return ""


## ``value`` as a list of ``n`` whole numbers, or empty when it isn't one.
static func wholes_of(value: Variant, n: int) -> Array[int]:
	var out: Array[int] = []
	if not value is Array:
		return out
	var items: Array = value
	if items.size() != n or not items.all(is_whole):
		return out
	for item: Variant in items:
		out.append(whole_of(item))
	return out


func _read(header: Dictionary, compressed: PackedByteArray) -> void:
	if text_of(header.get("format")) != FORMAT:
		problems.append("format is %s, not %s" % [header.get("format"), FORMAT])
		return
	if not is_whole(header.get("version")) or whole_of(header.get("version")) != VERSION:
		problems.append("version %s is not %d; this reader knows only %d" % [header.get("version"), VERSION, VERSION])
		return
	var snap: CellSnapshot = CellSnapshot.new()
	_read_shape(header, snap)
	_read_vocabularies(header, snap)
	_read_glow(header, snap)
	_read_actors(header)
	if not problems.is_empty():
		return
	var data: PackedByteArray = _inflate(header, compressed)
	if problems.is_empty():
		_read_channels(header, data, snap)
	if problems.is_empty():
		problems.append_array(snap.problems())
	snapshot = snap


func _read_shape(header: Dictionary, snap: CellSnapshot) -> void:
	var shape: Array[int] = wholes_of(header.get("shape"), 3)
	if shape.is_empty():
		problems.append("shape must be three whole numbers [nz, ny, nx], got %s" % [header.get("shape")])
		return
	snap.nz = shape[0]
	snap.ny = shape[1]
	snap.nx = shape[2]
	var cell: Variant = header.get("cell_m")
	if not cell is float:
		problems.append("cell_m must be a number, got %s" % [cell])
		return
	var cell_m: float = cell
	snap.cell_m = cell_m


func _read_vocabularies(header: Dictionary, snap: CellSnapshot) -> void:
	var regions: Variant = header.get("regions")
	var materials: Variant = header.get("materials")
	if not regions is Dictionary or not materials is Dictionary:
		problems.append("regions and materials must be objects")
		return
	var region_map: Dictionary = regions
	for key: Variant in region_map:
		var id_text: String = text_of(key)
		var region_name: String = text_of(region_map[key])
		if not (id_text.is_valid_int() and id_text.to_int() > 0 and not region_name.is_empty()):
			problems.append("regions: %s -> %s is not a positive id and a name" % [key, region_map[key]])
			return
		snap.region_names[id_text.to_int()] = region_name
	var material_map: Dictionary = materials
	for key: Variant in material_map:
		var material_name: String = text_of(key)
		if material_name.is_empty() or not is_whole(material_map[key]):
			problems.append("materials: %s -> %s is not a name and an id" % [key, material_map[key]])
			return
		snap.material_ids[material_name] = whole_of(material_map[key])


func _read_glow(header: Dictionary, snap: CellSnapshot) -> void:
	var glow: Variant = header.get("glow")
	if not glow is Dictionary:
		problems.append("glow must be an object")
		return
	var g: Dictionary = glow
	var calibration: Array[int] = wholes_of([g.get("offset_c"), g.get("scale_num"), g.get("scale_den")], 3)
	if calibration.is_empty() or calibration[2] <= 0:
		problems.append("glow needs whole offset_c, scale_num and scale_den, with scale_den > 0")
		return
	snap.glow_offset_c = float(calibration[0])
	snap.glow_scale_c_per_count = float(calibration[1]) / float(calibration[2])


func _read_actors(header: Dictionary) -> void:
	var listed: Variant = header.get("actors", [])
	if not listed is Array:
		problems.append("actors must be a list")
		return
	var items: Array = listed
	for actor: Variant in items:
		var a: Dictionary = {}
		if actor is Dictionary:
			a = actor
		var pos: Array[int] = wholes_of(a.get("pos_mm"), 3)
		if not is_whole(a.get("id")) or pos.is_empty():
			problems.append("actor %s needs a whole id and pos_mm [x, y, z]" % [actor])
			return
		if actors.has(whole_of(a.get("id"))):
			problems.append("actor %s appears twice" % [a.get("id")])
			return
		actors[whole_of(a.get("id"))] = Vector3(pos[0], pos[1], pos[2]) / 1000.0


func _inflate(header: Dictionary, compressed: PackedByteArray) -> PackedByteArray:
	# The compressed bytes are checked before Godot parses them: decompress prints its own ERROR on a corrupt stream.
	if _sha256(compressed) != text_of(header.get("data_gzip_sha256")):
		problems.append("the compressed data's SHA-256 is not %s" % [header.get("data_gzip_sha256")])
		return PackedByteArray()
	var size: int = whole_of(header.get("data_size"), 0)
	if size <= 0 or size > MAX_DATA_BYTES:
		problems.append("data_size %s is not a whole number in 1..%d" % [header.get("data_size"), MAX_DATA_BYTES])
		return PackedByteArray()
	var data: PackedByteArray = compressed.decompress_dynamic(MAX_DATA_BYTES, FileAccess.COMPRESSION_GZIP)
	if data.size() != size:
		problems.append("the data inflates to %d bytes, not %d" % [data.size(), size])
		return PackedByteArray()
	if _sha256(data) != text_of(header.get("data_sha256")):
		problems.append("the data's SHA-256 is not %s" % [header.get("data_sha256")])
		return PackedByteArray()
	return data


static func _sha256(bytes: PackedByteArray) -> String:
	var hashing: HashingContext = HashingContext.new()
	if hashing.start(HashingContext.HASH_SHA256) != OK or hashing.update(bytes) != OK:
		push_error("SnapshotFixture: SHA-256 is unavailable")
		return ""
	return hashing.finish().hex_encode()


func _read_channels(header: Dictionary, data: PackedByteArray, snap: CellSnapshot) -> void:
	var listed: Variant = header.get("channels")
	if not listed is Dictionary:
		problems.append("channels must be an object")
		return
	var channels: Dictionary = listed
	for channel: String in DTYPES:
		var spec: Dictionary = {}
		if channels.get(channel) is Dictionary:
			spec = channels[channel]
		if text_of(spec.get("dtype")) != DTYPES[channel]:
			problems.append("%s: dtype %s, not %s" % [channel, spec.get("dtype"), DTYPES[channel]])
			continue
		var offset: int = whole_of(spec.get("offset"))
		var size: int = whole_of(spec.get("size"))
		if offset < 0 or size < 0 or offset + size > data.size():
			problems.append("%s: offset %s and size %s don't lie inside the data" % [channel, spec.get("offset"), spec.get("size")])
			continue
		snap.channels[channel] = data.slice(offset, offset + size)
