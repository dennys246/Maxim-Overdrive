extends SceneTree
## D-B2 probe (docs/design/client_objects.md §2): fuel objects as a MultiMesh with per-instance custom data, segment
## state in 2-D data textures read in vertex and fragment, RH 3-D linear filtering, the coverage of thin rods with and
## without a pixel floor and 4x MSAA, and the GDScript cost of instance builds and per-frame segment uploads (the
## minimum of 50). Windowed (the dummy renderer of --headless draws nothing):
## godot --rendering-driver opengl3 --rendering-method gl_compatibility --resolution 1280x720 --path tools/godot_probes
##       -s res://probe_fuel_objects.gd
## Prints PROBE lines; writes rods_*.png into the probe project's user:// directory.

const W: int = 1280
const H: int = 720
const SIZE_M: float = 10.0  # the golden camera: 72 px/m
const ROWS_W: int = 256

var vp: SubViewport
var out_dir: String
var cam_dir: Vector3

func _initialize() -> void:
	out_dir = ProjectSettings.globalize_path("user://")
	vp = SubViewport.new()
	vp.size = Vector2i(W, H)
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	vp.transparent_bg = false
	root.add_child(vp)
	var env: WorldEnvironment = WorldEnvironment.new()
	var e: Environment = Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0, 0, 0)
	env.environment = e
	vp.add_child(env)
	var cam: Camera3D = Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = SIZE_M
	# Elevation 40 deg, yaw 45 deg, looking at the origin from 60 m.
	var el: float = deg_to_rad(40.0)
	var yaw: float = deg_to_rad(45.0)
	var dir: Vector3 = Vector3(cos(el) * sin(yaw), sin(el), cos(el) * cos(yaw))
	cam.transform = Transform3D(Basis.looking_at(-dir, Vector3.UP), dir * 60.0)
	cam.near = 0.1
	cam.far = 200.0
	vp.add_child(cam)
	cam_dir = dir
	_run.call_deferred()

func _seg_textures(thick: PackedByteArray, temps: PackedFloat32Array) -> Array[ImageTexture]:
	var n: int = thick.size()
	var rows: int = ceili(float(n) / ROWS_W)
	var tb: PackedByteArray = thick.duplicate()
	var err: int = tb.resize(rows * ROWS_W)
	assert(err == OK)
	var hb: PackedByteArray = PackedByteArray()
	err = hb.resize(rows * ROWS_W * 2)
	assert(err == OK)
	for i: int in n:
		hb.encode_half(i * 2, temps[i])
	var ti: Image = Image.create_from_data(ROWS_W, rows, false, Image.FORMAT_R8, tb)
	var hi: Image = Image.create_from_data(ROWS_W, rows, false, Image.FORMAT_RH, hb)
	return [ImageTexture.create_from_image(ti), ImageTexture.create_from_image(hi)]

func _rods(floor_px: float) -> MultiMeshInstance3D:
	# Three rods 1 m long along x, at z = -1, 0, 1: radius 0.01 m (a 20 mm stick), 0.05 m, 0.1 m; 50 segments each.
	# The 0.05 m rod has segments 20-29 at thickness 0 (burnt through), and every rod a temperature ramp.
	var cyl: CylinderMesh = CylinderMesh.new()
	cyl.top_radius = 1.0
	cyl.bottom_radius = 1.0
	cyl.height = 1.0
	cyl.radial_segments = 12
	cyl.rings = 50
	var mm: MultiMesh = MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	mm.mesh = cyl
	mm.instance_count = 3
	var radii: Array[float] = [0.01, 0.05, 0.1]
	var thick: PackedByteArray = PackedByteArray()
	var temps: PackedFloat32Array = PackedFloat32Array()
	var e1: int = thick.resize(150)
	var e2: int = temps.resize(150)
	assert(e1 == OK and e2 == OK)
	for k: int in 3:
		var r: float = radii[k]
		# Local y (the cylinder's axis) onto world x; scale radius r on the other axes.
		var basis: Basis = Basis(Vector3(0, -1, 0) * r, Vector3(1, 0, 0), Vector3(0, 0, 1) * r)
		mm.set_instance_transform(k, Transform3D(basis, Vector3(0.0, 0.3, float(k - 1))))
		mm.set_instance_custom_data(k, Color(float(k * 50), 50.0, 0.0, 0.0))
		for s: int in 50:
			thick[k * 50 + s] = 0 if (k == 1 and s >= 20 and s < 30) else 255
			temps[k * 50 + s] = 20.0 * s
	var tex: Array[ImageTexture] = _seg_textures(thick, temps)
	var mat: ShaderMaterial = ShaderMaterial.new()
	mat.shader = load("res://probe_fuel_objects_rod.gdshader")
	mat.set_shader_parameter("thickness_tex", tex[0])
	mat.set_shader_parameter("temp_tex", tex[1])
	mat.set_shader_parameter("floor_radius_m", floor_px * 0.5 * SIZE_M / H)
	var mmi: MultiMeshInstance3D = MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.material_override = mat
	return mmi

