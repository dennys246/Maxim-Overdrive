extends Node3D
## The client's root (client_rendering.md §7.1). Node3D is any node with a 3-D transform, so the world, the camera
## rig and the actors hang under it. Step 2 holds only the skeleton; Net, World, CameraRig and Hud arrive in steps 7
## and 8.


func _ready() -> void:
	var info: Dictionary = Engine.get_version_info()
	if not EnginePin.matches(info):
		push_error("Godot %s is not the pinned %s" % [info.get("string"), EnginePin.pinned()])
