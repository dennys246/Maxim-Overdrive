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
const ROD_FRINGE_SHADER: Shader = preload("res://addons/engine/render/fuel_rod_fringe.gdshader")
const SLAB_SHADER: Shader = preload("res://addons/engine/render/fuel_slab.gdshader")
const FLAME_SHADER: Shader = preload("res://addons/engine/render/fuel_flame.gdshader")
## Must equal the shaders' ``ROW_WIDTH`` and ``recipe_colours[]`` size; test_fuel_pass.gd holds them together.
const ROW_WIDTH: int = 256
const PALETTE_SIZE: int = 16
## The last slot is magenta, never a recipe's: an unknown recipe, or one past the palette, draws in it (§4.1).
const UNCOLOURED_SLOT: int = PALETTE_SIZE - 1
const INSTANCE_TEXELS: int = 3
## The segment columns each sampler uploads, with the image format their bytes already are.
const SEGMENT_TEXTURES: Dictionary[StringName, String] = {
	&"temperature_tex": "surface_temperature_c", &"ignited_tex": "ignited_fraction",
	&"thickness_tex": "thickness_fraction", &"char_tex": "char_fraction",
}
const UNCOLOURED: Color = Color(1.0, 0.0, 1.0)
## What the pass draws (the shaders' fuel_debug): shaded, or §7.2's ID masks, unlit: fuel white, or flames white.
enum View { SHADED = 0, FUEL_ID = 1, FLAME_ID = 2 }
## A Phase 1 flame's height at full ignition, metres: inside fire_model §4.1's 0.1-0.3 m for starter flames
## `[engineering]`. Set on the flame shader and used for its culling box, so the two can't disagree.
const FLAME_HEIGHT_M: float = 0.2
## The flicker's most extra height at full amount: the flame shader's 0.2 · sin, which use_flicker's clamp bounds.
const FLICKER_HEIGHT: float = 0.2
## The slab shader's floor stops growing below this edge sine, so a slab grows by at most 2 floor pixels / 0.25.
const SLAB_MAX_GROWTH_PX: float = 8.0
## The unit meshes' half extents in local axes: _init's cylinder (radius 1, height 1) and Godot's default 1 m box.
const ROD_HALF: Vector3 = Vector3(1.0, 0.5, 1.0)
const SLAB_HALF: Vector3 = Vector3(0.5, 0.5, 0.5)

var rods: MultiMeshInstance3D = MultiMeshInstance3D.new()
var slabs: MultiMeshInstance3D = MultiMeshInstance3D.new()
## Phase 1 flames (§5.3): one camera-facing quad per segment row, collapsed by its shader unless the segment flames.
var flames: MultiMeshInstance3D = MultiMeshInstance3D.new()
## The instance images last built, kept so tests can read what the shader is given (the headless renderer keeps no
## texture contents).
var instance_images: Dictionary[String, Image] = {}
## How many times instances were rebuilt: a burnout or a new temperature must not add one.
var rebuilds: int = 0
var _materials: Dictionary[String, ShaderMaterial] = {
	"rod": ShaderMaterial.new(), "rod_core": ShaderMaterial.new(), "rod_fade": ShaderMaterial.new(),
	"slab": ShaderMaterial.new(), "flame": ShaderMaterial.new(),
}
## Each kind's materials: a rod draws its depth, then its colour's core and fade, each the previous one's next pass.
const KIND_MATERIALS: Dictionary[String, Array] = {
	"rod": ["rod", "rod_core", "rod_fade"], "slab": ["slab"], "flame": ["flame"],
}
## The structure and region map of the last frame drawn (§3.2): a frame whose structure differs is checked and rebuilt.
var _structure: Dictionary = {}
var _regions: Dictionary[int, String] = {}
var _recipe_slots: Dictionary[int, int] = {}
## The palette use_palette last set, applied by the next frame show_fuel draws.
var _palette: Array[Vector3] = []
var _palette_slots: Dictionary[int, int] = {}
var _set_names: Array[StringName] = []
var _floor_half_m: float = 0.0
var _render_scale: float = 1.0
## The objects' boxes as built, before any vertex-shader growth (computed here: the renderer's own box isn't readable
## headless, and this one is the data's).
var _boxes: Dictionary[String, AABB] = {"rod": AABB(), "slab": AABB()}
var _flame_width_m: float = 0.0


