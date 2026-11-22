// Glow and flames (client_rendering.md §5.3): light the surface gives off, added on top of the lit colour.
//
// Emission is HDR: it may exceed 1.0, and the WorldEnvironment's glow (bloom) spreads what does into the pixels
// around it, which is how a screen suggests something brighter than white. So glow changes brightness, not only hue
// (CLAUDE.md, "never colour alone"), and §6.4's check measures it in greyscale.

// The sampler's filter is fixed at compile time in Godot, so the tier's choice is a #define (CR-N1, EX-N3): the
// top-level shader file defines GLOW_LINEAR or not before including this.
#ifdef GLOW_LINEAR
uniform sampler3D glow_tex : filter_linear, repeat_disable;
#else
uniform sampler3D glow_tex : filter_nearest, repeat_disable;
#endif
uniform sampler3D burning_tex : filter_nearest, repeat_disable;
// surface_glow's calibration from the catalogue: T = offset + scale * count, in °C.
// Sentinels: a scale of 0 glows nothing until CellVolume sets the snapshot's calibration.
uniform float glow_offset_c = 0.0;
uniform float glow_scale_c = 0.0;
// 0 in goldens (animation off, §6.1); 1 in play.
uniform float flicker_amount = 0.0;

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
const vec3 FLAME_COLOUR = vec3(1.0, 0.42, 0.08);
const float FLAME_GAIN = 1.6;

// surface_glow in counts (0-255) for the face with outward normal ``n_cell`` at ``p_cell``. Linear filtering
// samples at the cell's centre plane, half a cell in from the face, so it blends across the face with the
// neighbouring cells and never with the air cell in front of it.
float glow_count(ivec3 cell, vec3 p_cell, vec3 n_cell) {
#ifdef GLOW_LINEAR
	// textureLod at level 0: an implicit-derivative texture() inside data-dependent branches is undefined in GLSL.
	return textureLod(glow_tex, (p_cell - 0.5 * n_cell) / vec3(cells), 0.0).r * 255.0;
#else
	return texelFetch(glow_tex, cell, 0).r * 255.0;
#endif
}

// The emission for a skin at count ``g``: GLOW_GAIN (T_K / 1773)^4 in HDR, a stylisation (T^4 is total radiance, not
// visible radiance; PH-N2, CR-N4), less its value at the offset, so a count of 0 (at or below 525 °C) emits nothing
// and the first count emits almost nothing. Hue runs dull red, orange, yellow-white.
vec3 glow_emission(float g) {
	if (g <= 0.0) {
		return vec3(0.0);
	}
	float t_c = glow_offset_c + glow_scale_c * g;
	float k = (t_c + 273.15) / GLOW_REFERENCE_K;
	float k0 = (glow_offset_c + 273.15) / GLOW_REFERENCE_K;
	float level = GLOW_GAIN * (k * k * k * k - k0 * k0 * k0 * k0);
	float span = clamp(g / 255.0, 0.0, 1.0);
	vec3 hue = span < 0.5 ? mix(GLOW_DULL, GLOW_ORANGE, span * 2.0) : mix(GLOW_ORANGE, GLOW_WHITE, span * 2.0 - 1.0);
	return hue * level;
}

// Flames from ``burning``, the burning fraction of the cell's fuel surface: an emissive flicker. Particles (§5.3)
// are not built yet.
vec3 flame_emission(ivec3 cell, float time) {
	float b = texelFetch(burning_tex, cell, 0).r;
	if (b <= 0.0) {
		return vec3(0.0);
	}
	float phase = dot(lattice_hash(cell), vec3(6.2831853));
	float flicker = 1.0 + flicker_amount * 0.35 * sin(time * 9.0 + phase);
	return FLAME_COLOUR * FLAME_GAIN * b * flicker;
}
