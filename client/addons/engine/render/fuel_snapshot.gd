class_name FuelSnapshot
extends RefCounted
## One frame's fuel tables as the object pass reads them (docs/design/client_objects.md §3): the objects, their
## geometry per kind and their segments' state, column by column, plus the vocabularies that name kinds and recipes.
## This is the seam between whatever decodes fuel and what draws it, as CellSnapshot is for cells. Today the client
## test fixture fills it (client/tests/support/fuel_fixture.gd); step 7's decoder will fill the same object.
## RefCounted, not Resource: it is never saved or edited, and it frees itself when the last holder lets go.
##
## Columns are kept as the bytes that arrived, little-endian, keyed "<table>.<column>", so the per-frame segment
## columns upload as textures without a GDScript loop (§4.1). Only problems(), run when the trigger bytes change,
## walks rows.

## client_objects.md §3.2 and §3.3: each table's columns and their dtypes, in wire order.
const OBJECTS: Dictionary[String, String] = {
	"object_id": "u32", "recipe_id": "u16", "region_id": "u16", "kind": "u8", "state": "u8",
	"segment_count": "u16", "segment_length_m": "f32",
}
const RODS: Dictionary[String, String] = {
	"object_id": "u32", "origin_x_m": "f32", "origin_y_m": "f32", "origin_z_m": "f32",
	"axis_x": "f32", "axis_y": "f32", "axis_z": "f32", "length_m": "f32", "radius_m": "f32",
}
const SLABS: Dictionary[String, String] = {
	"object_id": "u32", "origin_x_m": "f32", "origin_y_m": "f32", "origin_z_m": "f32",
	"length_axis_x": "f32", "length_axis_y": "f32", "length_axis_z": "f32",
	"width_axis_x": "f32", "width_axis_y": "f32", "width_axis_z": "f32",
	"length_m": "f32", "width_m": "f32", "thickness_m": "f32",
}
const SEGMENTS: Dictionary[String, String] = {
	"object_id": "u32", "seg": "u16", "surface_temperature_c": "f16",
	"ignited_fraction": "u8", "thickness_fraction": "u8", "char_fraction": "u8",
}
const DTYPE_BYTES: Dictionary[String, int] = {"u8": 1, "u16": 2, "u32": 4, "f16": 2, "f32": 4}
## The kinds this client can draw. A frame naming another is refused: a new kind is a protocol bump
## (client_rendering.md §4.1), never something an old client guesses at.
const DRAWABLE_KINDS: Array[String] = ["rod", "slab"]
## How far a unit axis may be from length 1 (client_objects.md §3.2).
const UNIT_TOLERANCE: float = 1e-6

## Rows per table: "objects", "rods", "slabs", "segments".
var rows: Dictionary[String, int] = {}
## "<table>.<column>" -> the column's little-endian bytes.
var columns: Dictionary[String, PackedByteArray] = {}
## Kind name -> id and recipe name -> id, from welcome's vocabularies.
var kind_ids: Dictionary[String, int] = {}
var recipe_ids: Dictionary[String, int] = {}


## Each table's column spec, by table name.
static func tables() -> Dictionary[String, Dictionary]:
	return {"objects": OBJECTS, "rods": RODS, "slabs": SLABS, "segments": SEGMENTS}


func column(table: String, name: String) -> PackedByteArray:
	return columns.get("%s.%s" % [table, name], PackedByteArray())


## The bytes whose change means the structure changed (§3.2): every objects column but state, the geometry tables
## and the segments' keys. A native compare against the last frame's decides whether problems() and the rebuild run.
func trigger_bytes() -> PackedByteArray:
	var out: PackedByteArray = PackedByteArray()
	for table: String in ["objects", "rods", "slabs"]:
		var spec: Dictionary = tables()[table]
		for name: String in spec:
			if not (table == "objects" and name == "state"):
				out.append_array(column(table, name))
	out.append_array(column("segments", "object_id"))
	out.append_array(column("segments", "seg"))
	return out