func _init() -> void:
	var cylinder: CylinderMesh = CylinderMesh.new()
	cylinder.top_radius = 1.0
	cylinder.bottom_radius = 1.0
	cylinder.height = 1.0
	cylinder.radial_segments = 12
	cylinder.rings = 0
	_materials["rod"].shader = ROD_SHADER
	_materials["rod_core"].shader = ROD_FRINGE_SHADER
	_materials["rod_fade"].shader = ROD_FRINGE_SHADER
	_materials["rod_fade"].set_shader_parameter(&"fade_half", true)
	# Engine why: next_pass draws the same mesh again with another material; the depth pass writes every rod's
	# silhouette before the colour blends, so crossing rods occlude by depth (fuel_rod.gdshaderinc, review C-S1).
	_materials["rod"].next_pass = _materials["rod_core"]
	_materials["rod_core"].next_pass = _materials["rod_fade"]
	# Every rod pass blends, so they sort in the transparent pass, where priority, not distance, orders them: every
	# rod's depth, then every rod's core, then every rod's fade (so a front fade lands on a rear core, review D1),
	# then the flames.
	_materials["rod_core"].render_priority = 1
	_materials["rod_fade"].render_priority = 2
	_materials["slab"].shader = SLAB_SHADER
	_materials["flame"].shader = FLAME_SHADER
	# Flames last, whatever the camera: by box centre a flame could sort before a rod's colour pass, which would then
	# blend over the light the flame added (C-S2).
	_materials["flame"].render_priority = 3
	_setup(rods, cylinder, _materials["rod"])
	_setup(slabs, BoxMesh.new(), _materials["slab"])
	_setup(flames, QuadMesh.new(), _materials["flame"])
	_param_on("flame", &"flame_height_m", FLAME_HEIGHT_M)


func _setup(instance: MultiMeshInstance3D, mesh: Mesh, material: ShaderMaterial) -> void:
	var multimesh: MultiMesh = MultiMesh.new()
	multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multimesh.mesh = mesh
	instance.multimesh = multimesh
	instance.material_override = material
	add_child(instance)


## Draw ``snap`` and return what is wrong with it; a refused frame draws nothing new, and the last good one stays.
## ``region_names`` is the region map (id -> name). The structural check and the rebuild run only when the structure or
## the region map changes (§3.2); every frame gets the per-frame check, so a steady burn costs a compare, the
## per-frame check (its temperature loop, about 1.8 ms at 2×10⁴ segments, measured) and its segment uploads.
func show_fuel(snap: FuelSnapshot, region_names: Dictionary[int, String]) -> Array[String]:
	# Every check runs before anything is drawn: a refused frame changes no instance, texture or colour (review TB2-B1).
	var frame: Array[String] = snap.frame_problems()
	if not frame.is_empty():
		return frame
	var structure: Dictionary = snap.structure()
	var rebuild: bool = structure != _structure or region_names != _regions or _palette_slots != _recipe_slots
	if rebuild:
		var found: Array[String] = snap.problems(region_names)
		if not found.is_empty():
			return found
	if not _palette.is_empty():
		_param(&"recipe_colours", _palette)
	if rebuild:
		_recipe_slots = _palette_slots
		_rebuild(snap)
		# A deep copy: the snapshot's own arrays edited in place must still read as a change (review TB2-S1).
		_structure = structure.duplicate(true)
		_regions = region_names.duplicate()
	for uniform_name: StringName in SEGMENT_TEXTURES:
		var bytes: PackedByteArray = snap.column("segments", SEGMENT_TEXTURES[uniform_name])
		var format: Image.Format = Image.FORMAT_RH if uniform_name == &"temperature_tex" else Image.FORMAT_R8
		_param(uniform_name, _row_texture(bytes, format, uniform_name))
	_param(&"state_tex", _row_texture(snap.column("objects", "state"), Image.FORMAT_R8, &"state_tex"))
	return []


