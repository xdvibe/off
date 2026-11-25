import requests,json
from pathlib import Path
P=Path('more');P.mkdir(exist_ok=True)
u='https://gql.twitch.tv/gql'
headers={'Client-ID':'kimne78kx3ncx6brgo4mv6wki5h1ko','User-Agent':'Mozilla/5.0'}
qs=[
 'query { user(login: "fantik_69") { clips(first:100,criteria:{period:ALL_TIME,sort:VIEWS_DESC}) { edges { node { id title createdAt viewCount durationSeconds url } } pageInfo { hasNextPage } } } }',
 'query { user(login: "fantik_69") { clips(first:100,criteria:{sort:VIEWS_DESC}) { edges { node { id title createdAt viewCount durationSeconds url } } pageInfo { hasNextPage } } } }',
 'query { user(login: "fantik_69") { clips(first:100,criteria:{period:LAST_YEAR,sort:VIEWS_DESC}) { edges { node { id title createdAt viewCount durationSeconds url } } pageInfo { hasNextPage } } } }'
]
for i,q in enumerate(qs):
 try:
  r=requests.post(u,headers=headers,json={'query':q},timeout=15)
  o=r.json()
  print('QUERY',i,'HTTP',r.status_code,'ERRORS',o.get('errors'),flush=True)
  edges=o.get('data',{}).get('user',{}).get('clips',{}).get('edges',[])
  print('TOTAL',len(edges),flush=True)
  for e in edges[:100]:
   x=e['node'];print('CLIP',x['title'],x['createdAt'],x['viewCount'],x['durationSeconds'],x['url'],flush=True)
  (P/f'clips_{i}.json').write_text(json.dumps(o,ensure_ascii=False,indent=2))
 except Exception as e:print('FAILED',repr(e),flush=True)
