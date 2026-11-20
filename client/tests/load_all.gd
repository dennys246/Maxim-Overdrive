extends SceneTree
## Loads every script scripts/godot_check.py names after `--`, and names each one that doesn't load. In 4.7.2 a
## script that fails to compile still loads as a non-null Script that cannot be instantiated, so both are checked;
## an abstract script cannot be instantiated by design and counts as loaded.


func _initialize() -> void:
	var paths: PackedStringArray = OS.get_cmdline_user_args()
	for path: String in paths:
		var script: Script = load(path) as Script
		if script == null or not (script.can_instantiate() or script.is_abstract()):
			print("godot-check: unloadable ", path)
	print("godot-check: loaded %d scripts" % paths.size())
	quit(0)
