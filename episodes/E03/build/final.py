import json, os, subprocess, sys
S=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); W=f'{S}/work'
J=json.load(open(f'{W}/timeline.json')); segs=J['segs']; TL=J['tl']
sched=json.load(open(f'{W}/ov_sched.json'))
out=sys.argv[1]
with open(f'{W}/segs.txt','w') as f:
    for i in range(len(segs)): f.write(f"file '{W}/segs/s{i:03d}.mp4'\n")
inputs=['-f','concat','-safe','0','-i',f'{W}/segs.txt','-i',f'{W}/mix_final.wav']
fc=[]; last='0:v'
for k,(name,t0) in enumerate(sched.items()):
    idx=k+2
    inputs+=['-framerate','24','-i',f'{W}/ov/{name}/%04d.png']
    t0f=round(t0*24)/24
    fc.append(f"[{idx}:v]format=rgba,setpts=PTS+{t0f:.5f}/TB[o{k}]")
    fc.append(f"[{last}][o{k}]overlay=eof_action=pass:format=auto[b{k}]"); last=f'b{k}'
fc.append(f"[{last}]ass={W}/karaoke.ass:fontsdir={S}/fonts,format=yuv420p[v]")
cmd=['ffmpeg','-nostdin','-v','error','-stats','-y',*inputs,'-filter_complex',';'.join(fc),'-map','[v]','-map','1:a',
     '-c:v','libx264','-crf','18','-preset','medium','-profile:v','high','-pix_fmt','yuv420p','-r','24',
     '-c:a','aac','-b:a','320k','-ar','48000','-movflags','+faststart','-t',f"{TL['TOTAL']:.4f}",out]
subprocess.run(cmd,check=True)
