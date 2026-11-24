#!/usr/bin/env python3
"""New 22 November Fantik69 VOD: four non-repeating narrative hooks and shorts."""
from pathlib import Path
import argparse, json, os, re, subprocess, zipfile, wave
import numpy as np
from faster_whisper import WhisperModel

P=Path("fantik69_nov22");P.mkdir(exist_ok=True)
URL="https://www.twitch.tv/videos/2937332065"

def run(*args):
    print("RUN",str(args)[:300],flush=True)
    subprocess.run([str(a) for a in args],check=True)

def ast(t):
    t=max(t,0);return f"{int(t//3600)}:{int(t//60)%60:02d}:{t%60:05.2f}"

def esc(x):
    return str(x).replace("\\","").replace("{","(").replace("}",")").replace("\n"," ")

def score_hook(t):
    x=t.lower()
    hits=sum(x.count(w) for w in ["ахах","хаха","я в шоке","серьезно","серьёзно","ебан","бляд","пизд","нихуя","что за","охуе","почему","прикинь","аху","ору","сука","саксофон"])
    return min(8,hits)

def choose_title(text,idx):
    x=text.lower()
    if "саксоф" in x:return "САКСОФОНИСТ УСТРОИЛ ШОУ"
    if "песня" in x or "поёт" in x:return "НА СВИДАНИИ НАЧАЛИ ПЕТЬ"
    if "свидан" in x:return "ВОТ ТАКОЕ СВИДАНИЕ!"
    if "девушк" in x:return "ФАНТИК И ДЕВУШКА НА СТРИМЕ"
    if "жен" in x or "парен" in x:return "НЕОЖИДАННЫЙ РАЗГОВОР"
    if "ахах" in x or "хаха" in x:return "ФАНТИК НЕ СДЕРЖАЛ СМЕХ"
    if "бляд" in x or "нихуя" in x:return "ФАНТИК НЕ ОЖИДАЛ ТАКОГО"
    return ["НЕОЖИДАННЫЙ МОМЕНТ НА СТРИМЕ","РАЗГОВОР ПОШЁЛ НЕ ПО ПЛАНУ","ФАНТИК В ШОКЕ ОТ ПРОИСХОДЯЩЕГО","ЭТО СЛУЧИЛОСЬ В ПРЯМОМ ЭФИРЕ"][idx%4]

def create_ass(words,st,en,path,head):
    # Safe top title, purple brand plate and per-word highlighted Russian subtitles.
    pre="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,DejaVu Sans,66,&H00FFFFFF,&H00FFFFFF,&H00000000,&H75000000,1,0,0,0,100,100,0,0,1,5,2,8,70,70,130,1
Style: Brand,DejaVu Sans,68,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,&H006D20B0,1,0,0,0,100,100,0,0,3,16,0,2,50,50,255,1
Style: Caption,DejaVu Sans,67,&H00FFFFFF,&H0000FFFF,&H00000000,&H7F000000,1,0,0,0,100,100,0,0,1,5,2,2,100,100,430,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # Make top line breaks at max 20 chars.
    parts=head.split();line1="";line2=""
    for word in parts:
        if len(line1)+len(word)+1<=23 or not line1:line1=(line1+" "+word).strip()
        else:line2=(line2+" "+word).strip()
    title=esc(line1)+(r"\N"+esc(line2) if line2 else "")
    events=[f"Dialogue: 3,0:00:00.00,{ast(en-st)},Hook,,0,0,0,,{title}",
            f"Dialogue: 3,0:00:00.00,{ast(en-st)},Brand,,0,0,0,,TWITCH : FANTIK_69"]
    accepted=[w for w in words if w["end"]>st and w["start"]<en and w["word"].strip()]
    groups=[];g=[]
    for w in accepted:
        n=sum(len(t["word"])+1 for t in g)
        if g and (len(g)>=4 or n+len(w["word"])+1>24 or w["start"]-g[-1]["end"]>0.8):
            groups.append(g);g=[]
        g.append(w)
    if g:groups.append(g)
    for g in groups:
        for i,w in enumerate(g):
            a=max(0,w["start"]-st);b=min(en-st,w["end"]-st)
            if b<=a:continue
            line=" ".join((r"{\c&H0000FFFF&}" if i==j else r"{\c&H00FFFFFF&}")+esc(t["word"]) for j,t in enumerate(g))
            events.append(f"Dialogue: 4,{ast(a)},{ast(b)},Caption,,0,0,0,,{line}")
    path.write_text(pre+"\n".join(events)+"\n",encoding="utf-8-sig")

