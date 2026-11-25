import subprocess,json,requests,io,math
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np
from faster_whisper import WhisperModel
P=Path('candidates_new');P.mkdir(exist_ok=True)
r=requests.post('https://gql.twitch.tv/gql',headers={'Client-ID':'kimne78kx3ncx6brgo4mv6wki5h1ko','User-Agent':'Mozilla/5.0'},json={'query':'query { user(login: "fantik_69") { clips(first:100,criteria:{period:LAST_MONTH,sort:VIEWS_DESC}) { edges { node { id title createdAt viewCount durationSeconds url } } } } }'},timeout=25)
r.raise_for_status()
clips=[e['node'] for e in r.json()['data']['user']['clips']['edges']]
titles=['НАЧИРИКАЛ','ЧУВАЧКИИИИИ','ЧО С НИМ','WW','разъебался в щепки','благодетель']
model=WhisperModel('base',device='cpu',compute_type='int8',cpu_threads=4)
results=[]
for i,t in enumerate(titles):
 found=[v for v in clips if v['title']==t]
 if not found:continue
 v=found[0]
 target=P/f'extra_{i+1:02}.mp4'
 print('DOWNLOADING',t,v['url'],flush=True)
 proc=subprocess.run(['yt-dlp','--no-playlist','--retries','3','-S','res:720','--merge-output-format','mp4','-o',str(target),v['url']],capture_output=True,text=True,timeout=180)
 if not target.exists() or target.stat().st_size<50000:
  print('DOWNLOAD_FAILED',t,proc.stderr[-800:],flush=True);continue
 frames=[]
 for j,timestamp in enumerate([max(1,int(v['durationSeconds']*.2)),max(1,int(v['durationSeconds']*.5)),max(1,int(v['durationSeconds']*.8))]):
  path=P/f'extra_{i+1:02}_{j+1}.jpg'
  subprocess.run(['ffmpeg','-y','-v','error','-ss',str(timestamp),'-i',str(target),'-frames:v','1','-vf','scale=480:-2',str(path)],capture_output=True)
  if path.exists():frames.append(path.name)
 raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(target),'-vn','-ac','1','-ar','16000','-f','f32le','-'])
 audio=np.frombuffer(raw,dtype=np.float32)
 try:
  segs,_=model.transcribe(audio,language='ru',beam_size=3,word_timestamps=True,vad_filter=True)
  words=[dict(start=round(float(w.start),2),end=round(float(w.end),2),word=w.word.strip()) for s in segs for w in s.words or [] if w.start is not None and w.end is not None and w.word.strip()]
 except Exception as ex:
  print('ASR_FAILED',repr(ex),flush=True);words=[]
 item=dict(filename=target.name,title=v['title'],id=v['id'],url=v['url'],duration=float(v['durationSeconds']),viewCount=v['viewCount'],frames=frames,words=words,transcript=' '.join(w['word'] for w in words))
 results.append(item)
 print('DONE',t,(' '.join(w['word'] for w in words))[:450],flush=True)
(P/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
W,H=520,340
image=Image.new('RGB',(W*3,H*len(results)),(11,13,21))
draw=ImageDraw.Draw(image)
for i,item in enumerate(results):
 for j,fn in enumerate(item['frames']):
  pic=Image.open(P/fn).convert('RGB')
  pic.thumbnail((W-20,H-65))
  x=j*W+(W-pic.width)//2
  y=i*H+43
  image.paste(pic,(x,y))
  draw.text((j*W+12,i*H+12),f"{item['title'][:26]}  {j+1} / {item['duration']:.0f}s",fill='white')
image.save(P/'CONTACT.jpg',quality=90)
print('ALL_DONE',len(results),flush=True)
