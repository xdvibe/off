from pathlib import Path
import subprocess, base64, json
P=Path("demo_choices");P.mkdir(exist_ok=True)
sources=[
 ("NA_CHIRIKAL","https://www.twitch.tv/fantik_69/clip/StupidDarkPidgeonCoolStoryBro-uU2x7zOMJuF5I3De",None),
 ("CHO_S_NIM","https://www.twitch.tv/fantik_69/clip/InspiringGoldenSnoodPrimeMe-m1i9iEnCj0TwNoFB",None),
 ("NOV21_TANKS","https://www.twitch.tv/videos/2936145096","*00:42:00-00:42:14"),
]
for name,url,sec in sources:
  path=P/(name+".mp4")
  cmd=["yt-dlp","--no-playlist","--merge-output-format","mp4","-S","res:720","--retries","5","-o",str(path)]
  if sec:cmd.extend(["--download-sections",sec])
  cmd.append(url)
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
  print("DOWNLOADED",name,p.returncode,path.stat().st_size if path.exists() else 0,p.stderr[-400:],flush=True)
  if not path.exists():continue
  for sec in (2.5,6.5,10.):
    image=P/f"{name}_{str(sec).replace('.','_')}.jpg"
    subprocess.run(["ffmpeg","-v","error","-y","-ss",str(sec),"-i",str(path),"-frames:v","1","-vf","scale=320:-2","-q:v","7",str(image)],capture_output=True)
    if image.exists():
      b64=base64.b64encode(image.read_bytes()).decode()
      print("PREVIEW_B64",name,sec,b64,flush=True)
print("END",flush=True)
