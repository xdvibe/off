import json, subprocess, re, sys, math
from pathlib import Path
import numpy as np
from faster_whisper import WhisperModel

day=sys.argv[1]
vod={'21':'2936145096','22':'2937332065'}[day]
excluded={'21':[780,1155,1278,3050,3355,3602],'22':[2671,3723,780,1155,3050,3355]}[day]
root=Path('work');root.mkdir(exist_ok=True)
out=Path('finished');out.mkdir(exist_ok=True)
def run(args):
    subprocess.run(list(map(str,args)),check=True)
def get(args):
    return subprocess.check_output(list(map(str,args)))
def stamp(t):
    t=max(0,t)
    return f'{int(t//3600)}:{int(t//60)%60:02}:{t%60:05.2f}'
def clean(t):
    return t.replace('\\','').replace('{','(').replace('}',')').replace('\n',' ')
src=root/'vod.mp4'
run(['yt-dlp','--no-playlist','--no-part','-S','res:720','--retries','10','--fragment-retries','10','--merge-output-format','mp4','-o',src,'https://www.twitch.tv/videos/'+vod])
audio=np.frombuffer(get(['ffmpeg','-v','error','-i',src,'-vn','-ac','1','-ar','16000','-f','f32le','-']),dtype=np.float32).copy()
print('VOD',vod,'duration',len(audio)/16000,'bytes',src.stat().st_size,flush=True)
model=WhisperModel('tiny',device='cpu',compute_type='int8',cpu_threads=4)
segments,_=model.transcribe(audio,language='ru',beam_size=1,vad_filter=True,condition_on_previous_text=False)
segs=[dict(start=float(s.start),end=float(s.end),text=s.text.strip()) for s in segments if s.text.strip()]
(root/'transcript.json').write_text(json.dumps(segs,ensure_ascii=False,indent=2),encoding='utf-8')
del model
# Rank complete exchanges and surprising reactions; do not use a volume-only highlight.
strong=re.compile(r'не поверишь|прикинь|представля|серь[её]зно|ты ч[еёо]|что за|какого|не может быть|в смысле|я в шоке|охуе|ахуе|пиздец|ахах|хаха|смешно|угар|ебать|блять|офигеть|капец|почему',re.I)
weak=re.compile(r'чат.?рулет|рулетк|розыгрыш|разыгра|тысяча|победител|подпис|донат|прич[её]ск|промокод|ссылка в',re.I)
cand=[]
for i,s in enumerate(segs):
    st=max(0,s['start']-.12)
    if any(abs(st-x)<55 for x in excluded):continue
    if i and s['start']-segs[i-1]['end']<.13 and not re.search(r'[.!?…]$',segs[i-1]['text']):continue
    for j in range(i,min(i+8,len(segs))):
        en=segs[j]['end']+.18
        dur=en-st
        if dur>13.85:break
        if dur<7:continue
        phrase=' '.join(x['text'] for x in segs[i:j+1])
        if weak.search(phrase) or len(phrase.split())<9:continue
        cues=len(strong.findall(phrase))
        ending=segs[j]['text']
        closure=bool(re.search(r'[.!?…]$',ending))
        if not closure:continue
        if not cues and '?' not in phrase:continue
        # Prefer clear setup plus an answer or a reaction toward the end.
        ending_cues=len(strong.findall(ending))
        score=3*cues+2*ending_cues+2*('?' in phrase[:-len(ending)] if len(phrase)>len(ending) else False)+1.5*closure+min(len(phrase.split())/10,3)
        cand.append((score,st,en,phrase))
cand.sort(reverse=True)
print('CANDIDATES',len(cand),flush=True)
for c in cand[:25]:print('CANDIDATE',c,flush=True)
picks=[]
for c in cand:
    if any(abs(c[1]-p[1])<75 for p in picks):continue
    picks.append(c)
    if len(picks)==8:break
if len(picks)<2:raise RuntimeError('Not enough eligible scenes; no filler export')
model=WhisperModel('base',device='cpu',compute_type='int8',cpu_threads=4)
made=[]
for score,st,en,phrase in picks:
    if len(made)==2:break
    a=audio[int(st*16000):int(en*16000)]
    ss,_=model.transcribe(a,language='ru',beam_size=4,word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
    words=[(float(w.start),float(w.end),w.word.strip()) for s in ss for w in (s.words or []) if w.word.strip() and w.start is not None and w.end is not None]
    text=' '.join(w[2] for w in words)
    if len(words)<8 or weak.search(text):continue
    if not strong.search(text) and '?' not in text:continue
    idx=len(made)+1
    dur=en-st
    # Use verbatim hook rather than an invented claim.
    first=re.split(r'[.!?…]',text)[0].strip().split()
    title=' '.join(first[:6]).upper()
    if len(title)>40:title=' '.join(first[:4]).upper()
    title=clean(title)
    header="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,DejaVu Sans,65,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,5,0,8,75,75,420,1
Style: Brand,DejaVu Sans,43,&H00F0A1C8,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,3,0,8,50,50,548,1
Style: Caption,DejaVu Sans,66,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,5,0,2,65,65,465,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events=[f'Dialogue: 0,0:00:00.00,{stamp(dur)},Hook,,0,0,0,,{title}',f'Dialogue: 0,0:00:00.00,{stamp(dur)},Brand,,0,0,0,,TWITCH: FANTIK_69']
    for k in range(0,len(words),4):
        group=words[k:k+4]
        aa=max(0,group[0][0]);bb=min(dur,group[-1][1]+.10)
        if bb<=aa:continue
        events.append(f'Dialogue: 0,{stamp(aa)},{stamp(bb)},Caption,,0,0,0,,'+clean(' '.join(w[2] for w in group)))
    ass=root/f'{day}_{idx}.ass'
    ass.write_text(header+'\n'.join(events)+'\n',encoding='utf-8')
    dest=out/f'FANTIK69_{day}_{idx:02}.mp4'
    vf=f'[0:v]split=2[bg][fg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=35,eq=brightness=-0.18[blur];[fg]scale=1080:-2[front];[blur][front]overlay=0:(H-h)/2,ass={ass}[v]'
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',f'{st:.3f}','-i',src,'-t',f'{dur:.3f}','-filter_complex',vf,'-map','[v]','-map','0:a:0','-r','30','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',dest])
    meta=json.loads(get(['ffprobe','-v','error','-show_streams','-show_format','-of','json',dest]))
    actual=float(meta['format']['duration'])
    if actual>14 or not any(x.get('codec_type')=='audio' for x in meta['streams']):
        dest.unlink();continue
    made.append(dict(file=dest.name,vod=vod,start=st,end=en,duration=actual,transcript=text,score=score))
    print('EXPORTED',made[-1],flush=True)
(out/f'moments_{day}.json').write_text(json.dumps(made,ensure_ascii=False,indent=2),encoding='utf-8')
if len(made)!=2:raise RuntimeError('Two validated-duration candidates not found; no filler export')
