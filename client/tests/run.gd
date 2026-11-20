extends SceneTree
## The client test runner: `godot --headless --path client -s res://tests/run.gd`. A script run with `-s` must be
## the main loop itself, and SceneTree is the main loop that has a scene tree, so tests can add nodes.
## Every res://tests/unit/test_*.gd is a RefCounted whose test_* methods take a TestContext. The last line printed
## is the sentinel the gate requires; Godot's exit status alone is never trusted (CR-B1).

const UNIT_DIR: String = "res://tests/unit"


func _initialize() -> void:
	var t: TestContext = TestContext.new()
	for file: String in DirAccess.get_files_at(UNIT_DIR):
		if file.begins_with("test_") and file.ends_with(".gd"):
			_run_suite(UNIT_DIR.path_join(file), t)
	print(t.summary())
	quit(0 if t.passed() else 1)


func _run_suite(path: String, t: TestContext) -> void:
	var script: GDScript = load(path) as GDScript
	if script == null or not script.can_instantiate():
		t.begin(path)
		t.check(false, "the suite does not load")
		return
	var suite: Object = script.new()
	for method: Dictionary in script.get_script_method_list():
		var method_name: String = method["name"]
		if method_name.begins_with("test_"):
			print("client-tests: run %s::%s" % [path.get_file(), method_name])
			t.begin("%s::%s" % [path.get_file(), method_name])
			suite.call(method_name, t)
