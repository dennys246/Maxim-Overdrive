class_name CellVolume
extends MeshInstance3D
## The cell volume (client_rendering.md §5, §7.1): one box mesh over the snapshot's extent and the raymarch shader
## that draws its cells. It owns the textures and the uniforms; what it draws comes only from a CellSnapshot (the
## channels) and from the camera and the cut-away (view state), and nothing it computes leaves the client.
## Engine whys: MeshInstance3D draws one mesh with one material, which is all a raymarch needs; a BoxMesh is the
## cheapest geometry that covers every pixel the volume can appear in; ShaderMaterial carries our own shader and its
## uniforms.

const SHADER_LINEAR: Shader = preload("res://addons/engine/render/cell_volume_linear.gdshader")
const SHADER_NEAREST: Shader = preload("res://addons/engine/render/cell_volume_nearest.gdshader")
const PALETTE_SIZE: int = 16

enum Pass { SHADED = 0, OCCLUDER = 1, CRACK_MASK = 2, GLOW_MASK = 3 }

var _material: ShaderMaterial = ShaderMaterial.new()
var _box: BoxMesh = BoxMesh.new()


func _init() -> void:
	mesh = _box
	material_override = _material
	_material.shader = SHADER_LINEAR


## Upload ``snap``'s channels and size the box to its extent. The snapshot must be drawable (snap.problems() empty):
## its filler refuses one that isn't.
func show_snapshot(snap: CellSnapshot) -> void:
	var extent_world: Vector3 = Vector3(snap.nx, snap.ny, snap.nz) * snap.cell_m
	_box.size = IsoCamera.to_godot(extent_world).abs()
	position = IsoCamera.to_godot(extent_world * 0.5)
	_param("cells", Vector3i(snap.nx, snap.ny, snap.nz))
	_param("cell_m", snap.cell_m)
	_param("centre_godot", position)
	_param("glow_offset_c", snap.glow_offset_c)
	_param("glow_scale_c", snap.glow_scale_c_per_count)
	_param("material_tex", VolumeTextures.texture(snap, snap.channels["material"], Image.FORMAT_R8))
	_param("region_tex", VolumeTextures.texture(snap, snap.channels["region"], Image.FORMAT_RG8))
	_param("crack_tex", VolumeTextures.texture(snap, snap.channels["crack"], Image.FORMAT_R8))
	_param("glow_tex", VolumeTextures.texture(snap, snap.channels["surface_glow"], Image.FORMAT_R8))
	_param("burning_tex", VolumeTextures.texture(snap, snap.channels["burning"], Image.FORMAT_R8))
	_param("bricks_tex", VolumeTextures.bricks_texture(snap))


## The tier's shader variant and detail uniforms (§5.5).
func use_tier(tier: RenderTier) -> void:
	_material.shader = SHADER_LINEAR if tier.glow_linear else SHADER_NEAREST
	_param("crack_substeps", tier.crack_substeps)
	_param("ao_taps", tier.ao_taps)


## Albedo by material id: ``colours`` maps a material id to its colour; ids it lacks draw black.
func use_palette(colours: Dictionary[int, Color]) -> void:
	var out: Array[Vector3] = []
	for id: int in PALETTE_SIZE:
		var c: Color = colours.get(id, Color.BLACK)
		out.append(Vector3(c.r, c.g, c.b))
	_param("palette", PackedVector3Array(out))


## The cut-away's result (Cutaway.cut_regions and stump_top_m).
func use_cut(ids: PackedInt32Array, stump_top_m: float) -> void:
	var padded: PackedInt32Array = ids.duplicate()
	if padded.resize(Cutaway.MAX_CUT) != OK:
		push_error("CellVolume: could not size the cut list")
	_param("cut_ids", padded)
	_param("cut_count", mini(ids.size(), Cutaway.MAX_CUT))
	_param("stump_top_m", stump_top_m)


## The metres one rendered pixel spans (IsoCamera.pixel_metres), which sets the narrowest crack groove (§5.4).
func use_pixel_metres(metres: float) -> void:
	_param("pixel_m", metres)


func use_pass(which: Pass) -> void:
	_param("debug_mode", int(which))


## 0 freezes the flame flicker (goldens, §6.1); 1 is play.
func use_flicker(amount: float) -> void:
	_param("flicker_amount", amount)


## A uniform's current value, for tests.
func uniform(uniform_name: StringName) -> Variant:
	return _material.get_shader_parameter(uniform_name)


func shader() -> Shader:
	return _material.shader


func _param(uniform_name: StringName, value: Variant) -> void:
	_material.set_shader_parameter(uniform_name, value)
