class_name FuelPass
extends Node3D
## The fuel-object pass (docs/design/client_objects.md §4): one MultiMesh per kind, one instance per object, drawn
## beside the cell volume and composited with it by the depth buffer. What it draws comes only from a FuelSnapshot
## (the tables) and the camera's pixel size; nothing it computes leaves the client.
## Engine whys: a MultiMeshInstance3D draws every instance of one mesh in one draw call with per-instance
## transforms, where a node per object would be 2,000 nodes and 2,000 draw calls; Node3D is the parent because the
## pass is a group of meshes with no transform of its own; data textures carry segment state because Compatibility
## keeps per-instance custom data at half float (§2).

const ROD_SHADER: Shader = preload("res://addons/engine/render/fuel_rod.gdshader")
const SLAB_SHADER: Shader = preload("res://addons/engine/render/fuel_slab.gdshader")
## Must equal the shaders' ``ROW_WIDTH`` and ``recipe_colours[]`` size; test_fuel_pass.gd holds them together.
const ROW_WIDTH: int = 256
const PALETTE_SIZE: int = 16
const INSTANCE_TEXELS: int = 3
## The segment columns each sampler uploads, with the image format their bytes already are.
const SEGMENT_TEXTURES: Dictionary[StringName, String] = {
	&"temperature_tex": "surface_temperature_c", &"ignited_tex": "ignited_fraction",
	&"thickness_tex": "thickness_fraction", &"char_tex": "char_fraction",
}
const UNCOLOURED: Color = Color(1.0, 0.0, 1.0)

var rods: MultiMeshInstance3D = MultiMeshInstance3D.new()
var slabs: MultiMeshInstance3D = MultiMeshInstance3D.new()
## The instance images last built, kept so tests can read what the shader is given (the headless renderer keeps no
## texture contents).
var instance_images: Dictionary[String, Image] = {}
## How many times instances were rebuilt: a burnout or a new temperature must not add one.
var rebuilds: int = 0
var _materials: Dictionary[String, ShaderMaterial] = {"rod": ShaderMaterial.new(), "slab": ShaderMaterial.new()}
var _trigger: PackedByteArray = PackedByteArray()
var _recipe_slots: Dictionary[int, int] = {}
var _set_names: Array[StringName] = []


func _init() -> void:
	var cylinder: CylinderMesh = CylinderMesh.new()
	cylinder.top_radius = 1.0
	cylinder.bottom_radius = 1.0
	cylinder.height = 1.0
	cylinder.radial_segments = 12
	cylinder.rings = 0
	_materials["rod"].shader = ROD_SHADER
	_materials["slab"].shader = SLAB_SHADER
	_setup(rods, cylinder, _materials["rod"])
	_setup(slabs, BoxMesh.new(), _materials["slab"])


func _setup(instance: MultiMeshInstance3D, mesh: Mesh, material: ShaderMaterial) -> void:
	var multimesh: MultiMesh = MultiMesh.new()
	multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multimesh.mesh = mesh
	instance.multimesh = multimesh
	instance.material_override = material
	add_child(instance)


## Draw ``snap``, which must be drawable (its filler refused it otherwise). Instances are rebuilt only when the
## trigger bytes change (§3.2), so a steady burn uploads its segment columns and nothing else.
func show_fuel(snap: FuelSnapshot) -> void:
	var trigger: PackedByteArray = snap.trigger_bytes()
	if trigger != _trigger:
		_rebuild(snap)
		_trigger = trigger
	for uniform_name: StringName in SEGMENT_TEXTURES:
		var bytes: PackedByteArray = snap.column("segments", SEGMENT_TEXTURES[uniform_name])
		var format: Image.Format = Image.FORMAT_RH if uniform_name == &"temperature_tex" else Image.FORMAT_R8
		_param(uniform_name, _row_texture(bytes, format, uniform_name))
	_param(&"state_tex", _row_texture(snap.column("objects", "state"), Image.FORMAT_R8, &"state_tex"))


## Albedo by recipe for every recipe in ``ids`` (name -> id), from ``colours`` (id -> linear colour). Returns what is
## wrong, for the caller to report: a recipe the palette doesn't colour, or more recipes than the shader holds. Those
## draw magenta.
func use_palette(ids: Dictionary[String, int], colours: Dictionary[int, Color]) -> Array[String]:
	var problems: Array[String] = []
	var out: Array[Vector3] = []
	_recipe_slots.clear()
	for recipe_name: String in ids:
		var slot: int = _recipe_slots.size()
		if slot >= PALETTE_SIZE:
			problems.append("recipe %s is past the shader's %d colours" % [recipe_name, PALETTE_SIZE])
			continue
		_recipe_slots[ids[recipe_name]] = slot
		var colour: Color = colours[ids[recipe_name]] if colours.has(ids[recipe_name]) else UNCOLOURED
		if not colours.has(ids[recipe_name]):
			problems.append("recipe %s has no colour" % recipe_name)
		out.append(Vector3(colour.r, colour.g, colour.b))
	while out.size() < PALETTE_SIZE:
		out.append(Vector3(UNCOLOURED.r, UNCOLOURED.g, UNCOLOURED.b))
	_param(&"recipe_colours", out)
	_trigger = PackedByteArray()  # slots feed the instance texture: rebuild on the next frame
	return problems


