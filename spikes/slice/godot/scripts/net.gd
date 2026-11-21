class_name SliceNet
extends RefCounted
## The slice-0 wire, client side: length-prefixed JSON over TCP to 127.0.0.1 (spikes/slice/slice_server/wire.py).
## StreamPeerTCP, not WebSocketPeer: the slice's server is stdlib Python, which has no WebSocket server, and raw TCP
## with a length prefix is the simplest framing both ends can share. Step 7 designs the real protocol.

const VERSION: String = "slice-0"

var _peer: StreamPeerTCP = StreamPeerTCP.new()
var _buffer: PackedByteArray = PackedByteArray()
var _token: String = ""
var _hello_sent: bool = false


func open(port: int, token: String) -> Error:
	_token = token
	_peer.big_endian = true
	return _peer.connect_to_host("127.0.0.1", port)


func is_connected_to_server() -> bool:
	return _peer.get_status() == StreamPeerTCP.STATUS_CONNECTED


## Every complete message that has arrived since the last call.
func poll() -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	var _status: Error = _peer.poll()
	if not is_connected_to_server():
		return out
	if not _hello_sent:
		_hello_sent = true
		send({"type": "hello", "version": VERSION, "token": _token})
	var available: int = _peer.get_available_bytes()
	if available > 0:
		var got: Array = _peer.get_data(available)
		var chunk: PackedByteArray = got[1]
		_buffer.append_array(chunk)
	while _buffer.size() >= 4:
		var length: int = (_buffer[0] << 24) | (_buffer[1] << 16) | (_buffer[2] << 8) | _buffer[3]
		if _buffer.size() < 4 + length:
			break
		var text: String = _buffer.slice(4, 4 + length).get_string_from_utf8()
		_buffer = _buffer.slice(4 + length)
		var parsed: Variant = JSON.parse_string(text)
		if parsed is Dictionary:
			var message: Dictionary = parsed
			out.append(message)
		else:
			push_error("slice: a frame that is not a JSON object")
	return out


func send(message: Dictionary) -> void:
	var body: PackedByteArray = JSON.stringify(message).to_utf8_buffer()
	_peer.put_u32(body.size())
	var err: Error = _peer.put_data(body)
	if err != OK:
		push_error("slice: send failed: %s" % error_string(err))


## A cell channel as the server packs it: base64 of zlib-compressed bytes, with the inflated size.
static func unpack_cells(packed: Dictionary) -> PackedByteArray:
	var size: int = num_int(packed["n"])
	var text: String = packed["z"]
	return Marshalls.base64_to_raw(text).decompress(size, FileAccess.COMPRESSION_DEFLATE)


## JSON numbers arrive as floats in a Variant; typed GDScript refuses int() or float() of a Variant, so every read
## goes through an assignment to a typed local first.
static func num(value: Variant) -> float:
	var f: float = value
	return f


static func num_int(value: Variant) -> int:
	var f: float = value
	return int(f)


static func vec3(value: Variant) -> Vector3:
	var a: Array = value
	return SliceVoxels.to_godot(num(a[0]), num(a[1]), num(a[2]))
