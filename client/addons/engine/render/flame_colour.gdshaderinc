// The colour of burning, shared by the cell pass's flames (emission.gdshaderinc) and a flaming fuel surface
// (fuel_object.gdshaderinc, client_objects.md §5.2), so a burning wall and a burning stick are one hue. Each pass keeps
// its own gain.
const vec3 FLAME_COLOUR = vec3(1.0, 0.42, 0.08);
