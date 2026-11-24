import json, subprocess, requests, datetime
from pathlib import Path
out=[]
q='query { user(login: "fantik_69") { id displayName videos(first: 10, type: ARCHIVE, sort: TIME) { edges { node { id title createdAt lengthSeconds } } } } }'
for headers in [
 {'Client-ID':'kimne78kx3ncx6brgo4mv6wki5h1ko','Content-Type':'application/json'},
 {'Client-ID':'kimne78kx3ncx6brgo4mv6wki5h1ko','Content-Type':'application/json','User-Agent':'Mozilla/5.0'}
]:
 try:
  r=requests.post('https://gql.twitch.tv/gql',headers=headers,json={'query':q},timeout=25)
  print('GQL',r.status_code,r.text[:5000],flush=True)
  if r.ok and r.json().get('data',{}).get('user',{}).get('videos',{}).get('edges'):
   out=r.json()['data']['user']['videos']['edges'];break
 except Exception as e:print('GQL_ERROR',repr(e),flush=True)
for url in [
 'https://www.twitch.tv/fantik_69/videos?filter=archives&sort=time',
 'https://www.twitch.tv/fantik_69/videos',
 'https://www.twitch.tv/fantik_69',
]:
 try:
  p=subprocess.run(['yt-dlp','--flat-playlist','--playlist-end','6','--skip-download','--dump-json',url],capture_output=True,text=True,timeout=90)
  print('YTDLP_URL',url,'RETURN',p.returncode,'STDOUT',p.stdout[:7500],'STDERR',p.stderr[:2500],flush=True)
  for line in p.stdout.splitlines():
   try:
    d=json.loads(line)
    if d.get('id') and ('video' in d.get('url','').lower() or d.get('ie_key')=='TwitchVod'):
     out.append({'node':{'id':str(d['id']),'title':d.get('title'),'createdAt':d.get('release_timestamp') or d.get('timestamp') or d.get('upload_date')}})
   except:pass
 except Exception as e: print('YTDLP_ERROR',url,repr(e),flush=True)
Path('latest_vods.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print('FINAL_VODS',json.dumps(out,ensure_ascii=False)[:9000],flush=True)
