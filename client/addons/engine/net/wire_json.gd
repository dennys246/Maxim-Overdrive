class_name WireJson
extends RefCounted
## The server's JSON as the client reads it: a strict parser of RFC 8259 written for the wire (O63), the twin of the
## server's decoder (src/simcore/protocol/strict_json.py). RefCounted with static entry points, not a Node: decoding
## is pure logic, so it needs no scene tree and tests call it directly.
##
## Why not Godot's JSON class: measured on 4.7.2, it accepts leading zeros, trailing commas and raw control
## characters, stops reading at a NUL, keeps the last of a repeated key, reads every number as a double and turns
## 1e400 into inf. Patching those with text scans missed cases twice (step 7 review, E-S1, W-S1, C-S1), so this reads
## the grammar itself and refuses, with bad_json, what the server's decoder refuses: text past max_bytes; bytes that
## are not UTF-8; anything outside the grammar (a BOM, a NUL, a trailing comma, a leading zero, a raw control
## character in a string); a key repeated in one object, compared decoded (O60); a lone surrogate; an integer of
## magnitude 2^53 or more (O59); a number that overflows a double; containers nested past MAX_DEPTH.
##
## An integer literal reads as an int, exact; a number with a point or an exponent reads as a float and is listed in
## ``non_integer_keys`` under its top-level key ("" when it sits deeper), since the server's JSON holds integers only
## (O62) and the caller refuses it there.

const MAX_DEPTH: int = 32
const INT_MAX: int = 9007199254740991  # 2^53 - 1: the largest n for which a double tells n from n + 1
const _INT_DIGITS: int = 16  # INT_MAX's digit count: longer is past the pin, refused before to_int (18 would do too)
## The digits of 2^1024 - 2^970, halfway between the largest double and the next power: at or past it a literal
## rounds to inf, as Python's float() rounds it (to even); below it, to the largest double. String.to_float rounds
## some of those below to inf (step 7 delta review D-N2).
const _PAST_DOUBLE: String = (
	"1797693134862315807937289714053034150799341327100378269361737789804449682927647509466490179775872070" +
	"9633028641669288791094655554785194040263065748867150582068190890200070838367627385484581771153176447" +
	"5730270069855571366959622842914819860834936475292719074168444365510704342711559699508093042880177904" +
	"174497792"
)
const _LARGEST_DOUBLE: float = 1.7976931348623157e308

var _bytes: PackedByteArray
var _at: int = 0
var _read: WireRead = WireRead.new()
var _depth: int = 0


## The value ``bytes`` hold, or the refusal.
static func parse(bytes: PackedByteArray, max_bytes: int) -> WireRead:
	if bytes.size() > max_bytes:
		return WireRead.refused("bad_json", "a message of %d bytes, past the %d-byte cap" % [bytes.size(), max_bytes])
	var parser: WireJson = WireJson.new()
	parser._bytes = bytes
	parser._space()
	var value: Variant = parser._value("")
	parser._space()
	if parser._read.ok and parser._at != bytes.size():
		parser._fail("text after the value")
	if parser._read.ok:
		parser._read.value = value
	return parser._read


## O62's rule on the server's JSON, in the server's order (grammar._header, strict_json.integers_only), for a ``read``
## whose value is an object: first its version when it carries one (``versioned``; missing, a bool or a float is
## bad_version, and so is another version), then any number written with a point or an exponent, anywhere, not_int.
## The one place the client applies the rule, for frame headers and text messages alike.
static func server_rules(read: WireRead, protocol: int, versioned: bool) -> void:
	if not read.ok:
		return
	var message: Dictionary = read.value
	if versioned:
		var version: int = WireFields.version(read, message.get("protocol"))
		if read.ok and version != protocol:
			read.refuse("bad_version", "protocol %d; this client knows %d" % [version, protocol])
	if read.ok and not read.non_integer_keys.is_empty():
		read.refuse("not_int", "a number with a point or an exponent; the server's JSON holds integers only")


func _fail(why: String) -> void:
	_read.refuse("bad_json", "not JSON: %s at byte %d" % [why, _at])