func _lin3d() -> MeshInstance3D:
	var hb: PackedByteArray = PackedByteArray()
	var err: int = hb.resize(4)
	assert(err == OK)
	hb.encode_half(0, 0.0)
	hb.encode_half(2, 1000.0)
	var img: Image = Image.create_from_data(2, 1, false, Image.FORMAT_RH, hb)
	var t3: ImageTexture3D = ImageTexture3D.new()
	err = t3.create(Image.FORMAT_RH, 2, 1, 1, false, [img])
	assert(err == OK)
	var q: QuadMesh = QuadMesh.new()
	q.size = Vector2(1, 1)
	var mat: ShaderMaterial = ShaderMaterial.new()
	mat.shader = load("res://probe_fuel_objects_rh3d.gdshader")
	mat.set_shader_parameter("t3d", t3)
	var mi: MeshInstance3D = MeshInstance3D.new()
	mi.mesh = q
	mi.material_override = mat
	mi.transform = Transform3D(Basis.looking_at(-cam_dir, Vector3.UP), Vector3(-3.0, 0.5, 3.0))
	return mi

func _frame() -> Image:
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	return vp.get_texture().get_image()

func _project(p: Vector3) -> Vector2:
	return vp.get_camera_3d().unproject_position(p)

func _measure_rod(img: Image, k: int, label: String) -> void:
	# Along the rod's projected axis, at each pixel step, count lit pixels across it within 6 px.
	var a: Vector2 = _project(Vector3(-0.5, 0.3, float(k - 1)))
	var b: Vector2 = _project(Vector3(0.5, 0.3, float(k - 1)))
	var steps: int = int(a.distance_to(b))
	var normal: Vector2 = (b - a).normalized().orthogonal()
	var widths: Array[int] = []
	var covs: Array[float] = []
	var zero: int = 0
	for i: int in range(2, steps - 2):
		var c: Vector2 = a.lerp(b, float(i) / steps)
		var lit: int = 0
		var cov: float = 0.0
		for j: int in range(-8, 9):
			cov += img.get_pixelv(Vector2i((c + normal * j).round())).g / 0.2
			var p: Vector2i = Vector2i((c + normal * j).round())
			if img.get_pixelv(p).r > 0.02 or img.get_pixelv(p).g > 0.05:
				lit += 1
		widths.append(lit)
		covs.append(cov)
		if lit == 0:
			zero += 1
	var mn: int = 99
	var mx: int = 0
	var sum: int = 0
	for w: int in widths:
		mn = mini(mn, w)
		mx = maxi(mx, w)
		sum += w
	var cm: float = 0.0
	for v: float in covs: cm += v
	cm /= covs.size()
	var cv: float = 0.0
	for v: float in covs: cv += (v - cm) * (v - cm)
	cv = sqrt(cv / covs.size()) / maxf(cm, 1e-6)
	print("PROBE rod %s k=%d coverage mean=%.2f cv=%.3f" % [label, k, cm, cv])
	print("PROBE rod %s k=%d steps=%d width min=%d max=%d mean=%.2f empty_steps=%d" % [label, k, widths.size(), mn, mx, float(sum) / widths.size(), zero])

