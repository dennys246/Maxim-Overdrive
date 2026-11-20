extends SceneTree
## §9 probe: does WebSocketPeer send an Origin header when handshake_headers is never set? A listener records the
## handshake. Headless: godot --headless --path client -s res://tests/probes/probe_ws_origin.gd -- <port>

const FRAMES: int = 120

var _ws: WebSocketPeer = WebSocketPeer.new()
var _frames: int = 0


func _initialize() -> void:
	var port: int = int(OS.get_cmdline_user_args()[0])
	print("probe ws: inbound_buffer_size=%d max_queued_packets=%d" % [_ws.inbound_buffer_size, _ws.max_queued_packets])
	var err: Error = _ws.connect_to_url("ws://127.0.0.1:%d" % port)
	print("probe ws: connect_to_url -> %s" % error_string(err))


func _process(_delta: float) -> bool:
	_ws.poll()
	_frames += 1
	return _frames >= FRAMES
