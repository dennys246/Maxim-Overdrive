extends Node3D
## The slice's client: draws what the server sends, sends what the player asks for, computes nothing that feeds
## back into the world. Server states arrive at 10 Hz; the body is drawn one tick behind, interpolated between the
## last two states, so it moves smoothly at the screen's frame rate (the usual "interpolation delay").
##
## Controls: WASD move (relative to the camera), Shift Overdrive, F kindle, Q/E orbit the camera, H heat view.
## Optional user arguments after "--": --demo walks east and kindles the crate; --capture=<png> --frames=<n> saves
## the frame n frames after the first state and quits (a visual check, not a golden).

const TICK_S: float = 0.1
const CAMERA_DISTANCE_M: float = 5.5
const CAMERA_PITCH_DEG: float = 35.0
const ORBIT_DEG_S: float = 90.0
const RESEND_S: float = 0.25

var _net: SliceNet = SliceNet.new()
var _voxels: SliceVoxels = SliceVoxels.new()
var _body: MeshInstance3D = MeshInstance3D.new()
var _camera: Camera3D = Camera3D.new()
var _hud: Label = Label.new()
var _flames: Dictionary = {}  # region name -> CPUParticles3D
var _prev_pos: Vector3 = Vector3.ZERO
var _pos: Vector3 = Vector3.ZERO
var _since_state: float = 0.0
var _have_state: bool = false
var _orbit_deg: float = -90.0  # looking east, down the alley
var _heat_view: bool = false
var _last_move: Dictionary = {}
var _since_move: float = 0.0
var _keys_down: Dictionary = {}  # Key -> bool, for edge detection
var _status: String = "connecting"
var _state_kb: float = 0.0
var _work_j: float = 0.0
var _vitals: Label = Label.new()  # core temperature, coolant, Overdrive: words and bars, never colour alone
var _fire_lines: PackedStringArray = PackedStringArray()
var _puddle: MeshInstance3D = null
var _vendor: MeshInstance3D = MeshInstance3D.new()
var _vendor_label: Label3D = Label3D.new()  # a billboard label: always faces the camera, drawn in the 3-D scene
var _vendor_state: String = ""
var _line_left_s: float = 0.0
var _say_box: LineEdit = LineEdit.new()
var _typing: bool = false
var _speed: float = 0.0
var _events: PackedStringArray = PackedStringArray()
var _args: Dictionary = {}
var _frames_since_state: int = 0
var _server_tick: int = 0
var _demo_start_tick: int = -1
var _demo_kindled: bool = false


func _ready() -> void:
	_args = _user_args()
	_build_scene()
	var run_file: String = ProjectSettings.globalize_path("res://").path_join("../run/session.json")
	var text: String = FileAccess.get_file_as_string(run_file)
	var parsed: Variant = JSON.parse_string(text)
	if not parsed is Dictionary:
		_status = "no server: start it first (cd spikes/slice && ../../.venv/bin/python -m slice_server serve)"
		return
	var run: Dictionary = parsed
	var token: String = run["token"]
	var err: Error = _net.open(SliceNet.num_int(run["port"]), token)
	if err != OK:
		_status = "connect failed: %s" % error_string(err)


func _user_args() -> Dictionary:
	var out: Dictionary = {}
	for arg: String in OS.get_cmdline_user_args():
		var parts: PackedStringArray = arg.trim_prefix("--").split("=", true, 1)
		out[parts[0]] = parts[1] if parts.size() > 1 else "true"
	return out


