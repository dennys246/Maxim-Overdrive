class_name FrameDecoder
extends RefCounted
## The client's cell-frame decoder (client_rendering.md §4.1; world_v2.md §8): the twin of the server's
## src/simcore/protocol/grammar.py, with its checks in the same order and its refusal codes, held to the same golden
## fixtures (client/tests/fixtures/wire/manifest.json). Defence in depth (boundaries §5.3): a frame that fails any
## check yields nothing, never a crash and never a partly drawn world.
##
## A frame is [u32 header length][JSON header][arrays], little-endian. The checks:
## 1. the frame's length, the header length, and the header as ASCII, strict JSON (bad_shape, bad_json);
## 2. protocol first, so a newer frame is refused for its version (bad_version);
## 3. the header's closed schema (unknown_field, missing_field, unknown_kind, not_int, ...);
## 4. the catalogue hash against welcome's (bad_version);
## 5. the layout: each array the size its container and dtype give, back to back (bad_shape);
## 6. the extension rule: unknown optional grids, tables and channels ignored, unknown required ones refused
##    (unknown_field); a known channel identical to this build's (bad_shape); every required channel present
##    (missing_field).

const PROTOCOL: int = 0
const CELL_GRID: String = "cells"
const MAX_HEADER_BYTES: int = 64 * 1024
const MAX_EXTENT: int = 65535
const MAX_GRIDS: int = 8
const MAX_TABLES: int = 16
const MAX_ARRAYS: int = 64
const HEADER_KEYS: Array[String] = [
	"protocol", "kind", "tick", "shape", "regions_version", "catalogue", "compression", "grids", "tables", "arrays",
]
const GRID_KEYS: Array[String] = ["name", "required", "shape", "cell_size_um", "origin_um"]
const TABLE_KEYS: Array[String] = ["name", "required", "rows"]
const ARRAY_KEYS: Array[String] = ["channel", "of", "offset", "size", "uncompressed_size"]
const CHANNEL_KEYS: Array[String] = ["name", "unit", "dtype", "encoding", "required", "scale", "offset"]


## The frame in ``data``, read by this build's ``known`` channels (WireCatalogue.v0()) and held to the ``catalogue``
## hash welcome announced; ``read.value`` is the WireFrame when ``read.ok``.
static func decode(data: PackedByteArray, known: Array[Dictionary], catalogue: String, max_bytes: int) -> WireRead:
	var read: WireRead = WireRead.new()
	var header: Dictionary = _header(read, data, max_bytes)
	if not read.ok:
		return read
	if header["catalogue"] != catalogue:
		return WireRead.refused("bad_version", "frame: a catalogue hash other than welcome's")
	var containers: Dictionary = _containers(read, header)
	var payload: int = data.size() - 4 - data.decode_u32(0)
	if read.ok:
		_layout(read, header, containers, payload)
	var taken: Array[Dictionary] = []
	var ignored: Array[String] = []
	if read.ok:
		ignored = _extension(read, header, containers, known, taken)
	if read.ok:
		_required(read, taken, known)
	if read.ok:
		read.value = _frame(header, taken, ignored, data.slice(4 + data.decode_u32(0)))
	return read


## Checks 1 to 3: the header, read to typed values (ints as int, channels as typed descriptions).
static func _header(read: WireRead, data: PackedByteArray, max_bytes: int) -> Dictionary:
	if data.size() < 4 or data.size() > max_bytes:
		read.refuse("bad_shape", "frame: %d bytes, outside [4, %d]" % [data.size(), max_bytes])
		return {}
	var length: int = data.decode_u32(0)
	if length <= 0 or length > mini(MAX_HEADER_BYTES, data.size() - 4):
		read.refuse("bad_shape", "frame: a header length of %d" % length)
		return {}
	var bytes: PackedByteArray = data.slice(4, 4 + length)
	for b: int in bytes:
		if b > 0x7F:
			read.refuse("bad_json", "frame: a header byte outside ASCII")
			return {}
	var json: WireRead = WireJson.parse(bytes, MAX_HEADER_BYTES)
	if not json.ok:
		read.refuse(json.code, json.reason)
		return {}
	if not json.value is Dictionary:
		read.refuse("bad_shape", "frame: the header is not a JSON object")
		return {}
	var raw: Dictionary = json.value
	var version: int = WireFields.version(read, raw.get("protocol"), json.non_integer_keys.has("protocol"))
	if read.ok and version != PROTOCOL:
		read.refuse("bad_version", "frame: protocol %d; this reader knows %d" % [version, PROTOCOL])
	if read.ok and not json.non_integer_keys.is_empty():  # O62, after the version as strict_json.integers_only
		read.refuse("not_int", "frame header: a number with a point or an exponent; it holds integers only")
	if not read.ok:
		return {}
	return _read_header(read, raw)


