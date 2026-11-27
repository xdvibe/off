import json, subprocess, re, sys, math
from pathlib import Path
from datetime import datetime, timezone
import requests, numpy as np
from faster_whisper import WhisperModel
from PIL import Image, ImageDraw
P=Path("review");P.mkdir(exist_ok=True)
W=Path("work");W.mkdir(exist_ok=True)
def run(a):subprocess.run(list(map(str,a)),check=True)
def output(a):return subprocess.check_output(list(map(str,a)))
q='query { user(login:"fantik_69") { videos(first:10,type:ARCHIVE,sort:TIME) { edges { node { id title createdAt lengthSeconds } } } } }'
r=requests.post('https://gql.twitch.tv/gql',headers={'Client-ID':'kimne78kx3ncx6brgo4mv6wki5h1ko'},json={'query':q},timeout=35)
r.raise_for_status()
nodes=[x['node'] for x in r.json()['data']['user']['videos']['edges']]
print('VODS',json.dumps(nodes,ensure_ascii=False),flush=True)
matches=[v for v in nodes if v['createdAt'].startswith('2026-11-26') and 'МЕДЛЕННЫЕ СВИДАНИЯ' in v['title'].upper()]
if not matches:raise RuntimeError('Exact Nov 26 broadcast was not found; refusing to substitute older VOD')
vod=matches[0];(P/'source.json').write_text(json.dumps(vod,ensure_ascii=False,indent=2))
url='https://www.twitch.tv/videos/'+vod['id']
src=W/'vod.mp4'
run(['yt-dlp','--no-playlist','--no-part','-S','res:720','--retries','10','--fragment-retries','10','--concurrent-fragments','4','--merge-output-format','mp4','-o',src,url])
audio=np.frombuffer(output(['ffmpeg','-v','error','-i',src,'-vn','-ac','1','-ar','16000','-f','f32le','-']),dtype=np.float32).copy()
model=WhisperModel('tiny',device='cpu',compute_type='int8',cpu_threads=4)
segments,_=model.transcribe(audio,language='ru',beam_size=1,vad_filter=True,condition_on_previous_text=False)
rows=[]
for i,s in enumerate(segments):
    rows.append(dict(start=round(s.start,2),end=round(s.end,2),text=s.text.strip()))
    if i%80==0:print('ASR',i,s.end,s.text[:160],flush=True)
(P/'full_transcript.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
del model
topic=re.compile(r'слей|слэй|slay|номинац|стример|манер[аыу]|лева|л[её]о|ростик|бустер|братик|парадеевич|пят[её]рк|куертов|кореш|сасавот|майот|меллстрой|сода|дил[а-я]+|скандал|преми|известн|блогер|тикток|твич',re.I)
event=re.compile(r'обман|развод|наеб|кину[л]|подстав|украл|сломал|потерял|заплатил|заработал|миллион|тысяч|рубл|доллар|сосед|выгнал|увол|поссор|конфликт|спалил|оказал|признал|прикинь|представля|не поверишь|серь[её]зно|ахуе|охуе|в шоке|пиздец|ахах|хаха|смешно|угар|не может быть|как так|что за',re.I)
filler=re.compile(r'розыгрыш|тысяча в чат|плюс в чат|нажимаем|подписываемся|настройк|секундочку|слышно меня|проверка звука',re.I)
# Candidate scores are retrieval heuristics, not editorial 1–10 scores.
cand=[]
for i,s in enumerate(rows):
    for j in range(i,min(i+9,len(rows))):
        st=s['start'];en=rows[j]['end'];d=en-st
        if d>28:break
        if d<7:continue
        t=' '.join(x['text'] for x in rows[i:j+1])
        if len(t.split())<9:continue
        top=len(topic.findall(t));ev=len(event.findall(t));bad=len(filler.findall(t))
        if not top and not ev:continue
        score=top*3+ev*2+('?' in t)*1.2+bool(re.search(r'[.!?…]$',t))*1.5-bad*5
        score+=min(len(t.split())/12,3)
        cand.append((score,st,en,t))
cand.sort(reverse=True)
picks=[]
for c in cand:
    if all(abs(c[1]-p[1])>35 for p in picks):picks.append(c)
    if len(picks)>=24:break
model=WhisperModel('base',device='cpu',compute_type='int8',cpu_threads=4)
results=[]
for k,(score,st,en,t) in enumerate(picks,1):
    a=max(0,st-2);b=min(len(audio)/16000,en+3)
    segs,_=model.transcribe(audio[int(a*16000):int(b*16000)],language='ru',beam_size=3,word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
    words=[];phrases=[]
    for s in segs:
        phrases.append(dict(start=round(a+s.start,2),end=round(a+s.end,2),text=s.text.strip()))
        words.extend(dict(start=round(a+w.start,2),end=round(a+w.end,2),word=w.word) for w in s.words or [] if w.start is not None and w.end is not None)
    meta=dict(id=k,start=round(a,2),end=round(b,2),retrieval_score=round(score,2),phrases=phrases,words=words)
    results.append(meta)
    print('CANDIDATE',k,json.dumps({key:value for key,value in meta.items() if key!='words'},ensure_ascii=False),flush=True)
    # Preserve original layout for later manually chosen crops.
    run(['ffmpeg','-v','error','-y','-ss',a,'-i',src,'-t',b-a,'-vf','scale=1280:-2','-c:v','libx264','-preset','veryfast','-crf','21','-c:a','aac','-b:a','160k',P/f'candidate_{k:02}.mp4'])
    run(['ffmpeg','-v','error','-y','-ss',(b-a)/2,'-i',P/f'candidate_{k:02}.mp4','-frames:v','1','-vf','scale=640:-2',P/f'frame_{k:02}.jpg'])
    (P/'candidates.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('COMPLETE',len(results),flush=True)