func _build_scene() -> void:
	# Black background: Compatibility maps a non-black clear colour differently with glow on, off and at render
	# scale 0.5 (measured on phase1/client-shader), and glow is on here for the emissive cells.
	var env: Environment = Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color.BLACK
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.55, 0.6, 0.7)
	env.ambient_light_energy = 0.6
	env.glow_enabled = true
	var world_env: WorldEnvironment = WorldEnvironment.new()
	world_env.environment = env
	add_child(world_env)
	var sun: DirectionalLight3D = DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-55.0, 30.0, 0.0)
	sun.light_energy = 0.8
	add_child(sun)
	add_child(_voxels)
	var capsule: CapsuleMesh = CapsuleMesh.new()
	capsule.radius = 0.3
	capsule.height = 1.8
	var skin: StandardMaterial3D = StandardMaterial3D.new()
	skin.albedo_color = Color(0.2, 0.75, 0.9)
	capsule.material = skin
	_body.mesh = capsule
	add_child(_body)
	var apron: CapsuleMesh = CapsuleMesh.new()
	apron.radius = 0.3
	apron.height = 1.8
	var cloth: StandardMaterial3D = StandardMaterial3D.new()
	cloth.albedo_color = Color(0.95, 0.6, 0.2)
	apron.material = cloth
	_vendor.mesh = apron
	_vendor_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_vendor_label.position = Vector3(0.0, 1.35, 0.0)
	_vendor_label.pixel_size = 0.004
	_vendor_label.font_size = 40
	_vendor_label.outline_size = 10
	_vendor_label.width = 600.0
	_vendor_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_vendor.add_child(_vendor_label)
	add_child(_vendor)
	_camera.fov = 60.0
	add_child(_camera)
	_hud.position = Vector2(12, 8)
	_hud.add_theme_font_size_override("font_size", 15)
	var layer: CanvasLayer = CanvasLayer.new()
	layer.add_child(_hud)
	_vitals.position = Vector2(12, 560)
	_vitals.add_theme_font_size_override("font_size", 20)
	layer.add_child(_vitals)
	_say_box.position = Vector2(12, 520)
	_say_box.size = Vector2(520, 32)
	_say_box.placeholder_text = "say something to the vendor, Enter to send"
	_say_box.visible = false
	var _connected: int = _say_box.text_submitted.connect(_on_say)
	layer.add_child(_say_box)
	add_child(layer)


func _process(delta: float) -> void:
	for message: Dictionary in _net.poll():
		_on_message(message)
	_since_state += delta
	if _have_state:
		_body.position = _prev_pos.lerp(_pos, clampf(_since_state / TICK_S, 0.0, 1.0)) + Vector3(0.0, 0.9, 0.0)
	_read_input(delta)
	_place_camera()
	_hud.text = _hud_text()
	_maybe_capture()


func _on_message(message: Dictionary) -> void:
	var kind: String = message.get("type", "")
	match kind:
		"welcome":
			_on_welcome(message)
		"state":
			_on_state(message)
		"npc_line":
			var text: String = message["text"]
			var source: String = message["source"]
			_vendor_label.text = text
			_line_left_s = 6.0
			var _logged: bool = _events.append("vendor (%s): %s" % [source, text])
			if _events.size() > 4:
				_events.remove_at(0)
		"event", "error":
			var _added: bool = _events.append(JSON.stringify(message))
			if _events.size() > 4:
				_events.remove_at(0)


func _on_welcome(message: Dictionary) -> void:
	var shape: Array = message["shape"]
	var raw_palette: Dictionary = message["palette"]
	var palette: Dictionary = {}
	for key: String in raw_palette:
		var rgb: Array = raw_palette[key]
		palette[key.to_int()] = Color8(SliceNet.num_int(rgb[0]), SliceNet.num_int(rgb[1]), SliceNet.num_int(rgb[2]))
	var size: Vector3i = Vector3i(SliceNet.num_int(shape[0]), SliceNet.num_int(shape[1]), SliceNet.num_int(shape[2]))
	_voxels.configure(size, SliceNet.num(message["dx_m"]), palette)
	_status = "connected"


