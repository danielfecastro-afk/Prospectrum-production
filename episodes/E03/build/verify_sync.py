import json, os, subprocess, math
import numpy as np
S=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); W=f'{S}/work'
J=json.load(open(f'{W}/timeline.json')); segs=J['segs']
K=max(1920/1284,1080/716)
w,h=192,108
def frames(path, vf, ss=None, n=None):
    cmd=['ffmpeg','-nostdin','-v','error']
    if ss is not None: cmd+=['-ss',f'{ss:.4f}']
    cmd+=['-i',path,'-vf',vf,'-f','rawvideo','-pix_fmt','gray']
    if n: cmd+=['-frames:v',str(n)]
    a=np.frombuffer(subprocess.run(cmd+['-'],capture_output=True).stdout,np.uint8).astype(np.float32)
    a=a.reshape(-1,h,w)[:, :80, :]   # top 74% (exclude karaoke)
    a=a-a.mean(axis=(1,2),keepdims=True); a/= a.std(axis=(1,2),keepdims=True)+1e-6
    return a
rows=[]
groups={}
for i,s in enumerate(segs):
    if s.get('sung'):
        key=(s['clip'],round(s['anchor'],3)); groups.setdefault(key,[]).append((i,s))
for (clip,anchor),lst in groups.items():
    s=lst[0][1]
    # source frames at native rate, same zoom/crop/flip as each piece
    errs=[]
    for i,sg in lst:
        z=sg['zoom']; Wd=math.ceil(1284*K*z/2)*2; Hd=math.ceil(716*K*z/2)*2
        vf=f"scale={Wd}:{Hd},crop=1920:1080,{'hflip,' if sg['flip'] else ''}scale={w}:{h}"
        src=frames(f'{S}/dl/{clip}.mp4',vf)
        sfps=30 if src.shape[0]>int(sg.get('n',0)) and clip not in () else 30
        r=subprocess.run(['ffprobe','-v','error','-select_streams','v','-show_entries','stream=r_frame_rate','-of','csv=p=0',f'{S}/dl/{clip}.mp4'],capture_output=True,text=True).stdout.strip()
        sfps=eval(r)
        dur=sg['m1']-sg['m0']
        for frac in (0.2,0.5,0.8):
            t=sg['m0']+dur*frac
            fr=round(t*24)/24
            m=frames(f'{W}/master.mp4',f'scale={w}:{h}',ss=fr,n=1)[0]
            song_t=sg['song_a']+(fr-sg['m0'])
            exp_src=song_t-anchor
            if exp_src> (src.shape[0]-1)/sfps: continue   # freeze tail
            d=((src-m)**2).mean(axis=(1,2))
            k=int(d.argmin())
            errs.append((k/sfps-exp_src)*1000)
    errs=np.array(errs)
    rows.append((clip,anchor,s['song_a'],len(errs),errs.mean(),np.abs(errs).max()))
print(f"{'clip':5s} {'anchor':>8s} {'song_in':>8s} {'n':>2s} {'mean_ms':>8s} {'max_ms':>7s}")
for r in rows: print(f"{r[0]:5s} {r[1]:8.3f} {r[2]:8.2f} {r[3]:2d} {r[4]:8.1f} {r[5]:7.1f}")