func _time_buffers() -> void:
	for n: int in [2000, 20000]:
		var best: int = 1 << 30
		var mm: MultiMesh = MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.instance_count = n
		for rep: int in 50:
			var t0: int = Time.get_ticks_usec()
			var buf: PackedFloat32Array = PackedFloat32Array()
			var err: int = buf.resize(n * 16)
			assert(err == OK)
			for i: int in n:
				var o: int = i * 16
				buf[o] = 0.01; buf[o + 3] = float(i) * 0.01
				buf[o + 5] = 1.0; buf[o + 7] = 0.3
				buf[o + 10] = 0.01; buf[o + 11] = 1.0
				buf[o + 12] = float(i * 50); buf[o + 13] = 50.0
			mm.buffer = buf
			best = mini(best, Time.get_ticks_usec() - t0)
		print("PROBE instances n=%d build+assign min_us=%d" % [n, best])
	# Per-frame segment state upload: 2e4 rows of f16 and three u8 columns, no GDScript loop (bytes as from the wire).
	var rows: int = 20000
	var h: int = ceili(float(rows) / ROWS_W)
	var hb: PackedByteArray = PackedByteArray()
	var err2: int = hb.resize(h * ROWS_W * 2)
	assert(err2 == OK)
	var ub: PackedByteArray = PackedByteArray()
	err2 = ub.resize(h * ROWS_W * 4)
	assert(err2 == OK)
	var th: ImageTexture = ImageTexture.create_from_image(Image.create_from_data(ROWS_W, h, false, Image.FORMAT_RH, hb))
	var tu: ImageTexture = ImageTexture.create_from_image(Image.create_from_data(ROWS_W, h, false, Image.FORMAT_RGBA8, ub))
	var best2: int = 1 << 30
	for rep: int in 50:
		var t0: int = Time.get_ticks_usec()
		var wire_h: PackedByteArray = hb.slice(0, rows * 2)
		var wire_u: PackedByteArray = ub.slice(0, rows * 4)
		var e3: int = wire_h.resize(h * ROWS_W * 2)
		var e4: int = wire_u.resize(h * ROWS_W * 4)
		assert(e3 == OK and e4 == OK)
		th.update(Image.create_from_data(ROWS_W, h, false, Image.FORMAT_RH, wire_h))
		tu.update(Image.create_from_data(ROWS_W, h, false, Image.FORMAT_RGBA8, wire_u))
		best2 = mini(best2, Time.get_ticks_usec() - t0)
	print("PROBE segment upload rows=%d min_us=%d" % [rows, best2])

func _run() -> void:
	print("PROBE renderer=%s video=%s" % [RenderingServer.get_current_rendering_method(), RenderingServer.get_video_adapter_name()])
	var rods: MultiMeshInstance3D = _rods(0.0)
	vp.add_child(rods)
	vp.add_child(_lin3d())
	var img: Image = await _frame()
	var e: int = img.save_png(out_dir + "rods_nofloor.png")
	assert(e == OK)
	for k: int in 3:
		_measure_rod(img, k, "nofloor")
	var c: Vector2 = _project(Vector3(-3.0, 0.5, 3.0))
	print("PROBE lin3d RH midpoint value=%.4f (expect 0.5; nearest would give 0 or 1)" % img.get_pixelv(Vector2i(c.round())).r)
	# Segment colour: the 0.1 m rod's temperature ramp, red channel at its 10th and 40th segment.
	for s: int in [10, 40]:
		var p: Vector2 = _project(Vector3(-0.5 + (s + 0.5) / 50.0, 0.3, 1.0))
		print("PROBE seg colour s=%d red=%.3f expect=%.3f" % [s, img.get_pixelv(Vector2i(p.round())).r, 20.0 * s / 1000.0])
	rods.queue_free()
	var rods2: MultiMeshInstance3D = _rods(2.0)
	vp.add_child(rods2)
	img = await _frame()
	e = img.save_png(out_dir + "rods_floor2px.png")
	assert(e == OK)
	for k: int in 3:
		_measure_rod(img, k, "floor2px")
	rods2.queue_free()
	vp.msaa_3d = Viewport.MSAA_4X
	var rods3: MultiMeshInstance3D = _rods(0.0)
	vp.add_child(rods3)
	img = await _frame()
	for k: int in 3:
		_measure_rod(img, k, "msaa4")
	rods3.queue_free()
	var rods4: MultiMeshInstance3D = _rods(2.0)
	vp.add_child(rods4)
	img = await _frame()
	for k: int in 3:
		_measure_rod(img, k, "msaa4+floor2px")
	_time_buffers()
	print("PROBE done")
	quit(0)
