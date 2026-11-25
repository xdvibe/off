#!/usr/bin/env python3
import argparse,json,subprocess,re,math
from pathlib import Path
from faster_whisper import WhisperModel
p=argparse.ArgumentParser();p.add_argument("--date",required=True);args=p.parse_args()
sources={"2026-11-21":"2936145096","2026-11-22":"2937332065"}
vod=sources[args.date];P=Path("transcripts_full");P.mkdir(exist_ok=True)
f=P/f"{args.date}.mp4";a=P/f"{args.date}.wav"
def run(cmd):
 print("RUN",cmd[:7],flush=True);subprocess.run([str(x) for x in cmd],check=True)
run(["yt-dlp","--no-playlist","--no-part","-S","res:360","--retries","10","--fragment-retries","10","--merge-output-format","mp4","-o",str(f),f"https://www.twitch.tv/videos/{vod}"])
print("FILE",f.stat().st_size,flush=True)
run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(f),"-vn","-ar","16000","-ac","1","-c:a","pcm_s16le",str(a)])
print("AUDIO",a.stat().st_size,flush=True)
model=WhisperModel("base",device="cpu",compute_type="int8",cpu_threads=4)
import wave,numpy as np
with wave.open(str(a),"rb") as wf:
    raw=wf.readframes(wf.getnframes())
    audio=np.frombuffer(raw,dtype="<i2").astype(np.float32)/32768.0
segments,_=model.transcribe(audio,language="ru",beam_size=2,word_timestamps=False,vad_filter=True,condition_on_previous_text=False,temperature=0.0)
items=[]
for i,s in enumerate(segments):
 row={"start":round(s.start,2),"end":round(s.end,2),"text":s.text.strip()}
 items.append(row)
 if i%50==0: print("PROGRESS",i,round(s.end,1),s.text[:160],flush=True)
p=P/f"full_{args.date}.json"
p.write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding="utf-8")
# Windows of 25 seconds with top narrative phrases.  Filter weak conversational fillers and promos.
cues=["почему","представляешь","прикинь","вчера","сегодня","случил","сосед","в доме","знаешь","знаете","неожидан","смешно","ахах","смешно","пиздец","охуе","ахуе","ебат","бля","я в шоке","у меня","у него","как-то раз","рассказ","история","момент","показать","живет","живёт","прямо","не поверишь","в жизни","в реальности"]
ban=["тысяча в чат","пишите","разыгра","розыгрыш","следите","подпис","донат","чат рулетка"]
windows=[]
duration=items[-1]["end"] if items else 0
for st in range(0,int(duration),12):
 chunk=[s for s in items if s["end"]>st and s["start"]<st+27]
 if not chunk:continue
 phrase=" ".join(z["text"] for z in chunk);lo=phrase.lower()
 sc=sum(lo.count(c)*(3 if c in ["сосед","история","прикинь","вчера","не поверишь","в реальности"] else 1) for c in cues)
 sc-=sum(lo.count(c)*3 for c in ban)
 # Prefer coherent content length and turns.
 sc+=min(len(phrase.split())/15,6)
 windows.append({"start":st,"end":st+27,"score":round(sc,2),"text":phrase[:850]})
windows.sort(key=lambda x:x["score"],reverse=True)
(P/f"ranked_{args.date}.json").write_text(json.dumps(windows[:200],ensure_ascii=False,indent=2),encoding="utf-8")
for w in windows[:70]:
 print("RANK",args.date,w["start"],w["score"],w["text"][:280],flush=True)
print("DONE",args.date,len(items),duration,flush=True)
