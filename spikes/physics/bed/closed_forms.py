"""Closed-form checks quoted in bed.md (spike): char self-heating threshold, flame-return bound,
envelope loss at T_p, pilot face ignition time."""

import math

from constants import NOMINAL as p
from constants import SIGMA_SB as sb
from model import DH_CO, DH_CO2, rho_air
from scipy.optimize import brentq

T0 = p.t_amb


def q_ox(T, h, kinetics=True, arthur=True):
    ks = p.ks_a * math.exp(-p.ks_ta / T)
    res = (1 / (rho_air(T) * ks) if kinetics else 0.0) + p.cp_air / h
    fo2 = p.y_o2 / res
    r = 2500 * math.exp(-6240 / T) if arthur else 0.0
    f = r / (1 + r)
    s = (32 / 12.011) * (1 - f) + (16 / 12.011) * f
    return fo2 / s * (DH_CO2 * (1 - f) + DH_CO * f)


def draught_loss(T, h):
    """Interior char: convective draught loss to inlet air, net radiation ~0."""
    return h * (T - T0)


def self_heating_balance(T, h):
    return q_ox(T, h) - draught_loss(T, h)


print("char oxidation heat at T_p=380 C, h=25:", round(q_ox(p.t_p, 25) / 1e3, 2), "kW/m2")
for h in (15.0, 25.0):
    try:
        tstar = brentq(self_heating_balance, 700, 1400, args=(h,))
        print(f"interior char self-heating threshold (h={h}): {tstar - 273.15:.0f} C")
    except ValueError as e:
        print("no crossing", h, e)
    for kin, ar, lab in (
        (False, False, "spec 6d diffusion+CO2"),
        (True, True, "kinetics+Arthur"),
        (False, True, "diffusion+Arthur"),
    ):
        q = q_ox(1100.0, h, kin, ar)
        print(f"  {lab}: q_ox(827 C) = {q / 1e3:.1f} kW/m2")
print("flame-return stability bound L_g/(chi_r dH) =", round(p.l_g / (p.chi_r * p.dh_vol), 3))
loss_tp = p.eps * sb * (p.t_p**4 - T0**4) + p.h_env * (p.t_p - T0)
print(
    "bare-face loss at T_p:",
    round(loss_tp / 1e3, 2),
    "kW/m2 (so a 15.9 kW/m2 pilot has a",
    round(15.92 - loss_tp / 1e3, 1),
    "kW/m2 margin)",
)
krc = p.k_wood * p.rho_wood * p.c_wood
q = 2000 / (math.pi * 0.04)
print("thermally thick t_ig, no losses (spec's closed form):", round(math.pi / 4 * krc * (p.t_p - T0) ** 2 / q**2), "s")
