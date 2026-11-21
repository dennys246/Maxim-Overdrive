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
## Must equal the shader's ``palette[]`` size (lighting.gdshaderinc); test_cell_volume.gd holds the two together.
const PALETTE_SIZE: int = 16
## The sampler uniform each channel uploads to.
const CHANNEL_TEXTURES: Dictionary[StringName, String] = {
	&"material_tex": "material", &"region_tex": "region", &"crack_tex": "crack",
	&"glow_tex": "surface_glow", &"burning_tex": "burning",
}
## A crack polygon spans at least this many pixels, so grooves at their pixel floor never fill a face: the laptop
## tier, at 0.028 m per pixel, drew one-cell polygons as speckle with no shape left.
const CRACK_MIN_POLYGON_PX: float = 12.0
## How far past an octave boundary the zoom must move before the crack pattern changes octave, so a zoom resting on
## a boundary (the default 12 m view sits exactly on one) never flickers between two patterns.
const OCTAVE_HYSTERESIS: float = 0.1

## What a material the palette doesn't colour draws as: loud magenta, never black on a black night.
const UNCOLOURED: Color = Color(1.0, 0.0, 1.0)

enum Pass { SHADED = 0, OCCLUDER = 1, CRACK_MASK = 2, GLOW_MASK = 3 }

var _material: ShaderMaterial = ShaderMaterial.new()
var _box: BoxMesh = BoxMesh.new()
var _set_names: Array[StringName] = []
var _cell_m: float = 0.0
var _pixel_m: float = 0.0
var _octave: int = -1


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
	_cell_m = snap.cell_m
	_update_crack_spacing()
	_param("centre_godot", position)
	_param("glow_offset_c", snap.glow_offset_c)
	_param("glow_scale_c", snap.glow_scale_c_per_count)
	for uniform_name: StringName in CHANNEL_TEXTURES:
		var channel: String = CHANNEL_TEXTURES[uniform_name]
		var format: Image.Format = Image.FORMAT_RG8 if channel == "region" else Image.FORMAT_R8
		_param(uniform_name, VolumeTextures.texture(snap, snap.channels[channel], format, _texture(uniform_name)))
	_param(&"bricks_tex", VolumeTextures.bricks_texture(snap, _texture(&"bricks_tex")))


## The tier's shader variant and detail uniforms (§5.5).
func use_tier(tier: RenderTier) -> void:
	_material.shader = SHADER_LINEAR if tier.glow_linear else SHADER_NEAREST
	_param("crack_substeps", tier.crack_substeps)
	_param("ao_taps", tier.ao_taps)


## Albedo by material id for every material in ``ids`` (the snapshot's vocabulary, name -> id), from ``colours``
## (id -> linear colour, MaterialPalette.by_id). A solid material the palette doesn't colour, or an id the shader's
## palette can't hold, is reported and drawn magenta, not left black and invisible.
func use_palette(ids: Dictionary[String, int], colours: Dictionary[int, Color]) -> void:
	var out: Array[Vector3] = []
	for id: int in PALETTE_SIZE:
		out.append(Vector3(UNCOLOURED.r, UNCOLOURED.g, UNCOLOURED.b))
	for material_name: String in ids:
		var id: int = ids[material_name]
		if id < 0 or id >= PALETTE_SIZE:
			push_error("CellVolume: material %s has id %d; the shader's palette holds 0..%d" % [material_name, id, PALETTE_SIZE - 1])
		elif colours.has(id):
			out[id] = Vector3(colours[id].r, colours[id].g, colours[id].b)
		elif id != 0:
			push_error("CellVolume: the palette has no colour for material %s; it draws magenta" % material_name)
	_param("palette", PackedVector3Array(out))


## The cut-away's result (Cutaway.cut_regions and stump_top_m).
func use_cut(ids: PackedInt32Array, stump_top_m: float) -> void:
	var padded: PackedInt32Array = ids.duplicate()
	if padded.resize(Cutaway.MAX_CUT) != OK:
		push_error("CellVolume: could not size the cut list")
	_param("cut_ids", padded)
	_param("cut_count", mini(ids.size(), Cutaway.MAX_CUT))
	_param("stump_top_m", stump_top_m)


## The metres one rendered pixel spans (IsoCamera.pixel_metres), which sets the narrowest crack groove and the
## crack pattern's octave (§5.4).
func use_pixel_metres(metres: float) -> void:
	if not metres > 0.0:
		push_error("CellVolume: a pixel spans %s m; it must be positive" % metres)
		return
	_param("pixel_m", metres)
	_pixel_m = metres
	_update_crack_spacing()


## The crack octave for a cell of ``cell_m`` seen at ``pixel_m`` metres per pixel, given the ``current`` octave (-1
## for none): the smallest power of two that keeps a polygon CRACK_MIN_POLYGON_PX pixels across, kept at ``current``
## while the exact value stays within OCTAVE_HYSTERESIS of it.
static func crack_octave(cell_m: float, pixel_m: float, current: int) -> int:
	var exact: float = log(CRACK_MIN_POLYGON_PX * pixel_m / cell_m) / log(2.0)
	if current >= 0 and exact > current - 1 - OCTAVE_HYSTERESIS and exact < current + OCTAVE_HYSTERESIS:
		return current
	return maxi(0, ceili(exact))


func _update_crack_spacing() -> void:
	if _cell_m > 0.0 and _pixel_m > 0.0:
		_octave = crack_octave(_cell_m, _pixel_m, _octave)
		_param("crack_spacing_m", _cell_m * pow(2.0, _octave))


func use_pass(which: Pass) -> void:
	_param("debug_mode", int(which))


## 0 freezes the flame flicker (goldens, §6.1); 1 is play.
func use_flicker(amount: float) -> void:
	_param("flicker_amount", amount)


## A uniform's current value, for tests.
func uniform(uniform_name: StringName) -> Variant:
	return _material.get_shader_parameter(uniform_name)


## Every uniform name this node has set, for the test that holds them to the shader's declarations.
func uniform_names() -> Array[StringName]:
	return _set_names


func shader() -> Shader:
	return _material.shader


func _texture(uniform_name: StringName) -> ImageTexture3D:
	var current: Variant = _material.get_shader_parameter(uniform_name)
	if current is ImageTexture3D:
		var tex: ImageTexture3D = current
		return tex
	return null


func _param(uniform_name: StringName, value: Variant) -> void:
	if not _set_names.has(uniform_name):
		_set_names.append(uniform_name)
	_material.set_shader_parameter(uniform_name, value)
