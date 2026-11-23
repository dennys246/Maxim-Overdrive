extends RefCounted
## Integers on the wire (client_rendering.md §3, §4.1): JSON.stringify writes an int as an integer but a float as
## "5500.0", so every value the client sends is cast with int() first; JSON.parse_string turns every number into a
## float, so every integer the client reads is cast back, and every integer on the JSON path stays below 2^53 (O59):
## 2^53 and 2^53 + 1 parse to one double.


func test_stringify_writes_ints_as_integers_and_floats_with_a_point(t: TestContext) -> void:
	t.check_eq(JSON.stringify(int(5500.0)), "5500", "an int")
	t.check_eq(JSON.stringify(5500.0), "5500.0", "a float of the same value")
	t.check_eq(JSON.stringify([int(1000.0), int(-1000.0)]), "[1000,-1000]", "a direction vector")
	t.check_eq(JSON.stringify({"target_mm": int(3200.7)}), "{\"target_mm\":3200}", "int() truncates")


func test_parse_returns_floats_that_lose_integers_above_2_pow_53(t: TestContext) -> void:
	var parsed: Variant = JSON.parse_string("{\"tick\": 5500, \"at\": 9007199254740992, \"over\": 9007199254740993}")
	t.check(parsed is Dictionary, "an object parses to a Dictionary")
	if not parsed is Dictionary:
		return
	var d: Dictionary = parsed
	t.check_eq(typeof(d["tick"]), TYPE_FLOAT, "an integer is read back as a float")
	var at: float = d["at"]
	var over: float = d["over"]
	t.check_eq(int(at), 9007199254740992, "2^53 survives")
	t.check(int(over) != 9007199254740993, "2^53 + 1 does not")
