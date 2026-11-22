extends RefCounted
## The camera geometry (render/iso_camera.gd): the world-to-Godot map is a rotation, the placed camera looks along
## the horizontal forward the cut-away reads, and the pixel footprint follows zoom and render scale.


func test_the_axis_map_is_a_rotation_and_round_trips(t: TestContext) -> void:
	var x: Vector3 = IsoCamera.to_godot(Vector3(1, 0, 0))
	var y: Vector3 = IsoCamera.to_godot(Vector3(0, 1, 0))
	var z: Vector3 = IsoCamera.to_godot(Vector3(0, 0, 1))
	t.check_eq(z, Vector3.UP, "world up is Godot up")
	t.check(x.cross(y).is_equal_approx(z), "x cross y is z after the map: no mirror")
	var p: Vector3 = Vector3(1.5, -2.0, 3.25)
	t.check_eq(IsoCamera.to_world(IsoCamera.to_godot(p)), p, "round trip")


func test_the_placed_camera_looks_along_the_forward_the_cut_reads(t: TestContext) -> void:
	var camera: Camera3D = Camera3D.new()
	for k: int in 4:
		var yaw: float = IsoCamera.step_yaw(k)
		IsoCamera.place(camera, Vector3(6.3, 2.9, 0.7), yaw, 10.0)
		var look: Vector3 = IsoCamera.to_world(-camera.transform.basis.z)
		var flat: Vector2 = Vector2(look.x, look.y).normalized()
		t.check(flat.is_equal_approx(IsoCamera.horizontal_forward(yaw)), "step %d: %s" % [k, flat])
		t.check(is_equal_approx(rad_to_deg(asin(-look.z)), IsoCamera.ELEVATION_DEG), "step %d elevation" % k)
	t.check_eq(camera.projection, Camera3D.PROJECTION_ORTHOGONAL, "orthographic")
	camera.free()


func test_the_golden_view_is_72_px_per_metre(t: TestContext) -> void:
	t.check(is_equal_approx(1.0 / IsoCamera.pixel_metres(10.0, 720, 1.0), 72.0), "§1's 72 px/m")
	t.check(is_equal_approx(IsoCamera.pixel_metres(10.0, 720, 0.5), 2.0 * IsoCamera.pixel_metres(10.0, 720, 1.0)), "half scale doubles it")
