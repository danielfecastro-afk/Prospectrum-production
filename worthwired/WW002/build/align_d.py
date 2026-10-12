import os, wave, json, sys
from pocketsphinx import Decoder, get_model_path
mp=get_model_path(); D=sys.argv[1]
T={'V1':"hey my friend no credit no problem come see me today",
   'V2':"no down payment doesn't matter just bring your license or your passport",
   'V3':"brand new cars from just four ninety nine a month",
   'V4':"and your first payment not for ninety days drive it home today"}
out={}
for k,t in T.items():
    d=Decoder(hmm=os.path.join(mp,'en-us/en-us'),dict=os.path.join(mp,'en-us/cmudict-en-us.dict'),loglevel='FATAL',samprate=16000)
    d.set_align_text(t)
    data=wave.open(os.path.join(D,k+'.wav')).readframes(10**9)
    d.start_utt(); d.process_raw(data,full_utt=True); d.end_utt()
    segs=[(s.word,s.start_frame/100,s.end_frame/100) for s in d.seg() if s.word not in('<s>','</s>','<sil>','(NULL)')]
    out[k]=segs; print(k,' '.join(f'{w}@{a:.2f}-{b:.2f}' for w,a,b in segs))
json.dump(out,open(os.path.join(D,'align_d.json'),'w'))
