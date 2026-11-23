extends SceneTree
## The client's connection against a real listener (tests/test_godot_net.py runs it; boundaries §5.3):
## `godot --headless --path client -s res://tests/net_check.gd`, with the port in MAXIM_OVERDRIVE_NET_PORT and the
## token where NetClient reads it (MAXIM_OVERDRIVE_TOKEN or the file MAXIM_OVERDRIVE_TOKEN_FILE names).
## It polls NetClient once per frame, as the game's _process will, until the client holds a welcome or a refusal (a
## closed socket is one), then prints one line the test reads: Godot's exit status is never trusted (CR-B1).
## Engine why: a SceneTree script is its own main loop, so _process runs once per frame with no scene; the bound is
## the test's outer timeout, not a frame count, since a headless frame takes as long as the loop takes.

const PORT_ENV: String = "MAXIM_OVERDRIVE_NET_PORT"

## With this set, a bare WebSocketPeer instead: it sends hello and counts the packets it ever holds before the close,
## the engine fact NetClient's close-reason read rests on.
const RAW_ENV: String = "MAXIM_OVERDRIVE_NET_RAW"
## With this set, the check waits past welcome for a cell frame, and prints its shape.
const FRAME_ENV: String = "MAXIM_OVERDRIVE_NET_FRAME"

var _client: NetClient = NetClient.new()
var _raw: WebSocketPeer = null
var _raw_packets: int = 0
var _raw_hello: bool = false
var _done: bool = false


func _initialize() -> void:
	var port: int = OS.get_environment(PORT_ENV).to_int()
	if not OS.get_environment(RAW_ENV).is_empty():
		_raw = WebSocketPeer.new()
		var connected: Error = _raw.connect_to_url("ws://127.0.0.1:%d" % port)
		if connected != OK:
			_finish("net-check: open failed %s" % error_string(connected))
		return
	var opened: Error = _client.open(port, NetClient.token_from_environment())
	if opened != OK:
		_finish("net-check: open failed %s" % error_string(opened))


func _process(_delta: float) -> bool:
	if _done:
		return true
	if _raw != null:
		_poll_raw()
		return _done
	_client.poll()
	var session: NetSession = _client.session
	var want_frame: bool = not OS.get_environment(FRAME_ENV).is_empty()
	if want_frame and session.last_frame != null:
		var frame: WireFrame = session.last_frame
		_finish("net-check: frame %d %d %d" % [frame.nz, frame.ny, frame.nx])
	elif want_frame and not session.ended():
		return _done
	elif not session.welcome.is_empty():
		var hash_ok: bool = session.welcome.get("catalogue_hash") == WireCatalogue.catalogue_hash(WireCatalogue.v0())
		_finish("net-check: welcome %s catalogue %s" % [session.welcome.get("role"), "same" if hash_ok else "differs"])
	elif session.ended():
		_finish("net-check: refused %s" % session.refusal)
	return _done


func _poll_raw() -> void:
	_raw.poll()
	if _raw.get_ready_state() == WebSocketPeer.STATE_OPEN and not _raw_hello:
		var hello: Dictionary = {"type": "hello", "protocol": 0, "token": NetClient.token_from_environment()}
		_raw_hello = _raw.send_text(JSON.stringify(hello)) == OK
	while _raw.get_available_packet_count() > 0:
		var _packet: PackedByteArray = _raw.get_packet()
		_raw_packets += 1
	if _raw.get_ready_state() == WebSocketPeer.STATE_CLOSED:
		_done = true
		print("net-check: raw packets %d reason %s" % [_raw_packets, _raw.get_close_reason()])
		quit(0)


func _finish(line: String) -> void:
	print(line)
	_done = true
	_client.peer.close()
	quit(0)
