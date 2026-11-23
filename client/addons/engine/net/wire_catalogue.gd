class_name WireCatalogue
extends RefCounted
## The channels this client build knows (client_rendering.md §4.2), described as the wire states them: the client's
## copy of the server's registry (src/simcore/protocol/catalogue.py). A name is an identity, so a frame's channel of a
## known name must match its description here term for term. A test hashes these as c14n-1 does and compares the
## result with the server's v0 hash in the fixture manifest, so the two registries can't drift apart unseen.


## Protocol v0's cell channels, in the server's order. Every one is required.
static func v0() -> Array[Dictionary]:
	return [
		channel("material", "id", "u8", "raw", true, [1, 1]),
		channel("region", "id", "u16", "raw", true, [1, 1]),
		channel("crack", "ratio", "u8", "linear", true, [1, 255]),
		channel("temperature_c", "celsius", "f16", "raw", true, [1, 1]),
	]


## Bytes per value of each wire dtype, all little-endian.
const DTYPE_BYTES: Dictionary[String, int] = {"u8": 1, "u16": 2, "u32": 4, "f16": 2, "f32": 4}
const DTYPES: Array[String] = ["u8", "u16", "u32", "f16", "f32"]
const ENCODINGS: Array[String] = ["raw", "linear"]


## One channel's description, as the wire states it and FrameDecoder compares it. The offset is 0/1 for every
## channel v0 knows.
static func channel(
	name: String, unit: String, dtype: String, encoding: String, required: bool, scale: Array[int]
) -> Dictionary:
	return {
		"name": name, "unit": unit, "dtype": dtype, "encoding": encoding, "required": required, "scale": scale,
		"offset": [0, 1],
	}


## The catalogue hash of ``descriptions``: sha256/c14n-1 over them in order. JSON.stringify with sorted keys and no
## indent writes c14n-1's text for these values: string keys, ASCII strings, bools and integers (measured on 4.7.2).
static func catalogue_hash(descriptions: Array[Dictionary]) -> String:
	var hashing: HashingContext = HashingContext.new()
	var hashed: bool = (
		hashing.start(HashingContext.HASH_SHA256) == OK
		and hashing.update(JSON.stringify(descriptions, "", true).to_utf8_buffer()) == OK
	)
	if not hashed:
		# An empty hash matches no catalogue, so every frame is then refused (bad_version), loudly, never drawn.
		push_error("WireCatalogue: SHA-256 failed")
		return ""
	return WireFields.DIGEST_SCHEME + ":" + hashing.finish().hex_encode()
