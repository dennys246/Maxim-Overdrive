class_name WireJson
extends RefCounted
## The server's JSON as the client reads it (boundaries §9.1; O59, O60): the defence-in-depth twin of the server's
## strict decoder (src/simcore/protocol/strict_json.py). RefCounted with static functions, not a Node: decoding is
## pure logic, so it needs no scene tree and tests call it directly.
##
## Godot's JSON class reads every number as a double, keeps the last of a repeated key, and turns 1e400 into inf
## (measured on 4.7.2), so after it parses the text this reader refuses, with bad_json: text past max_bytes; a byte
## outside ASCII (the server writes ASCII only); containers nested past MAX_DEPTH; a number that is not finite or
## whose magnitude is 2^53 or more (2^53 + 1 parses to 2^53, so the pin sits below both). Then one pass over the
## known-valid text finds a repeated key, compared decoded, and every number written with a point or an exponent:
## the server writes integers only, and the text is the only place 5 and 5.0 differ.

const MAX_DEPTH: int = 32
const INT_LIMIT: float = 9007199254740992.0  # 2^53: every magnitude at or past it is refused


## The parsed value, or the refusal. ``non_integer_keys`` lists, for each number written with a point or an exponent,
## the key it belongs to ("" inside an array); the caller decides what that means where.
static func parse(text: String, max_bytes: int) -> WireRead:
	var bytes: PackedByteArray = text.to_utf8_buffer()
	if bytes.size() > max_bytes:
		return WireRead.refused("bad_json", "a message of %d bytes, past the %d-byte cap" % [bytes.size(), max_bytes])
	for b: int in bytes:
		if b > 0x7F:
			return WireRead.refused("bad_json", "a byte outside ASCII")
	var json: JSON = JSON.new()
	if json.parse(text) != OK:
		return WireRead.refused("bad_json", "not JSON: %s" % json.get_error_message())
	var problem: String = _check_value(json.data)
	if not problem.is_empty():
		return WireRead.refused("bad_json", problem)
	var read: WireRead = _scan(text)
	if read.ok:
		read.value = json.data
	return read


## Depth and every number, iteratively (no recursion to bound).
static func _check_value(value: Variant) -> String:
	var stack: Array = [[value, 1]]
	while not stack.is_empty():
		var top: Array = stack.pop_back()
		var item: Variant = top[0]
		var depth: int = top[1]
		if item is Dictionary or item is Array:
			if depth > MAX_DEPTH:
				return "containers nested past %d levels" % MAX_DEPTH
			var children: Array = []
			if item is Dictionary:
				var d: Dictionary = item
				children = d.values()
			else:
				children = item
			for child: Variant in children:
				stack.append([child, depth + 1])
		elif item is float:
			var f: float = item
			if not is_finite(f) or absf(f) >= INT_LIMIT:
				return "a number past what a double holds exactly"
	return ""


## One pass over text the parser has accepted: repeated keys (refused) and non-integer number literals (listed).
static func _scan(text: String) -> WireRead:
	var read: WireRead = WireRead.new()
	var objects: Array[Dictionary] = []  # per open container: the keys seen so far (none for an array)
	var is_object: Array[bool] = []
	var last_key: Array[String] = []
	var i: int = 0
	var n: int = text.length()
	while i < n:
		var c: String = text[i]
		if c == '"':
			var j: int = i + 1
			while text[j] != '"':
				j += 2 if text[j] == "\\" else 1
			var k: int = j + 1
			while k < n and text[k] in " \t\r\n":
				k += 1
			if not is_object.is_empty() and is_object[-1] and k < n and text[k] == ":":
				var key: String = JSON.parse_string(text.substr(i, j - i + 1))
				if objects[-1].has(key):
					return WireRead.refused("bad_json", "a key repeated in one object")
				objects[-1][key] = true
				last_key[-1] = key
			i = j + 1
		elif c == "{" or c == "[":
			objects.append({})
			is_object.append(c == "{")
			last_key.append("")
			i += 1
		elif c == "}" or c == "]":
			objects.pop_back()
			is_object.pop_back()
			last_key.pop_back()
			i += 1
		elif c == "-" or (c >= "0" and c <= "9"):
			var j: int = i
			while j < n and text[j] in "0123456789+-.eE":
				j += 1
			var literal: String = text.substr(i, j - i)
			if literal.contains(".") or literal.contains("e") or literal.contains("E"):
				var holder: String = last_key[-1] if not is_object.is_empty() and is_object[-1] else ""
				read.non_integer_keys.append(holder)
			i = j
		else:
			i += 1
	return read
