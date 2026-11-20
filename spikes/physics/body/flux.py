"""Incident radiant flux on a vertical body element facing the crate: point source and solid flame (view factor).

Geometry: the crate's vertical axis is x = y = 0, its base at z = 0. The body stands at horizontal distance d from
that axis, on the +x side, facing -x. A target is a vertical differential element at height z on the body's front.
"""

from __future__ import annotations

import math

import constants as C
import numpy as np


def equivalent_diameter(side: float) -> float:
    """NUREG-1805 eq 5-3: the diameter of a circle with the crate's footprint."""
    return math.sqrt(4.0 * side * side / math.pi)


def heskestad_height(q_kw: float, d: float) -> float:
    return C.HESKESTAD_A * q_kw**0.4 - C.HESKESTAD_B * d


# ---- point source (NUREG-1805 eq 5-1, Drysdale; Modak's cosine form for an element off the centre height) ----


def point_source(q_kw: float, hf: float, dist: float, z: float) -> float:
    """chi_r Q cos(theta) / (4 pi R^2), source at the flame's mid-height, vertical target facing the axis. kW/m^2."""
    dz = z - hf / 2.0
    r2 = dist * dist + dz * dz
    cos_t = dist / math.sqrt(r2)
    return C.CHI_R * q_kw * cos_t / (4.0 * math.pi * r2)


# ---- solid cylinder flame: NUREG-1805 eq 5-12/5-13 (Beyler 2002) and an independent quadrature ---------------


def _fv_closed(h_up: float, dist: float, diam: float) -> float:
    """View factor from a vertical element to a cylinder of height h_up whose base is level with the element."""
    if h_up <= 0.0:
        return 0.0
    s = 2.0 * dist / diam
    h = 2.0 * h_up / diam
    a = (h * h + s * s + 1.0) / (2.0 * s)
    t1 = math.atan(h / math.sqrt(s * s - 1.0)) / (math.pi * s)
    t2 = h / (math.pi * s) * math.atan(math.sqrt((s - 1.0) / (s + 1.0)))
    t3 = (
        a
        * h
        / (math.pi * s * math.sqrt(a * a - 1.0))
        * math.atan(math.sqrt((a + 1.0) * (s - 1.0) / ((a - 1.0) * (s + 1.0))))
    )
    return t1 - t2 + t3


def cylinder_vf_closed(z0: float, z1: float, dist: float, diam: float, z: float) -> float:
    """Cylinder side from z0 to z1, element at height z (two-cylinder superposition, NUREG eq 5-14)."""
    a, b = z0 - z, z1 - z
    if a >= 0.0:
        return _fv_closed(b, dist, diam) - _fv_closed(a, dist, diam)
    if b <= 0.0:
        return _fv_closed(-a, dist, diam) - _fv_closed(-b, dist, diam)
    return _fv_closed(b, dist, diam) + _fv_closed(-a, dist, diam)


def cylinder_vf_quadrature(
    z0: float, z1: float, dist: float, diam: float, z: float, *, n_phi: int = 720, n_z: int = 800
) -> float:
    """dF = cos1 cos2 / (pi s^2) dA over the visible side (midpoint rule), the check on the closed form."""
    rad = diam / 2.0
    phi = (np.arange(n_phi) + 0.5) * (2.0 * math.pi / n_phi)
    zz = z0 + (np.arange(n_z) + 0.5) * ((z1 - z0) / n_z)
    p, zg = np.meshgrid(phi, zz, indexing="ij")
    px, py = rad * np.cos(p), rad * np.sin(p)
    rx, ry, rz = dist - px, -py, z - zg  # surface point -> target
    s2 = rx * rx + ry * ry + rz * rz
    s = np.sqrt(s2)
    cos_surf = (np.cos(p) * rx + np.sin(p) * ry) / s  # outward normal (cos, sin, 0)
    cos_tgt = rx / s  # target normal is -x; direction target -> surface is -r
    ok = (cos_surf > 0.0) & (cos_tgt > 0.0)
    da = rad * (2.0 * math.pi / n_phi) * ((z1 - z0) / n_z)
    return float(np.sum(np.where(ok, cos_surf * cos_tgt / (math.pi * s2), 0.0)) * da)


