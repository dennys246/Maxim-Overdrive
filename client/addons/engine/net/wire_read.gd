class_name WireRead
extends RefCounted
## What reading something off the wire gave: a value, or a refusal with its code from the server's vocabulary
## (src/simcore/core/refusals.py) and a reason for the log. The first refusal wins; later ones are not recorded, so a
## reader can run its checks in the server's order and report what the server would.

var ok: bool = true
var code: String = ""
var reason: String = ""
var value: Variant = null
## WireJson: for each number written with a point or an exponent, the key it belongs to ("" inside an array).
var non_integer_keys: Array[String] = []


static func refused(refusal_code: String, why: String) -> WireRead:
	var read: WireRead = WireRead.new()
	read.refuse(refusal_code, why)
	return read


func refuse(refusal_code: String, why: String) -> void:
	if ok:
		ok = false
		code = refusal_code
		reason = why
