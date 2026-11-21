extends RefCounted
## The cut-away rule (render/cutaway.gd): which walls are cut, from the walls' boxes in the committed alley fixture,
## at every yaw. Visual only; these hold the rule without a GPU, and the rendered check (cutaway_check.tscn, judged by
## scripts/golden_measures.py) holds what it draws.

const SOUTH: int = 2
const NORTH: int = 3
const END: int = 4
const CRATE: int = 5


func _walls() -> Dictionary[int, Rect2]:
	var snap: CellSnapshot = SnapshotFixture.named("alley_cold").snapshot
	var names: PackedStringArray = PackedStringArray(["wall_south", "wall_north", "wall_end"])
	return Cutaway.flagged_boxes(snap, snap.region_cell_bounds(), names)


func test_the_flagged_boxes_are_the_authored_walls(t: TestContext) -> void:
	var walls: Dictionary[int, Rect2] = _walls()
	t.check_eq(str(walls.keys()), str([SOUTH, NORTH, END]), "only the walls, by id")
	t.check(walls[SOUTH].is_equal_approx(Rect2(1.2, 0.0, 10.8, 0.4)), "wall_south: %s" % [walls[SOUTH]])
	t.check(walls[END].is_equal_approx(Rect2(11.6, 0.4, 0.4, 3.2)), "wall_end: %s" % [walls[END]])
	t.check(not walls.has(CRATE), "the crate is never flagged")


func test_the_walls_on_the_cameras_side_are_cut_at_every_yaw(t: TestContext) -> void:
	var walls: Dictionary[int, Rect2] = _walls()
	var player: Vector2 = Vector2(5.5, 2.925)
	# Yaw 45 looks north-west from the south-east; each step turns the camera 90 degrees anticlockwise from above.
	var expected: Array = [[SOUTH, END], [NORTH, END], [NORTH], [SOUTH]]
	for k: int in 4:
		var cut: PackedInt32Array = Cutaway.cut_regions(walls, player, IsoCamera.step_yaw(k))
		t.check_eq(Array(cut), expected[k], "step %d" % k)


func test_a_side_walls_cut_never_depends_on_where_along_it_the_player_stands(t: TestContext) -> void:
	# §2's box-centre rule cut wall_north, behind the player, at yaw 45 whenever x < 5.7 m: its centre is 6.6 m along.
	var walls: Dictionary[int, Rect2] = _walls()
	var yaw: float = IsoCamera.step_yaw(0)
	for x: float in [1.5, 3.0, 5.5, 5.7, 6.0, 8.0, 11.3]:
		for y: float in [0.65, 2.0, 3.35]:
			var cut: PackedInt32Array = Cutaway.cut_regions(walls, Vector2(x, y), yaw)
			t.check(not cut.has(NORTH) and cut.has(SOUTH), "at (%s, %s): %s" % [x, y, cut])
	var centre_rule_cuts_north: bool = (walls[NORTH].get_center() - Vector2(5.5, 2.925)).dot(IsoCamera.horizontal_forward(yaw)) < 0.0
	t.check(centre_rule_cuts_north, "the case the box-centre rule gets wrong is still this one")


func test_the_stump_and_the_cut_limit(t: TestContext) -> void:
	t.check(is_equal_approx(Cutaway.stump_top_m(0.4), 0.7), "a 0.3 m stump above the feet")
	t.check_eq(Cutaway.nearest_point(Rect2(1, 1, 2, 2), Vector2(0, 5)), Vector2(1, 3), "the nearest point of a box")
	var many: Dictionary[int, Rect2] = {}
	for id: int in range(1, 12):
		many[id] = Rect2(5.0, -10.0, 1.0, 1.0)  # south-east of the player: the camera's side at yaw 45
	var cut: PackedInt32Array = Cutaway.cut_regions(many, Vector2.ZERO, IsoCamera.step_yaw(0))
	t.check_eq(cut.size(), Cutaway.MAX_CUT, "at most the shader's array of ids")