## Albedo by recipe for every recipe in ``ids`` (name -> id), from ``colours`` (id -> linear colour). Returns what is
## wrong, for the caller to report: a recipe the palette doesn't colour, or more recipes than the shader holds. Those
## draw magenta. The palette takes effect with the next frame drawn, so a refused frame never recolours the last good
## one (review TB2-S3); instances are rebuilt then only if a recipe's slot changed.
func use_palette(ids: Dictionary[String, int], colours: Dictionary[int, Color]) -> Array[String]:
	var problems: Array[String] = []
	var out: Array[Vector3] = []
	var slots: Dictionary[int, int] = {}
	for recipe_name: String in ids:
		var slot: int = slots.size()
		if slot >= UNCOLOURED_SLOT:
			problems.append("recipe %s is past the shader's %d colours" % [recipe_name, UNCOLOURED_SLOT])
			continue
		slots[ids[recipe_name]] = slot
		var colour: Color = colours.get(ids[recipe_name], UNCOLOURED)
		if not colours.has(ids[recipe_name]):
			problems.append("recipe %s has no colour" % recipe_name)
		out.append(Vector3(colour.r, colour.g, colour.b))
	while out.size() < PALETTE_SIZE:
		out.append(Vector3(UNCOLOURED.r, UNCOLOURED.g, UNCOLOURED.b))
	_palette = out
	_palette_slots = slots
	return problems


## Half a rod's drawn width, metres: its radius, floored at one output pixel so the rod is never narrower than 2 (§4.2).
## The rod shader's v_drawn_m is this rule on the GPU (floor_half_m is one output pixel); the golden footprints and
## the stability check call this, so the checks measure the width the shader draws.
static func drawn_half_m(radius_m: float, output_pixel_m: float) -> float:
	return maxf(radius_m, output_pixel_m)


## 0 in goldens (animation off, client_rendering.md §6.1), 1 in play: the flames' flicker.
func use_flicker(amount: float) -> void:
	_param_on("flame", &"flame_flicker", clampf(amount, 0.0, 1.0))


## What to draw: shaded, or one of the ID masks §7.2's checks read.
func use_view(view: View) -> void:
	_param(&"fuel_debug", int(view))


## Metres one output pixel spans (§4.2's floor is two of them), and the tier's render scale, which sets the rods'
## edge fade to one rendered pixel. Refuses a size or scale that isn't a positive finite number.
func use_pixel_metres(output_pixel_m: float, render_scale: float) -> String:
	if not (is_finite(output_pixel_m) and output_pixel_m > 0.0):
		return "output pixel size %s is not a positive number of metres" % output_pixel_m
	if not (is_finite(render_scale) and render_scale > 0.0):
		return "render scale %s is not a positive number" % render_scale
	_floor_half_m = output_pixel_m
	_render_scale = render_scale
	_param(&"floor_half_m", output_pixel_m)
	_param_on("rod", &"render_pixel_m", output_pixel_m / render_scale)
	_fit_boxes()
	return ""


func _rebuild(snap: FuelSnapshot) -> void:
	rebuilds += 1
	var first: PackedInt32Array = snap.first_rows()
	var rod_xf: PackedFloat32Array = FuelGeometry.rod_buffer(snap)
	var slab_xf: PackedFloat32Array = FuelGeometry.slab_buffer(snap)
	_place(rods, snap, "rod", rod_xf, first)
	_place(slabs, snap, "slab", slab_xf, first)
	_boxes = {"rod": FuelGeometry.bounds(rod_xf, ROD_HALF), "slab": FuelGeometry.bounds(slab_xf, SLAB_HALF)}
	_flame_width_m = FuelGeometry.widest_flame_m(snap)
	flames.multimesh.instance_count = snap.rows["segments"]
	if snap.rows["segments"] > 0:
		flames.multimesh.buffer = FuelGeometry.flame_buffer(snap)
	var objects: PackedFloat32Array = FuelGeometry.segment_objects(snap)
	_param_on("flame", &"segment_object_tex", _row_texture(objects.to_byte_array(), Image.FORMAT_RF, &"segment_object_tex"))
	_fit_boxes()


