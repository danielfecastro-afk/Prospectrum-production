import sys, subprocess, numpy as np
SR=16000; H=160; N=1024
x=np.frombuffer(subprocess.run(['ffmpeg','-nostdin','-v','error','-i',sys.argv[1],'-ac','1','-ar',str(SR),'-f','f32le','-'],capture_output=True).stdout,dtype=np.float32)
nf=(len(x)-N)//H
w=np.hanning(N)
fr=np.lib.stride_tricks.as_strided(x,(nf,N),(x.strides[0]*H,x.strides[0]))
S=np.log1p(100*np.abs(np.fft.rfft(fr*w,axis=1))[:,5:200])
fl=np.maximum(S[1:]-S[:-1],0).sum(1); fl=np.concatenate([[0],fl])
rms=20*np.log10(np.sqrt((fr**2).mean(1))+1e-6)
# peak pick
k=np.convolve(fl,np.ones(15)/15,'same')
on=[]
for i in range(3,nf-3):
    if fl[i]==fl[i-3:i+4].max() and fl[i]>k[i]*1.5+5 and rms[i+3]>-40:
        if not on or i-on[-1]>12: on.append(i)
np.save(sys.argv[2], np.array(on)*H/SR)
