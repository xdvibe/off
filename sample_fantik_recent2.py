#!/usr/bin/env python3
import json, subprocess, os, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from faster_whisper import WhisperModel

P=Path("recent2_samples")
P.mkdir(exist_ok=True)
SOURCES=[
 ("2026-11-22","2937332065",[210,390,870,1260,1620,2160,2670,3090,3720,4110]),
 ("2026-11-21","2936145096",[228,690,978,1278,1860,2136,2520,2880,3300,3600])
]
def clock(t): return f"{t//3600:02d}:{(t//60)%60:02d}:{t%60:02d}"
def run(a,timeout=180):
  p=subprocess.run([str(v) for v in a],text=True,capture_output=True,timeout=timeout)
  if p.returncode:print("ERROR",p.returncode,p.stderr[-1100:],flush=True)
  return p.returncode
items=[]
for date,vid,times in SOURCES:
 for k,st in enumerate(times,1):
  tag=f"{date}_{k:02d}"
  f=P/(tag+".mp4")
  print("SAMPLE",tag,clock(st),flush=True)
  rc=run(["yt-dlp","--no-playlist","--download-sections",f"*{clock(st)}-{clock(st+18)}",
          "-S","res:360","--merge-output-format","mp4","--retries","3","-o",str(f),
          f"https://www.twitch.tv/videos/{vid}"],timeout=180)
  if rc or not f.exists() or f.stat().st_size<50000: continue
  frames=[]
  for i,t in enumerate([3,11]):
   o=P/(tag+f"_{i}.jpg")
   run(["ffmpeg","-y","-v","error","-ss",str(t),"-i",str(f),"-vf","scale=420:-2","-frames:v","1",str(o)],timeout=30)
   if o.exists():frames.append(o.name)
  items.append(dict(tag=tag,source_date=date,source_vod_id=vid,source_start=st,path=f.name,frames=frames))
  print("SAVED",tag,f.stat().st_size,flush=True)
print("SAMPLED",len(items),flush=True)
# Transcription for ranking readable scenes.
model=WhisperModel("tiny",device="cpu",compute_type="int8",cpu_threads=4)
for item in items:
 f=P/item["path"]
 try:
  buf=subprocess.check_output(["ffmpeg","-v","error","-i",str(f),"-vn","-ac","1","-ar","16000","-f","f32le","-"],timeout=40)
  a=np.frombuffer(buf,dtype=np.float32).copy()
  segs,_=model.transcribe(a,language="ru",beam_size=2,word_timestamps=False,vad_filter=True,condition_on_previous_text=False)
  tr=" ".join(z.text.strip() for z in segs)
  item["transcript"]=tr
  item["words"]=len(tr.split())
  print("WORDS",item["tag"],tr[:420],flush=True)
 except Exception as e:
  item["transcript"]="";item["words"]=0
  print("TRANSCRIPTION_ERR",item["tag"],repr(e),flush=True)
del model
(P/"metadata.json").write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding="utf-8")
# Contact boards separated by source
for date,vid,times in SOURCES:
 sub=[x for x in items if x["source_date"]==date]
 w,h=440,290
 sheet=Image.new("RGB",(w*2,h*len(sub)),"#171822")
 draw=ImageDraw.Draw(sheet)
 for row,it in enumerate(sub):
  for c,fr in enumerate(it["frames"]):
   img=Image.open(P/fr).convert("RGB")
   img.thumbnail((w-8,h-42))
   sheet.paste(img,(w*c+(w-img.width)//2,h*row+35))
  draw.text((8,h*row+4),f'{it["tag"]} {clock(it["source_start"])} | {it.get("transcript","")[:55]}',fill="white")
 sheet.save(P/f"CONTACT_{date}.jpg",quality=85)
print("COMPLETE",flush=True)
