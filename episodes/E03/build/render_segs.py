import json, os, subprocess, sys, math
from concurrent.futures import ThreadPoolExecutor
S=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DL=f'{S}/dl'; OUT=f'{S}/work/segs'; os.makedirs(OUT,exist_ok=True)
J=json.load(open(f'{S}/work/timeline.json')); segs=J['segs']
FPS=24; K=max(1920/1284,1080/716)
ENC=['-c:v','libx264','-crf','12','-preset','fast','-pix_fmt','yuv420p','-r','24','-threads','2']

def vchain(inp, sg, src_in, n, label):
    z=sg.get('zoom',1.0); sp=sg.get('speed',1.0)
    W=math.ceil(1284*K*z/2)*2; H=math.ceil(716*K*z/2)*2
    warm=sg.get('warm',0.0)
    g=(f"eq=saturation=1.05,colorbalance=rs={0.015+warm:.3f}:bs={-0.015-warm:.3f}:"
       f"rm={0.02+warm:.3f}:bm={-0.02-warm:.3f}:rh={0.01+warm/2:.3f}:bh={-0.01-warm/2:.3f}")
    c=(f"[{inp}:v]trim=start={max(src_in,0):.4f},setpts=(PTS-STARTPTS)/{sp:.5f},fps=24,"
       f"tpad=stop_mode=clone:stop_duration=30,trim=end_frame={n},setpts=PTS-STARTPTS,"
       f"scale={W}:{H}:flags=lanczos,crop=1920:1080,")
    if sg.get('flip'): c+="hflip,"
    c+=g+",format=yuv420p,setsar=1"
    return c+f"[{label}]"

def exact_in(sg):
    # correct for frame rounding so source time tracks exact master time
    return sg['src_in'] + (sg['f0']/FPS - sg['m0'])*sg.get('speed',1.0)

def job(i):
    sg=segs[i]
    if sg.get('special'): return
    out=f'{OUT}/s{i:03d}.mp4'
    if os.path.exists(out) and '-f' not in sys.argv: return
    n=sg['n']; inputs=['-i',f"{DL}/{sg['clip']}.mp4"]
    fc=[vchain(0,sg,exact_in(sg),n,'v')]
    last='v'
    tr=sg.get('trans')
    if tr:
        pv=segs[i-1]; d=round(tr[1]*FPS)
        inputs+=['-i',f"{DL}/{pv['clip']}.mp4"]
        tail_in=exact_in(pv)+pv['n']/FPS*pv.get('speed',1.0)
        clipdur=float(subprocess.run(['ffprobe','-v','error','-select_streams','v','-show_entries','format=duration',
                                      '-of','csv=p=0',f"{DL}/{pv['clip']}.mp4"],capture_output=True,text=True).stdout)
        tail_in=min(tail_in, clipdur-0.1)   # past the end -> hold last frame (tpad clones it)
        fc.append(vchain(1,pv,tail_in,d,'t'))
        fc.append(f"[t][v]xfade=transition={tr[0]}:duration={d/FPS:.4f}:offset=0,trim=end_frame={n}[x]")
        last='x'
    fd=sg.get('fade')
    if fd:
        kind,st,du=fd
        f={'in':f'fade=t=in:st=0:d={du}','inwhite':f'fade=t=in:st=0:d={du}:color=white',
           'out':f'fade=t=out:st={st}:d={du}'}[kind]
        fc.append(f"[{last}]{f}[y]"); last='y'
    cmd=['ffmpeg','-nostdin','-v','error','-y',*inputs,'-filter_complex',';'.join(fc),'-map',f'[{last}]','-frames:v',str(n),*ENC,'-an',out]
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode: print(i,r.stderr[-2000:]); return
    print('ok',i,sg['clip'],flush=True)

idx=[int(a) for a in sys.argv[1:] if a.isdigit()] or range(len(segs))
with ThreadPoolExecutor(4) as ex: list(ex.map(job,idx))
