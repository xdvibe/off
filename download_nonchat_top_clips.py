from pathlib import Path
import json,subprocess,io,math
from PIL import Image,ImageDraw
P=Path("top_clip_media");P.mkdir(exist_ok=True)
j=json.loads(Path("input/clips.json").read_text())
clips=[e["node"] for e in j["data"]["user"]["clips"]["edges"]]
names=["бамболеейлоааа","ДРЭЙ МАФИЯ","иууу","ХАХАХАХАХХА","босс сказал босс сделал","энкьюэрчичи","захожу в клуб забираю двух (для эдита)","Ы","упал"]
selection=[next(x for x in clips if x["title"]==t) for t in names]
saved=[]
for i,x in enumerate(selection):
 fn=P/f"candidate_{i+1:02}.mp4"
 print("FETCH",i+1,x["title"],x["url"],flush=True)
 r=subprocess.run(["yt-dlp","--no-playlist","-S","res:720","--merge-output-format","mp4","--retries","3","-o",str(fn),x["url"]],capture_output=True,text=True,timeout=200)
 print("FETCH_RESULT",r.returncode,r.stderr[-600:],flush=True)
 if not fn.exists() or fn.stat().st_size<100000:continue
 duration=float(x["durationSeconds"])
 for n,t in enumerate([max(.2,duration*.2),max(.5,duration*.5),max(1,duration*.8)]):
  fr=P/f"frame_{i+1:02}_{n+1}.jpg"
  subprocess.run(["ffmpeg","-y","-v","error","-ss",str(t),"-i",str(fn),"-frames:v","1","-vf","scale=480:-2",str(fr)],check=False)
 saved.append({"file":fn.name,"title":x["title"],"slug":x["slug"],"url":x["url"],"duration":duration,"viewCount":x["viewCount"],"createdAt":x["createdAt"],"frames":[f"frame_{i+1:02}_{n+1}.jpg" for n in range(3)]})
Path("top_clip_media/metadata.json").write_text(json.dumps(saved,ensure_ascii=False,indent=2))
w,h=515,350
im=Image.new("RGB",(w*3,h*len(saved)),"#101117");d=ImageDraw.Draw(im)
for idx,x in enumerate(saved):
 for k,path in enumerate(x["frames"]):
  try:
   frame=Image.open(P/path).convert("RGB")
   frame.thumbnail((w-25,h-55))
   im.paste(frame,(k*w+(w-frame.width)//2,idx*h+50))
  except:continue
  d.text((k*w+14,idx*h+14),x["title"][:37]+"  "+str(k+1),fill="white")
im.save("top_clip_media/CONTACT.jpg",quality=88)
print("DONE",len(saved),flush=True)
