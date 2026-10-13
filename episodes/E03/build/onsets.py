import sys, subprocess, numpy as np
SR=8000; H=80
x=np.frombuffer(subprocess.run(['ffmpeg','-nostdin','-v','error','-i',sys.argv[1],'-ac','1','-ar',str(SR),'-f','f32le','-'],capture_output=True).stdout,dtype=np.float32)
n=len(x)//H; e=20*np.log10(np.sqrt((x[:n*H].reshape(n,H)**2).mean(1))+1e-6)
thr=float(sys.argv[2]) if len(sys.argv)>2 else -35
on=e>thr
segs=[];s=None
for i,v in enumerate(on):
    if v and s is None: s=i
    if not v and s is not None:
        if i-s>=5: segs.append((s/100,i/100))
        s=None
# merge gaps <0.08
m=[]
for a,b in segs:
    if m and a-m[-1][1]<0.08: m[-1]=(m[-1][0],b)
    else: m.append((a,b))
print(' '.join(f'{a:.2f}-{b:.2f}' for a,b in m))
