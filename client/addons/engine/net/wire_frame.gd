class_name WireFrame
extends RefCounted
## A cell frame the client's decoder accepted (FrameDecoder): its header's numbers and its known channels' bytes.
## Arrays are [nz, ny, nx], x fastest (client_rendering.md §4.1), so one z-slice is one Godot Image.

var tick: int = 0
var regions_version: int = 0
var nz: int = 0
var ny: int = 0
var nx: int = 0
var cell_size_um: int = 0
## [x, y, z] of cell (0, 0, 0)'s corner, in world micrometres.
var origin_um: Array[int] = []
var channels: Dictionary[String, PackedByteArray] = {}
## What the extension rule ignored, in header order: "grid:<name>", "table:<name>", "channel:<name>".
var ignored: Array[String] = []


## The index of cell [z, y, x] in a channel's values.
func index(z: int, y: int, x: int) -> int:
	return x + nx * (y + ny * z)
