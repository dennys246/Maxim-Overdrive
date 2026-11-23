class_name WireFields
extends RefCounted
## Typed readers for values parsed off the wire, one per converter the server's schema applies
## (src/simcore/core/schema.py, converters.py), each refusing with the server's code: so a header the server would
## refuse for a field, the client refuses for that field with the same code, which the shared fixtures check. Each
## reader records only the first refusal on ``read`` and returns a neutral value after one, so a caller reads field
## after field and checks once.
##
## WireJson reads an integer literal as an int, exact below 2^53; the server's JSON holds no other number (O62), so a
## float never reaches these readers from it, and whole() still takes one for the client's own data.

const INT_MAX: int = 9007199254740991  # 2^53 - 1 (O59)
const DIGEST_SCHEME: String = "sha256/c14n-1"
const MAX_NAME_CHARS: int = 64  # checks.IDENTITY_KEY_CHARS; the fixtures manifest holds the two equal


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


## A version, read before anything else as the server's read_version does: a whole number from 0, never a bool, a
## float or missing (bad_version). ``was_float`` is the parser's word that it was written with a point or exponent.
static func version(read: WireRead, value: Variant, was_float: bool) -> int:
	if was_float or not value is int:
		read.refuse("bad_version", "protocol must be a whole number")
		return -1
	var whole_version: int = value
	if whole_version < 0:
		read.refuse("bad_version", "protocol must be a whole number from 0")
		return -1
	return whole_version


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


## A wire name (``converters.WireName``, client_rendering §4.1): 1 to 64 characters of printable ASCII (0x20 to 0x7E),
## no outer spaces, no ':'. ASCII on both sides, so neither reader needs Unicode tables, which differ by version; an
## escape can decode to any character, so the check reads the decoded name, never the header's bytes.
static func identity(read: WireRead, value: Variant, what: String) -> String:
	var text: String = ""
	if value is String:
		text = value
	var ok: bool = value is String and text.length() > 0 and text.length() <= MAX_NAME_CHARS and not text.contains(":")
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
	# \z, not $: PCRE's $ also matches before a final newline, which Python's fullmatch never does (review W-S4)
	var shape: RegEx = RegEx.create_from_string("^([a-z0-9]+/[a-z0-9]+-[0-9]+):[0-9a-f]{64}\\z")
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
