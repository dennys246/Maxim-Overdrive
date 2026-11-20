extends Node3D
## §9 probe: a u16 region id uploaded as FORMAT_RG8 (the wire's little-endian bytes, unchanged) and read back in a
## spatial shader with texelFetch as r + 256·g. Every one of the 65,536 ids is drawn as one pixel that is white when
## the shader decoded its own index. Needs a real renderer:
## godot --rendering-driver opengl3 --rendering-method gl_compatibility --resolution 256x256
##       --path tools/godot_probes res://probe_rg8.tscn

const SIDE: int = 256
const DEPTH: int = 16
const ROWS: int = 16

@onready var _quad: MeshInstance3D = $Quad


func _ready() -> void:
	var slices: Array[Image] = []
	for z: int in DEPTH:
		var bytes: PackedByteArray = PackedByteArray()
		var resized: Error = bytes.resize(SIDE * ROWS * 2) as Error
		if resized != OK:
			push_error("probe rg8: resize failed: %s" % error_string(resized))
		for i: int in SIDE * ROWS:
			bytes.encode_u16(i * 2, z * SIDE * ROWS + i)  # little-endian, as the wire sends u16
		slices.append(Image.create_from_data(SIDE, ROWS, false, Image.FORMAT_RG8, bytes))
	var texture: ImageTexture3D = ImageTexture3D.new()
	var err: Error = texture.create(Image.FORMAT_RG8, SIDE, ROWS, DEPTH, false, slices)
	if err != OK:
		push_error("probe rg8: create failed: %s" % error_string(err))
	var material: ShaderMaterial = _quad.get_surface_override_material(0) as ShaderMaterial
	material.set_shader_parameter("ids", texture)
	await RenderingServer.frame_post_draw
	var image: Image = get_viewport().get_texture().get_image()
	var wrong: int = 0
	for y: int in image.get_height():
		for x: int in image.get_width():
			if image.get_pixel(x, y).g < 0.5:
				wrong += 1
	print("probe rg8: %dx%d pixels, %d decoded wrong, adapter=%s" % [
		image.get_width(), image.get_height(), wrong, RenderingServer.get_video_adapter_name()])
	get_tree().quit(0)
