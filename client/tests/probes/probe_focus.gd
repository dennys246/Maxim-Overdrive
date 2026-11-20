extends SceneTree
## §9 probe: is a held key released when the window loses focus? Presses W through Input.parse_input_event, brings
## the window to the front, and prints the key state every 30 frames and at each focus notification. Something else
## must take focus while it runs; on macOS (osascript from a shell that may send Apple Events):
## (perl -e 'select(undef, undef, undef, 2)'; osascript -e 'tell application "Finder" to activate') &
## godot --rendering-driver opengl3 --path client -s res://tests/probes/probe_focus.gd

const LAST_FRAME: int = 300
const EVERY: int = 30

var _frames: int = 0


func _initialize() -> void:
	DisplayServer.window_move_to_foreground()
	var press: InputEventKey = InputEventKey.new()
	press.keycode = KEY_W
	press.physical_keycode = KEY_W
	press.pressed = true
	Input.parse_input_event(press)


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT or what == NOTIFICATION_APPLICATION_FOCUS_IN:
		var event: String = "FOCUS_OUT" if what == NOTIFICATION_APPLICATION_FOCUS_OUT else "FOCUS_IN"
		print("probe focus: frame %d %s, W pressed=%s" % [_frames, event, Input.is_physical_key_pressed(KEY_W)])


func _process(_delta: float) -> bool:
	_frames += 1
	if _frames % EVERY == 0:
		print("probe focus: frame %d focused=%s W pressed=%s" % [
			_frames, DisplayServer.window_is_focused(), Input.is_physical_key_pressed(KEY_W)])
	return _frames >= LAST_FRAME
