class_name EnginePin
extends RefCounted
## The Godot version this client is built and tested on. CLAUDE.md pins it: an upgrade is its own branch.
## RefCounted, not Node: plain logic needs no scene tree, so tests can call it directly, and it frees itself.

const MAJOR: int = 4
const MINOR: int = 7
const PATCH: int = 2
const STATUS: String = "stable"


## True when ``info`` (the shape of ``Engine.get_version_info()``) is the pinned release.
static func matches(info: Dictionary) -> bool:
	return (
		info.get("major") == MAJOR
		and info.get("minor") == MINOR
		and info.get("patch") == PATCH
		and info.get("status") == STATUS
	)


static func pinned() -> String:
	return "%d.%d.%d.%s" % [MAJOR, MINOR, PATCH, STATUS]
