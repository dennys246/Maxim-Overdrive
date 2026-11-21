class_name SliceVoxels
extends MultiMeshInstance3D
## The alley's solid cells as one MultiMesh of cubes. A MultiMesh draws every instance in a single draw call, from
## one mesh plus a per-instance buffer (transform, colour, custom data), which is why it suits grey-box voxels where
## thousands of separate MeshInstance3D nodes would each cost a call. Cells buried on all six sides are skipped.
##
## The server's axes are x east, y north, z up; Godot's are x right, y up, -z forward. A cell centre at server
## (x, y, z) is drawn at Godot (x, z, -y), which keeps both right-handed.

const FLOATS_PER_INSTANCE: int = 20  # 12 transform, 4 colour, 4 custom

var _shape: Vector3i = Vector3i.ZERO
var _dx: float = 0.2
var _palette: Dictionary = {}  # material id (int) -> Color
var _material: PackedByteArray = PackedByteArray()
var _cells: PackedInt32Array = PackedInt32Array()  # the cell index drawn by each instance
var _buffer: PackedFloat32Array = PackedFloat32Array()
var _shader: ShaderMaterial = ShaderMaterial.new()


static func to_godot(x: float, y: float, z: float) -> Vector3:
	return Vector3(x, z, -y)


func configure(shape: Vector3i, dx: float, palette: Dictionary) -> void:
	_shape = shape
	_dx = dx
	_palette = palette
	var box: BoxMesh = BoxMesh.new()
	box.size = Vector3.ONE
	multimesh = MultiMesh.new()
	multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multimesh.use_colors = true
	multimesh.use_custom_data = true
	multimesh.mesh = box
	_shader.shader = preload("res://shaders/voxel.gdshader")
	material_override = _shader


func set_show_heat(on: bool) -> void:
	_shader.set_shader_parameter("show_heat", on)


func _index(i: int, j: int, k: int) -> int:
	return (i * _shape.y + j) * _shape.z + k  # C order, as the server packs it


func _solid(i: int, j: int, k: int) -> bool:
	if i < 0 or j < 0 or k < 0 or i >= _shape.x or j >= _shape.y or k >= _shape.z:
		return false
	return _material[_index(i, j, k)] != 0


func _exposed(i: int, j: int, k: int) -> bool:
	return not (_solid(i - 1, j, k) and _solid(i + 1, j, k) and _solid(i, j - 1, k) and _solid(i, j + 1, k)
		and _solid(i, j, k - 1) and _solid(i, j, k + 1))


func _rebuild() -> void:
	_cells.clear()
	for i: int in _shape.x:
		for j: int in _shape.y:
			for k: int in _shape.z:
				if _solid(i, j, k) and _exposed(i, j, k):
					var _added: bool = _cells.append(_index(i, j, k))
	multimesh.instance_count = _cells.size()
	var _resized: int = _buffer.resize(_cells.size() * FLOATS_PER_INSTANCE)


## Draw one state: the four uint8 channels, each one byte per cell in C order.
func show_cells(material: PackedByteArray, crack: PackedByteArray, glow: PackedByteArray, heat: PackedByteArray) -> void:
	if material != _material:
		_material = material
		_rebuild()
	var nyz: int = _shape.y * _shape.z
	for n: int in _cells.size():
		var c: int = _cells[n]
		@warning_ignore("integer_division")
		var i: int = c / nyz
		@warning_ignore("integer_division")
		var j: int = (c % nyz) / _shape.z
		var k: int = c % _shape.z
		var at: Vector3 = to_godot((i + 0.5) * _dx, (j + 0.5) * _dx, (k + 0.5) * _dx)
		var cracked: float = crack[c] / 255.0
		var s: float = _dx * (1.0 - 0.35 * cracked)  # a cracked cell shrinks: shape, not only shade
		var colour: Color = _palette.get(int(material[c]), Color.MAGENTA)
		var o: int = n * FLOATS_PER_INSTANCE
		_buffer[o] = s
		_buffer[o + 1] = 0.0
		_buffer[o + 2] = 0.0
		_buffer[o + 3] = at.x
		_buffer[o + 4] = 0.0
		_buffer[o + 5] = s
		_buffer[o + 6] = 0.0
		_buffer[o + 7] = at.y
		_buffer[o + 8] = 0.0
		_buffer[o + 9] = 0.0
		_buffer[o + 10] = s
		_buffer[o + 11] = at.z
		_buffer[o + 12] = colour.r
		_buffer[o + 13] = colour.g
		_buffer[o + 14] = colour.b
		_buffer[o + 15] = 1.0
		_buffer[o + 16] = glow[c] / 255.0
		_buffer[o + 17] = cracked
		_buffer[o + 18] = heat[c] / 255.0
		_buffer[o + 19] = 0.0
	multimesh.buffer = _buffer
