from pathlib import Path
import subprocess,numpy as np,json
from faster_whisper import WhisperModel
P=Path("samples")
names=["candidate_01.mp4","candidate_07.mp4","candidate_08.mp4","candidate_09.mp4"]
model=WhisperModel("small",device="cpu",compute_type="int8",cpu_threads=4)
result={}
for f in names:
 raw=subprocess.check_output(["ffmpeg","-v","error","-i",str(P/f),"-vn","-ar","16000","-ac","1","-f","f32le","-"])
 ar=np.frombuffer(raw,dtype=np.float32).copy()
 segments,_=model.transcribe(ar,language="ru",beam_size=4,word_timestamps=True,condition_on_previous_text=False,vad_filter=True)
 words=[]
 for seg in segments:
  for w in seg.words or []:
   if w.start is not None and w.end is not None and w.word.strip():
    words.append(dict(start=float(w.start),end=float(w.end),word=w.word.strip()))
 result[f]={"words":words,"transcript":" ".join(w["word"] for w in words)}
 print(f,result[f]["transcript"],flush=True)
Path("transcript_best.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
