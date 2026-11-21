class_name GoldenShot
extends RefCounted
## One ``--shot=<fixture>:<tier>:<pass>:<png>`` of the golden scene (tests/golden.gd), parsed, and the checks that a
## shot's fixture and tier can be drawn. Separate from the scene so the headless runner can test every refusal: the
## scene itself needs a display, which the gate's runner doesn't have.

const PASSES: Dictionary[String, CellVolume.Pass] = {
	"shaded": CellVolume.Pass.SHADED,
	"crack_mask": CellVolume.Pass.CRACK_MASK,
	"glow_mask": CellVolume.Pass.GLOW_MASK,
}

var fixture: String = ""
var tier: String = ""
var pass_kind: CellVolume.Pass = CellVolume.Pass.SHADED
var png: String = ""
## Why the shot can't be drawn; empty when it can.
var problem: String = ""


static func parse(text: String) -> GoldenShot:
	var shot: GoldenShot = GoldenShot.new()
	var parts: PackedStringArray = text.split(":", true, 3)
	if parts.size() != 4 or parts[0].is_empty() or parts[1].is_empty() or parts[3].is_empty():
		shot.problem = "a shot is <fixture>:<tier>:<pass>:<png>, got %s" % text
	elif not PASSES.has(parts[2]):
		shot.problem = "pass %s is not one of %s" % [parts[2], ", ".join(PASSES.keys())]
	elif not parts[3].is_absolute_path():
		shot.problem = "the png path %s must be absolute (Godot reads a relative one against the project)" % parts[3]
	else:
		shot.fixture = parts[0]
		shot.tier = parts[1]
		shot.pass_kind = PASSES[parts[2]]
		shot.png = parts[3]
	return shot


## Why ``fixture`` and ``tier`` can't draw a golden with ``player`` as the player; empty when they can.
static func usable(source: SnapshotFixture, drawn_with: RenderTier, player: int) -> String:
	if not source.problems.is_empty():
		return "fixture: " + "; ".join(source.problems)
	if drawn_with == null or not drawn_with.problems().is_empty():
		return "no usable tier"
	if not source.actors.has(player):
		return "the fixture has no player (actor %d)" % player
	if source.snapshot.region_id("crate") == 0:
		return "the fixture has no crate region to centre the golden camera on"
	return ""