func _on_state(message: Dictionary) -> void:
	var cells: Dictionary = message["cells"]
	var channels: Array[PackedByteArray] = []
	for channel: String in ["material", "crack", "glow", "heat"]:
		var packed: Dictionary = cells[channel]
		channels.append(SliceNet.unpack_cells(packed))
	_voxels.show_cells(channels[0], channels[1], channels[2], channels[3])
	_server_tick = SliceNet.num_int(message["tick"])
	var body: Dictionary = message["body"]
	var v: Array = body["vel"]
	var now: Vector3 = SliceNet.vec3(body["pos"])
	_prev_pos = _pos if _have_state else now
	_pos = now
	_speed = Vector2(SliceNet.num(v[0]), SliceNet.num(v[1])).length()
	_work_j = SliceNet.num(body["work_j"])
	_since_state = 0.0
	_have_state = true
	var burning: Array = message["burning"]
	_show_flames(burning)
	var heat: Dictionary = message["heat"]
	_show_vitals(heat)
	var fires: Array = message["fires"]
	_show_fires(fires)
	var vendor: Dictionary = message["vendor"]
	_vendor.position = SliceNet.vec3(vendor["pos"]) + Vector3(0.0, 0.9, 0.0)
	_vendor.rotation.y = SliceNet.num(vendor["yaw"]) - PI / 2.0  # server yaw is from +x; Godot's from -z
	_vendor_state = vendor["state"]
	if _puddle == null:
		_puddle = _make_puddle(message["puddle"], now.y)
	_state_kb = JSON.stringify(message).length() / 1024.0


## A text bar: grey-box and readable without colour.
static func _bar(fraction: float, width: int) -> String:
	var filled: int = clampi(roundi(fraction * width), 0, width)
	return "#".repeat(filled) + "-".repeat(width - filled)


func _show_vitals(heat: Dictionary) -> void:
	var core: float = SliceNet.num(heat["core_c"])
	var warn: float = SliceNet.num(heat["warn_c"])
	var trip: float = SliceNet.num(heat["trip_c"])
	var coolant: float = SliceNet.num(heat["coolant"])
	var tripped: bool = heat["tripped"]
	var overdrive: bool = heat["overdrive"]
	var in_puddle: bool = heat["in_puddle"]
	var state: String = "TRIPPED: cooling down" if tripped else ("WARN: overheating" if core >= warn else "ok")
	_vitals.text = "core  %5.1f C  [%s]  %s\ncoolant      [%s] %3.0f%%%s\nOverdrive %s   radiant %.1f kW/m2" % [
		core, _bar((core - 37.0) / (trip - 37.0), 24), state,
		_bar(coolant, 24), coolant * 100.0, "   (in the puddle: refilling)" if in_puddle else "",
		"ON" if overdrive else "off", SliceNet.num(heat["flux_w_m2"]) / 1000.0,
	]
	# Colour adds to the words, never replaces them.
	_vitals.modulate = Color(1.0, 0.45, 0.35) if tripped or core >= warn else Color.WHITE


func _show_fires(fires: Array) -> void:
	_fire_lines.clear()
	for entry: Dictionary in fires:
		var name_: String = entry["region"]
		var burning: bool = entry["burning"]
		var burnt_out: bool = entry["burnt_out"]
		var what: String = "burnt out" if burnt_out else ("BURNING" if burning else "skin %.0f C" % SliceNet.num(entry["skin_c"]))
		var _added: bool = _fire_lines.append("%-9s fuel [%s] %s" % [name_, _bar(SliceNet.num(entry["fuel"]), 12), what])


