import json, re, sys, wave
from pocketsphinx import Decoder, get_model_path
import os
W = sys.argv[1]
mp = get_model_path()
dic = {}
for line in open(os.path.join(mp, 'en-us/cmudict-en-us.dict')):
    p = line.split()
    w = p[0]
    if '(' in w: continue
    dic[w] = ' '.join(p[1:])
EXTRA = {'worthwired': 'W ER TH W AY ER D', 'cfpb': 'S IY EH F P IY B IY', 'ftc': 'EH F T IY S IY',
         'u.s.': 'Y UW EH S', 'yo-yo': 'Y OW Y OW', 're-sign': 'R IY S AY N', 'used-car': 'Y UW Z D K AA R',
         'out-the-door': 'AW T DH AH D AO R', 'trade-ins': 'T R EY D IH N Z', 'trade-in': 'T R EY D IH N',
         'pre-approved': 'P R IY AH P R UW V D', 'twenty-six': 'T W EH N T IY S IH K S',
         'twenty-eight': 'T W EH N T IY EY T', 'twenty-one': 'T W EH N T IY W AH N',
         'twenty-two': 'T W EH N T IY T UW', 'twenty-five': 'T W EH N T IY F AY V',
         'twenty-three': 'T W EH N T IY TH R IY', 'twenty-four': 'T W EH N T IY F AO R',
         'sixty-nine': 'S IH K S T IY N AY N', 'forty-four': 'F AO R T IY F AO R', 'newcomers': 'N UW K AH M ER Z',
         'paperwork': 'P EY P ER W ER K', 'edmunds': 'EH D M AH N D Z', 'experian': 'EH K S P IH R IY AH N',
         "fitch's": 'F IH CH IH Z', 'markup': 'M AA R K AH P', 'overpriced': 'OW V ER P R AY S T', 'upfront': 'AH P F R AH N T',
         'playbook': 'P L EY B UH K', 'subprime': 'S AH B P R AY M'}
def tok(text):
    words = []
    for raw in text.split():
        w = raw.lower().strip('.,:;?!"()…').replace('...', '')
        w = w.strip('.,:;?!"')
        if raw.lower().startswith('u.s.'): w = 'u.s.'
        if not w: continue
        words.append((raw, w))
    return words
out = {}
for line in open(os.path.join(W, 'narration.txt')):
    key, text = line.rstrip('\n').split('|', 1)
    words = tok(text)
    d = Decoder(hmm=os.path.join(mp, 'en-us/en-us'), dict=os.path.join(mp, 'en-us/cmudict-en-us.dict'), loglevel='FATAL', samprate=16000)
    seq = []
    for i, (raw, w) in enumerate(words):
        if w in EXTRA:
            ww = 'qqz' + re.sub(r'[^a-z]', '', w)
            
            if d.lookup_word(ww) is None: d.add_word(ww, EXTRA[w], True)
            seq.append(ww)
        elif w in dic:
            seq.append(w)
        else:
            print('OOV', key, w, file=sys.stderr); seq.append(w)
    d.set_align_text(' '.join(seq))
    data = wave.open(os.path.join(W, 'narr', key + '.wav')).readframes(10**9)
    d.start_utt(); d.process_raw(data, full_utt=True); d.end_utt()
    segs = [(s.word, s.start_frame / 100, s.end_frame / 100) for s in d.seg() if s.word not in ('<s>', '</s>', '<sil>', '(NULL)')]
    if len(segs) != len(words):
        print('MISMATCH', key, len(segs), len(words), file=sys.stderr)
    out[key] = [{'w': words[i][0], 's': segs[i][1], 'e': segs[i][2]} for i in range(min(len(segs), len(words)))]
json.dump(out, open(os.path.join(W, 'align.json'), 'w'), indent=0)
for k, v in out.items():
    print(k, ' '.join(f"{x['w']}@{x['s']:.1f}" for x in v[:12]), '...', v[-1]['w'], v[-1]['e'])
