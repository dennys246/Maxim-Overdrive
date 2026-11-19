import time, numpy as np
from scipy import ndimage
def best(f, n=5):
    f(); t=[]
    for _ in range(n):
        s=time.perf_counter(); f(); t.append(time.perf_counter()-s)
    return min(t)*1e3
for dx in (0.2,0.1,0.05):
    sh=(int(16/dx),int(10/dx),int(4/dx))
    solid=np.zeros(sh,bool)
    # outer walls 0.4 m thick, 3 interior walls, a floor
    w=max(2,int(round(0.4/dx)))
    solid[:w]=solid[-w:]=True; solid[:,:w]=solid[:,-w:]=True; solid[:,:,:w]=True
    for x in (4,8,12):
        i=int(x/dx); solid[i:i+w]=True
    air=~solid
    tl=best(lambda: ndimage.label(air))
    lab,n=ndimage.label(air)
    # per-room reductions: bincount of a field over labels
    f=np.random.default_rng(0).random(sh)
    tb=best(lambda: np.bincount(lab.ravel(), weights=f.ravel(), minlength=n+1))
    # face-open-area between rooms along x: count faces where labels differ & both air
    def faces():
        a=lab[:-1]; b=lab[1:]; m=(a!=b)&(a>0)&(b>0)
        return np.unique(np.stack([a[m],b[m]]),axis=1)
    tf=best(faces)
    # local relabel of a 2m chunk
    ch=air[:int(2/dx),:int(2/dx),:]
    tc=best(lambda: ndimage.label(ch))
    # 2x2x2 coarsen to 0.2m (open volume fraction)
    r=int(round(0.2/dx))
    def coarsen():
        return air.reshape(sh[0]//r,r,sh[1]//r,r,sh[2]//r,r).mean(axis=(1,3,5))
    tco=best(coarsen)
    print(f"dx={dx} cells={air.size:,} rooms={n} label={tl:.1f}ms bincount={tb:.1f}ms faces_x={tf:.1f}ms chunk_label={tc:.2f}ms coarsen_to_0.2={tco:.1f}ms")
