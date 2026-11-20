extends SceneTree
## The client test runner: `godot --headless --path client -s res://tests/run.gd`. A script run with `-s` must be
## the main loop itself, and SceneTree is the main loop that has a scene tree, so tests can add nodes and await frames.
## Every test_*.gd under res://tests/unit (subdirectories too) is a RefCounted whose test_* methods take a TestContext.
## Each test is awaited before the next starts, so a test that awaits a frame finishes, checks and all, before the
## summary (S2C-B1); a test that makes no check fails. The last line printed is the sentinel the gate requires.
## Godot's exit status alone is never trusted (CR-B1): the quit code below is belt and braces, since a failure
## already turns the sentinel into a FAIL line.

const UNIT_DIR: String = "res://tests/unit"


func _initialize() -> void:
	var t: TestContext = TestContext.new()
	for path: String in _suites(UNIT_DIR):
		await _run_suite(path, t)
	print(t.summary())
	quit(0 if t.passed() else 1)


## Every test_*.gd under ``dir``, depth first, in name order, so the run order is the same everywhere.
func _suites(dir: String) -> Array[String]:
	var found: Array[String] = []
	for sub: String in DirAccess.get_directories_at(dir):
		found.append_array(_suites(dir.path_join(sub)))
	for file: String in DirAccess.get_files_at(dir):
		if file.begins_with("test_") and file.ends_with(".gd"):
			found.append(dir.path_join(file))
	return found


func _run_suite(path: String, t: TestContext) -> void:
	var script: GDScript = load(path) as GDScript
	if script == null or not script.can_instantiate():
		t.begin(path)
		t.check(false, "the suite does not load")
		t.finish()
		return
	var suite: Object = script.new()
	var found: int = 0
	for method: Dictionary in script.get_script_method_list():
		var method_name: String = method["name"]
		if method_name.begins_with("test_"):
			found += 1
			var test_name: String = "%s::%s" % [path.trim_prefix(UNIT_DIR + "/"), method_name]
			print("client-tests: run ", test_name)
			t.begin(test_name)
			# Awaiting a plain method returns at once; awaiting one that awaits waits for all of it.
			await suite.call(method_name, t)
			t.finish()
	if found == 0:
		# A test_*.gd that runs nothing (a misspelt method, say) would otherwise pass silently (S2D-N1).
		t.begin(path)
		t.check(false, "has no test_ methods")
		t.finish()