## Metres one output pixel spans (§4.2's floor is two of them). Refuses a size that isn't a positive finite number.
func use_pixel_metres(output_pixel_m: float) -> String:
	if not (is_finite(output_pixel_m) and output_pixel_m > 0.0):
		return "output pixel size %s is not a positive number of metres" % output_pixel_m
	_param(&"floor_half_m", output_pixel_m)
	return ""


func _rebuild(snap: FuelSnapshot) -> void:
	rebuilds += 1
	var first: PackedInt32Array = snap.first_rows()
	var rod_id: int = snap.kind_ids.get("rod", -1)
	var rod_rows: Array[int] = []
	var slab_rows: Array[int] = []
	var kind_of: PackedByteArray = snap.column("objects", "kind")
	for row: int in snap.rows["objects"]:
		if kind_of[row] == rod_id:
			rod_rows.append(row)
		else:
			slab_rows.append(row)
	_place(rods, snap, "rods", rod_rows, first)
	_place(slabs, snap, "slabs", slab_rows, first)


## Instance transforms and the instance texture for one kind. Instance i is geometry row i, which FuelSnapshot holds
## to be the kind's objects in object order.
func _place(instance: MultiMeshInstance3D, snap: FuelSnapshot, table: String, object_rows: Array[int], first: PackedInt32Array) -> void:
	var n: int = object_rows.size()
	instance.multimesh.instance_count = n
	var bytes: PackedByteArray = PackedByteArray()
	if bytes.resize(maxi(n, 1) * INSTANCE_TEXELS * 4) != OK:
		push_error("FuelPass: cannot allocate %d instances" % n)
		return
	for i: int in n:
		var row: int = object_rows[i]
		instance.multimesh.set_instance_transform(i, FuelGeometry.transform(snap, table, i))
		_write_instance(bytes, i, snap, row, first[row])
	var image: Image = Image.create_from_data(INSTANCE_TEXELS, maxi(n, 1), false, Image.FORMAT_RGBA8, bytes)
	instance_images[table] = image
	_materials[table.trim_suffix("s")].set_shader_parameter(&"instance_tex", ImageTexture.create_from_image(image))
	if not _set_names.has(&"instance_tex"):
		_set_names.append(&"instance_tex")


func _write_instance(bytes: PackedByteArray, i: int, snap: FuelSnapshot, row: int, first_row: int) -> void:
	var at: int = i * INSTANCE_TEXELS * 4
	bytes.encode_u32(at, first_row)
	var slot: int = _recipe_slots.get(snap.column("objects", "recipe_id").decode_u16(row * 2), PALETTE_SIZE - 1)
	bytes[at + 3] = slot
	bytes.encode_u16(at + 4, snap.column("objects", "segment_count").decode_u16(row * 2))
	bytes.encode_u16(at + 6, row)
	bytes.encode_float(at + 8, snap.column("objects", "segment_length_m").decode_float(row * 4))


## A column as a texture ROW_WIDTH texels wide, row i at (i mod ROW_WIDTH, i div ROW_WIDTH): the bytes as they arrived,
## padded to whole rows, with no per-row loop. Updated in place while its size holds.
func _row_texture(bytes: PackedByteArray, format: Image.Format, key: StringName) -> ImageTexture:
	var texel: int = 2 if format == Image.FORMAT_RH else 1
	var rows: int = maxi(ceili(float(bytes.size()) / float(texel * ROW_WIDTH)), 1)
	var padded: PackedByteArray = bytes.duplicate()
	if padded.resize(rows * ROW_WIDTH * texel) != OK:
		push_error("FuelPass: cannot pad %s" % key)
	var image: Image = Image.create_from_data(ROW_WIDTH, rows, false, format, padded)
	var current: Variant = _materials["rod"].get_shader_parameter(key)
	if current is ImageTexture:
		var texture: ImageTexture = current
		if texture.get_height() == rows and texture.get_format() == format:
			texture.update(image)
			return texture
	return ImageTexture.create_from_image(image)


## Every uniform name this pass has set, so a test can hold them to the shaders' own declarations.
func uniform_names() -> Array[StringName]:
	return _set_names


func _param(param_name: StringName, value: Variant) -> void:
	if not _set_names.has(param_name):
		_set_names.append(param_name)
	for kind: String in _materials:
		_materials[kind].set_shader_parameter(param_name, value)
