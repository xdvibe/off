#!/usr/bin/env python3
"""One Fantik69 approval sample, 9:16, with a focused subject and streamer reaction."""
from pathlib import Path
import json, subprocess, re
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from faster_whisper import WhisperModel

ROOT=Path("client_demo"); ROOT.mkdir(exist_ok=True)
SRC=Path("demo_choices/NOV21_TANKS.mp4")
if not SRC.is_file():
    raise FileNotFoundError(SRC)
DURATION=9.4
def run(cmd):
    print("RUN"," ".join(map(str,cmd))[:300],flush=True)
    subprocess.run([str(x) for x in cmd],check=True)
def font(px):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]:
        if Path(p).exists(): return ImageFont.truetype(p,px)
    return ImageFont.load_default()
def center(d,txt,y,f,fill,stroke=(0,0,0,255),sw=5):
    bb=d.textbbox((0,0),txt,font=f,stroke_width=sw)
    x=int((1080-(bb[2]-bb[0]))/2-bb[0])
    d.text((x,y),txt,font=f,fill=fill,stroke_width=sw,stroke_fill=stroke)

overlay=Image.new("RGBA",(1080,1920),(0,0,0,0))
d=ImageDraw.Draw(overlay)
center(d,"ЧТО У НЕГО",113,font(77),(255,255,255,255),sw=6)
center(d,"НА ГОЛОВЕ?!",207,font(77),(255,255,255,255),sw=6)
# Small reference-style streamer badge, not a giant banner.
d.rounded_rectangle((273,1690,807,1766),radius=8,fill=(145,71,255,246))
center(d,"TWITCH : FANTIK_69",1699,font(45),(255,255,255,255),stroke=(62,24,100,230),sw=2)
overlay.save(ROOT/"graphics.png")

# Actual transcript for timed caption. Do not invent text when recognition is uncertain.
model=WhisperModel("base",device="cpu",compute_type="int8",cpu_threads=4)
audio=np.frombuffer(subprocess.check_output(["ffmpeg","-v","error","-i",str(SRC),"-vn","-ar","16000","-ac","1","-f","f32le","-"],timeout=30),dtype=np.float32).copy()
segs,_=model.transcribe(audio,language="ru",beam_size=4,word_timestamps=True,condition_on_previous_text=False)
words=[]
for s in segs:
    for w in (s.words or []):
        if w.start is not None and w.end is not None and w.word.strip():
            words.append({"start":round(float(w.start),2),"end":round(float(w.end),2),"word":w.word.strip()})
print("ASR"," ".join(w["word"] for w in words),flush=True)
(ROOT/"transcript.json").write_text(json.dumps(words,ensure_ascii=False,indent=2))
caption_start,caption_end=0,0
for i in range(len(words)-1):
    if re.sub(r"\W","",words[i]["word"].lower()) in ("это","эта") and re.sub(r"\W","",words[i+1]["word"].lower()) in ("что","чё","че"):
        caption_start=max(0,words[i]["start"]-.6)
        caption_end=min(DURATION,words[i+1]["end"]+.2)
        break
caption=Image.new("RGBA",(1080,1920),(0,0,0,0))
d=ImageDraw.Draw(caption)
center(d,"А ЭТО ЧТО?!",1812,font(67),(255,220,12,255),stroke=(5,5,7,255),sw=6)
caption.save(ROOT/"caption.png")
print("CAPTION_INTERVAL",caption_start,caption_end,flush=True)
vf=(
 "[0:v]scale=1280:720,split=3[bg][main][face];"
 "[bg]scale=360:640:force_original_aspect_ratio=increase,crop=360:640,gblur=sigma=15,scale=1080:1920[blur];"
 "[main]crop=680:430:300:110,scale=1000:632,setsar=1[scene];"
 "[face]crop=280:205:990:510,scale=720:540,setsar=1[streamer];"
 "[blur][scene]overlay=40:390[tmp1];"
 "[tmp1][streamer]overlay=180:1120[tmp2];"
 "[tmp2][1:v]overlay=0:0[tmp3];"
 "[tmp3][2:v]overlay=0:0:enable='between(t,"+str(caption_start)+","+str(caption_end)+")'[v]"
)
out=ROOT/"Fantik69_DEMO_FOR_CLIENT.mp4"
run(["ffmpeg","-y","-hide_banner","-loglevel","error","-ss",4.0,"-i",SRC,
     "-loop","1","-i",ROOT/"graphics.png",
     "-loop","1","-i",ROOT/"caption.png",
     "-t",DURATION,"-filter_complex",vf,"-map","[v]","-map","0:a:0?",
     "-r","30","-c:v","libx264","-preset","veryfast","-crf","21",
     "-pix_fmt","yuv420p","-c:a","aac","-b:a","160k",
     "-movflags","+faststart",out])
info=json.loads(subprocess.check_output(["ffprobe","-v","quiet","-of","json","-show_format","-show_streams",out]))
print("OUTPUT",out.stat().st_size,info["format"]["duration"],
      [(s.get("codec_type"),s.get("width"),s.get("height")) for s in info["streams"]],flush=True)
# Expose representative frames in logs as compact base64 for visual QA, and save them as artifacts.
import base64
for t in [1.5,5.0,8.3]:
    still=ROOT/f"proof_{str(t).replace('.','_')}.jpg"
    run(["ffmpeg","-y","-v","error","-ss",str(t),"-i",out,"-frames:v","1","-vf","scale=360:-2","-q:v","7",still])
    print("PROOF_JPEG",t,base64.b64encode(still.read_bytes()).decode(),flush=True)
print("SAMPLE_READY",flush=True)
