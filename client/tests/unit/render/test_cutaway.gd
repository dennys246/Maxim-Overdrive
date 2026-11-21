extends RefCounted
## The cut-away rule (render/cutaway.gd): which walls are cut, from the walls' boxes in the committed alley fixture,
## at every yaw. Visual only; these hold the rule without a GPU, and the rendered check (cutaway_check.tscn, judged by
## scripts/golden_measures.py) holds what it draws.

const SOUTH: int = 2
const NORTH: int = 3
const END: int = 4
const CRATE: int = 5


func _walls() -> Dictionary[int, AABB]:
	var snap: CellSnapshot = SnapshotFixture.named("alley_cold").snapshot
	var names: PackedStringArray = PackedStringArray(["wall_south", "wall_north", "wall_end"])
	return Cutaway.flagged_boxes(snap, snap.region_cell_bounds(), names)


func _cut(walls: Dictionary[int, AABB], x: float, y: float, k: int) -> PackedInt32Array:
	return Cutaway.cut_regions(walls, Vector3(x, y, 0.4), IsoCamera.step_yaw(k), PackedInt32Array())


func test_the_flagged_boxes_are_the_authored_walls(t: TestContext) -> void:
	var walls: Dictionary[int, AABB] = _walls()
	t.check_eq(str(walls.keys()), str([SOUTH, NORTH, END]), "only the walls, by id")
	t.check(walls[SOUTH].is_equal_approx(AABB(Vector3(1.2, 0.0, 0.4), Vector3(10.8, 0.4, 4.0))), "wall_south: %s" % [walls[SOUTH]])
	t.check(walls[END].is_equal_approx(AABB(Vector3(11.6, 0.4, 0.4), Vector3(0.4, 3.2, 4.0))), "wall_end: %s" % [walls[END]])
	t.check(not walls.has(CRATE), "the crate is never flagged")


func test_the_wall_between_the_body_and_the_camera_is_cut_at_every_yaw(t: TestContext) -> void:
	var walls: Dictionary[int, AABB] = _walls()
	# From the kindling spot: the camera is south-east at step 0, then north-east, north-west and south-west. The end
	# wall is 6 m east, beyond the 4.8 m a sightline climbs over a 4 m wall, so it is never in the way here.
	var expected: Array = [[SOUTH], [NORTH], [NORTH], [SOUTH]]
	for k: int in 4:
		t.check_eq(Array(_cut(walls, 5.5, 2.925, k)), expected[k], "step %d" % k)
	# Beside the end wall, the sightline to a south-east camera passes beyond wall_south's end: only the end wall.
	t.check_eq(Array(_cut(walls, 11.35, 2.0, 0)), [END], "beside the end wall")


func test_along_a_side_wall_the_cut_does_not_change(t: TestContext) -> void:
	# Mid-alley, where no sightline to the camera can pass a wall's end; near the ends the cut changes where the
	# wall's shadow does, which the next tests hold.
	var walls: Dictionary[int, AABB] = _walls()
	for k: int in 4:
		var first: PackedInt32Array = _cut(walls, 5.0, 2.0, k)
		for x: float in [5.0, 5.5, 5.7, 6.0, 7.0, 8.0]:
			for y: float in [0.65, 2.0, 3.35]:
				var cut: PackedInt32Array = _cut(walls, x, y, k)
				t.check(cut.has(NORTH) == first.has(NORTH) and cut.has(SOUTH) == first.has(SOUTH), "step %d at (%s, %s): %s, not %s" % [k, x, y, cut, first])


func test_off_the_walls_ends_only_a_wall_in_the_way_is_cut(t: TestContext) -> void:
	var walls: Dictionary[int, AABB] = _walls()
	# The box-centre rule cut wall_north here at yaw 45, behind the player.
	t.check(not _cut(walls, 0.6, 3.35, 0).has(NORTH), "the pavement at yaw 45: wall_north is behind")
	# The short-side rule left wall_south standing here while it hid half the body (delta review 2).
	t.check(_cut(walls, 0.9, 0.3, 0).has(SOUTH), "level with wall_south's thickness, beside its end: cut")
	t.check(_cut(walls, 0.9, 3.7, 1).has(NORTH), "the same beside wall_north's end")
	# With the camera to the west, nothing stands between: the walls are all east of the pavement.
	for y: float in [0.3, 0.65, 2.0, 3.35, 3.7]:
		t.check(Array(_cut(walls, 0.6, y, 2)).has(SOUTH) == false, "step 2 at (0.6, %s): wall_south is behind" % y)