## Every reason this snapshot can't be drawn; empty when it can. ``region_names`` is the region map (id -> name), so a
## fuel object's region must be one the map knows. Run when trigger_bytes() changes; state_problems() runs every frame.
func problems(region_names: Dictionary[int, String]) -> Array[String]:
	var out: Array[String] = _shape_problems()
	if not out.is_empty():
		return out
	out.append_array(_vocabulary_problems())
	out.append_array(_object_problems(region_names))
	out.append_array(_segment_key_problems())
	out.append_array(_geometry_problems())
	return out


## The one per-frame check: state is 0 (live) or 1 (burnt out), the only values §3.2 defines.
func state_problems() -> Array[String]:
	var state: PackedByteArray = column("objects", "state")
	for i: int in state.size():
		if state[i] > 1:
			return ["object row %d has state %d; only 0 and 1 are defined" % [i, state[i]]]
	return []


## Each object's first row in the segments table, in object order.
func first_rows() -> PackedInt32Array:
	var counts: PackedByteArray = column("objects", "segment_count")
	var n: int = rows.get("objects", 0)
	var out: PackedInt32Array = PackedInt32Array()
	if out.resize(n) != OK:
		push_error("FuelSnapshot: cannot allocate %d first rows" % n)
		return out
	var running: int = 0
	for i: int in n:
		out[i] = running
		running += counts.decode_u16(i * 2)
	return out


func _shape_problems() -> Array[String]:
	var out: Array[String] = []
	var spec: Dictionary[String, Dictionary] = tables()
	for table: String in spec:
		if not rows.has(table) or rows[table] < 0:
			out.append("no row count for %s" % table)
			continue
		var cols: Dictionary = spec[table]
		for name: String in cols:
			var dtype: String = cols[name]
			var want: int = rows[table] * DTYPE_BYTES[dtype]
			var got: int = column(table, name).size()
			if got != want:
				out.append("%s.%s has %d bytes, not %d" % [table, name, got, want])
	return out


func _vocabulary_problems() -> Array[String]:
	var out: Array[String] = []
	for kind_name: String in kind_ids:
		if not DRAWABLE_KINDS.has(kind_name):
			out.append("kind %s is not one this client draws" % kind_name)
	return out


func _object_problems(region_names: Dictionary[int, String]) -> Array[String]:
	var out: Array[String] = []
	var counts: PackedByteArray = column("objects", "segment_count")
	var total: int = 0
	for i: int in rows["objects"]:
		var recipe: int = column("objects", "recipe_id").decode_u16(i * 2)
		var region: int = column("objects", "region_id").decode_u16(i * 2)
		var kind: int = column("objects", "kind")[i]
		if not recipe_ids.values().has(recipe):
			out.append("object row %d names recipe %d, which welcome's map doesn't" % [i, recipe])
		if not region_names.has(region):
			out.append("object row %d names region %d, which the region map doesn't" % [i, region])
		if not kind_ids.values().has(kind):
			out.append("object row %d names kind %d, which welcome's vocabulary doesn't" % [i, kind])
		var length: float = column("objects", "segment_length_m").decode_float(i * 4)
		if not (is_finite(length) and length > 0.0):
			out.append("object row %d has segment length %s" % [i, length])
		total += counts.decode_u16(i * 2)
	if total != rows["segments"]:
		out.append("segment counts sum to %d, but there are %d segment rows" % [total, rows["segments"]])
	return out


