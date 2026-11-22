class_name FuelGeometry
extends RefCounted
## Fuel objects' instance transforms from their geometry rows (docs/design/client_objects.md §3.2): the one place the
## object pass turns metres in the world's frame into Godot transforms, through IsoCamera.to_godot, the GDScript half
## of the one axis mapping (the shaders' axes.gdshaderinc is the other). The transforms are in Godot's frame, so the
## MultiMesh's culling box is where the objects are.
##
## Engine why: each function returns a MultiMesh buffer, 12 floats per instance (the 3×4 transform, row by row), which
## FuelPass assigns in one call. Setting instances one by one, with the columns looked up per row, cost 52-71 ms at the
## world limits (review P-B1); a column is decoded once here, natively, and each row is plain float reads.

## Which world axis a perpendicular is built against, unless the object's axis is nearly parallel to it.
const UP: Vector3 = Vector3(0.0, 0.0, 1.0)
const EAST: Vector3 = Vector3(1.0, 0.0, 0.0)
## Floats per instance in a MultiMesh TRANSFORM_3D buffer with no colour or custom data.
const FLOATS: int = 12
## A Phase 1 flame's width over a rod: four radii, at least this many metres `[engineering]`.
const MIN_ROD_FLAME_M: float = 0.04


## One instance per rods row: a unit cylinder along local y, scaled to the rod's length and radius.
static func rod_buffer(snap: FuelSnapshot) -> PackedFloat32Array:
	var rods: Rods = Rods.new(snap)
	var out: PackedFloat32Array = _sized(rods.lengths.size())
	for r: int in rods.lengths.size():
		var axis: Vector3 = rods.axis(r)
		var length: float = rods.lengths[r]
		var radius: float = rods.radii[r]
		var across: Vector3 = axis.cross(EAST if absf(axis.dot(UP)) > 0.9 else UP).normalized()
		var other: Vector3 = across.cross(axis)  # across × axis, so (across, axis, other) is right-handed
		var basis: Basis = Basis(IsoCamera.to_godot(across) * radius, IsoCamera.to_godot(axis) * length,
			IsoCamera.to_godot(other) * radius)
		_put(out, r, basis, IsoCamera.to_godot(rods.origin(r) + axis * length * 0.5))
	return out


## One instance per slabs row: a unit box centred at the origin, length along local x, thickness along y, width along
## z. A slab spans origin to origin + L·length axis + W·width axis + T·normal, normal = length axis × width axis
## (fire_solid §1.1: the segmented face is the one at origin + T·normal). Local z is the negated width axis, so the
## basis stays right-handed and the faces keep their winding.
static func slab_buffer(snap: FuelSnapshot) -> PackedFloat32Array:
	var slabs: Slabs = Slabs.new(snap)
	var out: PackedFloat32Array = _sized(slabs.lengths.size())
	for r: int in slabs.lengths.size():
		var along: Vector3 = slabs.along(r)
		var across: Vector3 = slabs.across(r)
		var normal: Vector3 = along.cross(across)
		var sizes: Vector3 = Vector3(slabs.lengths[r], slabs.widths[r], slabs.thicknesses[r])
		var basis: Basis = Basis(IsoCamera.to_godot(along) * sizes.x, IsoCamera.to_godot(normal) * sizes.z,
			IsoCamera.to_godot(-across) * sizes.y)
		var centre: Vector3 = slabs.origin(r) + (along * sizes.x + across * sizes.y + normal * sizes.z) * 0.5
		_put(out, r, basis, IsoCamera.to_godot(centre))
	return out


