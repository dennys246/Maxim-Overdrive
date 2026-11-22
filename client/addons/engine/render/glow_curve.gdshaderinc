// The glow curve (client_rendering.md §5.3), shared by the cell and fuel passes (client_objects.md §5.1, §5.2) so a
// hot wall and a hot stick at one temperature glow alike.

// 7, not §5.3's first 4: at 4 the ember envelope near 920 °C stayed below the bloom threshold and read dull; at 7 it
// blooms from about 910 °C. The cost: from about 1,230 °C every channel passes 1.0, so the linear tonemap draws the
// top fifth of the range flat white, and the bloom halo, which keeps growing with the HDR value, carries the heat
// beyond it (on the laptop tier, with bloom off, that band is plain white: B7). A soft knee and the Reinhard and AgX
// tonemappers were measured as alternatives and rejected: the knee washed the crate grey and killed the bloom, the
// tonemappers barely narrowed the band and dimmed the frame (owner, 2026-11-21).
const float GLOW_GAIN = 7.0;
const float GLOW_REFERENCE_K = 1773.0;
const vec3 GLOW_DULL = vec3(0.55, 0.04, 0.0);
const vec3 GLOW_ORANGE = vec3(1.0, 0.38, 0.04);
const vec3 GLOW_WHITE = vec3(1.0, 0.88, 0.62);
// The emission of a surface at ``t_c`` degrees C: GLOW_GAIN ((T_K / 1773)^4 - (T0_K / 1773)^4) in HDR, a stylisation
// (T^4 is total radiance, not visible radiance; PH-N2, CR-N4), less its value at ``start_c``, so a surface at the start
// emits nothing. ``span`` in [0, 1] runs the hue dull red, orange, yellow-white. The caller has checked t_c > start_c.
vec3 glow_curve(float t_c, float start_c, float span) {
	float k = (t_c + 273.15) / GLOW_REFERENCE_K;
	float k0 = (start_c + 273.15) / GLOW_REFERENCE_K;
	float level = GLOW_GAIN * (k * k * k * k - k0 * k0 * k0 * k0);
	vec3 hue = span < 0.5 ? mix(GLOW_DULL, GLOW_ORANGE, span * 2.0) : mix(GLOW_ORANGE, GLOW_WHITE, span * 2.0 - 1.0);
	return hue * level;
}
