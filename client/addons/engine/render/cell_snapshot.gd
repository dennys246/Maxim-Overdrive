class_name CellSnapshot
extends RefCounted
## One cell frame as the renderer reads it: the shape, the spacing, the channels' bytes, and the vocabularies that
## name their values. This is the seam between whatever decodes cells and what draws them. Today the client test
## fixtures fill it (client/tests/support/snapshot_fixture.gd); step 7's decoder will fill the same object from a
## wire frame, so nothing here knows about the wire (protocol v0 isn't frozen; client_rendering.md §4).
## RefCounted, not Resource: it is never saved or edited in the editor, and it frees itself when the last holder
## lets go.
##
## Arrays are [nz, ny, nx] in C order, x fastest: one z-slice is nx * ny values, row by row, which is exactly one
## Godot Image, so a slice uploads without reshuffling.

## The channels the shader reads, with their bytes per cell (client_rendering.md §4.2). temperature_c, the f16 debug
## view, is not drawn by any pass yet, so it isn't required here.
const CHANNEL_BYTES: Dictionary[String, int] = {
	"material": 1, "region": 2, "crack": 1, "surface_glow": 1, "burning": 1,
}

var nx: int = 0
var ny: int = 0
var nz: int = 0
var cell_m: float = 0.0
var channels: Dictionary[String, PackedByteArray] = {}
## region id -> name; 0 is "no region" and has no entry.
var region_names: Dictionary[int, String] = {}
## material name -> id, the vocabulary the palette colours cells by (air is 0).
var material_ids: Dictionary[String, int] = {}
## surface_glow's calibration, T = offset_c + scale_c_per_count * g, from the catalogue's integer rational.
var glow_offset_c: float = 0.0
var glow_scale_c_per_count: float = 0.0


func cells() -> int:
	return nx * ny * nz


## Every reason this snapshot can't be drawn; empty when it can. The decoder (or fixture loader) that fills a
## snapshot calls this and refuses on any reason, so the renderer never sees a short array.
func problems() -> Array[String]:
	var out: Array[String] = []
	if nx <= 0 or ny <= 0 or nz <= 0:
		out.append("shape %d x %d x %d is empty" % [nx, ny, nz])
	if not cell_m > 0.0:
		out.append("cell_m %s is not positive" % cell_m)
	if material_ids.is_empty():
		out.append("no material vocabulary")
	if not glow_scale_c_per_count > 0.0:
		out.append("surface_glow's scale %s is not positive" % glow_scale_c_per_count)
	for channel: String in CHANNEL_BYTES:
		if not channels.has(channel):
			out.append("no %s channel" % channel)
		elif channels[channel].size() != cells() * CHANNEL_BYTES[channel]:
			out.append("%s has %d bytes, not %d" % [channel, channels[channel].size(), cells() * CHANNEL_BYTES[channel]])
	return out


## The id of the region called ``name``, or 0 when there is none.
func region_id(region_name: String) -> int:
	for id: int in region_names:
		if region_names[id] == region_name:
			return id
	return 0


## Byte offset of cell (x, y, z) in a one-byte channel.
func index(x: int, y: int, z: int) -> int:
	return (z * ny + y) * nx + x


## Every region's cell-index bounding box, id -> AABB in cell units (position = min corner, size = extent), in one
## pass over the region channel. Regions with no cells are absent. Run once per region map, not per frame: it is
## O(cells) in GDScript.
func region_cell_bounds() -> Dictionary[int, AABB]:
	var region: PackedByteArray = channels["region"]
	var lo: Dictionary[int, Vector3i] = {}
	var hi: Dictionary[int, Vector3i] = {}
	var i: int = 0
	for z: int in nz:
		for y: int in ny:
			for x: int in nx:
				var id: int = region[i] | (region[i + 1] << 8)
				i += 2
				if id == 0:
					continue
				var at: Vector3i = Vector3i(x, y, z)
				if lo.has(id):
					lo[id] = lo[id].min(at)
					hi[id] = hi[id].max(at)
				else:
					lo[id] = at
					hi[id] = at
	var out: Dictionary[int, AABB] = {}
	for id: int in lo:
		out[id] = AABB(Vector3(lo[id]), Vector3(hi[id] - lo[id] + Vector3i.ONE))
	return out
