#!/usr/bin/env python3
"""Revise four Fantik69 speed-dating shorts from ORIGINAL Twitch VOD.
Focus on speakers, remove weak starts/pauses, rerun Russian word-aligned subtitles.
"""
import json, math, os, re, subprocess, sys, wave, zipfile
from pathlib import Path
import numpy as np
import cv2
from faster_whisper import WhisperModel

URL="https://www.twitch.tv/videos/2937332065"
OUT=Path("Fantik69_quality_v2");OUT.mkdir(exist_ok=True)
RAW=OUT/"raw";RAW.mkdir(exist_ok=True)
CLIPS=OUT/"READY";CLIPS.mkdir(exist_ok=True)
MOMENTS=[
 {"start":623,"end":648,"title":"ФАНТИК НЕ МОЖЕТ ВКЛЮЧИТЬ ВЕБКУ?"},
 {"start":1960,"end":1988,"title":"СКИПНУЛ ИЗ-ЗА ЦВЕТА ВОЛОС?"},
 {"start":2340,"end":2368,"title":"«ТЫ СЛИШКОМ МИЛЫЙ»"},
 {"start":3470,"end":3498,"title":"ФАНТИК ЗАБРАЛ 1000 ₽"},
]

def run(*args, capture=False, allow_fail=False):
    print("RUN", " ".join(str(x) for x in args)[:320], flush=True)
    p=subprocess.run([str(x) for x in args],text=True,stdout=subprocess.PIPE if capture else None,stderr=subprocess.PIPE if capture else None)
    if p.returncode and not allow_fail:
        print("STDERR",(p.stderr or "")[-4000:],flush=True)
        raise RuntimeError(f"Command failed: {args[0]} {p.returncode}")
    return p

def probe(path):
    r=run("ffprobe","-v","error","-show_streams","-show_format","-of","json",path,capture=True)
    return json.loads(r.stdout)

def fmt(t):
    t=max(0,float(t));return f"{int(t//3600)}:{int(t//60)%60:02d}:{t%60:05.2f}"

def esc(s):
    return str(s).replace("\\","").replace("{","(").replace("}",")").replace("\n"," ").strip()

def make_subs(words, seconds, path, title):
    # Captions have max four words + 26 chars, highlighted word in yellow.
    head="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,DejaVu Sans,65,&H00FFFFFF,&H00FFFFFF,&H00000000,&H81000000,1,0,0,0,100,100,0,0,1,4,2,8,75,75,75,1
Style: Brand,DejaVu Sans,62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H81000000,1,0,0,0,100,100,0,0,1,2,0,2,60,60,342,1
Style: Captions,DejaVu Sans,66,&H00FFFFFF,&H0000FFFF,&H00000000,&H8D000000,1,0,0,0,100,100,0,0,1,5,1,2,85,85,92,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # Title split to two lines, no clipped top text.
    l1="";l2=""
    for word in title.split():
        if len(l1)+len(word)+1<=24: l1=(l1+" "+word).strip()
        else: l2=(l2+" "+word).strip()
    titletext=esc(l1)+(r"\N"+esc(l2) if l2 else "")
    lines=[f"Dialogue: 2,0:00:00.00,{fmt(seconds)},Hook,,0,0,0,,{titletext}",
           f"Dialogue: 3,0:00:00.00,{fmt(seconds)},Brand,,0,0,0,,TWITCH : FANTIK_69"]
    groups=[];g=[]
    for w in words:
        if not w["word"]:continue
        oldchars=sum(len(x["word"])+1 for x in g)
        if g and (len(g)>=4 or oldchars+len(w["word"])>26 or w["start"]-g[-1]["end"]>.8):
            groups.append(g);g=[]
        g.append(w)
    if g:groups.append(g)
    for g in groups:
        for i,w in enumerate(g):
            a=max(0,w["start"]); b=min(float(seconds),w["end"])
            if b<=a:continue
            colored=" ".join((r"{\c&H0000FFFF&}" if i==j else r"{\c&H00FFFFFF&}")+esc(v["word"]) for j,v in enumerate(g))
            lines.append(f"Dialogue: 4,{fmt(a)},{fmt(b)},Captions,,0,0,0,,{colored}")
    path.write_text(head+"\n".join(lines)+"\n",encoding="utf-8-sig")

