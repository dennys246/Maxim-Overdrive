extends RefCounted
## The upload (render/volume_textures.gd): each z-slice of a channel is one Image whose pixel (x, y) is cell
## (x, y, z), the u16 region id splits into RG8 low and high bytes, and the bricks mark exactly the 4^3 blocks that
## hold a solid cell. An asymmetric snapshot pins the axes: any swap or flip moves a value to the wrong pixel.


static func asymmetric() -> CellSnapshot:
	var snap: CellSnapshot = CellSnapshot.new()
	snap.nx = 5
	snap.ny = 3
	snap.nz = 6
	snap.cell_m = 0.1
	snap.glow_scale_c_per_count = 1.0
	for channel: String in CellSnapshot.CHANNEL_BYTES:
		var bytes: PackedByteArray = PackedByteArray()
		var _ok: int = bytes.resize(snap.cells() * CellSnapshot.CHANNEL_BYTES[channel])
		snap.channels[channel] = bytes
	# One solid cell at (4, 2, 5), the far corner on every axis, in region 0x0102 = 258.
	snap.channels["material"][snap.index(4, 2, 5)] = 1
	snap.channels["region"][2 * snap.index(4, 2, 5)] = 0x02
	snap.channels["region"][2 * snap.index(4, 2, 5) + 1] = 0x01
	# A value that is distinct per cell, so every pixel's position is checked.
	for z: int in snap.nz:
		for y: int in snap.ny:
			for x: int in snap.nx:
				snap.channels["crack"][snap.index(x, y, z)] = x + 10 * y + 40 * z
	return snap


func test_each_slice_pixel_is_its_cell(t: TestContext) -> void:
	var snap: CellSnapshot = asymmetric()
	t.check(snap.problems().is_empty(), "the snapshot is drawable: %s" % [snap.problems()])
	var wrong: int = 0
	for z: int in snap.nz:
		var image: Image = VolumeTextures.slice(snap.channels["crack"], snap.nx, snap.ny, z, 1, Image.FORMAT_R8)
		for y: int in snap.ny:
			for x: int in snap.nx:
				if roundi(image.get_pixel(x, y).r * 255.0) != x + 10 * y + 40 * z:
					wrong += 1
	t.check_eq(wrong, 0, "pixels that aren't their cell")


func test_the_region_id_splits_low_byte_red_high_byte_green(t: TestContext) -> void:
	var snap: CellSnapshot = asymmetric()
	var image: Image = VolumeTextures.slice(snap.channels["region"], snap.nx, snap.ny, 5, 2, Image.FORMAT_RG8)
	var c: Color = image.get_pixel(4, 2)
	t.check_eq(roundi(c.r * 255.0) + 256 * roundi(c.g * 255.0), 258, "the decoded id")
	t.check_eq(str(snap.region_cell_bounds()), str({258: AABB(Vector3(4, 2, 5), Vector3.ONE)}), "the region's bounds")


func test_bricks_mark_exactly_the_occupied_blocks(t: TestContext) -> void:
	var snap: CellSnapshot = asymmetric()
	t.check_eq([VolumeTextures.brick_count(5), VolumeTextures.brick_count(3), VolumeTextures.brick_count(6)], [2, 1, 2], "brick counts round up")
	var bricks: PackedByteArray = VolumeTextures.bricks(snap)
	# Bricks are [bz, by, bx] = 2 x 1 x 2; the solid cell (4, 2, 5) is in brick (1, 0, 1), index (1 * 1 + 0) * 2 + 1.
	t.check_eq(Array(bricks), [0, 0, 0, 255], "only the far brick is occupied")
	snap.channels["material"][snap.index(4, 2, 5)] = 0
	t.check_eq(Array(VolumeTextures.bricks(snap)), [0, 0, 0, 0], "an empty volume has no occupied brick")


func test_a_short_channel_is_not_drawable(t: TestContext) -> void:
	var snap: CellSnapshot = asymmetric()
	snap.channels["burning"] = PackedByteArray([0])
	t.check(snap.problems().size() == 1, "one problem: %s" % [snap.problems()])
	var _erased: bool = snap.channels.erase("crack")
	snap.nx = 0
	snap.cell_m = 0.0
	snap.glow_scale_c_per_count = 0.0
	var said: String = " | ".join(snap.problems())
	for expected: String in ["shape 0 x 3 x 6 is empty", "cell_m 0.0 is not positive", "scale 0.0 is not positive", "no crack channel"]:
		t.check(said.contains(expected), "names '%s': %s" % [expected, said])