## The puddle: a flat, glossy patch on the floor. Visual only; the server decides who stands in it.
func _make_puddle(xy: Variant, floor_y: float) -> MeshInstance3D:
	var r: Array = xy
	var x0: float = SliceNet.num(r[0])
	var y0: float = SliceNet.num(r[1])
	var x1: float = SliceNet.num(r[2])
	var y1: float = SliceNet.num(r[3])
	var plane: PlaneMesh = PlaneMesh.new()
	plane.size = Vector2(x1 - x0, y1 - y0)
	var water: StandardMaterial3D = StandardMaterial3D.new()
	water.albedo_color = Color(0.12, 0.22, 0.4)
	water.roughness = 0.05
	water.metallic = 0.4
	plane.material = water
	var puddle: MeshInstance3D = MeshInstance3D.new()
	puddle.mesh = plane
	puddle.position = SliceVoxels.to_godot((x0 + x1) / 2.0, (y0 + y1) / 2.0, 0.0) + Vector3(0.0, floor_y + 0.01, 0.0)
	add_child(puddle)
	return puddle


func _show_flames(burning: Array) -> void:
	var lit: Dictionary = {}
	for entry: Dictionary in burning:
		var region: String = entry["region"]
		lit[region] = true
		if not _flames.has(region):
			_flames[region] = _make_flame(SliceNet.vec3(entry["at"]))
	for region: String in _flames.keys():
		if not lit.has(region):
			var flame: CPUParticles3D = _flames[region]
			flame.queue_free()
			var _gone: bool = _flames.erase(region)


## Purely visual flames. CPUParticles3D, not GPUParticles3D: a handful of emitters costs nothing on the CPU, and it
## behaves the same on every Compatibility driver.
func _make_flame(at: Vector3) -> CPUParticles3D:
	var flame: CPUParticles3D = CPUParticles3D.new()
	var quad: QuadMesh = QuadMesh.new()
	quad.size = Vector2(0.18, 0.18)
	var look: StandardMaterial3D = StandardMaterial3D.new()
	look.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	look.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	look.albedo_color = Color(1.0, 0.55, 0.15)
	look.emission_enabled = true
	look.emission = Color(1.0, 0.45, 0.1)
	look.emission_energy_multiplier = 3.0
	quad.material = look
	flame.mesh = quad
	flame.amount = 60
	flame.lifetime = 0.8
	flame.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	flame.emission_box_extents = Vector3(0.25, 0.05, 0.25)
	flame.direction = Vector3.UP
	flame.spread = 15.0
	flame.gravity = Vector3(0.0, 1.5, 0.0)
	flame.initial_velocity_min = 0.4
	flame.initial_velocity_max = 0.9
	flame.scale_amount_min = 0.6
	flame.scale_amount_max = 1.4
	flame.position = at + Vector3(0.0, 0.3, 0.0)
	add_child(flame)
	return flame


func _pressed_once(key: Key) -> bool:
	var down: bool = Input.is_physical_key_pressed(key)
	var was: bool = _keys_down.get(key, false)
	_keys_down[key] = down
	return down and not was


func _on_say(text: String) -> void:
	if not text.strip_edges().is_empty() and _net.is_connected_to_server():
		_net.send({"type": "say", "text": text.strip_edges().left(200)})
	_say_box.clear()
	_say_box.visible = false
	_say_box.release_focus()
	_typing = false


func _read_input(delta: float) -> void:
	_line_left_s = maxf(0.0, _line_left_s - delta)
	_vendor_label.visible = _line_left_s > 0.0
	if _typing:
		_send_move(Vector2.ZERO, false, delta)  # stand still while typing: the keys are words now
		return
	if _pressed_once(KEY_ENTER):
		_typing = true
		_say_box.visible = true
		_say_box.grab_focus()
		return
	if _pressed_once(KEY_SPACE) and _net.is_connected_to_server():
		_net.send({"type": "strike"})
	if Input.is_physical_key_pressed(KEY_Q):
		_orbit_deg += ORBIT_DEG_S * delta
	if Input.is_physical_key_pressed(KEY_E):
		_orbit_deg -= ORBIT_DEG_S * delta
	if _pressed_once(KEY_H):
		_heat_view = not _heat_view
		_voxels.set_show_heat(_heat_view)
	var wish: Vector2 = Vector2(_axis(KEY_D, KEY_A), _axis(KEY_W, KEY_S))
	var kindle: bool = _pressed_once(KEY_F)
	if _args.has("demo"):
		var demo: Array = _demo_input(delta)
		wish = demo[0]
		kindle = demo[1]
	_send_move(wish, Input.is_physical_key_pressed(KEY_SHIFT), delta)
	if kindle and _net.is_connected_to_server():
		_net.send({"type": "kindle"})



