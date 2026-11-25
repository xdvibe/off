import subprocess,json,requests
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np
from faster_whisper import WhisperModel
P=Path('historic_candidates');P.mkdir(exist_ok=True)
r=requests.post('https://gql.twitch.tv/gql',headers={'Client-ID':'kimne78kx3ncx6brgo4mv6wki5h1ko','User-Agent':'Mozilla/5.0'},json={'query':'query { user(login: "fantik_69") { clips(first:100,criteria:{period:ALL_TIME,sort:VIEWS_DESC}) { edges { node { id title createdAt viewCount durationSeconds url } } } } }'},timeout=25)
r.raise_for_status()
a=[x['node'] for x in r.json()['data']['user']['clips']['edges']]
titles=['лучший полёт стрима','побег','помог чем смог','умер','здравствуйте глеб борисович','100к донат','пока клава','У ФАНТИКА ЗАВЕЛИСЬ ПРИЗРАКИ??????','фантик умер в прямом эфире пожуй говна']
asr=WhisperModel('base',device='cpu',compute_type='int8',cpu_threads=4)
all=[]
for i,title in enumerate(titles):
 match=next((x for x in a if x['title']==title),None)
 if match is None:print('MISSING',title,flush=True);continue
 v=match;file=P/f'moment_{i+1:02}.mp4'
 print('FETCH',i+1,title,v['url'],flush=True)
 z=subprocess.run(['yt-dlp','--no-playlist','--retries','4','-S','res:720','--merge-output-format','mp4','-o',str(file),v['url']],capture_output=True,text=True,timeout=180)
 if not file.exists() or file.stat().st_size<20000:
  print('FETCH_FAILED',title,z.stderr[-600:],flush=True);continue
 frames=[]
 for k,f in enumerate([.12,.38,.63,.86]):
  seconds=max(.15,float(v['durationSeconds'])*f)
  im=P/f'moment_{i+1:02}_f{k}.jpg'
  subprocess.run(['ffmpeg','-v','error','-y','-ss',str(seconds),'-i',str(file),'-frames:v','1','-vf','scale=450:-2',str(im)],capture_output=True)
  if im.exists():frames.append(im.name)
 try:
  raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(file),'-vn','-ac','1','-ar','16000','-f','f32le','-'])
  samples=np.frombuffer(raw,dtype=np.float32).copy()
  segs,_=asr.transcribe(samples,language='ru',beam_size=3,word_timestamps=True,vad_filter=True)
  words=[dict(start=round(float(w.start),2),end=round(float(w.end),2),word=w.word.strip()) for s in segs for w in s.words or [] if w.start is not None and w.end is not None and w.word.strip()]
 except Exception as ex:
  print('TRANSCRIPTION_FAIL',title,repr(ex),flush=True);words=[]
 record=dict(filename=file.name,title=title,url=v['url'],createdAt=v['createdAt'],duration=v['durationSeconds'],views=v['viewCount'],frames=frames,words=words,transcript=' '.join(w['word'] for w in words))
 all.append(record); print('DONE',title,record['transcript'][:350],flush=True)
(P/'metadata.json').write_text(json.dumps(all,ensure_ascii=False,indent=2))
W,H=480,300
contact=Image.new('RGB',(W*4,H*len(all)),'#0e0f18');d=ImageDraw.Draw(contact)
for i,r in enumerate(all):
 for k,fn in enumerate(r['frames']):
  im=Image.open(P/fn).convert('RGB');im.thumbnail((W-20,H-55))
  contact.paste(im,(W*k+(W-im.width)//2,i*H+42))
  d.text((W*k+8,i*H+10),r['title'][:29]+f" [{k+1}]",fill='white')
contact.save(P/'CONTACT.jpg',quality=85)
print('DONE_TOTAL',len(all),flush=True)
