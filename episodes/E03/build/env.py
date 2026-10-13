import sys, subprocess, numpy as np
SR=8000; H=80  # 10ms
def load(p, ss=None, t=None):
    cmd=['ffmpeg','-nostdin','-v','error']
    if ss is not None: cmd+=['-ss',str(ss)]
    if t is not None: cmd+=['-t',str(t)]
    cmd+=['-i',p,'-ac','1','-ar',str(SR),'-f','f32le','-']
    return np.frombuffer(subprocess.run(cmd,capture_output=True).stdout,dtype=np.float32)
def env(x):
    n=len(x)//H; e=np.sqrt((x[:n*H].reshape(n,H)**2).mean(1)); e=np.log(e+1e-4); return e
ref=env(load(sys.argv[1]))
# args: name ss dur  center  window
for spec in sys.argv[2:]:
    ss,dur,center=map(float,spec.split(':'))
    q=env(load(sys.argv[1],ss,dur)); q=q-q.mean()
    best=None
    for off in np.arange(center-1.0,center+1.0,0.01):
        i=int(round(off*100)); r=ref[i:i+len(q)]; r=r-r.mean()
        c=(r*q).sum()/np.sqrt((r*r).sum()*(q*q).sum())
        if best is None or c>best[1]: best=(off,c)
    print(f'src {ss}+{dur} -> {best[0]:.2f} (corr {best[1]:.2f}) expected {center}')