func _peek() -> int:
	return _bytes[_at] if _at < _bytes.size() else -1


func _space() -> void:
	while _at < _bytes.size() and _bytes[_at] in [0x20, 0x09, 0x0A, 0x0D]:
		_at += 1


func _value(key: String) -> Variant:
	if not _read.ok:
		return null
	match _peek():
		0x7B:
			return _object()
		0x5B:
			return _array()
		0x22:
			return _string()
		0x74:
			return _word("true", true)
		0x66:
			return _word("false", false)
		0x6E:
			return _word("null", null)
	var b: int = _peek()
	if b == 0x2D or (b >= 0x30 and b <= 0x39):
		return _number(key)
	_fail("no value")
	return null


func _word(word: String, value: Variant) -> Variant:
	var spelled: PackedByteArray = word.to_ascii_buffer()
	if _bytes.slice(_at, _at + spelled.size()) != spelled:
		_fail("no value")
		return null
	_at += spelled.size()
	return value


func _enter() -> bool:
	_depth += 1
	if _depth > MAX_DEPTH:
		_read.refuse("bad_json", "containers nested past %d levels" % MAX_DEPTH)
		return false
	_at += 1
	_space()
	return true


func _object() -> Dictionary:
	var out: Dictionary = {}
	if not _enter():
		return out
	if _peek() == 0x7D:
		_at += 1
		_depth -= 1
		return out
	while _read.ok:
		if _peek() != 0x22:
			_fail("a key that is not a string")
			return out
		var name: String = _string()
		_space()
		if _peek() != 0x3A:
			_fail("no colon after a key")
			return out
		_at += 1
		_space()
		var member: Variant = _value(name if _depth == 1 else "")
		if _read.ok and out.has(name):
			_read.refuse("bad_json", "a key repeated in one object")
		out[name] = member
		_space()
		if not _separated(0x7D):
			return out
	return out


func _array() -> Array:
	var out: Array = []
	if not _enter():
		return out
	if _peek() == 0x5D:
		_at += 1
		_depth -= 1
		return out
	while _read.ok:
		out.append(_value(""))
		_space()
		if not _separated(0x5D):
			return out
	return out


## After a member: a comma and more (never a trailing comma), or the closing bracket. False when the container ends.
func _separated(closing: int) -> bool:
	if _peek() == closing:
		_at += 1
		_depth -= 1
		return false
	if _peek() != 0x2C:
		_fail("no comma between members")
		return false
	_at += 1
	_space()
	return true  # a trailing comma fails where the next member should start: a key or a value never begins with ] or }


func _string() -> String:
	_at += 1  # the opening quote
	var utf8: PackedByteArray = PackedByteArray()
	while _read.ok:
		var b: int = _peek()
		if b == -1:
			_fail("an unterminated string")
		elif b == 0x22:
			_at += 1
			return _decoded(utf8)
		elif b == 0x5C:
			_escape(utf8)
		elif b < 0x20:
			_fail("a raw control character in a string")
		elif b < 0x80:
			utf8.append_array(PackedByteArray([b]))  # append() returns a bool the parser has no use for
			_at += 1
		else:
			_utf8_sequence(utf8)
	return ""


## The text ``utf8`` holds, exactly. Godot's get_string_from_utf8 drops a leading U+FEFF (measured on 4.7.2, step 7
## delta review W-SF1), so text that starts with one is built code point by code point; the bytes were held to the
## standard on the way in, so every sequence here is whole, and none is U+0000 (refused, see _escape).
static func _decoded(utf8: PackedByteArray) -> String:
	var bom: bool = utf8.size() >= 3 and utf8[0] == 0xEF and utf8[1] == 0xBB and utf8[2] == 0xBF
	if not bom:
		return utf8.get_string_from_utf8()
	var out: String = ""
	var i: int = 0
	while i < utf8.size():
		var lead: int = utf8[i]
		var length: int = 1 if lead < 0x80 else 2 if lead < 0xE0 else 3 if lead < 0xF0 else 4
		var cp: int = lead if length == 1 else lead & (0x1F if length == 2 else 0x0F if length == 3 else 0x07)
		for k: int in range(1, length):
			cp = (cp << 6) | (utf8[i + k] & 0x3F)
		out += String.chr(cp)
		i += length
	return out


