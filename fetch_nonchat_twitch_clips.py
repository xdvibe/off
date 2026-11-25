from pathlib import Path
import requests,json
P=Path("clip_candidates");P.mkdir(exist_ok=True)
q='''query {
 user(login:"fantik_69") {
  clips(first:100,criteria:{period:LAST_MONTH,sort:VIEWS_DESC}) {
   edges { node { id slug title createdAt viewCount durationSeconds url game { name } videoQualities { quality sourceURL } } }
  }
 }
}'''
r=requests.post('https://gql.twitch.tv/gql',
 headers={'Client-ID':'kimne78kx3ncx6brgo4mv6wki5h1ko','User-Agent':'Mozilla/5.0'},
 json={'query':q},timeout=25)
print("STATUS",r.status_code,r.text[:7000],flush=True)
r.raise_for_status()
obj=r.json()
Path("clip_candidates/clips.json").write_text(json.dumps(obj,ensure_ascii=False,indent=2))
for e in obj.get("data",{}).get("user",{}).get("clips",{}).get("edges",[]):
 x=e["node"]
 print("CLIP",x.get("createdAt"),x.get("viewCount"),x.get("durationSeconds"),x.get("title"),x.get("url"),flush=True)
