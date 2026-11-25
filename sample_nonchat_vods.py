from pathlib import Path
import json,subprocess,shlex
import PIL.Image as I
from PIL import ImageDraw,ImageFont
P=Path("nonchat_sample");P.mkdir(exist_ok=True)
vods=[("SLAY_17NOV","2931409944",[180,900,1700,2500,3300,4500]),("GAZY_21NOV","2936145096",[220,1500,3000])]
rows=[]
def stamp(s):
 h=s//3600;m=(s%3600)//60;ss=s%60
 return f"{h:02d}:{m:02d}:{ss:02d}"
for nick,vid,times in vods:
 for n,ss in enumerate(times,1):
  tag=f"{nick}_{n:02}"
  fn=P/(tag+".mp4")
  cmd=["yt-dlp","--no-playlist","--download-sections",f"*{stamp(ss)}-{stamp(ss+11)}","-S","res:360","--merge-output-format","mp4","-o",str(fn),f"https://www.twitch.tv/videos/{vid}"]
  print("DOWNLOAD",tag,stamp(ss),flush=True)
  r=subprocess.run(cmd,text=True,capture_output=True,timeout=180)
  print("RESULT",tag,r.returncode,r.stderr[-600:],flush=True)
  if not fn.exists() or fn.stat().st_size<25000:continue
  img=P/(tag+".jpg")
  ff=["ffmpeg","-y","-loglevel","error","-ss","3","-i",str(fn),"-frames:v","1","-vf","scale=500:-2",str(img)]
  subprocess.run(ff,check=False)
  if img.exists():
   rows.append(dict(tag=tag,time=ss,video=str(fn),image=str(img),size=fn.stat().st_size))
   print("OK",tag,flush=True)
(Path("nonchat_sample/metadata.json")).write_text(json.dumps(rows,ensure_ascii=False,indent=2))
if rows:
 import math
 w,h=550,360
 sheet=I.new("RGB",(w*3,h*math.ceil(len(rows)/3)),"#11121a")
 draw=ImageDraw.Draw(sheet)
 for i,r in enumerate(rows):
  im=I.open(r["image"]).convert("RGB")
  im.thumbnail((540,305))
  x=(i%3)*w+(w-im.width)//2
  y=(i//3)*h+45
  sheet.paste(im,(x,y))
  draw.text(((i%3)*w+16,(i//3)*h+12),r["tag"]+" @ "+stamp(r["time"]),fill="#ffffff")
 sheet.save("nonchat_sample/CONTACT.jpg",quality=90)
print("DONE",len(rows),flush=True)
