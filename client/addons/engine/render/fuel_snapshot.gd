class_name FuelSnapshot
extends RefCounted
## One frame's fuel tables as the object pass reads them (docs/design/client_objects.md §3): the objects, their
## geometry per kind and their segments' state, column by column, plus the vocabularies that name kinds and recipes.
## This is the seam between whatever decodes fuel and what draws it, as CellSnapshot is for cells. Today the client
## test fixture fills it (client/tests/support/fuel_fixture.gd); step 7's decoder will fill the same object.
## RefCounted, not Resource: it is never saved or edited, and it frees itself when the last holder lets go.
##
## Columns are kept as the bytes that arrived, little-endian, keyed "<table>.<column>", so the per-frame segment
## columns upload as textures without a GDScript loop (§4.1). Only problems(), run when structure() changes, walks
## rows, and it reads each column once, never per row (a per-row lookup made it 29-41 ms at the world limits).

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
## fire_solid.md §1.3's world limits, the most a server sends: checked before any size is multiplied, and well inside
## what the drawing side encodes (a first segment row in 24 bits, an object row in 16, a texture height of 2,048).
const MAX_OBJECTS: int = 2000
const MAX_SEGMENTS: int = 20000
## The columns whose change is a structural change (§3.2): every objects column but state, the geometry tables and the
## segments' keys. The rest change every frame and are only held to their size (frame_problems).
const FRAME_COLUMNS: Array[String] = [
	"objects.state", "segments.surface_temperature_c", "segments.ignited_fraction", "segments.thickness_fraction",
	"segments.char_fraction",
]

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


## An f32 column as floats, decoded natively in one call.
func floats(table: String, name: String) -> PackedFloat32Array:
	return column(table, name).to_float32_array()


## The objects rows of one kind, in object order: geometry row i of that kind's table is object row geometry_rows(kind)[i]
## (problems() holds the tables to that). The one place an object's table is decided, so the pass, the flames and the
## checks can't disagree.
func geometry_rows(kind: String) -> PackedInt32Array:
	var out: Array[int] = []
	var id: int = kind_ids.get(kind, -1)
	var kinds: PackedByteArray = column("objects", "kind")
	for i: int in kinds.size():
		if kinds[i] == id:
			out.append(i)
	return PackedInt32Array(out)


## What a structural change compares (§3.2): the structural columns, the row counts and the vocabularies. Cheap to build
## (the arrays are shared, not copied) and compared natively; whoever draws holds the last drawn one.
func structure() -> Dictionary:
	var out: Dictionary = {"#rows": rows.duplicate(), "#kinds": kind_ids.duplicate(), "#recipes": recipe_ids.duplicate()}
	for key: String in columns:
		if not FRAME_COLUMNS.has(key):
			out[key] = columns[key]
	return out


## Every reason this snapshot's structure can't be drawn; empty when it can. ``region_names`` is the region map (id ->
## name), so a fuel object's region must be one the map knows. Run when structure() changes; frame_problems() runs on
## every frame.
func problems(region_names: Dictionary[int, String]) -> Array[String]:
	var out: Array[String] = _shape_problems()
	if not out.is_empty():
		return out
	out.append_array(_vocabulary_problems())
	out.append_array(_object_problems(region_names))
	out.append_array(_segment_key_problems())
	out.append_array(_geometry_problems())
	return out


## The per-frame check: the columns that change every frame hold their row counts' sizes (the structural check doesn't
## see them change), and state is 0 (live) or 1 (burnt out), the only values §3.2 defines.
func frame_problems() -> Array[String]:
	var spec: Dictionary[String, Dictionary] = tables()
	for key: String in FRAME_COLUMNS:
		var table: String = key.get_slice(".", 0)
		var dtype: String = spec[table][key.get_slice(".", 1)]
		var want: int = rows.get(table, 0) * DTYPE_BYTES[dtype]
		var got: PackedByteArray = columns.get(key, PackedByteArray())
		if got.size() != want:
			return ["%s has %d bytes, not %d" % [key, got.size(), want]]
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
	var limits: Dictionary[String, int] = {
		"objects": MAX_OBJECTS, "rods": MAX_OBJECTS, "slabs": MAX_OBJECTS, "segments": MAX_SEGMENTS,
	}
	var spec: Dictionary[String, Dictionary] = tables()
	for table: String in spec:
		if not rows.has(table) or rows[table] < 0 or rows[table] > limits[table]:
			out.append("%s has %s rows, outside 0..%d (fire_solid §1.3)" % [table, rows.get(table), limits[table]])
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
	for kind_name_: String in kind_ids:
		if not DRAWABLE_KINDS.has(kind_name_):
			out.append("kind %s is not one this client draws" % kind_name_)
	# A kind id is a u8 in objects.kind and a recipe id a u16 in objects.recipe_id (fire_solid §1.1).
	for pair: Array in [["kinds", kind_ids, 0xFF], ["recipes", recipe_ids, 0xFFFF]]:
		var vocabulary: Dictionary = pair[1]
		var seen: Dictionary[int, bool] = {}
		for name: String in vocabulary:
			var id: int = vocabulary[name]
			if id < 0 or id > pair[2]:
				out.append("%s %s has id %d, outside 0..%d" % [pair[0], name, id, pair[2]])
			if seen.has(id):
				out.append("two %s share id %d" % [pair[0], id])
			seen[id] = true
	return out