## Instance transforms and the instance texture for one kind. Instance i is geometry row i, object row
## snap.geometry_rows(kind)[i].
func _place(instance: MultiMeshInstance3D, snap: FuelSnapshot, kind: String, transforms: PackedFloat32Array, first: PackedInt32Array) -> void:
	var object_rows: PackedInt32Array = snap.geometry_rows(kind)
	var n: int = object_rows.size()
	instance.multimesh.instance_count = n
	if n > 0:
		instance.multimesh.buffer = transforms
	var bytes: PackedByteArray = PackedByteArray()
	if bytes.resize(maxi(n, 1) * INSTANCE_TEXELS * 4) != OK:
		push_error("FuelPass: cannot allocate %d instances" % n)
		return
	var recipes: PackedByteArray = snap.column("objects", "recipe_id")
	var counts: PackedByteArray = snap.column("objects", "segment_count")
	var lengths: PackedByteArray = snap.column("objects", "segment_length_m")
	for i: int in n:
		var row: int = object_rows[i]
		var at: int = i * INSTANCE_TEXELS * 4
		bytes.encode_u32(at, first[row])
		bytes[at + 3] = _recipe_slots.get(recipes.decode_u16(row * 2), UNCOLOURED_SLOT)
		bytes.encode_u16(at + 4, counts.decode_u16(row * 2))
		bytes.encode_u16(at + 6, row)
		bytes.encode_u32(at + 8, lengths.decode_u32(row * 4))  # the f32's bits, unchanged
	var image: Image = Image.create_from_data(INSTANCE_TEXELS, maxi(n, 1), false, Image.FORMAT_RGBA8, bytes)
	instance_images[kind + "s"] = image
	_param_on(kind, &"instance_tex", ImageTexture.create_from_image(image))


## Culling boxes from the data, grown by what the vertex shaders add: a rod's floor and fade, a slab's floored
## thickness, and a flame's height and half its width (the widest flame's, or the shader's four floor pixels). A flame
## rises from a point on its object, so the objects' box grown by that reach holds every flame.
func boxes() -> Dictionary[String, AABB]:
	return _boxes


func _fit_boxes() -> void:
	var px: float = _floor_half_m
	var rod_box: AABB = _boxes["rod"]
	# The rod shader widens a rod to its floor plus one rendered pixel: px · (1 + 1/scale) past its radius.
	var slab_box: AABB = _boxes["slab"]
	rods.custom_aabb = rod_box.grow(px * (1.0 + 1.0 / _render_scale))
	slabs.custom_aabb = slab_box.grow(SLAB_MAX_GROWTH_PX * px)
	var both: AABB = rod_box.merge(slab_box)
	if not slab_box.has_volume():
		both = rod_box  # an empty box is at the origin; merging it would stretch the flames' box to it
	elif not rod_box.has_volume():
		both = slab_box
	var reach: float = FLAME_HEIGHT_M * (1.0 + FLICKER_HEIGHT) + 0.5 * maxf(_flame_width_m, 4.0 * px)
	flames.custom_aabb = both.grow(reach)


## A column as a texture ROW_WIDTH texels wide, row i at (i mod ROW_WIDTH, i div ROW_WIDTH): the bytes as they arrived,
## padded to whole rows, with no per-row loop. Updated in place while its size holds.
func _row_texture(bytes: PackedByteArray, format: Image.Format, key: StringName) -> ImageTexture:
	var texel: int = {Image.FORMAT_RH: 2, Image.FORMAT_RF: 4}.get(format, 1)
	var rows: int = maxi(ceili(float(bytes.size()) / float(texel * ROW_WIDTH)), 1)
	var padded: PackedByteArray = bytes.duplicate()
	if padded.resize(rows * ROW_WIDTH * texel) != OK:
		push_error("FuelPass: cannot pad %s" % key)
	var image: Image = Image.create_from_data(ROW_WIDTH, rows, false, format, padded)
	var current: Variant = _materials["flame" if key == &"segment_object_tex" else "rod"].get_shader_parameter(key)
	if current is ImageTexture:
		var texture: ImageTexture = current
		if texture.get_height() == rows and texture.get_format() == format:
			texture.update(image)
			return texture
	return ImageTexture.create_from_image(image)


## Every uniform name this pass has set, so a test can hold them to the shaders' own declarations.
func uniform_names() -> Array[StringName]:
	return _set_names


## Set a uniform on one kind's materials only (``kind``: "rod", "slab" or "flame").
func _param_on(kind: String, param_name: StringName, value: Variant) -> void:
	if not _set_names.has(param_name):
		_set_names.append(param_name)
	for material_name: String in KIND_MATERIALS[kind]:
		_materials[material_name].set_shader_parameter(param_name, value)


func _param(param_name: StringName, value: Variant) -> void:
	if not _set_names.has(param_name):
		_set_names.append(param_name)
	for kind: String in _materials:
		_materials[kind].set_shader_parameter(param_name, value)