## One instance per segment row, in row order: its top edge's centre (where a Phase 1 flame rises from), scaled to the
## flame's width: four radii on a rod, at least MIN_ROD_FLAME_M, the slab's width on a slab. The per-segment loop is
## the rebuild's hot path (2x10^4 rows): to_godot is linear, so each object's base and direction map once, and a
## flame's basis is a uniform scale, so only its diagonal and origin are written.
static func flame_buffer(snap: FuelSnapshot) -> PackedFloat32Array:
	var segments: int = snap.rows.get("segments", 0)
	var out: PackedFloat32Array = _sized(segments)
	var first: PackedInt32Array = snap.first_rows()
	var counts: PackedInt32Array = _u16s(snap.column("objects", "segment_count"))
	var steps: PackedFloat32Array = snap.floats("objects", "segment_length_m")
	var rods: Rods = Rods.new(snap)
	var rod_rows: PackedInt32Array = snap.geometry_rows("rod")
	for r: int in rod_rows.size():
		var row: int = rod_rows[r]
		var top: Vector3 = IsoCamera.to_godot(rods.origin(r) + UP * rods.radii[r])
		var width: float = rod_flame_m(rods.radii[r])
		_flames(out, first[row], counts[row], steps[row], rods.lengths[r], top, IsoCamera.to_godot(rods.axis(r)), width)
	var slabs: Slabs = Slabs.new(snap)
	var slab_rows: PackedInt32Array = snap.geometry_rows("slab")
	for r: int in slab_rows.size():
		var row: int = slab_rows[r]
		var along: Vector3 = slabs.along(r)
		var edge: Vector3 = slabs.origin(r) + slabs.across(r) * slabs.widths[r] * 0.5 \
			+ along.cross(slabs.across(r)) * slabs.thicknesses[r]
		_flames(out, first[row], counts[row], steps[row], slabs.lengths[r], IsoCamera.to_godot(edge),
			IsoCamera.to_godot(along), slabs.widths[r])
	return out


## One object's flames, rows ``first`` onward: segment k's at ``base`` + ``direction`` · min((k + 0.5)ℓ, L), all in
## Godot's frame, scaled by ``width``.
static func _flames(out: PackedFloat32Array, first: int, count: int, step: float, length: float, base: Vector3,
		direction: Vector3, width: float) -> void:
	for k: int in count:
		var p: Vector3 = base + direction * minf((k + 0.5) * step, length)
		var at: int = (first + k) * FLOATS
		out[at] = width
		out[at + 3] = p.x
		out[at + 5] = width
		out[at + 7] = p.y
		out[at + 10] = width
		out[at + 11] = p.z


## A Phase 1 flame's width over a rod of ``radius_m``: four radii, at least MIN_ROD_FLAME_M.
static func rod_flame_m(radius_m: float) -> float:
	return maxf(4.0 * radius_m, MIN_ROD_FLAME_M)


## The widest flame flame_buffer places, metres: what the flames' culling box must reach sideways.
static func widest_flame_m(snap: FuelSnapshot) -> float:
	var out: float = 0.0
	for radius: float in snap.floats("rods", "radius_m"):
		out = maxf(out, rod_flame_m(radius))
	for width: float in snap.floats("slabs", "width_m"):
		out = maxf(out, width)
	return out


## Each segment row's object row, in the order flame_buffer places them: what the flame shader reads to honour its
## object's burnout (§4.3). As floats, exact to 2^24, far past MAX_OBJECTS.
static func segment_objects(snap: FuelSnapshot) -> PackedFloat32Array:
	var out: PackedFloat32Array = PackedFloat32Array()
	var counts: PackedInt32Array = _u16s(snap.column("objects", "segment_count"))
	for row: int in counts.size():
		var run: PackedFloat32Array = PackedFloat32Array()
		if run.resize(counts[row]) != OK:
			push_error("FuelGeometry: cannot allocate %d segments" % counts[row])
			return out
		run.fill(float(row))
		out.append_array(run)
	return out


## The box holding every instance of a buffer whose unit mesh spans ±``half`` in local axes (a rod's cylinder is
## (1, 0.5, 1), a slab's box (0.5, 0.5, 0.5)): each instance's box is its origin ± |basis| · half. Empty for no instances.
static func bounds(buffer: PackedFloat32Array, half: Vector3) -> AABB:
	var out: AABB = AABB()
	for i: int in floori(buffer.size() / float(FLOATS)):
		var at: int = i * FLOATS
		var reach: Vector3 = Vector3(
			absf(buffer[at]) * half.x + absf(buffer[at + 1]) * half.y + absf(buffer[at + 2]) * half.z,
			absf(buffer[at + 4]) * half.x + absf(buffer[at + 5]) * half.y + absf(buffer[at + 6]) * half.z,
			absf(buffer[at + 8]) * half.x + absf(buffer[at + 9]) * half.y + absf(buffer[at + 10]) * half.z)
		var box: AABB = AABB(Vector3(buffer[at + 3], buffer[at + 7], buffer[at + 11]) - reach, reach * 2.0)
		out = box if i == 0 else out.merge(box)
	return out


