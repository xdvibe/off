#!/usr/bin/env python3
import json,subprocess
from pathlib import Path
S=[
 ("01","2936145096",1278,1292,"2026-11-21","ФАНТИК ПЕРЕДЕЛАЛ ПРИЧЁСКУ"),
 ("02","2936145096",3602,3616,"2026-11-21","ВЫПАЛ ПОБЕДИТЕЛЬ РОЗЫГРЫША"),
 ("03","2937332065",2671,2685,"2026-11-22","ФАНТИК РАЗЫГРЫВАЕТ 1000"),
 ("04","2937332065",3723,3737,"2026-11-22","КТО ВЫИГРАЛ У ФАНТИКА?")
]
P=Path("recent2_hd");P.mkdir(exist_ok=True)
def clock(t):return f"{t//3600:02}:{t//60%60:02}:{t%60:02}"
meta=[]
for num,vid,st,en,day,title in S:
 o=P/f"RAW_{num}.mp4"
 cmd=["yt-dlp","--no-playlist","--download-sections",f"*{clock(st)}-{clock(en)}","-S","res:720","--merge-output-format","mp4","--retries","7","--fragment-retries","5","-o",str(o),f"https://www.twitch.tv/videos/{vid}"]
 print("GET",num,st,en,flush=True)
 subprocess.run(cmd,check=True)
 dur=subprocess.check_output(["ffprobe","-v","quiet","-show_entries","format=duration","-of","default=nk=1:nw=1",str(o)],text=True)
 meta.append({"num":num,"source_vod_id":vid,"start":st,"end":en,"date":day,"title":title,"file":o.name,"duration":float(dur),"bytes":o.stat().st_size})
 print("DONE",num,dur,o.stat().st_size,flush=True)
(P/"metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2))