static func _read_header(read: WireRead, raw: Dictionary) -> Dictionary:
	var h: Dictionary = WireFields.keys(read, raw, "frame header", HEADER_KEYS)
	if not read.ok:
		return {}
	var out: Dictionary = {}
	out["kind"] = WireFields.choice(read, h["kind"], "kind", ["full"])
	out["tick"] = WireFields.whole(read, h["tick"], "tick", 0, WireFields.INT_MAX)
	out["shape"] = WireFields.wholes(read, h["shape"], "shape", 3, 1, MAX_EXTENT)
	out["regions_version"] = WireFields.whole(read, h["regions_version"], "regions_version", 0, WireFields.INT_MAX)
	out["catalogue"] = WireFields.digest(read, h["catalogue"], "catalogue")
	out["compression"] = WireFields.choice(read, h["compression"], "compression", ["none"])
	var grids: Array[Dictionary] = []
	for g: Variant in WireFields.list_of(read, h["grids"], "grids", MAX_GRIDS):
		grids.append(_grid(read, g))
	var tables: Array[Dictionary] = []
	for t: Variant in WireFields.list_of(read, h["tables"], "tables", MAX_TABLES):
		tables.append(_table(read, t))
	var arrays: Array[Dictionary] = []
	for a: Variant in WireFields.list_of(read, h["arrays"], "arrays", MAX_ARRAYS):
		arrays.append(_array(read, a))
	out["grids"] = grids
	out["tables"] = tables
	out["arrays"] = arrays
	return out


static func _grid(read: WireRead, raw: Variant) -> Dictionary:
	var g: Dictionary = WireFields.keys(read, raw, "grid", GRID_KEYS)
	if not read.ok:
		return {}
	return {
		"name": WireFields.identity(read, g["name"], "grid name"),
		"required": WireFields.flag(read, g["required"], "grid required"),
		"shape": WireFields.wholes(read, g["shape"], "grid shape", 3, 1, MAX_EXTENT),
		"cell_size_um": WireFields.whole(read, g["cell_size_um"], "cell_size_um", 1, WireFields.INT_MAX),
		"origin_um": WireFields.wholes(read, g["origin_um"], "origin_um", 3, -WireFields.INT_MAX, WireFields.INT_MAX),
	}


static func _table(read: WireRead, raw: Variant) -> Dictionary:
	var t: Dictionary = WireFields.keys(read, raw, "table", TABLE_KEYS)
	if not read.ok:
		return {}
	return {
		"name": WireFields.identity(read, t["name"], "table name"),
		"required": WireFields.flag(read, t["required"], "table required"),
		"rows": WireFields.whole(read, t["rows"], "rows", 0, WireFields.INT_MAX),
	}


static func _array(read: WireRead, raw: Variant) -> Dictionary:
	var a: Dictionary = WireFields.keys(read, raw, "array", ARRAY_KEYS)
	if not read.ok:
		return {}
	return {
		"channel": _channel(read, a["channel"]),
		"of": WireFields.identity(read, a["of"], "of"),
		"offset": WireFields.whole(read, a["offset"], "offset", 0, WireFields.INT_MAX),
		"size": WireFields.whole(read, a["size"], "size", 0, WireFields.INT_MAX),
		"uncompressed_size": WireFields.whole(read, a["uncompressed_size"], "uncompressed_size", 0, WireFields.INT_MAX),
	}


## A channel's description, typed so it compares equal to WireCatalogue's; raw means scale 1/1 and offset 0/1, and a
## denominator is positive (catalogue.Channel's own checks).
static func _channel(read: WireRead, raw: Variant) -> Dictionary:
	var c: Dictionary = WireFields.keys(read, raw, "channel", CHANNEL_KEYS)
	if not read.ok:
		return {}
	var limit: int = WireFields.INT_MAX
	var out: Dictionary = {
		"name": WireFields.identity(read, c["name"], "channel name"),
		"unit": WireFields.identity(read, c["unit"], "unit"),
		"dtype": WireFields.choice(read, c["dtype"], "dtype", WireCatalogue.DTYPES),
		"encoding": WireFields.choice(read, c["encoding"], "encoding", WireCatalogue.ENCODINGS),
		"required": WireFields.flag(read, c["required"], "channel required"),
		"scale": WireFields.wholes(read, c["scale"], "scale", 2, -limit, limit),
		"offset": WireFields.wholes(read, c["offset"], "offset", 2, -limit, limit),
	}
	if not read.ok:
		return {}
	var scale: Array[int] = out["scale"]
	var offset: Array[int] = out["offset"]
	if out["encoding"] == "raw" and (scale != [1, 1] or offset != [0, 1]):
		read.refuse("bad_shape", "channel %s: raw, so scale 1/1 and offset 0/1" % out["name"])
	elif scale[1] <= 0 or offset[1] <= 0:
		read.refuse("bad_shape", "channel %s: a rational's denominator is positive" % out["name"])
	return out


