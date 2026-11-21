class_name Cutaway
extends RefCounted
## Which walls to cut so the player stays visible (client_rendering.md §2, T11). At a 40-degree elevation a 4 m wall
## hides 4.8 m of floor behind it, more than the alley is wide, so a wall between the camera and the player is cut
## down to a stump. Visual only: the result goes into shader uniforms and nowhere else (§2, "never fed back").
##
## The rule is the occlusion itself, in plan view: a flagged region is cut when a sightline from the player's body
## towards the camera, at the **target** yaw, meets the region's box before it has risen above the box's top. Along
## the ground that is within (box top - feet) / tan(40 degrees) of the body: 4.8 m for the alley's walls. Three
## sightlines spread across the body's width cover it. So a wall is cut exactly when it
## stands between the body and the camera: at a rotation's start, and wherever the walk takes the body into or out of
## a wall's shadow, near its ends. A wall already cut stays cut until the body is HOLD_M clear of it, so standing on
## that edge never makes the wall flicker (hysteresis, as for any threshold a moving value sits on).
##
## Why not a proxy point (§2 amended twice, owner 2026-11-21): the box centre cut a wall behind the player (wall_north
## at yaw 45 whenever x < 5.7 m); the nearest point popped as the player walked off a wall's end; the point across
## the short side left wall_south uncut while it hid half the body at (0.9, 0.3) on the pavement. Each proxy was
## right only where the walls are long and the player is inside them. Cut cells keep a stump: those whose top is at
## most the feet plus STUMP_M.

const STUMP_M: float = 0.3
## The shader's uniform array holds this many cut region ids (cell_volume: cut_ids).
const MAX_CUT: int = 8
## Half the width the sightlines cover: the body's 0.25 m radius and a margin for its silhouette's edge.
const BODY_HALF_WIDTH_M: float = 0.3
## How much wider a cut wall's sightlines are before it is restored (the hysteresis band).
const HOLD_M: float = 0.25


## The ids, among ``flagged`` (region id -> its box in world metres), to cut for a player whose feet are at
## ``feet_m`` with the camera turning to ``target_yaw``; ``held`` are the ids cut last time, which keep their cut
## within the HOLD_M band. In id order, at most MAX_CUT.
static func cut_regions(
	flagged: Dictionary[int, AABB], feet_m: Vector3, target_yaw: float, held: PackedInt32Array = PackedInt32Array()
) -> PackedInt32Array:
	var towards_camera: Vector2 = -IsoCamera.horizontal_forward(target_yaw)
	var feet: Vector2 = Vector2(feet_m.x, feet_m.y)
	var ids: Array[int] = []
	for id: int in flagged:
		var box: AABB = flagged[id]
		var reach: float = (box.end.z - feet_m.z) / tan(deg_to_rad(IsoCamera.ELEVATION_DEG))
		var plan: Rect2 = Rect2(box.position.x, box.position.y, box.size.x, box.size.y)
		var half_width: float = BODY_HALF_WIDTH_M + (HOLD_M if held.has(id) else 0.0)
		if _shadows(plan, feet, towards_camera, half_width, reach):
			ids.append(id)
	ids.sort()
	if ids.size() > MAX_CUT:
		push_warning("Cutaway: %d regions to cut, the shader holds %d; the rest stay drawn" % [ids.size(), MAX_CUT])
		ids = ids.slice(0, MAX_CUT)
	return PackedInt32Array(ids)


## True when any of the sightlines across a body ``half_width`` wide at ``feet`` meets ``plan`` within ``reach``.
## Sightlines every 0.15 m at most, so no wall thinner than that slips between two of them.
static func _shadows(plan: Rect2, feet: Vector2, towards_camera: Vector2, half_width: float, reach: float) -> bool:
	var across: Vector2 = Vector2(-towards_camera.y, towards_camera.x)
	var lines: int = ceili(2.0 * half_width / 0.15) + 1
	for i: int in lines:
		var offset: float = lerpf(-half_width, half_width, float(i) / float(lines - 1))
		if sightline_meets(plan, feet + across * offset, towards_camera, reach):
			return true
	return false


## True when the ray from ``origin`` along unit ``direction`` meets ``box`` within ``reach`` (a slab test: the ray is
## inside the box between the latest entry and the earliest exit over the two axes).
static func sightline_meets(box: Rect2, origin: Vector2, direction: Vector2, reach: float) -> bool:
	if reach <= 0.0:
		return false
	var enter: float = 0.0
	var leave: float = reach
	for axis: int in 2:
		var o: float = origin[axis]
		var d: float = direction[axis]
		var lo: float = box.position[axis]
		var hi: float = box.end[axis]
		if absf(d) < 1e-9:
			if o < lo or o > hi:
				return false
			continue
		var t0: float = (lo - o) / d
		var t1: float = (hi - o) / d
		enter = maxf(enter, minf(t0, t1))
		leave = minf(leave, maxf(t0, t1))
	return enter <= leave


## The height in metres below which a cut region's cells stay drawn: cells whose top is at most this are the stump.
static func stump_top_m(feet_z_m: float) -> float:
	return feet_z_m + STUMP_M


## The flagged regions of ``snap``: each name in ``names`` that the snapshot's region map has, with its cells'
## bounding box in world metres (for an authored box, the box itself). ``bounds`` is snap.region_cell_bounds(),
## passed in because it costs a pass over the cells.
static func flagged_boxes(snap: CellSnapshot, bounds: Dictionary[int, AABB], names: PackedStringArray) -> Dictionary[int, AABB]:
	var out: Dictionary[int, AABB] = {}
	for region_name: String in names:
		var id: int = snap.region_id(region_name)
		if id == 0 or not bounds.has(id):
			continue
		var b: AABB = bounds[id]
		out[id] = AABB(b.position * snap.cell_m, b.size * snap.cell_m)
	return out
