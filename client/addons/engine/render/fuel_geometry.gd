class_name FuelGeometry
extends RefCounted
## A fuel object's instance transform from its geometry row (docs/design/client_objects.md §3.2): the one place the
## object pass turns metres in the world's frame into a Godot transform, through IsoCamera.to_godot, the GDScript half
## of the one axis mapping (the shaders' axes.gdshaderinc is the other). The transform is in Godot's frame, so the
## MultiMesh's culling box is where the objects are.

## Which world axis a perpendicular is built against, unless the object's axis is nearly parallel to it.
const UP: Vector3 = Vector3(0.0, 0.0, 1.0)
const EAST: Vector3 = Vector3(1.0, 0.0, 0.0)


## Geometry row ``r`` of ``table`` ("rods" or "slabs") as the transform of a unit mesh: a unit cylinder along local y
## (rods) or a unit box centred at the origin (slabs, length along local x, thickness along y, width along z).
static func transform(snap: FuelSnapshot, table: String, r: int) -> Transform3D:
	if table == "rods":
		return _rod(snap, r)
	return _slab(snap, r)


static func _rod(snap: FuelSnapshot, r: int) -> Transform3D:
	var origin: Vector3 = _vector(snap, "rods", "origin_", "_m", r)
	var axis: Vector3 = _vector(snap, "rods", "axis_", "", r)
	var length: float = snap.column("rods", "length_m").decode_float(r * 4)
	var radius: float = snap.column("rods", "radius_m").decode_float(r * 4)
	var across: Vector3 = axis.cross(EAST if absf(axis.dot(UP)) > 0.9 else UP).normalized()
	var other: Vector3 = across.cross(axis)  # across × axis, so (across, axis, other) is right-handed
	var basis: Basis = Basis(IsoCamera.to_godot(across) * radius, IsoCamera.to_godot(axis) * length,
		IsoCamera.to_godot(other) * radius)
	return Transform3D(basis, IsoCamera.to_godot(origin + axis * length * 0.5))


## A slab spans origin to origin + L·length axis + W·width axis + T·normal, normal = length axis × width axis
## (fire_solid §1.1: the segmented face is the one at origin + T·normal). The box's local z is the negated width axis,
## so the basis stays right-handed and the faces keep their winding.
static func _slab(snap: FuelSnapshot, r: int) -> Transform3D:
	var origin: Vector3 = _vector(snap, "slabs", "origin_", "_m", r)
	var along: Vector3 = _vector(snap, "slabs", "length_axis_", "", r)
	var across: Vector3 = _vector(snap, "slabs", "width_axis_", "", r)
	var normal: Vector3 = along.cross(across)
	var length: float = snap.column("slabs", "length_m").decode_float(r * 4)
	var width: float = snap.column("slabs", "width_m").decode_float(r * 4)
	var thickness: float = snap.column("slabs", "thickness_m").decode_float(r * 4)
	var basis: Basis = Basis(IsoCamera.to_godot(along) * length, IsoCamera.to_godot(normal) * thickness,
		IsoCamera.to_godot(-across) * width)
	var centre: Vector3 = origin + (along * length + across * width + normal * thickness) * 0.5
	return Transform3D(basis, IsoCamera.to_godot(centre))


static func _vector(snap: FuelSnapshot, table: String, prefix: String, suffix: String, r: int) -> Vector3:
	return Vector3(
		snap.column(table, prefix + "x" + suffix).decode_float(r * 4),
		snap.column(table, prefix + "y" + suffix).decode_float(r * 4),
		snap.column(table, prefix + "z" + suffix).decode_float(r * 4))
