class_name WireFields
extends RefCounted
## Typed readers for values parsed off the wire, one per converter the server's schema applies
## (src/simcore/core/schema.py, converters.py), each refusing with the server's code: so a header the server would
## refuse for a field, the client refuses for that field with the same code. Each reader records only the first
## refusal on ``read`` and returns a neutral value after one, so a caller reads field after field and checks once.
##
## JSON numbers arrive as floats (§4.1); WireJson has already refused any written with a point or an exponent and any
## of magnitude 2^53 or more, so a float here holds an integer exactly and int() is exact.

const INT_MAX: int = 9007199254740991  # 2^53 - 1 (O59)
const DIGEST_SCHEME: String = "sha256/c14n-1"


## ``raw`` as a mapping with every ``required`` key and no other (closed keys, as ``checks.known_keys``).
static func keys(read: WireRead, raw: Variant, what: String, required: Array[String]) -> Dictionary:
	if not raw is Dictionary:
		read.refuse("bad_shape", "%s must be a mapping" % what)
		return {}
	var d: Dictionary = raw
	for key: Variant in d.keys():
		if not key is String or not required.has(key):
			read.refuse("unknown_field", "%s: an unknown key" % what)
			return {}
	for key: String in required:
		if not d.has(key):
			read.refuse("missing_field", "%s: missing %s" % [what, key])
			return {}
	return d


static func whole(read: WireRead, value: Variant, what: String, lo: int, hi: int) -> int:
	if value is bool or not (value is float or value is int):
		read.refuse("not_int", "%s must be a whole number" % what)
		return 0
	var f: float = value
	if f != floorf(f):
		read.refuse("not_int", "%s must be a whole number" % what)
		return 0
	var n: int = int(f)
	if n < lo or n > hi:
		read.refuse("out_of_range", "%s must be from %d to %d" % [what, lo, hi])
		return 0
	return n


static func wholes(read: WireRead, value: Variant, what: String, count: int, lo: int, hi: int) -> Array[int]:
	var out: Array[int] = []
	if not value is Array:
		read.refuse("bad_shape", "%s must be %d whole numbers" % [what, count])
		return out
	var items: Array = value
	if items.size() != count:
		read.refuse("bad_shape", "%s must be %d whole numbers" % [what, count])
		return out
	for item: Variant in items:
		out.append(whole(read, item, what, lo, hi))
	return out


static func choice(read: WireRead, value: Variant, what: String, words: Array[String]) -> String:
	var word: String = ""
	if value is String:
		word = value
	if not value is String or not words.has(word):
		read.refuse("unknown_kind", "%s must be one of %s" % [what, words])
		return ""
	return word


static func flag(read: WireRead, value: Variant, what: String) -> bool:
	if not value is bool:
		read.refuse("bad_shape", "%s must be true or false" % what)
		return false
	var b: bool = value
	return b


## An identity key (``checks.identity_key``): 1 to 64 printable characters, no outer spaces, no ':'. A header is ASCII,
## so printable is 0x20 to 0x7E.
static func identity(read: WireRead, value: Variant, what: String) -> String:
	var text: String = ""
	if value is String:
		text = value
	var ok: bool = value is String and text.length() > 0 and text.length() <= 64 and not text.contains(":")
	ok = ok and text == text.strip_edges()
	for i: int in text.length():
		ok = ok and text.unicode_at(i) >= 0x20 and text.unicode_at(i) <= 0x7E
	if not ok:
		read.refuse("bad_identity_key", "%s must be an identity key" % what)
		return ""
	return text


## A versioned digest in the one scheme this build knows (``digest.check_digest``).
static func digest(read: WireRead, value: Variant, what: String) -> String:
	var text: String = ""
	if value is String:
		text = value
	var shape: RegEx = RegEx.create_from_string("^([a-z0-9]+/[a-z0-9]+-[0-9]+):[0-9a-f]{64}$")
	var found: RegExMatch = shape.search(text)
	if not value is String or found == null:
		read.refuse("bad_shape", "%s must be a digest" % what)
		return ""
	if found.get_string(1) != DIGEST_SCHEME:
		read.refuse("bad_version", "%s is a %s digest" % [what, found.get_string(1)])
		return ""
	return text


## A list of at most ``max_items`` items, counted before any is read.
static func list_of(read: WireRead, value: Variant, what: String, max_items: int) -> Array:
	if not value is Array:
		read.refuse("bad_shape", "%s must be a list" % what)
		return []
	var items: Array = value
	if items.size() > max_items:
		read.refuse("over_budget", "%s holds at most %d items" % [what, max_items])
		return []
	return items
