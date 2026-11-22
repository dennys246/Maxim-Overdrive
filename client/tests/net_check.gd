extends SceneTree
## The client's connection against a real listener (tests/test_godot_net.py runs it; boundaries §5.3):
## `godot --headless --path client -s res://tests/net_check.gd`, with the port in MAXIM_OVERDRIVE_NET_PORT and the
## token where NetClient reads it (MAXIM_OVERDRIVE_TOKEN or the file MAXIM_OVERDRIVE_TOKEN_FILE names).
## It polls NetClient once per frame, as the game's _process will, until the client holds a welcome or a refusal (a
## closed socket is one), then prints one line the test reads: Godot's exit status is never trusted (CR-B1).
## Engine why: a SceneTree script is its own main loop, so _process runs once per frame with no scene; the bound is
## the test's outer timeout, not a frame count, since a headless frame takes as long as the loop takes.

const PORT_ENV: String = "MAXIM_OVERDRIVE_NET_PORT"

var _client: NetClient = NetClient.new()
var _done: bool = false


func _initialize() -> void:
	var port: int = OS.get_environment(PORT_ENV).to_int()
	var opened: Error = _client.open(port, NetClient.token_from_environment())
	if opened != OK:
		_finish("net-check: open failed %s" % error_string(opened))


func _process(_delta: float) -> bool:
	if _done:
		return true
	_client.poll()
	if not _client.welcome.is_empty():
		var hash_ok: bool = _client.welcome.get("catalogue_hash") == WireCatalogue.catalogue_hash(WireCatalogue.v0())
		_finish("net-check: welcome %s catalogue %s" % [_client.welcome.get("role"), "same" if hash_ok else "differs"])
	elif not _client.refusal.is_empty():
		_finish("net-check: refused %s" % _client.refusal)
	return _done


func _finish(line: String) -> void:
	print(line)
	_done = true
	_client.peer.close()
	quit(0)
