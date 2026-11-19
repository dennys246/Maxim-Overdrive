"""1-D probes: why thresholded cell-mean burning diverges across dx, and what converges.
Slab of wood, x in [0, L]; heat enters at x=0. Insulated far side. Explicit FV like heat.py."""
import math, numpy as np
rho, cp, k = 600.0, 1700.0, 0.15
L = 0.6
T0 = 20.0

def ignition_cellmean(dx, q=50e3, Tig=350.0, tmax=3000.0):
    """Surface flux q W/m2 into the first cell; ignition = first cell's mean T reaches Tig."""
    n = int(round(L / dx)); T = np.full(n, T0); a = k / (rho * cp)
    dt = 0.4 * dx * dx / a; dt = min(dt, 0.05); t = 0.0
    while t < tmax:
        f = k * (T[1:] - T[:-1]) / dx
        dT = np.zeros(n); dT[:-1] += f; dT[1:] -= f; dT[0] += q
        T += dt * dT / (rho * cp * dx); t += dt
        if T[0] >= Tig: return t
    return math.inf

def thick_closed_form(q=50e3, Tig=350.0):
    return math.pi / 4 * k * rho * cp * (Tig - T0) ** 2 / q**2

def volumetric(dx, model, P=1.0e5, R=0.3, t_end=180.0):
    """Game-like volumetric fire: P W/m2 spread by overlap over the *solid/fuel* inside x<R.
    model 'threshold': today's thermal_degrade + destroy at integrity 0, renormalising over survivors.
    model 'enthalpy': enthalpy H per cell; pyrolysis isothermal at Tp with heat of gasification Lg;
                      integrity = fuel mass fraction; weights by remaining fuel mass (continuous)."""
    n = int(round(L / dx)); edges = np.arange(n + 1) * dx
    ov = np.clip(np.minimum(edges[1:], R) - edges[:-1], 0, None) / dx
    a = k / (rho * cp); dt = min(0.4 * dx * dx / a, 0.05); t = 0.0
    T = np.full(n, T0); integ = np.ones(n); alive = np.ones(n, bool)
    Tp, Lg = 350.0, 1.8e6
    H = rho * cp * (T - T0)            # J/m3 sensible, fuel-mass weighted below
    Hp = rho * cp * (Tp - T0)
    while t < t_end - 1e-12:
        if model == 'threshold':
            w = ov * alive
            if w.sum() == 0: break
            src = P * w / (w.sum() * dx)          # W/m3
            kk = np.where(alive, k, 0.026); rc = np.where(alive, rho * cp, 1.2 * 1005)
            kf = 2 * kk[1:] * kk[:-1] / (kk[1:] + kk[:-1])
            f = kf * (T[1:] - T[:-1]) / dx
            dT = np.zeros(n); dT[:-1] += f; dT[1:] -= f
            T += dt * (dT / dx + src) / rc
            hot = alive & (T > 250)
            integ[hot] -= 0.01 * dt * (T[hot] - 250) / 100
            alive &= integ > 0; integ[~alive] = 0
        else:
            w = ov * integ
            if w.sum() <= 1e-12: break
            src = P * w / (w.sum() * dx)
            # T from H: sensible below Hp; plateau at Tp while fuel gasifies (mass-weighted rho*cp)
            m = integ; rcm = rho * cp * np.maximum(m, 1e-9)
            Tcell = T0 + np.minimum(H, Hp * np.maximum(m, 1e-9)) / rcm
            kk = k * np.ones(n)
            f = k * (Tcell[1:] - Tcell[:-1]) / dx
            dH = np.zeros(n); dH[:-1] += f; dH[1:] -= f
            H += dt * (dH / dx + src)
            # energy above the sensible cap of the remaining fuel gasifies fuel at Lg (+ its sensible heat leaves with it)
            cap = Hp * m
            excess = np.maximum(H - cap, 0.0)
            dm = np.minimum(excess / (rho * (Lg + cp * (Tp - T0))), m)
            m_new = m - dm
            H -= dm * rho * (Lg + cp * (Tp - T0))
            integ = m_new; T = Tcell
        t += dt
    return float(integ.mean())

if __name__ == '__main__':
    print('thermally thick ignition closed form t_ig =', round(thick_closed_form(), 2), 's')
    for dx in (0.2, 0.1, 0.05, 0.025, 0.0125, 0.00625, 0.003125):
        print(f'dx={dx:<9} cell-mean ignition t = {ignition_cellmean(dx):9.1f} s')
    for model in ('threshold', 'enthalpy'):
        for t_end in (60.0, 120.0, 180.0):
            r = [volumetric(dx, model, t_end=t_end) for dx in (0.2, 0.1, 0.05, 0.025)]
            print(model, t_end, ' '.join(f'{v:.3f}' for v in r))
