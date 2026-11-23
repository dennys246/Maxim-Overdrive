class_name NetClient
extends RefCounted
## The client's one connection to the host (client_rendering.md §4.3, §7.5; boundaries §5.3). RefCounted, not Node:
## whoever owns it calls poll() once per _process, so it runs in tests without a scene tree. What the messages mean is
## NetSession's; this holds the socket.
##
## WebSocketPeer is Godot's own WebSocket client (the transport decision: docs/architecture.md, "Transport"). Its
## buffers are set before connecting: the inbound one to a cell frame's cap, since the default (65,535 bytes) is
## smaller than a frame, and the queue to a bound, since a client that stops reading should hold a few packets, not
## Godot's default 4,096. handshake_headers is never set, so the upgrade carries no Origin header, which the host
## refuses (tests/test_godot_net.py captures the request). The order is the handshake, hello with the per-launch
## token, then welcome; text messages are JSON, binary ones cell frames, told apart by was_string_packet().
##
## The host ends a refused connection with an error and then a close whose reason is the same code. Godot 4.7.2 may
## drop a text packet that arrives in the same poll as the close (most runs; measured: tests/test_godot_net.py), so
## the close reason is read too, when nothing before it said why. Once the session has ended, the client closes and reads no
## more.

const INBOUND_BUFFER_BYTES: int = 4 * 1024 * 1024  # client_rendering §4.3; the server caps a frame at 3.5 MiB
const MAX_QUEUED_PACKETS: int = 64
## The token arrives by environment variable or a 0600 file the host wrote, never argv (boundaries §5.3).
const TOKEN_ENV: String = "MAXIM_OVERDRIVE_TOKEN"
const TOKEN_FILE_ENV: String = "MAXIM_OVERDRIVE_TOKEN_FILE"

var peer: WebSocketPeer = WebSocketPeer.new()
var session: NetSession = NetSession.new()
var _token: String = ""
var _hello_sent: bool = false


## The token from the environment: the variable, or the file it names.
static func token_from_environment() -> String:
	var token: String = OS.get_environment(TOKEN_ENV)
	var path: String = OS.get_environment(TOKEN_FILE_ENV)
	if token.is_empty() and not path.is_empty():
		token = FileAccess.get_file_as_string(path).strip_edges()
	return token


## A fresh connection: a new socket and a new session, so a reconnect says hello again.
func open(port: int, token: String) -> Error:
	peer = WebSocketPeer.new()
	session = NetSession.new()
	_hello_sent = false
	peer.inbound_buffer_size = INBOUND_BUFFER_BYTES
	peer.max_queued_packets = MAX_QUEUED_PACKETS
	_token = token
	return peer.connect_to_url("ws://127.0.0.1:%d" % port)


func poll() -> void:
	peer.poll()
	var state: WebSocketPeer.State = peer.get_ready_state()
	if state == WebSocketPeer.STATE_OPEN and not _hello_sent:
		var hello: Dictionary = {"type": "hello", "protocol": NetSession.PROTOCOL, "token": _token}
		var sent: Error = peer.send_text(JSON.stringify(hello))
		_hello_sent = sent == OK  # on a failed send, the next poll tries again; the host's deadline bounds it
		if not _hello_sent:
			push_error("NetClient: hello was not sent (%s)" % error_string(sent))
	while peer.get_available_packet_count() > 0 and not session.ended():
		var packet: PackedByteArray = peer.get_packet()
		if peer.was_string_packet():
			session.on_text(packet)
		else:
			session.on_frame(packet)
	if state == WebSocketPeer.STATE_CLOSED:
		# Only a code is taken from the peer: prose, or a reason past a close frame's 123 bytes, can't become ours
		var reason: String = peer.get_close_reason()
		var coded: bool = NetSession.CODE.search(reason) != null
		session.end(reason if coded else "closed")
	elif session.ended() and state == WebSocketPeer.STATE_OPEN:
		peer.close(1000, session.refusal)