def main():
    print("VIDEO",URL,flush=True)
    run("yt-dlp","--no-playlist","--no-part","-S","res:720","--retries","10","--fragment-retries","10","--merge-output-format","mp4","-o",str(P/"video.%(ext)s"),URL)
    sources=[f for f in P.glob("video.*") if f.suffix in [".mp4",".mkv",".webm"]]
    if not sources:raise RuntimeError("VOD did not download")
    src=sources[0]
    props=json.loads(subprocess.check_output(["ffprobe","-v","quiet","-show_format","-show_streams","-of","json",str(src)]))
    duration=float(props["format"]["duration"])
    print("VOD_DURATION",duration,"FILE",src.stat().st_size,flush=True)
    wav=P/"audio.wav"
    run("ffmpeg","-hide_banner","-loglevel","error","-y","-i",src,"-vn","-ac","1","-ar","16000","-c:a","pcm_s16le",wav)
    rms=[]
    with wave.open(str(wav),"rb") as w:
        while True:
            raw=w.readframes(16000)
            if not raw:break
            ar=np.frombuffer(raw,dtype="<i2").astype(np.float32)/32768
            rms.append(float(np.sqrt(np.mean(ar**2))) if len(ar) else 0)
    rms=np.asarray(rms)
    median=float(np.median(rms[rms>0])) if np.any(rms>0) else .01
    win=28.0
    candidates=[]
    for st in np.arange(0,max(1,duration-win),5):
        vol=rms[int(st):int(st+win)]
        if len(vol)<22:continue
        mean=float(np.mean(vol));v90=float(np.percentile(vol,90))
        variation=float(np.std(vol))
        z=min(7,v90/(median+.002))*2+min(5,mean/(median+.002))*1.2+min(5,variation/(median+.002))
        # Intro deserves a chance; streamer specifically asked for standout first moments.
        if st<120:z+=1.5
        candidates.append({"start":float(st),"end":float(st+win),"energy":float(z)})
    candidates.sort(key=lambda c:c["energy"],reverse=True)
    sample=[]
    # Ensure look at the beginning as saxophonist may appear near opening.
    for st in [8.,35.,60.,100.]:
        if st+win<=duration:sample.append({"start":st,"end":st+win,"energy":median*5})
    for c in candidates:
        if all(abs(c["start"]-v["start"])>=70 for v in sample):
            sample.append(c)
            if len(sample)>=34:break
    print("TRANSCRIBE_CANDIDATES",len(sample),flush=True)
    model=WhisperModel("small",device="cpu",compute_type="int8",cpu_threads=4)
    with wave.open(str(wav),"rb") as w:
        for i,c in enumerate(sample):
            w.setpos(int(c["start"]*16000))
            raw=w.readframes(int(win*16000))
            ar=np.frombuffer(raw,dtype="<i2").astype(np.float32)/32768
            try:
                segs,_=model.transcribe(ar,language="ru",beam_size=3,word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
                words=[]
                for s in segs:
                    for v in s.words or []:
                        if v.start is not None and v.end is not None and v.word.strip():
                            words.append({"start":c["start"]+float(v.start),"end":c["start"]+float(v.end),"word":v.word.strip()})
                transcript=" ".join(w["word"] for w in words)
                c["words"]=words
                c["transcript"]=transcript
                c["score"]=c["energy"]*.42+score_hook(transcript)*3.6+min(65,len(words))*.15
                if len(words)<13:c["score"]=-100
                if c["start"]<120 and "саксоф" in transcript.lower():c["score"]+=12
                print("CANDIDATE",i,round(c["start"],1),round(c["score"],1),transcript[:290],flush=True)
            except Exception as e:
                print("TRANSCRIBE_ERROR",repr(e),flush=True);c["score"]=-100
    del model
    ranked=sorted(sample,key=lambda c:c["score"],reverse=True)
    selected=[]
    for c in ranked:
        if c["score"]<0:continue
        if all(abs(c["start"]-x["start"])>100 for x in selected):
            selected.append(c)
            if len(selected)>=4:break
    if len(selected)!=4:raise RuntimeError("Could not find four distinct speech-driven moments")
    selected.sort(key=lambda c:c["start"])
    shots=P/"clips";shots.mkdir(exist_ok=True)
    index=[]
    for i,c in enumerate(selected,1):
        title=choose_title(c["transcript"],i-1)
        st,en=c["start"],c["end"]
        index.append({"number":i,"start":st,"end":en,"title":title,"transcript":c["transcript"],"score":round(c["score"],1)})
        sub=shots/f"Fantik69_NEW_{i:02}.ass"
        create_ass(c["words"],st,en,sub,title)
        dest=shots/f"Fantik69_NEW_{i:02}.mp4"
        vf=("[0:v]split=2[bg][fg];"
            "[bg]scale=540:960:force_original_aspect_ratio=increase,crop=540:960,gblur=sigma=12,scale=1080:1920[blur];"
            "[fg]scale=1440:-2,crop=1080:ih[front];"
            "[blur][front]overlay=(W-w)/2:(H-h)/2[tmp];"
            "[tmp]ass="+str(sub.resolve()).replace(":","\\:")+"[v]")
        run("ffmpeg","-hide_banner","-loglevel","error","-stats","-y","-ss",st,"-i",src,"-t",en-st,
            "-filter_complex",vf,"-map","[v]","-map","0:a:0?","-r","30","-c:v","libx264","-preset","veryfast","-crf","23","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-movflags","+faststart",dest)
        print("EXPORTED",str(dest),dest.stat().st_size,flush=True)
        # two preview frames for human quality review
        for at in (5,17):
            run("ffmpeg","-hide_banner","-loglevel","error","-y","-ss",at,"-i",dest,"-frames:v","1","-vf","scale=360:-2",shots/f"preview_{i:02}_{at:02}.jpg")
    (P/"selected_moments.json").write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding="utf-8")
    with zipfile.ZipFile(P/"Fantik69_4_NEW_Nov22_subtitled.zip","w",compression=zipfile.ZIP_STORED) as z:
        for f in shots.glob("*.mp4"):z.write(f,f.name)
    print("SUCCESS",json.dumps(index,ensure_ascii=False)[:4000],flush=True)
if __name__=="__main__":main()
