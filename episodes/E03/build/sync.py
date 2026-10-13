import sys, subprocess, numpy as np
from scipy.signal import fftconvolve
SR=8000
def load(p, ss=None, t=None):
    cmd=['ffmpeg','-nostdin','-v','error']
    if ss is not None: cmd+=['-ss',str(ss)]
    if t is not None: cmd+=['-t',str(t)]
    cmd+=['-i',p,'-ac','1','-ar',str(SR),'-f','f32le','-']
    return np.frombuffer(subprocess.run(cmd,capture_output=True).stdout,dtype=np.float32)
ref=load(sys.argv[1]); 
for clip in sys.argv[2:]:
    a=load(clip)
    if len(a)==0: print(clip,'noaudio'); continue
    a=a-a.mean()
    c=fftconvolve(ref, a[::-1], mode='valid')
    # normalize by local energy of ref
    e=np.sqrt(np.maximum(fftconvolve(ref**2, np.ones(len(a)), mode="valid"),0))+1e-3
    n=c/(e*np.linalg.norm(a))
    idx=np.argsort(n)[::-1]
    peaks=[]
    for i in idx:
        if all(abs(i-p)>SR*1.0 for p in peaks): peaks.append(i)
        if len(peaks)==4: break
    print(clip.split('/')[-1], ' '.join(f'{p/SR:7.3f}({n[p]:.2f})' for p in peaks), f'dur={len(a)/SR:.2f}')
