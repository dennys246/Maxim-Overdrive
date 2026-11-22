extends RefCounted
## The golden footprints (tests/support/fuel_footprints.gd) against the geometry the pass draws: one row per segment
## row, in row order, each rod's run from its origin to origin + L·axis, half the drawn width the floor gives
## (FuelPass.drawn_half_m), and a slab's rows on its own segment rows. scripts/golden_fuel.py reads pixels through
## these rows, so a mismatch here measures the wrong segments.


## A camera at the golden view, in a 1280x720 viewport in the tree (unproject_position needs both).
func _camera() -> Camera3D:
	var viewport: SubViewport = SubViewport.new()
	viewport.size = Vector2i(1280, 720)
	(Engine.get_main_loop() as SceneTree).root.add_child(viewport)
	var camera: Camera3D = Camera3D.new()
	viewport.add_child(camera)
	camera.current = true
	IsoCamera.place(camera, Vector3(3.5, 2.0, 0.4), IsoCamera.step_yaw(0), 10.0)
	return camera


## Point ``i`` (0 the start, 1 the end) of a footprint row, and its half width.
func _point(row: Array, i: int) -> Vector2:
	var x: float = row[2 * i]
	var y: float = row[2 * i + 1]
	return Vector2(x, y)


func _half(row: Array) -> float:
	var half: float = row[4]
	return half


func test_each_segment_row_has_its_footprint_on_its_own_object(t: TestContext) -> void:
	var f: FuelFixture = FuelFixture.named("fuel_ramp")
	var snap: FuelSnapshot = f.snapshot
	var camera: Camera3D = _camera()
	await (Engine.get_main_loop() as SceneTree).process_frame  # the root enters the tree on the main loop's first frame
	t.check(camera.is_inside_tree(), "the camera is in the tree")
	var pixel_m: float = 10.0 / 720.0
	var rows: Array[Array] = FuelFootprints.of(snap, camera, pixel_m)
	t.check_eq(rows.size(), snap.rows["segments"], "one row per segment row")
	var first: PackedInt32Array = snap.first_rows()
	var rod_rows: PackedInt32Array = snap.geometry_rows("rod")
	var last_rod: int = rod_rows.size() - 1
	var row: int = rod_rows[last_rod]
	var count: int = snap.column("objects", "segment_count").decode_u16(row * 2)
	var origin: Vector3 = Vector3(snap.floats("rods", "origin_x_m")[last_rod], snap.floats("rods", "origin_y_m")[last_rod],
		snap.floats("rods", "origin_z_m")[last_rod])
	var axis: Vector3 = Vector3(snap.floats("rods", "axis_x")[last_rod], snap.floats("rods", "axis_y")[last_rod],
		snap.floats("rods", "axis_z")[last_rod])
	var length: float = snap.floats("rods", "length_m")[last_rod]
	var start: Vector2 = camera.unproject_position(IsoCamera.to_godot(origin))
	var end: Vector2 = camera.unproject_position(IsoCamera.to_godot(origin + axis * length))
	var head: Array = rows[first[row]]
	var tail: Array = rows[first[row] + count - 1]
	t.check(_point(head, 0).is_equal_approx(start), "the last rod's first segment starts at its origin")
	t.check(_point(tail, 1).is_equal_approx(end), "and its last ends at origin + L·axis")
	var radius: float = snap.floats("rods", "radius_m")[last_rod]
	t.check(is_equal_approx(_half(head), FuelPass.drawn_half_m(radius, pixel_m) / pixel_m), "half the floored width")
	var thin: int = rod_rows[0]
	var floored: Array = rows[first[thin]]
	t.check(is_equal_approx(_half(floored), 1.0) or snap.floats("rods", "radius_m")[0] > pixel_m, "a thin rod's floor is 1 px")
	var slab_row: int = snap.geometry_rows("slab")[0]
	var slab_first: Array = rows[first[slab_row]]
	var slab_origin: Vector3 = Vector3(snap.floats("slabs", "origin_x_m")[0], snap.floats("slabs", "origin_y_m")[0],
		snap.floats("slabs", "origin_z_m")[0])
	var on_slab: Vector2 = _point(slab_first, 0)
	var near: float = on_slab.distance_to(camera.unproject_position(IsoCamera.to_godot(slab_origin)))
	t.check(near < 0.5 * snap.floats("slabs", "width_m")[0] / pixel_m + 2.0, "the slab's rows start at its origin's edge")
	camera.get_parent().free()


func test_the_floor_is_the_radius_or_one_output_pixel(t: TestContext) -> void:
	t.check_eq(FuelPass.drawn_half_m(0.005, 0.01), 0.01, "a thin rod is floored")
	t.check_eq(FuelPass.drawn_half_m(0.05, 0.01), 0.05, "a thick one keeps its radius")
