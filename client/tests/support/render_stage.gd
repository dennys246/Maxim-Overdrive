class_name RenderStage
extends SubViewport
## A stage the rendered checks draw on: the cell volume, capsules for bodies, the iso camera and a fixed night, in a
## viewport of its own size. Used by the golden and cut-away scenes (client/tests/*.tscn), never by the game.
## Engine whys: a SubViewport renders its own subtree to a texture at its own resolution and render scale, so a
## check can draw at any size whatever the window is, and read the pixels back; own_world_3d keeps its 3-D scene
## apart from the window's; capsules are MeshInstance3D with a CapsuleMesh, the body's collision cylinder with round
## ends (tile §2.1: radius 0.25 m, 1.8 m tall); WorldEnvironment holds the background and the bloom post-process.

const BODY_RADIUS_M: float = 0.25
const BODY_HEIGHT_M: float = 1.8
## Black, because Godot 4.7.2's Compatibility renderer maps a clear colour differently on each of its buffer paths:
## Color(0.03, 0.035, 0.05) came out (7, 9, 12) drawn directly, (28, 34, 50) with glow on and (1, 2, 7) at a render
## scale of 0.5 (measured on the M2), so the tiers disagreed over every background pixel (mean ΔE 11, §6.3) while
## the shader's own pixels matched. Black is black on every path.
const NIGHT: Color = Color(0.0, 0.0, 0.0)
const BODY_SHADED: Color = Color(0.85, 0.82, 0.74)
## The ID colour of the player's body in the occluder pass; nothing else draws pure red then.
const BODY_ID: Color = Color(1.0, 0.0, 0.0)

var volume: CellVolume = CellVolume.new()
var camera: Camera3D = Camera3D.new()
var _environment: Environment = Environment.new()
var _bodies: Node3D = Node3D.new()
var _body_material: StandardMaterial3D = StandardMaterial3D.new()
var _snapshot: CellSnapshot = null
var _bounds: Dictionary[int, AABB] = {}


func _init() -> void:
	own_world_3d = true
	render_target_update_mode = SubViewport.UPDATE_ALWAYS
	_environment.background_mode = Environment.BG_COLOR
	_environment.background_color = NIGHT
	_environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	# Bloom from HDR output above 1.0 (§5.3): only emission gets there, so only glow and flames bloom.
	_environment.glow_hdr_threshold = 1.0
	var world_environment: WorldEnvironment = WorldEnvironment.new()
	world_environment.environment = _environment
	_body_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	for child: Node in [volume, camera, world_environment, _bodies]:
		add_child(child)
	camera.current = true


func show_fixture(fixture: SnapshotFixture, palette: MaterialPalette) -> void:
	_snapshot = fixture.snapshot
	_bounds = _snapshot.region_cell_bounds()
	volume.show_snapshot(_snapshot)
	volume.use_palette(palette.by_id(fixture.material_ids))
	volume.use_flicker(0.0)


func use_tier(tier: RenderTier) -> void:
	volume.use_tier(tier)
	scaling_3d_scale = tier.scaling_3d_scale
	_environment.glow_enabled = tier.bloom


## Aim the iso camera at ``target_world_m`` from step yaw ``yaw`` with an orthographic ``size_m``.
func aim(target_world_m: Vector3, yaw: float, size_m: float) -> void:
	IsoCamera.place(camera, target_world_m, yaw, size_m)
	volume.use_pixel_metres(IsoCamera.pixel_metres(size_m, size.y, scaling_3d_scale))


## Cut the flagged walls for a player whose feet are at ``feet_world_m``, the camera turning to ``yaw``.
func cut_for(feet_world_m: Vector3, yaw: float, walls: CutawayRegions) -> void:
	var flagged: Dictionary[int, Rect2] = Cutaway.flagged_boxes(_snapshot, _bounds, walls.regions)
	var ids: PackedInt32Array = Cutaway.cut_regions(flagged, Vector2(feet_world_m.x, feet_world_m.y), yaw)
	volume.use_cut(ids, Cutaway.stump_top_m(feet_world_m.z))


## A region's cell bounding box in world metres; an empty AABB when the snapshot has no such region.
func volume_bounds_m(region_name: String) -> AABB:
	var id: int = _snapshot.region_id(region_name)
	if not _bounds.has(id):
		return AABB()
	return AABB(_bounds[id].position * _snapshot.cell_m, _bounds[id].size * _snapshot.cell_m)


## One capsule per body, feet at each position (world metres).
func place_bodies(feet: Array[Vector3]) -> void:
	for child: Node in _bodies.get_children():
		_bodies.remove_child(child)
		child.queue_free()
	var capsule: CapsuleMesh = CapsuleMesh.new()
	capsule.radius = BODY_RADIUS_M
	capsule.height = BODY_HEIGHT_M
	capsule.material = _body_material
	for at: Vector3 in feet:
		var body: MeshInstance3D = MeshInstance3D.new()
		body.mesh = capsule
		body.position = IsoCamera.to_godot(at + Vector3(0.0, 0.0, BODY_HEIGHT_M * 0.5))
		_bodies.add_child(body)


## The shaded look, or a mask pass: in a mask pass bloom is off (it would bleed white into black) and bodies draw in
## their ID colour.
func use_pass(which: CellVolume.Pass, bloom: bool) -> void:
	volume.use_pass(which)
	_body_material.albedo_color = BODY_SHADED if which == CellVolume.Pass.SHADED else BODY_ID
	_environment.glow_enabled = bloom and which == CellVolume.Pass.SHADED


## Draw one frame and return it. The viewport draws every frame (UPDATE_ALWAYS); frame_post_draw fires once that
## frame, subviewports included, has been drawn, so the texture holds what was set before the call.
func capture() -> Image:
	await RenderingServer.frame_post_draw
	return get_texture().get_image()
