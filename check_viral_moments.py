#!/usr/bin/env python3
import subprocess,json,os
from pathlib import Path
import numpy as np
from faster_whisper import WhisperModel
from PIL import Image,ImageDraw
root=Path("moment_candidates");root.mkdir(exist_ok=True)
clips=[
("CHUVACHKI","https://www.twitch.tv/fantik_69/clip/BrainyStrongCakeStoneLightning-3WCVn2PtjhntEPDm"),
("WW","https://www.twitch.tv/fantik_69/clip/PeacefulBoringQueleaSuperVinlin-SlOcHpAT28YKtZbe")
]
model=WhisperModel("base",device="cpu",compute_type="int8",cpu_threads=4)
results=[]
for name,url in clips:
    f=root/(name+".mp4")
    p=subprocess.run(["yt-dlp","--no-playlist","-S","res:720","--merge-output-format","mp4","-o",str(f),url],text=True,capture_output=True,timeout=160)
    print("DOWNLOAD",name,p.returncode,p.stderr[-600:],flush=True)
    if not f.exists():continue
    dur=float(subprocess.check_output(["ffprobe","-v","quiet","-show_entries","format=duration","-of","default=nk=1:nw=1",str(f)],text=True))
    arr=np.frombuffer(subprocess.check_output(["ffmpeg","-v","error","-i",str(f),"-vn","-ac","1","-ar","16000","-f","f32le","-"]),dtype=np.float32).copy()
    segments,_=model.transcribe(arr,language="ru",beam_size=4,word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
    words=[]
    for seg in segments:
        for w in seg.words or []:
            if w.start is not None and w.end is not None:
                words.append(dict(start=round(float(w.start),2),end=round(float(w.end),2),word=w.word.strip()))
    print("TRANSCRIPT",name," ".join(x['word'] for x in words),flush=True)
    meta=dict(name=name,url=url,duration=dur,words=words,video=f.name)
    results.append(meta)
    frames=[]
    for sec in range(2,int(dur),5):
       image=root/f"{name}_{sec:02}.jpg"
       subprocess.run(["ffmpeg","-v","error","-y","-ss",str(sec),"-i",str(f),"-frames:v","1","-vf","scale=480:-2",str(image)],capture_output=True)
       if image.exists():frames.append((sec,image))
    if frames:
       w,h=500,330
       sheet=Image.new("RGB",(w*4,h*((len(frames)+3)//4)),"#0d0e15")
       d=ImageDraw.Draw(sheet)
       for i,(sec,imgfile) in enumerate(frames):
          im=Image.open(imgfile).convert("RGB"); im.thumbnail((w-10,h-38))
          x=(i%4)*w+(w-im.width)//2;y=(i//4)*h+32
          sheet.paste(im,(x,y));d.text(((i%4)*w+10,(i//4)*h+9),f"{name}: {sec}s",fill="#ffffff")
       sheet.save(root/f"{name}_CONTACT.jpg")
(root/"metadata.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
print("RESULTS",len(results),flush=True)
