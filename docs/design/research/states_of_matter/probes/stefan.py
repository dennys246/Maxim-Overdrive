"""One-phase Stefan (Neumann) problem with the explicit enthalpy method: melted mass vs 2*lam*sqrt(alpha t).
Ice-like slab at T_m initially, wall at x=0 held at T_w > T_m (Dirichlet half-cell conductance). Nondimensional."""
import math, numpy as np
from scipy.optimize import brentq
from scipy.special import erf
rho=c=k=1.0; Lat=2.0; Tm=0.0; Tw=1.0; alpha=k/(rho*c)
Ste=c*(Tw-Tm)/Lat
lam=brentq(lambda l: math.sqrt(math.pi)*l*math.exp(l*l)*erf(l)-Ste, 1e-6, 5)
def run(n, t_end=0.5, Lx=2.0, cfl=0.25):
    dx=Lx/n; dt=cfl*dx*dx/alpha; steps=int(math.ceil(t_end/dt)); dt=t_end/steps
    H=np.zeros(n)  # H=0: solid at Tm; H in [0, rho L]: mushy at Tm; above: liquid
    def T(H): return Tm+np.maximum(H-rho*Lat,0)/(rho*c)
    for _ in range(steps):
        Tc=T(H); f=k*(Tc[1:]-Tc[:-1])/dx
        d=np.zeros(n); d[:-1]+=f; d[1:]-=f; d[0]+=k*(Tw-Tc[0])/(dx/2)
        H+=dt*d/dx
    melted=np.clip(H/(rho*Lat),0,1).sum()*dx  # liquid volume = sum phi dx
    # energy-consistent front: subtract sensible heat stored in liquid
    return melted
X=2*lam*math.sqrt(alpha*0.5)
print('lambda',lam,'X_exact',X)
prev=None
for n in (20,40,80,160,320,640):
    e=abs(run(n)-X); s=f'n={n:4d} dx={2/n:.5f} err={e:.3e}'
    if prev: s+=f'  p={math.log(prev/e,2):.2f}'
    print(s); prev=e