func test_walking_out_of_a_walls_shadow_restores_it_once_without_flicker(t: TestContext) -> void:
	# Camera to the north-west (step 2): walking west along y = 2.0 towards the alley mouth, wall_north leaves the
	# body's sightlines. With the hold, it comes back once, later, and a step back doesn't cut it again.
	var walls: Dictionary[int, AABB] = _walls()
	var held: PackedInt32Array = _cut(walls, 4.0, 2.0, 2)
	t.check(held.has(NORTH), "deep in the alley wall_north is in the way")
	var changes: int = 0
	var restored_at: float = -1.0
	for i: int in 41:
		var x: float = 4.0 - 0.05 * i
		var cut: PackedInt32Array = Cutaway.cut_regions(walls, Vector3(x, 2.0, 0.4), IsoCamera.step_yaw(2), held)
		if cut.has(NORTH) != held.has(NORTH):
			changes += 1
			restored_at = x
		held = cut
	t.check_eq(changes, 1, "wall_north changes once on the way out")
	var unheld: float = -1.0
	for i: int in 41:
		var x: float = 4.0 - 0.05 * i
		if unheld < 0.0 and not _cut(walls, x, 2.0, 2).has(NORTH):
			unheld = x
	t.check(restored_at < unheld - 0.1, "the hold restores it later than the bare rule would: %s < %s" % [restored_at, unheld])
	var step_back: PackedInt32Array = Cutaway.cut_regions(walls, Vector3(restored_at + 0.05, 2.0, 0.4), IsoCamera.step_yaw(2), held)
	t.check(not step_back.has(NORTH), "a step back does not cut it again: %s" % [step_back])


func test_the_sightline_slab_test(t: TestContext) -> void:
	var box: Rect2 = Rect2(1.0, 1.0, 2.0, 1.0)
	t.check(Cutaway.sightline_meets(box, Vector2(0.0, 1.5), Vector2(1.0, 0.0), 2.0), "straight into it")
	t.check(not Cutaway.sightline_meets(box, Vector2(0.0, 1.5), Vector2(1.0, 0.0), 0.9), "out of reach")
	t.check(not Cutaway.sightline_meets(box, Vector2(0.0, 1.5), Vector2(-1.0, 0.0), 5.0), "pointing away")
	t.check(not Cutaway.sightline_meets(box, Vector2(0.0, 2.5), Vector2(1.0, 0.0), 5.0), "parallel, beside it")
	t.check(Cutaway.sightline_meets(box, Vector2(0.0, 0.0), Vector2(0.7071068, 0.7071068), 5.0), "diagonally in")
	t.check(Cutaway.sightline_meets(box, Vector2(2.0, 1.5), Vector2(1.0, 0.0), 0.1), "starting inside it")
	t.check(not Cutaway.sightline_meets(box, Vector2(0.0, 1.5), Vector2(1.0, 0.0), 0.0), "a box no taller than the feet")


func test_the_stump_and_the_cut_limit(t: TestContext) -> void:
	t.check(is_equal_approx(Cutaway.stump_top_m(0.4), 0.6), "a 0.2 m stump above the feet")
	var many: Dictionary[int, AABB] = {}
	for id: int in range(1, 12):
		many[id] = AABB(Vector3(0.5, -0.5, 0.0), Vector3(1.0, 1.0, 4.0))  # south-east of the player, in the way at yaw 45
	t.check_eq(Cutaway.cut_regions(many, Vector3.ZERO, IsoCamera.step_yaw(0), PackedInt32Array()).size(), Cutaway.MAX_CUT, "at most the shader's array of ids")
