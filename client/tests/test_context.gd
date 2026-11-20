class_name TestContext
extends RefCounted
## What one client test run has checked and what failed. The runner owns one and hands it to every test method.
## GDScript has no exceptions: a failed check records itself and the test carries on, and a runtime error aborts
## only the method it happens in, so the gate also scans Godot's output for errors (scripts/godot_check.py).
## A test that ends having made no check fails: it cannot fail, so it proves nothing.

var _tests: int = 0
var _checks_in_test: int = 0
var _current: String = ""
var _failures: Array[String] = []


func begin(test_name: String) -> void:
	_tests += 1
	_checks_in_test = 0
	_current = test_name


func check(ok: bool, what: String) -> void:
	_checks_in_test += 1
	if not ok:
		_fail(what)


func check_eq(got: Variant, want: Variant, what: String) -> void:
	# Compared by their text form, which carries the type (1 and 1.0 differ): `==` on two Variants is itself a
	# Variant to the type checker, and Godot refuses it at runtime between some pairs of types.
	var g: String = var_to_str(got)
	var w: String = var_to_str(want)
	check(g == w, "%s: got %s, want %s" % [what, g, w])


## Called by the runner after each test returns (after its last await).
func finish() -> void:
	if _checks_in_test == 0:
		_fail("made no checks, so it cannot fail")


func passed() -> bool:
	return _tests > 0 and _failures.is_empty()


## The runner's last line, which the gate requires (client_rendering.md §7.3).
func summary() -> String:
	if passed():
		return "client-tests: PASS %d tests" % _tests
	return "client-tests: FAIL %d failure(s) in %d tests" % [_failures.size(), _tests]


func _fail(what: String) -> void:
	var line: String = "%s: %s" % [_current, what]
	_failures.append(line)
	printerr("client-tests: FAIL ", line)