static func _sized(n: int) -> PackedFloat32Array:
	var out: PackedFloat32Array = PackedFloat32Array()
	if out.resize(n * FLOATS) != OK:
		push_error("FuelGeometry: cannot allocate %d transforms" % n)
	return out


## Write ``basis`` and ``origin`` as instance ``i``: the 3×4 matrix row by row, Godot's MultiMesh buffer layout.
static func _put(out: PackedFloat32Array, i: int, basis: Basis, origin: Vector3) -> void:
	var at: int = i * FLOATS
	out[at] = basis.x.x
	out[at + 1] = basis.y.x
	out[at + 2] = basis.z.x
	out[at + 3] = origin.x
	out[at + 4] = basis.x.y
	out[at + 5] = basis.y.y
	out[at + 6] = basis.z.y
	out[at + 7] = origin.y
	out[at + 8] = basis.x.z
	out[at + 9] = basis.y.z
	out[at + 10] = basis.z.z
	out[at + 11] = origin.z


static func _u16s(bytes: PackedByteArray) -> PackedInt32Array:
	var out: PackedInt32Array = PackedInt32Array()
	var n: int = bytes.size() >> 1  # two bytes per u16
	if out.resize(n) != OK:
		push_error("FuelGeometry: cannot allocate %d counts" % n)
		return out
	for i: int in out.size():
		out[i] = bytes.decode_u16(i * 2)
	return out


## A vector's three f32 columns, decoded once.
static func _xyz(snap: FuelSnapshot, table: String, prefix: String, suffix: String) -> Array[PackedFloat32Array]:
	return [
		snap.floats(table, prefix + "x" + suffix), snap.floats(table, prefix + "y" + suffix),
		snap.floats(table, prefix + "z" + suffix),
	]


static func _at(xyz: Array[PackedFloat32Array], r: int) -> Vector3:
	return Vector3(xyz[0][r], xyz[1][r], xyz[2][r])


## The rods table's columns, decoded once.
class Rods:
	var origins: Array[PackedFloat32Array]
	var axes: Array[PackedFloat32Array]
	var lengths: PackedFloat32Array
	var radii: PackedFloat32Array

	func _init(snap: FuelSnapshot) -> void:
		origins = FuelGeometry._xyz(snap, "rods", "origin_", "_m")
		axes = FuelGeometry._xyz(snap, "rods", "axis_", "")
		lengths = snap.floats("rods", "length_m")
		radii = snap.floats("rods", "radius_m")

	func origin(r: int) -> Vector3:
		return FuelGeometry._at(origins, r)

	func axis(r: int) -> Vector3:
		return FuelGeometry._at(axes, r)


## The slabs table's columns, decoded once.
class Slabs:
	var origins: Array[PackedFloat32Array]
	var alongs: Array[PackedFloat32Array]
	var acrosses: Array[PackedFloat32Array]
	var lengths: PackedFloat32Array
	var widths: PackedFloat32Array
	var thicknesses: PackedFloat32Array

	func _init(snap: FuelSnapshot) -> void:
		origins = FuelGeometry._xyz(snap, "slabs", "origin_", "_m")
		alongs = FuelGeometry._xyz(snap, "slabs", "length_axis_", "")
		acrosses = FuelGeometry._xyz(snap, "slabs", "width_axis_", "")
		lengths = snap.floats("slabs", "length_m")
		widths = snap.floats("slabs", "width_m")
		thicknesses = snap.floats("slabs", "thickness_m")

	func origin(r: int) -> Vector3:
		return FuelGeometry._at(origins, r)

	func along(r: int) -> Vector3:
		return FuelGeometry._at(alongs, r)

	func across(r: int) -> Vector3:
		return FuelGeometry._at(acrosses, r)