func _escape(utf8: PackedByteArray) -> void:
	_at += 1
	var b: int = _peek()
	var simple: Dictionary = {
		0x22: 0x22, 0x5C: 0x5C, 0x2F: 0x2F, 0x62: 0x08, 0x66: 0x0C, 0x6E: 0x0A, 0x72: 0x0D, 0x74: 0x09,
	}
	if simple.has(b):
		var out: int = simple[b]
		utf8.append_array(PackedByteArray([out]))
		_at += 1
		return
	if b != 0x75:
		_fail("an unknown escape")
		return
	var cp: int = _hex4()
	if cp >= 0xDC00 and cp <= 0xDFFF:
		_read.refuse("bad_json", "a string holding a lone surrogate")
		return
	if cp >= 0xD800 and cp <= 0xDBFF:
		if _bytes.slice(_at, _at + 2) != PackedByteArray([0x5C, 0x75]):
			_read.refuse("bad_json", "a string holding a lone surrogate")
			return
		_at += 1
		var low: int = _hex4()
		if low < 0xDC00 or low > 0xDFFF:
			_read.refuse("bad_json", "a string holding a lone surrogate")
			return
		cp = 0x10000 + ((cp - 0xD800) << 10) + (low - 0xDC00)
	if cp == 0:  # a Godot String can't hold U+0000 (it becomes U+FFFD, measured), so the wire's text never does
		_read.refuse("bad_json", "a string holding U+0000")
		return
	utf8.append_array(String.chr(cp).to_utf8_buffer())


## The four hex digits after a ``\u`` (``_at`` on the ``u``), as a code unit; -1 after a refusal.
func _hex4() -> int:
	var digits: String = _bytes.slice(_at + 1, _at + 5).get_string_from_ascii()
	var hex: bool = digits.length() == 4
	for ch: String in digits:  # is_valid_hex_number would take a sign: \u+041 (step 7 delta review W-SF2)
		hex = hex and "0123456789abcdefABCDEF".contains(ch)
	if not hex:
		_fail("a \\u escape without four hex digits")
		return -1
	_at += 5
	return digits.hex_to_int()


## One UTF-8 sequence, held to the standard: no overlong form, no surrogate, nothing past U+10FFFF.
func _utf8_sequence(utf8: PackedByteArray) -> void:
	var lead: int = _peek()
	var length: int = 0  # a lead byte no sequence uses (C0, C1, F5 and up) stays 0
	if lead >= 0xC2 and lead <= 0xDF:
		length = 2
	elif lead >= 0xE0 and lead <= 0xEF:
		length = 3
	elif lead >= 0xF0 and lead <= 0xF4:
		length = 4
	if length == 0 or _at + length > _bytes.size():
		_read.refuse("bad_json", "bytes that are not UTF-8")
		return
	var cp: int = lead & (0x1F if length == 2 else 0x0F if length == 3 else 0x07)
	for i: int in range(1, length):
		var cont: int = _bytes[_at + i]
		if cont & 0xC0 != 0x80:
			_read.refuse("bad_json", "bytes that are not UTF-8")
			return
		cp = (cp << 6) | (cont & 0x3F)
	var smallest: int = [0, 0, 0x80, 0x800, 0x10000][length]
	if cp < smallest or cp > 0x10FFFF or (cp >= 0xD800 and cp <= 0xDFFF):
		_read.refuse("bad_json", "bytes that are not UTF-8")
		return
	utf8.append_array(_bytes.slice(_at, _at + length))
	_at += length


