import subprocess,json,sys
from pathlib import Path
import numpy as np
from faster_whisper import WhisperModel
P=Path('review2');P.mkdir(exist_ok=True)
W=Path('work');W.mkdir(exist_ok=True)
src=W/'vod.mp4'
def run(a):subprocess.run(list(map(str,a)),check=True)
def out(a):return subprocess.check_output(list(map(str,a)))
run(['yt-dlp','--no-playlist','--no-part','-S','res:720','--retries','10','--fragment-retries','10','--concurrent-fragments','4','--merge-output-format','mp4','-o',src,'https://www.twitch.tv/videos/2941324540'])
model=WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=4)
scenes=[('old_show',3438,3510),('deleted_clip',3587,3623),('media_competition',675,699),('million_online',745,766),('old_friend_story',4287,4339),('big_gift',4614,4636),('animals_show',5168,5215),('laugh_reaction',2465,2512),('teeth',5038,5064),('old_streamer',3529,3554),('performer',1797,1833),('old_streamer_return',3086,3130),('name_mandela',5267,5319)]
for name,a,b in scenes:
    f=P/(name+'.mp4')
    run(['ffmpeg','-v','error','-y','-ss',a,'-i',src,'-t',b-a,'-c:v','libx264','-preset','veryfast','-crf','20','-c:a','aac','-b:a','160k',f])
    audio=np.frombuffer(out(['ffmpeg','-v','error','-i',f,'-vn','-ar','16000','-ac','1','-f','f32le','-']),dtype=np.float32).copy()
    segs,_=model.transcribe(audio,language='ru',beam_size=5,word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
    rows=[dict(start=round(a+s.start,2),end=round(a+s.end,2),text=s.text,words=[dict(start=round(a+w.start,2),end=round(a+w.end,2),word=w.word) for w in s.words or [] if w.start is not None and w.end is not None]) for s in segs]
    (P/(name+'.json')).write_text(json.dumps(dict(source='2941324540',start=a,end=b,segments=rows),ensure_ascii=False,indent=2))
    print('SECOND_PASS',name,json.dumps([dict(start=r['start'],end=r['end'],text=r['text']) for r in rows],ensure_ascii=False),flush=True)
    run(['ffmpeg','-v','error','-y','-ss',(b-a)/2,'-i',f,'-frames:v','1','-vf','scale=640:-2',P/(name+'.jpg')])
