class_name IsoCamera
extends RefCounted
## The isometric 3/4 camera's geometry (client_rendering.md §1, T1, T10), and the one mapping between the world's
## axes and Godot's.
##
## The world (the server) is z-up: x east, y north, z up, in metres. Godot is y-up. A world point (x, y, z) is the
## Godot point (x, z, -y): a rotation, not a mirror (x cross -y is +z in Godot's frame, as x cross y is z in the
## world's), so handedness and every winding survive it.
##
## Why orthographic: parallel projection draws a metre the same size at every depth, which is what makes a 3/4 view
## read as a map, and the pixel footprint of a metre (needed for the crack width, §5.4) is one number for the frame.

const ELEVATION_DEG: float = 40.0
const DISTANCE_M: float = 60.0
## The yaw of the first 90-degree step (§1: 45 + k * 90).
const BASE_YAW_DEG: float = 45.0


static func to_godot(world_m: Vector3) -> Vector3:
	return Vector3(world_m.x, world_m.z, -world_m.y)


static func to_world(godot_m: Vector3) -> Vector3:
	return Vector3(godot_m.x, -godot_m.z, godot_m.y)


## The yaw in radians of step ``k`` (0..3): 45, 135, 225 and 315 degrees.
static func step_yaw(k: int) -> float:
	return deg_to_rad(BASE_YAW_DEG + 90.0 * posmod(k, 4))


## The camera's horizontal forward in the world's x-y plane at ``yaw``: the direction it looks, flattened. At yaw 45
## the camera sits south-east of its target and looks north-west. The cut-away rule (§2) reads this, so the camera
## and the cut can't disagree about which side of the player is the camera's.
static func horizontal_forward(yaw: float) -> Vector2:
	return Vector2(-sin(yaw), cos(yaw))


## Puts ``camera`` DISTANCE_M back from ``target_world_m`` at ``yaw`` and the fixed elevation, looking at it, with an
## orthographic ``size_m`` (the view's height in metres, Godot's KEEP_HEIGHT default).
static func place(camera: Camera3D, target_world_m: Vector3, yaw: float, size_m: float) -> void:
	var elevation: float = deg_to_rad(ELEVATION_DEG)
	var forward: Vector2 = horizontal_forward(yaw)
	var back_world: Vector3 = Vector3(-forward.x * cos(elevation), -forward.y * cos(elevation), sin(elevation))
	var target: Vector3 = to_godot(target_world_m)
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = size_m
	camera.near = 0.1
	camera.far = 200.0
	var at: Vector3 = target + to_godot(back_world) * DISTANCE_M
	# The basis directly, not Node3D.look_at, which needs the node in the scene tree and does nothing otherwise.
	camera.transform = Transform3D(Basis.looking_at(target - at, Vector3.UP), at)


## Metres one rendered pixel spans: the view height over the rendered height. ``render_scale`` is the viewport's
## scaling_3d_scale (the laptop tier draws at 0.5, so each of its pixels covers twice the metres).
static func pixel_metres(size_m: float, viewport_height_px: int, render_scale: float) -> float:
	return size_m / (float(viewport_height_px) * render_scale)
