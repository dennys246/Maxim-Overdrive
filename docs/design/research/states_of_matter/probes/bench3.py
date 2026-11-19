import time, numpy as np
def best(f, n=5):
    f(); t=[]
    for _ in range(n):
        s=time.perf_counter(); f(); t.append(time.perf_counter()-s)
    return min(t)*1e3
rng=np.random.default_rng(0)
sh=(320,200,80)
mat=rng.integers(0,8,sh).astype(np.uint8)
rcs=rng.uniform(1e6,4e6,8); Tm=rng.uniform(0,1500,8); L=rng.uniform(1e8,2e9,8)
a=rcs[mat]; Hs=a*Tm[mat]; Ls=L[mat]; Tmc=Tm[mat]; inva=1/a
H=rng.uniform(0,6e9,sh)
T=np.empty(sh)
def cached():
    np.multiply(H,inva,out=T)
    m=H>Hs
    if m.any():
        T[m]=np.where(H[m]<Hs[m]+Ls[m], Tmc[m], Tmc[m]+(H[m]-Hs[m]-Ls[m])*inva[m])
print("cached T_of_H, 50% cells above solidus:", round(best(cached),1),"ms")
H2=np.minimum(H, Hs*0.99); H2.flat[::1000]=Hs.flat[::1000]*1.01
def sparse():
    np.multiply(H2,inva,out=T)
    m=H2>Hs
    idx=np.flatnonzero(m)
    if idx.size:
        h=H2.flat[idx]; hs=Hs.flat[idx]; T.flat[idx]=np.where(h<hs+Ls.flat[idx], Tmc.flat[idx], Tmc.flat[idx]+(h-hs-Ls.flat[idx])*inva.flat[idx])
print("cached T_of_H, 0.1% cells transitioning:", round(best(sparse),1),"ms")
print("float64 bytes/field at max:", np.prod(sh)*8/1e6,"MB")
