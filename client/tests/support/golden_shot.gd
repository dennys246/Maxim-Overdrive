class_name GoldenShot
extends RefCounted
## One ``--shot=<fixture>[+<fuel>]:<tier>:<pass>:<png>`` of the golden scene (tests/golden.gd), parsed, and the checks
## that a shot's fixtures and tier can be drawn: the grammar's one statement. ``<fuel>`` names a fuel fixture drawn over
## the cells. Separate from the scene so the headless runner can test every refusal: the scene itself needs a display,
## which the gate's runner doesn't have.

const PASSES: Dictionary[String, CellVolume.Pass] = {
	"shaded": CellVolume.Pass.SHADED,
	"crack_mask": CellVolume.Pass.CRACK_MASK,
	"glow_mask": CellVolume.Pass.GLOW_MASK,
	"shaded_noflame": CellVolume.Pass.SHADED,
	"fuel_mask": CellVolume.Pass.OCCLUDER,
	"flame_mask": CellVolume.Pass.OCCLUDER,
}
## What the fuel pass draws in each pass, and whether flames do.
const FUEL_VIEWS: Dictionary[String, FuelPass.View] = {"fuel_mask": FuelPass.View.FUEL_ID, "flame_mask": FuelPass.View.FLAME_ID}
## The cell masks: a fuel fixture drawn into one would put shaded fuel in a mask that measures cells.
const CELL_MASKS: Array[String] = ["crack_mask", "glow_mask"]
const NO_FLAMES: Array[String] = ["shaded_noflame", "fuel_mask"]

var fixture: String = ""
## The fuel fixture drawn over the cells, or "" for none.
var fuel: String = ""
var fuel_view: FuelPass.View = FuelPass.View.SHADED
var flames: bool = true
var tier: String = ""
var pass_kind: CellVolume.Pass = CellVolume.Pass.SHADED
var png: String = ""
## Why the shot can't be drawn; empty when it can.
var problem: String = ""


static func parse(text: String) -> GoldenShot:
	var shot: GoldenShot = GoldenShot.new()
	var parts: PackedStringArray = text.split(":", true, 3)
	if parts.size() != 4 or parts[0].is_empty() or parts[1].is_empty() or parts[3].is_empty():
		shot.problem = "a shot is <fixture>[+<fuel>]:<tier>:<pass>:<png>, got %s" % text
	elif not PASSES.has(parts[2]):
		shot.problem = "pass %s is not one of %s" % [parts[2], ", ".join(PASSES.keys())]
	elif not parts[3].is_absolute_path():
		shot.problem = "the png path %s must be absolute (Godot reads a relative one against the project)" % parts[3]
	elif parts[0].split("+").size() > 2 or parts[0].ends_with("+") or parts[0].begins_with("+"):
		shot.problem = "fixtures are <cells> or <cells>+<fuel>, got %s" % parts[0]
	else:
		var names: PackedStringArray = parts[0].split("+")
		shot.fixture = names[0]
		shot.fuel = names[1] if names.size() == 2 else ""
		shot.tier = parts[1]
		shot.pass_kind = PASSES[parts[2]]
		shot.fuel_view = FUEL_VIEWS.get(parts[2], FuelPass.View.SHADED)
		shot.flames = not NO_FLAMES.has(parts[2])
		shot.png = parts[3]
	if shot.problem.is_empty() and shot.fuel.is_empty() and (FUEL_VIEWS.has(parts[2]) or parts[2] == "shaded_noflame"):
		shot.problem = "pass %s draws fuel, so it needs a <cells>+<fuel> fixture" % parts[2]
	if shot.problem.is_empty() and not shot.fuel.is_empty() and CELL_MASKS.has(parts[2]):
		shot.problem = "pass %s measures cells, so it draws no fuel fixture" % parts[2]
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


## Why the fuel fixture ``source`` can't be drawn; empty when it can.
static func fuel_usable(source: FuelFixture) -> String:
	if not source.problems.is_empty():
		return "fuel fixture: " + "; ".join(source.problems)
	return ""
