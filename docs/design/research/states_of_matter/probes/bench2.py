import time, numpy as np
def best(f, n=5):
    f(); t=[]
    for _ in range(n):
        s=time.perf_counter(); f(); t.append(time.perf_counter()-s)
    return min(t)*1e3
rng=np.random.default_rng(0)
for dx in (0.2,0.1,0.05):
    sh=(int(16/dx),int(10/dx),int(4/dx)); N=np.prod(sh)
    mat=rng.integers(0,8,sh).astype(np.uint8)
    # per-material: rho_cs (J/m3K solid), rho_cl, Tm, L (J/m3)
    rcs=rng.uniform(1e6,4e6,8); rcl=rcs*1.1; Tm=rng.uniform(0,1500,8); L=rng.uniform(1e8,2e9,8)
    H=rng.uniform(0,6e9,sh)
    def T_of_H():
        a=rcs[mat]; Hs=a*Tm[mat]; Hl=Hs+L[mat]
        T=np.where(H<Hs, H/a, np.where(H<Hl, Tm[mat], Tm[mat]+(H-Hl)/rcl[mat]))
        lf=np.clip((H-Hs)/L[mat],0,1)
        return T,lf
    t=best(T_of_H)
    # 2-phase via per-material table lookup (np.interp-style piecewise, K breakpoints) using searchsorted per material: skip
    # dirty-chunk mask: 16^3 chunk activity reduce
    c=int(round(1.0/dx))
    def chunk_active():
        T=H/2e6
        d=np.abs(T-20.0)>0.5
        s=(sh[0]//c,c,sh[1]//c,c,sh[2]//c,c)
        return d.reshape(s).any(axis=(1,3,5))
    tc=best(chunk_active)
    print(f"dx={dx} N={N:,} T_of_H={t:.1f}ms chunk_mask(1m)={tc:.1f}ms")
