#!/usr/bin/env python3
import argparse, json, math, os, re, shutil, subprocess, wave, zipfile
from pathlib import Path
import numpy as np
from faster_whisper import WhisperModel

def run(cmd):
    print("RUN:", " ".join(str(x) for x in cmd)[:250],flush=True)
    subprocess.run([str(x) for x in cmd], check=True)

def ass_t(t):
    t=max(0.,t);h=int(t//3600);m=int(t//60)%60
    return f"{h}:{m:02d}:{t%60:05.2f}"

def ass_word(w):
    return w.replace("\\","").replace("{","(").replace("}",")").replace("\n"," ")

def make_ass(words,start,end,path):
    all_words=[w for w in words if w["start"]<end and w["end"]>start]
    groups=[];group=[]
    for w in all_words:
        if group and (len(group)>=5 or w["start"]-group[-1]["end"]>0.7):
            groups.append(group);group=[]
        group.append(w)
    if group:groups.append(group)
    head="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,70,&H00FFFFFF,&H0000FFFF,&H00000000,&H8A000000,1,0,0,0,100,100,0,0,1,5,1,2,48,48,405,1
Style: Brand,DejaVu Sans,38,&H00FFFFFF,&H00FFFFFF,&H00000000,&H70000000,1,0,0,0,100,100,0,0,1,2,1,8,35,35,180,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events=[f"Dialogue: 0,0:00:00.00,{ass_t(end-start)},Brand,,0,0,0,,TWITCH: FANTIK_69"]
    for g in groups:
        for i,w in enumerate(g):
            a=max(start,w["start"])-start
            b=min(end,w["end"])-start
            if b<=a:continue
            ss=[]
            for j,x in enumerate(g):
                ss.append((r"{\c&H0000FFFF&}" if j==i else r"{\c&H00FFFFFF&}")+ass_word(x["word"]))
            events.append(f"Dialogue: 0,{ass_t(a)},{ass_t(b)},Caption,,0,0,0,,{' '.join(ss)}")
    path.write_text(head+"\n".join(events)+"\n",encoding="utf-8-sig")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--url",default="https://m.twitch.tv/videos/2936145096")
    args=p.parse_args()
    root=Path("fantik69_result")
    root.mkdir(exist_ok=True)
    run(["yt-dlp","--no-playlist","--no-part","-S","res:360","--retries","10","--fragment-retries","10","--merge-output-format","mp4","-o",str(root/"vod.%(ext)s"),args.url])
    src=next(p for p in root.glob("vod.*") if p.suffix.lower() in (".mp4",".mkv",".webm"))
    print("Downloaded source:",src,src.stat().st_size)
    metadata=json.loads(subprocess.check_output(["ffprobe","-v","quiet","-print_format","json","-show_format",str(src)]))
    duration=float(metadata["format"]["duration"])
    wav=root/"audio.wav"
    run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",src,"-vn","-ac","1","-ar","16000","-c:a","pcm_s16le",wav])
    # Use direct float32 audio arrays to avoid Python 3.14 / PyAV metadata_errors incompatibility.
    with wave.open(str(wav),"rb") as w:
        sr=w.getframerate()
        rms=[]
        while True:
            buf=w.readframes(sr)
            if not buf:break
            a=np.frombuffer(buf,dtype="<i2").astype(np.float32)/32768
            rms.append(float(np.sqrt(np.mean(a*a))) if len(a) else 0.0)
    rms=np.asarray(rms)
    med=float(np.median(rms[rms>0])) if np.any(rms>0) else .01
    length=26.0
    pre=[]
    for st in np.arange(5,max(6,duration-length),5):
        vol=rms[int(st):min(len(rms),int(st+length))]
        if len(vol)<10:continue
        peak=float(np.percentile(vol,88)/(med+.003))
        avg=float(np.mean(vol)/(med+.003))
        dynamic=float(np.std(vol)/(med+.003))
        score=min(peak,5)*2.0+min(avg,4)*1.4+min(dynamic,4)*1.7
        pre.append(dict(start=float(st),end=float(st+length),energy=score))
    # Exclude every previously delivered clip, including prior alternative outputs.
    already_used=[75,485,1555,1765,2690,3485,3760]
    pre=[c for c in pre if all(abs(c["start"]-old)>=80 for old in already_used)]
    pre.sort(key=lambda x:x["energy"],reverse=True)
    shortlist=[]
    for c in pre:
        if all(abs(c["start"]-q["start"])>=65 for q in shortlist):
            shortlist.append(c)
        if len(shortlist)>=22:break
    print("Candidate moments",len(shortlist),"duration",duration,flush=True)
    model=WhisperModel("tiny",device="cpu",compute_type="int8",cpu_threads=4)
    terms=re.compile(r"(ахах|хаха|хех|ору|рофл|пизд|бл[яе]|еб[аё]|жест|угар|треш|ёбан|смеш|офиг|аху|капец|ниху|что за|кек)")
    with wave.open(str(wav),"rb") as w:
        for index,c in enumerate(shortlist):
            w.setpos(max(0,int(c["start"]*sr)))
            buf=w.readframes(int(length*sr))
            audio=np.frombuffer(buf,dtype="<i2").astype(np.float32)/32768.0
            if len(audio)<sr*8:continue
            try:
                segments,_=model.transcribe(audio,language="ru",beam_size=3,word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
                words=[]
                for seg in segments:
                    for token in seg.words or []:
                        if token.start is not None and token.end is not None and token.word.strip():
                            words.append(dict(start=float(c["start"]+token.start),end=float(c["start"]+token.end),word=token.word.strip()))
                phrase=" ".join(x["word"].lower() for x in words)
                cues=len(terms.findall(phrase))
                c["score"]=c["energy"]*.32+min(cues,9)*2.7+min(len(words),60)*.13+min(phrase.count("?"),3)*.7
                c["preview"]=phrase[:220]
                c["words"]=words
                print("Candidate",index+1,"/",len(shortlist),"time",c["start"],"words",len(words),"score",round(c["score"],2),flush=True)
            except Exception as err:
                print("Transcription candidate failed",c["start"],repr(err),flush=True)
                c["score"]=-1
    del model
    shortlisted=[c for c in shortlist if c.get("score",-1)>0 and len(c.get("words",[]))>=8]
    shortlisted.sort(key=lambda c:c["score"],reverse=True)
    picked=[]
    for c in shortlisted:
        if all(c["start"]>p["end"]+60 or c["end"]<p["start"]-60 for p in picked):
            picked.append(c)
            if len(picked)==4:break
    if len(picked)<4:
        for c in shortlisted:
            if c not in picked and all(c["start"]>p["end"]+8 or c["end"]<p["start"]-8 for p in picked):
                picked.append(c)
                if len(picked)==4:break
    if len(picked)<4:raise RuntimeError("Found fewer than 4 speech moments.")
    picked.sort(key=lambda c:c["start"])
    words=[x for c in picked for x in c["words"]]
    (root/"selected_moments.json").write_text(json.dumps([dict(start=c["start"],end=c["end"],score=c["score"],preview=c["preview"]) for c in picked],ensure_ascii=False,indent=2),encoding="utf-8")
    clips=root/"clips";clips.mkdir(exist_ok=True)
    for i,c in enumerate(picked,1):
        st,en=c["start"],c["end"]
        ass=clips/f"fantik69_{i:02}.ass"
        make_ass(words,st,en,ass)
        dest=clips/f"fantik69_{i:02}.mp4"
        filt=("[0:v]split=2[bg][fg];"
              "[bg]scale=360:640:force_original_aspect_ratio=increase,crop=360:640,gblur=sigma=8,scale=1080:1920[blur];"
              "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[front];"
              "[blur][front]overlay=(W-w)/2:(H-h)/2[tmp];"
              "[tmp]ass="+str(ass.resolve()).replace("\\","\\\\").replace(":","\\:")+"[v]")
        run(["ffmpeg","-hide_banner","-loglevel","error","-stats","-y","-ss",st,"-i",src,"-t",en-st,
             "-filter_complex",filt,"-map","[v]","-map","0:a:0?","-r","30","-c:v","libx264","-preset","ultrafast","-crf","25","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-movflags","+faststart",dest])
        print("CLIP",i,dest,dest.stat().st_size)
    with zipfile.ZipFile(root/"Fantik69_4_EXTRA_NEW_captioned.mp4s.zip","w",zipfile.ZIP_DEFLATED,compresslevel=0) as f:
        for vid in clips.glob("*.mp4"):
            f.write(vid,arcname=vid.name)
    print("FINISHED!",root/"Fantik69_4_NEW_captioned.mp4s.zip")
if __name__=="__main__":main()