func _object_problems(region_names: Dictionary[int, String]) -> Array[String]:
	var out: Array[String] = []
	var oids: PackedByteArray = column("objects", "object_id")
	var recipes: PackedByteArray = column("objects", "recipe_id")
	var regions: PackedByteArray = column("objects", "region_id")
	var kinds: PackedByteArray = column("objects", "kind")
	var counts: PackedByteArray = column("objects", "segment_count")
	var lengths: PackedFloat32Array = floats("objects", "segment_length_m")
	var recipe_set: Array[int] = []
	recipe_set.assign(recipe_ids.values())
	var kind_set: Array[int] = []
	kind_set.assign(kind_ids.values())
	var total: int = 0
	var last_id: int = -1
	for i: int in rows["objects"]:
		var oid: int = oids.decode_u32(i * 4)
		if oid <= last_id:
			out.append("object row %d has id %d, not above the previous row's %d" % [i, oid, last_id])
		last_id = oid
		if not recipe_set.has(recipes.decode_u16(i * 2)):
			out.append("object row %d names recipe %d, which welcome's map doesn't" % [i, recipes.decode_u16(i * 2)])
		if not region_names.has(regions.decode_u16(i * 2)):
			out.append("object row %d names region %d, which the region map doesn't" % [i, regions.decode_u16(i * 2)])
		if not kind_set.has(kinds[i]):
			out.append("object row %d names kind %d, which welcome's vocabulary doesn't" % [i, kinds[i]])
		if not (is_finite(lengths[i]) and lengths[i] > 0.0):
			out.append("object row %d has segment length %s" % [i, lengths[i]])
		if counts.decode_u16(i * 2) == 0:
			out.append("object row %d has no segments" % i)
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
	var oids: PackedInt32Array = column("objects", "object_id").to_int32_array()
	for kind: String in DRAWABLE_KINDS:
		var want: Array[int] = []
		for row: int in geometry_rows(kind):
			want.append(oids[row])
		if column(kind + "s", "object_id").to_int32_array() != PackedInt32Array(want):
			out.append("%ss rows are not exactly the %s objects, in object order" % [kind, kind])
	out.append_array(_rod_problems())
	out.append_array(_slab_problems())
	return out


func _rod_problems() -> Array[String]:
	var out: Array[String] = []
	var origins: Array[PackedFloat32Array] = _vectors("rods", "origin_", "_m")
	var axes: Array[PackedFloat32Array] = _vectors("rods", "axis_", "")
	var lengths: PackedFloat32Array = floats("rods", "length_m")
	var radii: PackedFloat32Array = floats("rods", "radius_m")
	for r: int in rows["rods"]:
		var origin: Vector3 = _at(origins, r)
		var axis: Vector3 = _at(axes, r)
		var sizes: Vector2 = Vector2(lengths[r], radii[r])
		if not (origin.is_finite() and _is_unit(axis) and sizes.is_finite() and sizes.x > 0.0 and sizes.y > 0.0):
			out.append("rod row %d has bad geometry: origin %s, axis %s, length %s, radius %s"
				% [r, origin, axis, sizes.x, sizes.y])
	return out


func _slab_problems() -> Array[String]:
	var out: Array[String] = []
	var origins: Array[PackedFloat32Array] = _vectors("slabs", "origin_", "_m")
	var alongs: Array[PackedFloat32Array] = _vectors("slabs", "length_axis_", "")
	var acrosses: Array[PackedFloat32Array] = _vectors("slabs", "width_axis_", "")
	var size_columns: Array[PackedFloat32Array] = [
		floats("slabs", "length_m"), floats("slabs", "width_m"), floats("slabs", "thickness_m"),
	]
	for r: int in rows["slabs"]:
		var origin: Vector3 = _at(origins, r)
		var along: Vector3 = _at(alongs, r)
		var across: Vector3 = _at(acrosses, r)
		var sizes: Vector3 = _at(size_columns, r)
		var positive: bool = sizes.is_finite() and sizes.x > 0.0 and sizes.y > 0.0 and sizes.z > 0.0
		# Perpendicular too: the shaders' normals (MODEL_NORMAL_MATRIX) are right only for an orthogonal basis.
		var square: bool = absf(along.dot(across)) <= UNIT_TOLERANCE
		if not (origin.is_finite() and _is_unit(along) and _is_unit(across) and square and positive):
			out.append("slab row %d has bad geometry: origin %s, axes %s %s, sizes %s" % [r, origin, along, across, sizes])
	return out


## A vector's three f32 columns, decoded once.
func _vectors(table: String, prefix: String, suffix: String) -> Array[PackedFloat32Array]:
	return [
		floats(table, prefix + "x" + suffix), floats(table, prefix + "y" + suffix), floats(table, prefix + "z" + suffix),
	]


static func _at(xyz: Array[PackedFloat32Array], r: int) -> Vector3:
	return Vector3(xyz[0][r], xyz[1][r], xyz[2][r])


static func _is_unit(v: Vector3) -> bool:
	return v.is_finite() and absf(v.length() - 1.0) <= UNIT_TOLERANCE
