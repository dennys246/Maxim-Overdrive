class_name MaterialPalette
extends Resource
## Albedo by material name: how each material looks, as client data. The cells name a material by id; the
## snapshot's vocabulary turns ids into names, and this turns names into colours. Colours are sRGB as an artist
## picks them; ``by_id`` converts to linear, which is what the shader's lighting maths works in.

@export var colours: Dictionary[String, Color] = {}


## id -> linear colour for every material in ``ids`` (name -> id) that this palette colours.
func by_id(ids: Dictionary[String, int]) -> Dictionary[int, Color]:
	var out: Dictionary[int, Color] = {}
	for material_name: String in ids:
		if colours.has(material_name):
			out[ids[material_name]] = colours[material_name].srgb_to_linear()
	return out