func _number(key: String) -> Variant:
	var start: int = _at
	if _peek() == 0x2D:
		_at += 1
	if _peek() == 0x30:
		_at += 1  # a leading zero: 007 reads as 0, then fails where a comma or the end should be
	elif _digit(_peek()):
		while _digit(_peek()):
			_at += 1
	else:
		_fail("a number without digits")
		return null
	var integer: bool = true
	if _peek() == 0x2E:
		integer = false
		_at += 1
		if not _digits():
			return null
	if _peek() == 0x45 or _peek() == 0x65:
		integer = false
		_at += 1
		if _peek() == 0x2B or _peek() == 0x2D:
			_at += 1
		if not _digits():
			return null
	var text: String = _bytes.slice(start, _at).get_string_from_ascii()
	return _integer(text) if integer else _real(text, key)


func _digit(b: int) -> bool:
	return b >= 0x30 and b <= 0x39


func _digits() -> bool:
	if not _digit(_peek()):
		_fail("a fraction or exponent without digits")
		return false
	while _digit(_peek()):
		_at += 1
	return true


func _integer(text: String) -> Variant:
	# The digit count decides first, so a longer literal never reaches String.to_int: past int64 it returns -2^63
	# (with an engine ERROR above 2^63, silently at it), and absi(-2^63) is still negative. The fixtures at 2^63 and
	# integer_past_u64 hold it (step 7 delta 3, Wire B-1).
	var digits: int = text.length() - (1 if text.begins_with("-") else 0)
	if digits > _INT_DIGITS or absi(text.to_int()) > INT_MAX:
		_read.refuse("bad_json", "an integer of magnitude 2^53 or more (%d characters)" % text.length())
		return null
	return text.to_int()


func _real(text: String, key: String) -> Variant:
	var value: float = _double(text)
	if not is_finite(value):
		_read.refuse("bad_json", "a number too large for a double (%d characters)" % text.length())
		return null
	_read.non_integer_keys.append(key)
	return value


## The double a number literal names, as Python's float() reads it. String.to_float wraps or clamps a huge exponent
## (1e4294967296 reads as 1.0; step 7 delta review W-SF3), so the literal's decimal magnitude is worked out from its
## digits first, with an exponent too long to read saturated far past either edge, and the significant digits are
## handed to to_float with that magnitude. The class (finite or not) is Python's float()'s, at the largest double too;
## the digits are to_float's, which isn't correctly rounded, so a float's value is never part of the contract: the
## server's JSON holds none (O62), and a reader only classifies one.
static func _double(text: String) -> float:
	var negative: bool = text.begins_with("-")
	var body: String = text.trim_prefix("-")
	var mark: int = body.findn("e")
	var exponent: int = 0
	if mark >= 0:
		var digits: String = body.substr(mark + 1).trim_prefix("+")
		var direction: int = -1 if digits.begins_with("-") else 1
		digits = digits.trim_prefix("-").lstrip("0")
		exponent = direction * (100000 if digits.length() > 6 else digits.to_int())  # far past either edge
		body = body.substr(0, mark)
	var point: int = body.find(".")
	var whole: String = body if point < 0 else body.substr(0, point)
	var all_digits: String = whole + ("" if point < 0 else body.substr(point + 1))
	var significant: String = all_digits.lstrip("0")
	# Signs by statement, not by a conditional expression: -x if c else y reads as -(x if c else y) (measured, 4.7.2)
	var value: float = 0.0
	if significant.is_empty():
		return _signed(value, negative)
	var magnitude: int = whole.length() - (all_digits.length() - significant.length()) - 1 + exponent
	var tail: String = "" if significant.length() == 1 else "." + significant.substr(1)
	var normal: String = significant.substr(0, 1) + tail + "e" + str(magnitude)
	value = normal.to_float()
	if magnitude == 308 and not is_finite(value) and not _past_largest(significant):
		value = _LARGEST_DOUBLE
	elif magnitude == 308 and _past_largest(significant):
		value = INF
	return _signed(value, negative)


static func _signed(value: float, negative: bool) -> float:
	if negative:
		return -value
	return value


## Whether the significant digits ``digits`` (of a number of magnitude 10^308) reach _PAST_DOUBLE.
static func _past_largest(digits: String) -> bool:
	var width: int = maxi(digits.length(), _PAST_DOUBLE.length())
	return digits.rpad(width, "0") >= _PAST_DOUBLE.rpad(width, "0")
