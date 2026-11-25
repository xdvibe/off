from pathlib import Path
import subprocess,json,numpy as np
from faster_whisper import WhisperModel
BASE=Path("candidate_stories");BASE.mkdir(exist_ok=True)
clips=[
 ("22_chirik","https://www.twitch.tv/fantik_69/clip/StupidDarkPidgeonCoolStoryBro-uU2x7zOMJuF5I3De"),
 ("22_whatswrong","https://www.twitch.tv/fantik_69/clip/InspiringGoldenSnoodPrimeMe-m1i9iEnCj0TwNoFB"),
 ("22_chuvaki","https://www.twitch.tv/fantik_69/clip/BrainyStrongCakeStoneLightning-3WCVn2PtjhntEPDm"),
 ("22_ww","https://www.twitch.tv/fantik_69/clip/PeacefulBoringQueleaSuperVinlin-SlOcHpAT28YKtZbe"),
]
for name,url in clips:
 f=BASE/f"{name}.mp4"
 print("DOWNLOAD",name,flush=True)
 try:
  p=subprocess.run(["yt-dlp","--no-playlist","-S","res:720","--merge-output-format","mp4","--retries","5","-o",str(f),url],capture_output=True,text=True,timeout=130)
  print("FETCH_RES",name,p.returncode,p.stderr[-400:],flush=True)
 except Exception as e:
  print("FETCH_ERROR",name,repr(e),flush=True)
model=WhisperModel("small",device="cpu",compute_type="int8",cpu_threads=4)
for name,url in clips:
 f=BASE/f"{name}.mp4"
 if not f.exists():continue
 out=subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nk=1:nw=1",str(f)],text=True)
 duration=float(out.strip())
 print("DURATION",name,duration,flush=True)
 raw=subprocess.check_output(["ffmpeg","-v","error","-i",str(f),"-ar","16000","-ac","1","-vn","-f","f32le","-"],timeout=70)
 arr=np.frombuffer(raw,dtype=np.float32).copy()
 for segstart in np.arange(0,duration,11):
  seg=arr[int(segstart*16000):int(min(duration,segstart+14)*16000)]
  if len(seg)<16000*3:continue
  segments,_=model.transcribe(seg,language="ru",beam_size=4,vad_filter=True,condition_on_previous_text=False)
  sentence=" ".join(s.text.strip() for s in segments)
  print("SPEECH",name,round(float(segstart),1),sentence[:700],flush=True)
 for sec in [max(1,duration*.2), max(2,duration*.48),max(3,duration*.8)]:
  subprocess.run(["ffmpeg","-v","error","-y","-ss",str(sec),"-i",str(f),"-vf","scale=600:-2","-frames:v","1",str(BASE/f"{name}_{int(sec)}.jpg")])
print("DONE",flush=True)