def retrieve_segment(i,start,end):
    stem=RAW/f"segment{i:02}"
    old=[p for p in RAW.glob(f"segment{i:02}.*") if p.suffix.lower() in [".mp4",".mkv",".webm"]]
    if old:return old[0]
    begin=fmt(start).replace(".00",""); finish=fmt(end).replace(".00","")
    command=["yt-dlp","--no-playlist","--no-part","--download-sections",f"*{begin}-{finish}",
            "-S","res:720","--merge-output-format","mp4",
            "--retries","10","--fragment-retries","10",
            "-o",str(stem)+".%(ext)s",URL]
    run(*command)
    new=[p for p in RAW.glob(f"segment{i:02}.*") if p.suffix.lower() in [".mp4",".mkv",".webm"]]
    if not new:raise RuntimeError(f"Missing Twitch VOD segment #{i}")
    return new[0]

def shorten_silence_if_needed(src,number):
    if number!=3:return src
    det=run("ffmpeg","-hide_banner","-nostats","-i",src,"-af",
            "silencedetect=noise=-31dB:d=1.0","-f","null","-",capture=True,allow_fail=True)
    text=det.stderr or ""
    starts=[float(v) for v in re.findall(r"silence_start:\s*([\d.]+)",text)]
    ends=[float(v) for v in re.findall(r"silence_end:\s*([\d.]+)",text)]
    meta=probe(src);dur=float(meta["format"]["duration"])
    gaps=[(s,e) for s,e in zip(starts,ends) if e-s>1.15 and s>4 and e<dur-4]
    if not gaps:
        print("CLIP3_NO_SAFE_SILENCE_TO_REMOVE",flush=True);return src
    s,e=max(gaps,key=lambda x:x[1]-x[0])
    # Keep a 0.22s natural breath, omit only the middle of the gap.
    cut0=s+.13;cut1=e-.13
    target=RAW/"segment03_shortened.mp4"
    filt=(f"[0:v]trim=start=0:end={cut0},setpts=PTS-STARTPTS[v0];"
          f"[0:a]atrim=start=0:end={cut0},asetpts=PTS-STARTPTS[a0];"
          f"[0:v]trim=start={cut1}:end={dur},setpts=PTS-STARTPTS[v1];"
          f"[0:a]atrim=start={cut1}:end={dur},asetpts=PTS-STARTPTS[a1];"
          f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")
    run("ffmpeg","-hide_banner","-loglevel","error","-y","-i",src,"-filter_complex",filt,
        "-map","[v]","-map","[a]","-c:v","libx264","-preset","ultrafast","-crf","20","-c:a","aac","-b:a","160k",target)
    print("REMOVED_SILENCE",s,e,"RESULT",target,flush=True)
    return target

def analyze_face_panes(src,number):
    cap=cv2.VideoCapture(str(src));width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps=float(cap.get(cv2.CAP_PROP_FPS)) or 30;duration=(cap.get(cv2.CAP_PROP_FRAME_COUNT)/fps)
    face=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
    boxes=[]
    for sec in (4,8,12,17,22):
        cap.set(cv2.CAP_PROP_POS_MSEC,sec*1000)
        ok,frame=cap.read()
        if not ok:continue
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        gray=cv2.equalizeHist(gray)
        detected=face.detectMultiScale(gray,scaleFactor=1.08,minNeighbors=4,minSize=(30,30))
        for (x,y,w,h) in detected:
            boxes.append((x+w/2,y+h/2,w*h))
    cap.release()
    # Split speakers into left and right when possible.
    left=sorted([v for v in boxes if v[0]<width*.52],key=lambda v:v[2],reverse=True)
    right=sorted([v for v in boxes if v[0]>=width*.52],key=lambda v:v[2],reverse=True)
    centers=[
        (left[0][0],left[0][1]) if left else (width*.25,height*.45),
        (right[0][0],right[0][1]) if right else (width*.75,height*.45)
    ]
    print("FACE_DETECTION",number,{"w":width,"h":height,"count":len(boxes),"left":len(left),"right":len(right),"centers":centers},flush=True)
    return width,height,centers

def render(src,number,words,title):
    meta=probe(src);duration=float(meta["format"]["duration"])
    vs=next(x for x in meta["streams"] if x["codec_type"]=="video")
    width,height,centers=analyze_face_panes(src,number)
    # Two broad, cropped reaction panes from the original VOD for clips 1–3.
    # Wide windows preserve Discord speakers while giving their faces more screen space.
    cw=max(160,int(width*.49)//2*2)
    ch=max(140,int(cw*600/1080)//2*2)
    ch=min(ch,height//2*2)
    def pane(center):
        x=int(max(0,min(width-cw,center[0]-cw*.5)))
        y=int(max(0,min(height-ch,center[1]-ch*.40)))
        return f"crop={cw}:{ch}:{x}:{y},scale=1080:600:flags=lanczos"
    ass=CLIPS/f"Fantik69_REWORK_{number:02}.ass"
    make_subs(words,duration,ass,title)
    final=CLIPS/f"Fantik69_REWORK_{number:02}.mp4"
    if number==4:
        # Preserve wider streamer reaction, already strongest according to review.
        filt=("[0:v]split=2[bg][fg];"
              "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=26,eq=brightness=-0.16[blur];"
              "[fg]scale=1080:1120:force_original_aspect_ratio=increase,crop=1080:1120[main];"
              "[blur][main]overlay=0:295[tmp];")
    else:
        p1,p2=map(pane,centers)
        filt=("[0:v]split=3[bg][fg1][fg2];"
              "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=27,eq=brightness=-0.13[blur];"
              f"[fg1]{p1}[one];[fg2]{p2}[two];"
              "[blur][one]overlay=0:230[tmp0];"
              "[tmp0][two]overlay=0:844[tmp];")
    filt+=("[tmp]drawbox=x=170:y=1508:w=740:h=99:color=0x9146FF@0.96:t=fill,"
           "drawbox=x=170:y=1508:w=740:h=5:color=0xC1A1FF@0.9:t=fill[placed];"
           "[placed]ass="+str(ass.resolve()).replace("\\","\\\\").replace(":","\\:")+"[v]")
    run("ffmpeg","-hide_banner","-loglevel","error","-stats","-y","-i",src,"-filter_complex",filt,
        "-map","[v]","-map","0:a:0?","-r","30","-c:v","libx264","-preset","veryfast","-crf","22",
        "-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-movflags","+faststart",final)
    info=probe(final);v=next(s for s in info["streams"] if s["codec_type"]=="video")
    au=[s for s in info["streams"] if s["codec_type"]=="audio"]
    assert v["width"]==1080 and v["height"]==1920
    assert au and final.stat().st_size>100000
    assert 20<float(info["format"]["duration"])<35
    # screenshot preview in artifact
    for sec in [3,12]:
        run("ffmpeg","-hide_banner","-loglevel","error","-y","-ss",sec,"-i",final,
            "-frames:v","1","-vf","scale=405:-2",CLIPS/f"preview_{number:02}_{sec:02}.jpg")
    print("DONE_CLIP",number,"duration",info["format"]["duration"],"bytes",final.stat().st_size,flush=True)
    return final

def main():
    model=WhisperModel("small",device="cpu",compute_type="int8",cpu_threads=4)
    outputs=[]
    for number,c in enumerate(MOMENTS,1):
        src=retrieve_segment(number,c["start"],c["end"])
        src=shorten_silence_if_needed(src,number)
        audio=RAW/f"audio{number:02}.wav"
        run("ffmpeg","-hide_banner","-loglevel","error","-y","-i",src,"-vn","-ar","16000","-ac","1","-c:a","pcm_s16le",audio)
        with wave.open(str(audio),"rb") as w:
            raw=w.readframes(w.getnframes())
        a=np.frombuffer(raw,dtype="<i2").astype(np.float32)/32768
        segments,_=model.transcribe(a,language="ru",beam_size=5,word_timestamps=True,
           vad_filter=True,condition_on_previous_text=False,
           initial_prompt="Это русскоязычный стрим Fantik69, быстрые свидания. Вебка, Данька, Хитоми, волосы, скип, ты слишком милый, донат, тысяча рублей.")
        words=[]
        for s in segments:
            for w in s.words or []:
                if w.start is not None and w.end is not None and w.word.strip():
                    words.append({"start":float(w.start),"end":float(w.end),"word":w.word.strip()})
        if len(words)<7:raise RuntimeError(f"Too few subtitle words in clip {number}")
        print("TRANSCRIPT",number," ".join(w["word"] for w in words),flush=True)
        outputs.append(render(src,number,words,c["title"]))
    zipfile_path=OUT/"Fantik69_4_REWORKED_WEBKAM_SUBS.zip"
    with zipfile.ZipFile(zipfile_path,"w",compression=zipfile.ZIP_STORED) as z:
        for path in outputs:
            z.write(path,path.name)
    print("ALL_FOUR_COMPLETE",zipfile_path,zipfile_path.stat().st_size,flush=True)

if __name__=="__main__":main()
