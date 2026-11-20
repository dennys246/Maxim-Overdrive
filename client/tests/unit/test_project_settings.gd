extends RefCounted
## The live settings, as this engine reads project.godot. tests/test_client_project.py checks the file without Godot;
## this checks what the engine actually applies, so a warning added by an engine upgrade fails here at Warn.

const WARNINGS: String = "debug/gdscript/warnings/"
const ERROR_LEVEL: int = 2


func test_every_gdscript_warning_is_an_error(t: TestContext) -> void:
	var seen: int = 0
	for property: Dictionary in ProjectSettings.get_property_list():
		var key: String = property["name"]
		var type: int = property["type"]
		if key.begins_with(WARNINGS) and type == TYPE_INT:
			seen += 1
			t.check_eq(ProjectSettings.get_setting(key), ERROR_LEVEL, key)
	# The list itself is held by tests/test_client_project.py::WARNINGS_4_7_2; here, only that the walk found some.
	t.check(seen > 0, "no warning levels found")
	t.check_eq(ProjectSettings.get_setting(WARNINGS + "enable"), true, "warnings are enabled")


func test_no_directory_is_exempt_from_warnings(t: TestContext) -> void:
	# The 4.7.2 default exempts res://addons, which is where the engine half of the client lives.
	t.check_eq(ProjectSettings.get_setting(WARNINGS + "directory_rules"), {}, "directory_rules")


func test_the_renderer_is_compatibility(t: TestContext) -> void:
	t.check_eq(ProjectSettings.get_setting("rendering/renderer/rendering_method"), "gl_compatibility", "desktop")
	t.check_eq(ProjectSettings.get_setting("rendering/renderer/rendering_method.mobile"), "gl_compatibility", "mobile")
	t.check_eq(ProjectSettings.get_setting("rendering/renderer/rendering_method.web"), "gl_compatibility", "web")
