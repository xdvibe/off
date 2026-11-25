import subprocess, numpy as np, json
from pathlib import Path
from faster_whisper import WhisperModel
P=Path("samples")
clips=sorted(P.glob("*.mp4"))
model=WhisperModel("base",device="cpu",compute_type="int8",cpu_threads=4)
all=[]
for idx,f in enumerate(clips):
 raw=subprocess.check_output(["ffmpeg","-v","error","-i",str(f),"-vn","-ac","1","-ar","16000","-f","f32le","-"])
 audio=np.frombuffer(raw,dtype=np.float32).copy()
 segments,info=model.transcribe(audio,language="ru",beam_size=4,word_timestamps=True,condition_on_previous_text=False,vad_filter=True)
 words=[]
 for seg in segments:
  for w in seg.words or []:
   if w.start is not None and w.end is not None:
    words.append({"start":float(w.start),"end":float(w.end),"word":w.word.strip()})
 phrase=" ".join(x["word"] for x in words)
 entry={"file":f.name,"transcript":phrase,"words":words}
 all.append(entry)
 print("TRANSCRIPT",idx+1,len(clips),f.name,phrase[:2000],flush=True)
Path("transcripts.json").write_text(json.dumps(all,ensure_ascii=False,indent=2),encoding="utf-8")
