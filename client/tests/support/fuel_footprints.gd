class_name FuelFootprints
extends RefCounted
## Each segment's footprint on screen, in output pixels, for the measured checks (client_objects.md §7.2): where its
## centre line starts and ends and how far either side of it the segment draws. scripts/golden_fuel.py groups a
## frame's pixels by segment from this, so the checks read ignited, charred or burnt segments without re-deriving the
## camera. Written beside each fuel shot's PNG by the golden scene; projected by the camera that drew the frame.


## One row per segment, in segment-row order: [ax, ay, bx, by, half_width]. A rod's centre line is its axis, half its
## drawn width (the 2 px floor included) either side; a slab's is its top face's centre line, half its projected width
## either side.
static func of(snap: FuelSnapshot, camera: Camera3D, output_pixel_m: float) -> Array[Array]:
	var out: Array[Array] = []
	if out.resize(snap.rows["segments"]) != OK:
		push_error("FuelFootprints: cannot allocate %d rows" % snap.rows["segments"])
		return out
	var first: PackedInt32Array = snap.first_rows()
	var counts: PackedByteArray = snap.column("objects", "segment_count")
	var steps: PackedFloat32Array = snap.floats("objects", "segment_length_m")
	for kind: String in FuelSnapshot.DRAWABLE_KINDS:
		var object_rows: PackedInt32Array = snap.geometry_rows(kind)
		for r: int in object_rows.size():
			var row: int = object_rows[r]
			var count: int = counts.decode_u16(row * 2)
			var rows: Array[Array] = _rod(snap, camera, r, count, steps[row], output_pixel_m) if kind == "rod" \
				else _slab(snap, camera, r, count, steps[row])
			for k: int in count:
				out[first[row] + k] = rows[k]
	return out


static func _rod(snap: FuelSnapshot, camera: Camera3D, r: int, count: int, step: float, pixel_m: float) -> Array[Array]:
	var origin: Vector3 = _vector(snap, "rods", "origin_", "_m", r)
	var axis: Vector3 = _vector(snap, "rods", "axis_", "", r)
	var length: float = snap.column("rods", "length_m").decode_float(r * 4)
	var radius: float = snap.column("rods", "radius_m").decode_float(r * 4)
	var half_width: float = FuelPass.drawn_half_m(radius, pixel_m) / pixel_m
	var out: Array[Array] = []
	for k: int in count:
		var a: Vector2 = camera.unproject_position(IsoCamera.to_godot(origin + axis * (k * step)))
		var b: Vector2 = camera.unproject_position(IsoCamera.to_godot(origin + axis * minf((k + 1) * step, length)))
		out.append([a.x, a.y, b.x, b.y, half_width])
	return out


static func _slab(snap: FuelSnapshot, camera: Camera3D, r: int, count: int, step: float) -> Array[Array]:
	var origin: Vector3 = _vector(snap, "slabs", "origin_", "_m", r)
	var along: Vector3 = _vector(snap, "slabs", "length_axis_", "", r)
	var across: Vector3 = _vector(snap, "slabs", "width_axis_", "", r)
	var length: float = snap.column("slabs", "length_m").decode_float(r * 4)
	var width: float = snap.column("slabs", "width_m").decode_float(r * 4)
	var thickness: float = snap.column("slabs", "thickness_m").decode_float(r * 4)
	var centre_line: Vector3 = origin + across * width * 0.5 + along.cross(across) * thickness
	var out: Array[Array] = []
	for k: int in count:
		var a: Vector2 = camera.unproject_position(IsoCamera.to_godot(centre_line + along * (k * step)))
		var b: Vector2 = camera.unproject_position(IsoCamera.to_godot(centre_line + along * minf((k + 1) * step, length)))
		var edge: Vector2 = camera.unproject_position(IsoCamera.to_godot(centre_line + along * (k * step) + across * width * 0.5))
		out.append([a.x, a.y, b.x, b.y, a.distance_to(edge)])
	return out


static func _vector(snap: FuelSnapshot, table: String, prefix: String, suffix: String, r: int) -> Vector3:
	return Vector3(
		snap.column(table, prefix + "x" + suffix).decode_float(r * 4),
		snap.column(table, prefix + "y" + suffix).decode_float(r * 4),
		snap.column(table, prefix + "z" + suffix).decode_float(r * 4))