## Each grid and table by name: [element count, known, required].
static func _containers(read: WireRead, header: Dictionary) -> Dictionary:
	var out: Dictionary = {}
	var grids: Array[Dictionary] = header["grids"]
	var tables: Array[Dictionary] = header["tables"]
	for g: Dictionary in grids:
		var shape: Array[int] = g["shape"]
		out[g["name"]] = [shape[0] * shape[1] * shape[2], g["name"] == CELL_GRID, g["required"]]
	for t: Dictionary in tables:
		out[t["name"]] = [t["rows"], false, t["required"]]
	if out.size() != grids.size() + tables.size():
		read.refuse("bad_shape", "frame: two grids or tables share a name")
		return out
	var cells: Array[Dictionary] = []
	for g: Dictionary in grids:
		if g["name"] == CELL_GRID:
			cells.append(g)
	if cells.is_empty():
		read.refuse("missing_field", "frame: no cells grid")
	elif cells[0]["shape"] != header["shape"]:
		read.refuse("bad_shape", "frame: the cells grid's shape is not the frame's")
	return out


static func _layout(read: WireRead, header: Dictionary, containers: Dictionary, payload: int) -> void:
	var at: int = 0
	var arrays: Array[Dictionary] = header["arrays"]
	for a: Dictionary in arrays:
		var channel: Dictionary = a["channel"]
		if not containers.has(a["of"]):
			read.refuse("bad_shape", "channel %s belongs to no grid or table named %s" % [channel["name"], a["of"]])
			return
		var container: Array = containers[a["of"]]
		var count: int = container[0]
		var size: int = count * WireCatalogue.DTYPE_BYTES[channel["dtype"]]
		if a["offset"] != at or a["size"] != size or a["uncompressed_size"] != size:
			read.refuse("bad_shape", "channel %s is not %d bytes at offset %d" % [channel["name"], size, at])
			return
		at += size
	if at != payload:
		read.refuse("bad_shape", "frame: the arrays hold %d bytes; the payload is %d" % [at, payload])


## Check 6: fills ``taken`` with the arrays this reader takes and returns what it ignored, in header order.
static func _extension(
	read: WireRead, header: Dictionary, containers: Dictionary, known: Array[Dictionary], taken: Array[Dictionary]
) -> Array[String]:
	var ignored: Array[String] = []
	var grids: Array[Dictionary] = header["grids"]
	var tables: Array[Dictionary] = header["tables"]
	for g: Dictionary in grids:
		if g["name"] != CELL_GRID:
			if g["required"]:
				read.refuse("unknown_field", "frame: an unknown required grid %s" % g["name"])
				return ignored
			ignored.append("grid:%s" % g["name"])
	for t: Dictionary in tables:
		if t["required"]:
			read.refuse("unknown_field", "frame: an unknown required table %s" % t["name"])
			return ignored
		ignored.append("table:%s" % t["name"])
	var by_name: Dictionary = {}
	for c: Dictionary in known:
		by_name[c["name"]] = c
	var arrays: Array[Dictionary] = header["arrays"]
	for a: Dictionary in arrays:
		var channel: Dictionary = a["channel"]
		var container: Array = containers[a["of"]]
		if not container[1]:
			continue  # it belongs to an ignored grid or table
		if by_name.has(channel["name"]):
			var mine: Dictionary = by_name[channel["name"]]
			if not _same_channel(channel, mine):
				read.refuse("bad_shape", "channel %s differs from this reader's: a name is an identity" % channel["name"])
				return ignored
			taken.append(a)
		elif channel["required"]:
			read.refuse("unknown_field", "frame: an unknown required channel %s" % channel["name"])
			return ignored
		else:
			ignored.append("channel:%s" % channel["name"])
	return ignored


static func _same_channel(a: Dictionary, b: Dictionary) -> bool:
	for key: String in CHANNEL_KEYS:
		if a[key] != b[key]:
			return false
	return true


static func _required(read: WireRead, taken: Array[Dictionary], known: Array[Dictionary]) -> void:
	var names: Array[String] = []
	for a: Dictionary in taken:
		var channel: Dictionary = a["channel"]
		if names.has(channel["name"]):
			read.refuse("bad_shape", "frame: a channel appears twice")
			return
		names.append(channel["name"])
	for c: Dictionary in known:
		if c["required"] and not names.has(c["name"]):
			read.refuse("missing_field", "frame: no %s channel" % c["name"])
			return


static func _frame(
	header: Dictionary, taken: Array[Dictionary], ignored: Array[String], payload: PackedByteArray
) -> WireFrame:
	var frame: WireFrame = WireFrame.new()
	var shape: Array[int] = header["shape"]
	frame.nz = shape[0]
	frame.ny = shape[1]
	frame.nx = shape[2]
	frame.tick = header["tick"]
	frame.regions_version = header["regions_version"]
	var grids: Array[Dictionary] = header["grids"]
	for g: Dictionary in grids:
		if g["name"] == CELL_GRID:
			frame.cell_size_um = g["cell_size_um"]
			frame.origin_um = g["origin_um"]
	for a: Dictionary in taken:
		var channel: Dictionary = a["channel"]
		var start: int = a["offset"]
		var size: int = a["size"]
		frame.channels[channel["name"]] = payload.slice(start, start + size)
	frame.ignored = ignored
	return frame