func _axis(positive: Key, negative: Key) -> float:
	return float(Input.is_physical_key_pressed(positive)) - float(Input.is_physical_key_pressed(negative))


## --demo: walk forward (east, toward the crate) for 38 server ticks, kindling it at tick 34 on the way. Counted in
## the server's ticks, not the client's seconds: under load the server dilates time, and a wall-clock script once
## kindled after 22 ticks of walking instead of 34, 2 m short of the crate (found by replaying the session log).
func _demo_input(_delta: float) -> Array:
	if not _have_state:
		return [Vector2.ZERO, false]
	if _demo_start_tick < 0:
		_demo_start_tick = _server_tick
	var walked: int = _server_tick - _demo_start_tick
	var kindle_now: bool = walked >= 34 and not _demo_kindled
	if kindle_now:
		_demo_kindled = true
	return [Vector2(0.0, 1.0) if walked < 38 else Vector2.ZERO, kindle_now]  # forward: east at the starting orbit


## WASD is relative to the camera: forward is where the camera looks, flattened onto the ground.
func _send_move(wish: Vector2, overdrive: bool, delta: float) -> void:
	if not _net.is_connected_to_server():
		return
	var yaw: float = deg_to_rad(_orbit_deg)
	var forward: Vector2 = Vector2(-sin(yaw), cos(yaw))  # server x, y: orbit 0 faces north (+y)
	var right: Vector2 = Vector2(cos(yaw), sin(yaw))
	var direction: Vector2 = forward * wish.y + right * wish.x
	var message: Dictionary = {
		"type": "move", "dir": [direction.x, direction.y], "effort": 1.0 if direction.length() > 0.0 else 0.0,
		"overdrive": overdrive,
	}
	_since_move += delta
	if message != _last_move or _since_move >= RESEND_S:
		_net.send(message)
		_last_move = message
		_since_move = 0.0


func _place_camera() -> void:
	var target: Vector3 = _body.position + Vector3(0.0, 0.6, 0.0)
	var yaw: float = deg_to_rad(_orbit_deg)
	var pitch: float = deg_to_rad(CAMERA_PITCH_DEG)
	# Behind the body: server -forward is (sin, -cos) in x, y, which is Godot (sin, _, cos).
	var back: Vector3 = Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch))
	_camera.position = target + back * CAMERA_DISTANCE_M
	_camera.look_at(target)


func _hud_text() -> String:
	var lines: PackedStringArray = PackedStringArray([
		"slice-0  %s  %d fps" % [_status, Engine.get_frames_per_second()],
		"state %.1f KB/tick   speed %.2f m/s   drive work %.0f J" % [_state_kb, _speed, _work_j],
		"burning: %s   heat view (H): %s" % [", ".join(PackedStringArray(_flames.keys())), "on" if _heat_view else "off"],
		"WASD move   Shift Overdrive   F kindle   Space strike   Enter talk   Q/E orbit   vendor: %s" % _vendor_state,
	])
	lines.append_array(_fire_lines)
	lines.append_array(_events)
	return "\n".join(lines)


func _maybe_capture() -> void:
	if not _args.has("capture") or not _have_state:
		return
	_frames_since_state += 1
	var frames: String = _args.get("frames", "60")
	var wanted: int = frames.to_int()
	if _frames_since_state < wanted:
		return
	var path: String = _args["capture"]
	var err: Error = get_viewport().get_texture().get_image().save_png(path)
	print("slice: captured %s (%s)" % [path, error_string(err)])
	get_tree().quit()