## The segments' keys must be exactly the ones the objects imply: each object's segments 0..count-1, in object order.
## This also catches counts that sum right but are spread over the wrong objects.
func _segment_key_problems() -> Array[String]:
	if rows["segments"] != _implied_segment_rows():
		return []  # _object_problems has already reported the mismatch
	var want_oid: PackedByteArray = PackedByteArray()
	var want_seg: PackedByteArray = PackedByteArray()
	var err: int = want_oid.resize(rows["segments"] * 4) | want_seg.resize(rows["segments"] * 2)
	if err != OK:
		return ["cannot allocate the implied segment keys"]
	var row: int = 0
	var oids: PackedByteArray = column("objects", "object_id")
	var counts: PackedByteArray = column("objects", "segment_count")
	for i: int in rows["objects"]:
		for k: int in counts.decode_u16(i * 2):
			want_oid.encode_u32(row * 4, oids.decode_u32(i * 4))
			want_seg.encode_u16(row * 2, k)
			row += 1
	if want_oid != column("segments", "object_id") or want_seg != column("segments", "seg"):
		return ["the segments' keys are not the ones the objects' counts imply"]
	return []


func _implied_segment_rows() -> int:
	var total: int = 0
	var counts: PackedByteArray = column("objects", "segment_count")
	for i: int in rows["objects"]:
		total += counts.decode_u16(i * 2)
	return total


func _geometry_problems() -> Array[String]:
	var out: Array[String] = []
	var expected: Dictionary[String, Array] = {"rods": [] as Array[int], "slabs": [] as Array[int]}
	for i: int in rows["objects"]:
		var kind: int = column("objects", "kind")[i]
		var kind_name: String = _kind_name(kind)
		if kind_name in ["rod", "slab"]:
			var ids: Array[int] = expected[kind_name + "s"]
			ids.append(column("objects", "object_id").decode_u32(i * 4))
	for table: String in expected:
		var got: Array[int] = []
		for r: int in rows[table]:
			got.append(column(table, "object_id").decode_u32(r * 4))
		var want: Array[int] = expected[table]
		if got != want:
			out.append("%s rows are not exactly the %s objects, in object order" % [table, table.trim_suffix("s")])
	out.append_array(_rod_problems())
	out.append_array(_slab_problems())
	return out


func _rod_problems() -> Array[String]:
	var out: Array[String] = []
	for r: int in rows["rods"]:
		var axis: Vector3 = _vector("rods", "axis_", "", r)
		var origin: Vector3 = _vector("rods", "origin_", "_m", r)
		var length: float = column("rods", "length_m").decode_float(r * 4)
		var radius: float = column("rods", "radius_m").decode_float(r * 4)
		if not (origin.is_finite() and _is_unit(axis) and length > 0.0 and radius > 0.0):
			out.append("rod row %d has bad geometry: origin %s, axis %s, length %s, radius %s"
				% [r, origin, axis, length, radius])
	return out


func _slab_problems() -> Array[String]:
	var out: Array[String] = []
	for r: int in rows["slabs"]:
		var origin: Vector3 = _vector("slabs", "origin_", "_m", r)
		var along: Vector3 = _vector("slabs", "length_axis_", "", r)
		var across: Vector3 = _vector("slabs", "width_axis_", "", r)
		var sizes: Vector3 = Vector3(
			column("slabs", "length_m").decode_float(r * 4),
			column("slabs", "width_m").decode_float(r * 4),
			column("slabs", "thickness_m").decode_float(r * 4))
		var positive: bool = sizes.is_finite() and sizes.x > 0.0 and sizes.y > 0.0 and sizes.z > 0.0
		if not (origin.is_finite() and _is_unit(along) and _is_unit(across) and positive):
			out.append("slab row %d has bad geometry: origin %s, axes %s %s, sizes %s" % [r, origin, along, across, sizes])
	return out


func _kind_name(kind: int) -> String:
	for kind_name: String in kind_ids:
		if kind_ids[kind_name] == kind:
			return kind_name
	return ""


func _vector(table: String, prefix: String, suffix: String, r: int) -> Vector3:
	return Vector3(
		column(table, prefix + "x" + suffix).decode_float(r * 4),
		column(table, prefix + "y" + suffix).decode_float(r * 4),
		column(table, prefix + "z" + suffix).decode_float(r * 4))


func _is_unit(v: Vector3) -> bool:
	return v.is_finite() and absf(v.length() - 1.0) <= UNIT_TOLERANCE
