extends RefCounted
## The main scene loads and its root is the Node3D the tree in client_rendering.md §7.1 names.


func test_the_main_scene_instantiates_as_a_node3d(t: TestContext) -> void:
	var path: String = ProjectSettings.get_setting("application/run/main_scene")
	var packed: PackedScene = load(path) as PackedScene
	t.check(packed != null, "the main scene loads")
	if packed == null:
		return
	var main: Node = packed.instantiate()
	t.check(main is Node3D, "the root is a Node3D")
	t.check_eq(main.name, &"Main", "the root's name")
	main.free()
