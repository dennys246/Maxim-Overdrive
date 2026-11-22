class_name NetClient
extends RefCounted
## The client's one connection to the host (client_rendering.md §4.3, §7.5; boundaries §5.3). RefCounted, not Node:
## whoever owns it calls poll() once per _process, so it runs in tests without a scene tree.
##
## WebSocketPeer is Godot's own WebSocket client (the transport decision: docs/architecture.md, "Transport"). Its
## buffers are set before connecting, since the defaults are too small for a cell frame (inbound 65,535 bytes) and
## too deep for a client that must notice it is falling behind (4,096 queued packets). handshake_headers is never set,
## so the upgrade carries no Origin header, which the host refuses (a Python listener test captures the request).
## The order is the handshake, hello with the per-launch token, then welcome; text messages are JSON, binary ones cell
## frames, told apart by was_string_packet(). Anything refused is recorded with its code, never drawn.

const INBOUND_BUFFER_BYTES: int = 4 * 1024 * 1024
const MAX_QUEUED_PACKETS: int = 64
const PROTOCOL: int = 0
## The token arrives by environment variable or a 0600 file the host wrote, never argv (boundaries §5.3).
const TOKEN_ENV: String = "MAXIM_OVERDRIVE_TOKEN"
const TOKEN_FILE_ENV: String = "MAXIM_OVERDRIVE_TOKEN_FILE"

var peer: WebSocketPeer = WebSocketPeer.new()
## welcome as received, once it is; empty before.
var welcome: Dictionary = {}
## The last refusal: an error the server sent, what this client refused, or "closed <code>" when the connection ended
## with no reason; empty while all is well.
var refusal: String = ""
var last_frame: WireFrame = null
var _token: String = ""
var _hello_sent: bool = false


## The token from the environment: the variable, or the file it names.
static func token_from_environment() -> String:
	var token: String = OS.get_environment(TOKEN_ENV)
	var path: String = OS.get_environment(TOKEN_FILE_ENV)
	if token.is_empty() and not path.is_empty():
		token = FileAccess.get_file_as_string(path).strip_edges()
	return token


func open(port: int, token: String) -> Error:
	peer.inbound_buffer_size = INBOUND_BUFFER_BYTES
	peer.max_queued_packets = MAX_QUEUED_PACKETS
	_token = token
	return peer.connect_to_url("ws://127.0.0.1:%d" % port)


func poll() -> void:
	peer.poll()
	if peer.get_ready_state() == WebSocketPeer.STATE_CLOSED:
		_on_closed()
		return
	if peer.get_ready_state() == WebSocketPeer.STATE_OPEN and not _hello_sent:
		var sent: Error = peer.send_text(JSON.stringify({"type": "hello", "protocol": PROTOCOL, "token": _token}))
		_hello_sent = sent == OK  # on a failed send, the next poll tries again; the host's deadline bounds it
		if not _hello_sent:
			push_error("NetClient: hello was not sent (%s)" % error_string(sent))
	while peer.get_available_packet_count() > 0:
		var packet: PackedByteArray = peer.get_packet()
		if peer.was_string_packet():
			_on_text(packet.get_string_from_utf8())
		else:
			_on_frame(packet)


## The host refuses a handshake with an error and then a close whose reason is the same code (1008 "bad_token").
## Godot 4.7.2 drops a text packet that arrives in the same poll as the close (measured: tests/test_godot_net.py), so
## the close reason is what this client reads, when nothing before it said why.
func _on_closed() -> void:
	if refusal.is_empty():
		var reason: String = peer.get_close_reason()
		refusal = reason if not reason.is_empty() else "closed %d" % peer.get_close_code()


func _on_text(text: String) -> void:
	var read: WireRead = WireJson.parse(text, INBOUND_BUFFER_BYTES)
	if read.ok and not read.non_integer_keys.is_empty():
		read.refuse("not_int", "the server writes integers only")
	if not read.ok or not read.value is Dictionary:
		refusal = read.code if not read.ok else "bad_shape"
		return
	var message: Dictionary = read.value
	match message.get("type"):
		"welcome":
			if message.get("protocol") != float(PROTOCOL):
				refusal = "bad_version"
				return
			welcome = message
		"error":
			refusal = str(message.get("code"))
		_:
			refusal = "unknown_kind"


func _on_frame(packet: PackedByteArray) -> void:
	if welcome.is_empty():
		refusal = "bad_shape"  # a frame before welcome has no catalogue to be read by
		return
	var read: WireRead = FrameDecoder.decode(
		packet, WireCatalogue.v0(), str(welcome.get("catalogue_hash")), INBOUND_BUFFER_BYTES
	)
	if read.ok:
		last_frame = read.value
	else:
		refusal = read.code