def emissive_power_shokri_beyler(diam: float) -> float:
    return C.SB_E0_KW * 10.0 ** (-C.SB_K * diam)


def emissive_power_energy(q_kw: float, hf: float, diam: float) -> float:
    """chi_r Q spread over the cylinder's side and top.

    The solid flame that radiates exactly the point source's power.
    """
    area = math.pi * diam * hf + math.pi * diam * diam / 4.0
    return C.CHI_R * q_kw / area


# ---- ember phase: the crate's hot faces ---------------------------------------------------------------------


def _rect_parallel_corner(a: float, b: float, c: float) -> float:
    """Element parallel to an a x b rectangle, on the normal through one corner, at distance c (Howell C-ish)."""
    x, y = a / c, b / c
    return (
        x / math.sqrt(1 + x * x) * math.atan(y / math.sqrt(1 + x * x))
        + y / math.sqrt(1 + y * y) * math.atan(x / math.sqrt(1 + y * y))
    ) / (2.0 * math.pi)


def front_face_vf_closed(dist: float, z: float, side: float) -> float:
    """The crate's face toward the body (x = side/2, y in [-side/2, side/2], z in [0, side]), by superposition."""
    c = dist - side / 2.0
    half = side / 2.0
    if z >= side:  # the element is above the face: the strip from 0 to z minus the empty strip from side to z
        return 2.0 * (_rect_parallel_corner(half, z, c) - _rect_parallel_corner(half, z - side, c))
    return 2.0 * (_rect_parallel_corner(half, side - z, c) + _rect_parallel_corner(half, z, c))


def faces_vf_quadrature(dist: float, z: float, side: float, n: int = 600) -> tuple[float, float]:
    """(front, top) view factors by midpoint quadrature. Side faces are edge-on or facing away from the body."""
    half = side / 2.0
    u = -half + (np.arange(n) + 0.5) * (side / n)
    w = (np.arange(n) + 0.5) * (side / n)
    da = (side / n) ** 2
    # front face: points (half, y, zf), normal +x
    yy, zf = np.meshgrid(u, w, indexing="ij")
    rx, ry, rz = dist - half, -yy, z - zf
    s2 = rx * rx + ry * ry + rz * rz
    cos_s = rx / np.sqrt(s2)
    f_front = float(np.sum(cos_s * cos_s / (math.pi * s2)) * da)  # target cos equals surface cos here
    # top face: points (x, y, side), normal +z
    xx, yy2 = np.meshgrid(u, u, indexing="ij")
    rx, ry, rz = dist - xx, -yy2, z - side
    s2 = rx * rx + ry * ry + rz * rz
    s = np.sqrt(s2)
    cos_s, cos_t = rz / s, rx / s
    ok = (cos_s > 0.0) & (cos_t > 0.0)
    f_top = float(np.sum(np.where(ok, cos_s * cos_t / (math.pi * s2), 0.0)) * da)
    return f_front, f_top


def ember_emission(t_c: float) -> float:
    """Net emissive power of a char face to 20 degC surroundings, kW/m^2."""
    t, ta = t_c + 273.15, C.T_AMB_C + 273.15
    return C.EPS_CHAR * C.SIGMA * (t**4 - ta**4) / 1000.0


def ember_point(dist: float, z: float, side: float, e_kw: float) -> float:
    """Far-field Lambertian approximation: each face as a point at its centre, E A cos1 cos2 / (pi R^2)."""
    half = side / 2.0
    a = side * side
    rx, rz = dist - half, z - half
    r2 = rx * rx + rz * rz
    front = e_kw * a * (rx / math.sqrt(r2)) ** 2 / (math.pi * r2)
    rx, rz = dist, z - side
    r2 = rx * rx + rz * rz
    top = e_kw * a * max(rz, 0.0) / math.sqrt(r2) * rx / math.sqrt(r2) / (math.pi * r2) if rz > 0 else 0.0
    return front + top
