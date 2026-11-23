class_name NetSession
extends RefCounted
## What the client knows of its session, from the messages it reads (client_rendering.md §4.1, §4.3): pure logic, no
## socket, so every branch runs in a unit test (tests/unit/net/test_net_session.gd); NetClient feeds it packets.
##
## The first refusal wins and ends the session: a later message can't overwrite why it ended, and the owner closes
## the connection on it (``ended``). Text is the server's JSON (WireJson.parse_server: integers only, O62); binary is
## a cell frame, read by this build's catalogue only after a welcome whose catalogue hash is this build's (O64).

const PROTOCOL: int = 0
## The server's text messages (welcome, error) are small; a cell frame is binary and has its own cap.
const MAX_TEXT_BYTES: int = 256 * 1024
const MAX_FRAME_BYTES: int = 4 * 1024 * 1024
const ROLES: Array[String] = ["host", "guest"]

## welcome as read, once it is; empty before.
var welcome: Dictionary = {}
## The refusal that ended the session: an error the server sent, what this client refused, or the close's reason;
## empty while all is well.
var refusal: String = ""
var last_frame: WireFrame = null
var _catalogue: Array[Dictionary] = WireCatalogue.v0()
var _catalogue_hash: String = WireCatalogue.catalogue_hash(WireCatalogue.v0())


func ended() -> bool:
	return not refusal.is_empty()


func end(code: String) -> void:
	if refusal.is_empty():
		refusal = code


func on_text(bytes: PackedByteArray) -> void:
	if ended():
		return
	var read: WireRead = WireJson.parse_server(bytes, MAX_TEXT_BYTES)
	if read.ok and not read.non_integer_keys.is_empty():
		read.refuse("not_int", "the server writes integers only")
	if read.ok and not read.value is Dictionary:
		read.refuse("bad_shape", "a server message is a JSON object")
	if not read.ok:
		end(read.code)
		return
	var message: Dictionary = read.value
	match message.get("type"):
		"welcome":
			_on_welcome(message)
		"error":
			var code: Variant = message.get("code")
			var text: String = code if code is String else ""
			end(text if not text.is_empty() else "bad_shape")
		_:
			end("unknown_kind")


func _on_welcome(message: Dictionary) -> void:
	if not welcome.is_empty():
		end("bad_shape")  # welcome comes once
		return
	var read: WireRead = WireRead.new()
	var version: int = WireFields.version(read, message.get("protocol"), false)
	if read.ok and version != PROTOCOL:
		read.refuse("bad_version", "welcome: protocol %d; this client speaks %d" % [version, PROTOCOL])
	if read.ok:  # each read refuses through ``read``; the values themselves are kept in ``welcome``
		var _session: int = WireFields.whole(read, message.get("session"), "session", 1, WireJson.INT_MAX)
		var _role: String = WireFields.choice(read, message.get("role"), "role", ROLES)
		var _hash: String = WireFields.digest(read, message.get("catalogue_hash"), "catalogue_hash")
	if read.ok and message.get("catalogue_hash") != _catalogue_hash:
		read.refuse("bad_version", "welcome: a catalogue other than this build's")
	if not read.ok:
		end(read.code)
		return
	welcome = message


func on_frame(bytes: PackedByteArray) -> void:
	if ended():
		return
	if welcome.is_empty():
		end("bad_shape")  # a frame before welcome has no catalogue to be read by
		return
	var read: WireRead = FrameDecoder.decode(bytes, _catalogue, _catalogue_hash, MAX_FRAME_BYTES)
	if read.ok:
		last_frame = read.value
	else:
		end(read.code)
