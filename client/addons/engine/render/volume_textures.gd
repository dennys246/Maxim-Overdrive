class_name VolumeTextures
extends RefCounted
## The snapshot's channels as 3-D textures, plus the occupancy bricks the shader skips empty space with.
##
## Why 3-D textures: the shader walks the cell grid itself (a voxel raymarch, client_rendering.md §5.1), so it needs
## random access to any cell by its integer index. A 3-D texture is exactly that, an array the GPU can read at
## (x, y, z) with texelFetch, and uploading one is a single copy of bytes we already have, where building a mesh of
## 230,400 cells would cost a remesh on every change.
##
## Texture formats (§4.2): one-byte channels are FORMAT_R8, read in the shader as a normalised float (byte / 255);
## the u16 region id is FORMAT_RG8, low byte in r and high in g, recombined as r + 256 g (probed bit-exact on 4.7.2,
## docs/design/research/godot_probes.md). No mipmaps: a cell is never averaged with its neighbours, and texelFetch
## reads level 0 only.

## Edge of an occupancy brick, in cells (§5.2): 4 x 4 x 4 cells, so the alley's 120 x 40 x 48 is 30 x 10 x 12 bricks.
const BRICK: int = 4


## A ``format`` texture of the snapshot's shape from ``bytes`` ([nz, ny, nx], x fastest), one Image per z-slice.
static func texture(snap: CellSnapshot, bytes: PackedByteArray, format: Image.Format) -> ImageTexture3D:
	var per_cell: int = 2 if format == Image.FORMAT_RG8 else 1
	return _texture_of(bytes, snap.nx, snap.ny, snap.nz, per_cell, format)


## The occupancy bricks: 255 where any cell of the 4 x 4 x 4 brick is solid (material != 0), else 0. The shader
## jumps over a brick of 0 in one step instead of four to seven.
static func bricks(snap: CellSnapshot) -> PackedByteArray:
	var bx: int = brick_count(snap.nx)
	var by: int = brick_count(snap.ny)
	var bz: int = brick_count(snap.nz)
	var out: PackedByteArray = PackedByteArray()
	if out.resize(bx * by * bz) != OK:
		push_error("VolumeTextures: could not size the brick array")
		return out
	var material: PackedByteArray = snap.channels["material"]
	var i: int = 0
	for z: int in snap.nz:
		var bz_row: int = (z >> 2) * by
		for y: int in snap.ny:
			var row: int = (bz_row + (y >> 2)) * bx
			for x: int in snap.nx:
				if material[i] != 0:
					out[row + (x >> 2)] = 255
				i += 1
	return out


static func bricks_texture(snap: CellSnapshot) -> ImageTexture3D:
	var bx: int = brick_count(snap.nx)
	var by: int = brick_count(snap.ny)
	var bz: int = brick_count(snap.nz)
	return _texture_of(bricks(snap), bx, by, bz, 1, Image.FORMAT_R8)


static func brick_count(cells: int) -> int:
	return (cells + BRICK - 1) >> 2


## One z-slice of ``bytes`` as an Image: what texture() uploads for slice ``z``. Separate so a test can read back
## the exact pixels the GPU is given without a GPU (the headless renderer keeps no texture data).
static func slice(bytes: PackedByteArray, w: int, h: int, z: int, per_cell: int, format: Image.Format) -> Image:
	var size: int = w * h * per_cell
	return Image.create_from_data(w, h, false, format, bytes.slice(z * size, (z + 1) * size))


static func _texture_of(bytes: PackedByteArray, w: int, h: int, d: int, per_cell: int, format: Image.Format) -> ImageTexture3D:
	var images: Array[Image] = []
	for z: int in d:
		images.append(slice(bytes, w, h, z, per_cell, format))
	var tex: ImageTexture3D = ImageTexture3D.new()
	var err: Error = tex.create(format, w, h, d, false, images)
	if err != OK:
		push_error("VolumeTextures: ImageTexture3D.create failed: %s" % error_string(err))
	return tex
