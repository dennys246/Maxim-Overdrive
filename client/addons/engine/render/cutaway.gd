class_name Cutaway
extends RefCounted
## Which walls to cut so the player stays visible (client_rendering.md §2, T11). At a 40-degree elevation a 4 m wall
## hides 4.8 m of floor behind it, more than the alley is wide, so a wall between the camera and the player is cut
## down to a stump. Visual only: the result goes into shader uniforms and nowhere else (§2, "never fed back").
##
## The rule: a flagged region is cut when the point of its box nearest the player lies on the camera's side of the
## player, dot(q - p, f) < 0, with f the camera's horizontal forward at the **target** yaw, so a rotation decides the
## cut once, at its start, and the cut doesn't pop during the 0.25 s tween. Cut cells keep a stump: those whose top
## is at most the feet plus STUMP_M.
##
## Nearest point, not §2's box centre: a side wall is 10.8 m long, so its centre is up to 5 m along the alley from the
## player, and at a 45-degree yaw that along-wall offset alone flips the sign. At yaw 45 the centre rule cuts
## wall_north, which is behind the player, whenever the player stands west of x = 5.7 m (measured on the alley
## fixture; test_cutaway.gd keeps the case). The nearest point slides along a wall as the player walks, so for a side
## wall only the player's distance across the alley counts, and that never changes sign inside it: no pops.

const STUMP_M: float = 0.3
## The shader's uniform array holds this many cut region ids (cell_volume: cut_ids).
const MAX_CUT: int = 8


## The ids, among ``flagged`` (region id -> its box in world x-y metres), to cut for a player standing at
## ``player_xy_m`` with the camera turning to ``target_yaw``. In id order, at most MAX_CUT.
static func cut_regions(flagged: Dictionary[int, Rect2], player_xy_m: Vector2, target_yaw: float) -> PackedInt32Array:
	var forward: Vector2 = IsoCamera.horizontal_forward(target_yaw)
	var ids: Array[int] = []
	for id: int in flagged:
		if (nearest_point(flagged[id], player_xy_m) - player_xy_m).dot(forward) < 0.0:
			ids.append(id)
	ids.sort()
	if ids.size() > MAX_CUT:
		push_warning("Cutaway: %d regions to cut, the shader holds %d; the rest stay drawn" % [ids.size(), MAX_CUT])
		ids = ids.slice(0, MAX_CUT)
	return PackedInt32Array(ids)


## The height in metres below which a cut region's cells stay drawn: cells whose top is at most this are the stump.
static func stump_top_m(feet_z_m: float) -> float:
	return feet_z_m + STUMP_M


## The point of ``box`` nearest ``p`` (``p`` itself when inside).
static func nearest_point(box: Rect2, p: Vector2) -> Vector2:
	return p.clamp(box.position, box.end)


## The flagged regions of ``snap``: each name in ``names`` that the snapshot's region map has, with the x-y extent of
## its cells' bounding box in world metres (for an authored box, the box itself). ``bounds`` is
## snap.region_cell_bounds(), passed in because it costs a pass over the cells.
static func flagged_boxes(snap: CellSnapshot, bounds: Dictionary[int, AABB], names: PackedStringArray) -> Dictionary[int, Rect2]:
	var out: Dictionary[int, Rect2] = {}
	for region_name: String in names:
		var id: int = snap.region_id(region_name)
		if id == 0 or not bounds.has(id):
			continue
		var b: AABB = bounds[id]
		var c: float = snap.cell_m
		out[id] = Rect2(b.position.x * c, b.position.y * c, b.size.x * c, b.size.y * c)
	return out
