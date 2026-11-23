extends RefCounted
## NetSession's every branch without a socket (review C-S2 to C-S4): what the client makes of each server message, a
## welcome held to its fields and to this build's catalogue (O64), the first refusal kept, and frames only after a
## welcome. NetClient feeds it packets; tests/test_godot_net.py runs that half against the real host.

const FRAMES: String = "res://tests/fixtures/wire/frames"


func _welcome_fields() -> Dictionary:
	return {
		"type": "welcome", "protocol": 0, "session": 1, "role": "guest", "build": "simcore 0.0.1", "shape": [2, 2, 2],
		"catalogue_hash": WireCatalogue.catalogue_hash(WireCatalogue.v0()),
	}


func _welcome(changes: Dictionary = {}) -> PackedByteArray:
	var message: Dictionary = _welcome_fields()
	message.merge(changes, true)
	return _text(message)


func _text(message: Variant) -> PackedByteArray:
	# JSON.stringify writes an int as an integer and a float with a point, as the server's encoder never does
	return JSON.stringify(message).to_utf8_buffer()


func _after(messages: Array[PackedByteArray]) -> NetSession:
	var session: NetSession = NetSession.new()
	for m: PackedByteArray in messages:
		session.on_text(m)
	return session


func test_a_welcome_with_this_build_s_catalogue_starts_the_session(t: TestContext) -> void:
	var session: NetSession = _after([_welcome()])
	t.check(not session.ended(), "not ended: %s" % session.refusal)
	t.check_eq(session.welcome.get("role"), "guest", "welcome kept")


func test_each_wrong_welcome_ends_the_session_with_the_server_s_code(t: TestContext) -> void:
	var cases: Array[Array] = [
		[{"protocol": 1}, "bad_version"],
		[{"protocol": true}, "bad_version"],  # a bool, once a script error that stalled the client
		[{"protocol": "0"}, "bad_version"],
		[{"catalogue_hash": "sha256/c14n-1:" + "0".repeat(64)}, "bad_version"],
		[{"catalogue_hash": 7}, "bad_shape"],
		[{"role": "admin"}, "unknown_kind"],
		[{"session": 0}, "out_of_range"],
	]
	for c: Array in cases:
		var changes: Dictionary = c[0]
		t.check_eq(_after([_welcome(changes)]).refusal, c[1], str(changes))
	var no_hash: Dictionary = _welcome_fields()  # built, not parsed: JSON.parse_string would make protocol 0.0
	var _erased: bool = no_hash.erase("catalogue_hash")
	t.check_eq(_after([_text(no_hash)]).refusal, "bad_shape", "no catalogue hash")


func test_the_server_s_other_messages(t: TestContext) -> void:
	t.check_eq(_after([_text({"type": "error", "code": "bad_token"})]).refusal, "bad_token", "an error's code")
	t.check_eq(_after([_text({"type": "error"})]).refusal, "bad_shape", "an error without a code")
	t.check_eq(_after([_text({"type": "error", "code": "Not a code!"})]).refusal, "bad_shape", "prose as a code")
	t.check_eq(_after([_text({"type": "vote"})]).refusal, "unknown_kind", "an unknown type")
	t.check_eq(_after([_text([1, 2])]).refusal, "bad_shape", "not an object")
	t.check_eq(_after(["{\"type\":\"welcome\",\"protocol\":0,\"session\":1.0}".to_ascii_buffer()]).refusal, "not_int", "a float")
	var newer: PackedByteArray = "{\"type\":\"welcome\",\"protocol\":1,\"session\":1.0}".to_ascii_buffer()
	t.check_eq(_after([newer]).refusal, "bad_version", "a newer welcome is refused for its version, float or not")
	t.check_eq(_after(["{\"type\":".to_ascii_buffer()]).refusal, "bad_json", "not JSON")
	t.check_eq(_after([_welcome(), _welcome()]).refusal, "bad_shape", "welcome comes once")


func test_the_first_refusal_wins_and_ends_the_session(t: TestContext) -> void:
	var session: NetSession = _after([_welcome({"protocol": 1}), _welcome()])
	t.check_eq(session.refusal, "bad_version", "a later welcome doesn't overwrite why it ended")
	t.check(session.welcome.is_empty(), "and isn't read")
	session.end("closed 1000")
	t.check_eq(session.refusal, "bad_version", "nor does the close")


func test_a_frame_is_read_only_after_welcome(t: TestContext) -> void:
	var frame: PackedByteArray = FileAccess.get_file_as_bytes(FRAMES.path_join("base.bin"))
	var early: NetSession = NetSession.new()
	early.on_frame(frame)
	t.check_eq(early.refusal, "bad_shape", "a frame before welcome")
	var session: NetSession = _after([_welcome()])
	session.on_frame(frame)
	t.check(session.last_frame != null and not session.ended(), "a frame after welcome: %s" % session.refusal)
	session.on_frame(FileAccess.get_file_as_bytes(FRAMES.path_join("unknown_required_channel.bin")))
	t.check_eq(session.refusal, "unknown_field", "a refused frame ends the session")


func test_the_server_s_own_welcome_starts_the_session(t: TestContext) -> void:
	# Written by the server's encoder (scripts/wire_fixtures.py, the server set): the bytes the client gets on join
	var bytes: PackedByteArray = FileAccess.get_file_as_bytes("res://tests/fixtures/wire/server/welcome.json")
	t.check(not bytes.is_empty(), "the golden welcome is there")
	var session: NetSession = _after([bytes])
	t.check(not session.ended(), "accepted: %s" % session.refusal)
	t.check_eq(session.welcome.get("role"), "guest", "its role read")
