extends RefCounted
## The engine running the tests is the pinned one, and EnginePin tells a different release apart.


func test_the_running_engine_is_the_pinned_one(t: TestContext) -> void:
	t.check(EnginePin.matches(Engine.get_version_info()), "running %s" % Engine.get_version_info().get("string"))


func test_another_release_does_not_match(t: TestContext) -> void:
	var info: Dictionary = {"major": 4, "minor": 7, "patch": 2, "status": "stable"}
	t.check(EnginePin.matches(info), "the pinned release itself")
	for key: String in ["major", "minor", "patch"]:
		var other: Dictionary = info.duplicate()
		var value: int = other[key]
		other[key] = value + 1
		t.check(not EnginePin.matches(other), "a different %s" % key)
	var beta: Dictionary = info.duplicate()
	beta["status"] = "beta"
	t.check(not EnginePin.matches(beta), "a beta of the same version")
