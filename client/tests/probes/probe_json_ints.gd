extends SceneTree
## §9 probe: do integers survive JSON.stringify, and what does JSON.parse_string give back? Headless:
## godot --headless --path client -s res://tests/probes/probe_json_ints.gd


func _initialize() -> void:
	var cases: Array = [int(5500), 5500.0, int(5500.7), [int(1000.0), int(1000.0)], {"target_mm": int(3200.0)}]
	for value: Variant in cases:
		print("probe json: stringify(%s %s) = %s" % [type_string(typeof(value)), var_to_str(value), JSON.stringify(value)])
	var parsed: Variant = JSON.parse_string("{\"tick\": 5500, \"big\": 9007199254740993}")
	print("probe json: parse_string gives %s" % var_to_str(parsed))
	quit(0)
