import subprocess, sys, json, statistics, math
from pathlib import Path
import cv2
from faster_whisper import WhisperModel
import numpy as np
from PIL import Image, ImageDraw, ImageFont
day=sys.argv[1]
vod={'21':'2936145096','22':'2937332065'}[day]
scenes=[]
out=Path('finished');out.mkdir(exist_ok=True);work=Path('work');work.mkdir(exist_ok=True)
def run(args):
    subprocess.run([str(x) for x in args],check=True)
def probe(f):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(f)]))
src=work/'vod.mp4'
run(['yt-dlp','--no-playlist','--no-part','-S','res:1080','--retries','10','--fragment-retries','10','--merge-output-format','mp4','-o',src,'https://www.twitch.tv/videos/'+vod])
v=next(x for x in probe(src)['streams'] if x['codec_type']=='video');W,H=v['width'],v['height']
print('SOURCE',W,H,flush=True)
cascade=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
cap=cv2.VideoCapture(str(src))
fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def overlay(title,path):
    im=Image.new('RGBA',(1080,1920),(0,0,0,0));d=ImageDraw.Draw(im)
    lines=title.split('\n');fs=76
    while fs>40:
        font=ImageFont.truetype(fontpath,fs)
        if max(d.textlength(l,font=font) for l in lines)<=1000:break
        fs-=2
    for i,line in enumerate(lines):
        d.text((540,288+i*(fs+2)),line,font=font,anchor='mt',fill='white',stroke_width=6,stroke_fill='black')
    # Large flat purple Twitch-style nameplate, at lower edge of the camera.
    x0,y0,x1,y1=194,1456,948,1586
    d.rectangle((x0,y0,x1,y1),fill='#a33df5')
    ix,iy=222,1477
    d.polygon([(ix,iy+15),(ix+14,iy),(ix+73,iy),(ix+73,iy+50),(ix+51,iy+72),(ix+35,iy+72),(ix+18,iy+91),(ix+18,iy+69),(ix,iy+69)],fill='#141018')
    d.polygon([(ix+18,iy+10),(ix+63,iy+10),(ix+63,iy+45),(ix+47,iy+60),(ix+32,iy+60),(ix+24,iy+68),(ix+24,iy+56),(ix+18,iy+56)],fill='white')
    for px in (ix+35,ix+49):d.rectangle((px,iy+18,px+6,iy+34),fill='#141018')
    namefont=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',105)
    d.text((348,1522),'FANTIK_69',font=namefont,fill='white',anchor='lm')
    im.save(path)
meta=[]
model=WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=4)
# Independent verification of the unclear name and voting-service reveal.
for label,st,en in ({'21':[('million',2075,2102),('neighbor_conflict',198,223),('chair',2664,2683),('moderator_money',438,456)],'22':[('guests',3439,3477),('money_twist',3483,3506),('donation',3513,3536),('dating_conflict',2044,2072)]}[day]):
    wav=work/(label+'.wav')
    run(['ffmpeg','-v','error','-y','-ss',st,'-i',src,'-t',en-st,'-vn','-ar','16000','-ac','1',wav])
    audio=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(wav),'-f','f32le','-ac','1','-ar','16000','-']),dtype=np.float32).copy()
    segs,_=model.transcribe(audio,language='ru',beam_size=5,word_timestamps=True,condition_on_previous_text=False,vad_filter=True)
    records=[{'start':round(st+s.start,2),'end':round(st+s.end,2),'text':s.text,'words':[{'start':round(st+w.start,2),'end':round(st+w.end,2),'word':w.word} for w in s.words or [] if w.start is not None and w.end is not None]} for s in segs]
    (out/(label+'_transcript.json')).write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print('VERIFIED_ASR',label,json.dumps(records,ensure_ascii=False),flush=True)
    run(['ffmpeg','-v','error','-y','-ss',st,'-i',src,'-t',en-st,'-vf','scale=960:-2','-c:v','libx264','-preset','veryfast','-crf','23','-c:a','aac',out/(label+'_review.mp4')])
del model
for i,(st,en,title) in enumerate(scenes,1):
    duration=en-st
    faces=[];pink=[];sample=None
    for offset in np.linspace(.5,duration-.5,7):
        cap.set(cv2.CAP_PROP_POS_MSEC,(st+offset)*1000)
        ok,frame=cap.read()
        if not ok:continue
        sample=frame
        small=cv2.resize(frame,(640,360))
        # pink dating-show panel: use the lower central host camera, never crop the guests as host
        hsv=cv2.cvtColor(small,cv2.COLOR_BGR2HSV)
        mask=cv2.inRange(hsv,np.array([145,85,110]),np.array([179,255,255]))
        pink.append(float((mask>0).mean()))
        g=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
        for x,y,w,h in cascade.detectMultiScale(g,1.1,5,minSize=(22,22)):
            faces.append((x/640*W,y/360*H,w/640*W,h/360*H))
    is_show=bool(pink and statistics.median(pink)>.16)
    if is_show:
        # lower center webcam in the confirmed show layout
        bx,by,bw,bh=int(W*.334),int(H*.535),int(W*.332),int(H*.337)
    else:
        bx,by,bw,bh=0,0,W,H
    crop_h=bh//2*2;crop_w=min(bw,int(crop_h*1080/1116))//2*2
    relevant=[f for f in faces if bx<=f[0]+f[2]/2<=bx+bw and by<=f[1]+f[3]/2<=by+bh]
    if relevant:
        # reject tiny overlays; choose the largest consistent face detections.
        maxarea=max(f[2]*f[3] for f in relevant)
        relevant=[f for f in relevant if f[2]*f[3]>=maxarea*.48]
        cx=statistics.median(f[0]+f[2]/2 for f in relevant)
    else:cx=bx+bw*(.50 if is_show else .35)
    x=int(max(bx,min(bx+bw-crop_w,cx-crop_w/2)))//2*2
    y=by//2*2
    print('CROP',day,i,x,y,crop_w,crop_h,'show',is_show,flush=True)
    png=work/f'overlay_{i}.png';overlay(title,png)
    dest=out/f'FANTIK69_REF_{day}_{i}.mp4'
    # Ref layout: center 1080x1116 camera at y=402, only blurred camera above/below.
    vf=f'[0:v]crop={crop_w}:{crop_h}:{x}:{y},split=2[a][b];[a]scale=540:960:force_original_aspect_ratio=increase,crop=540:960,gblur=sigma=28,eq=brightness=-0.15,scale=1080:1920[bg];[b]scale=1080:1116[fg];[bg][fg]overlay=0:402[base];[base][1:v]overlay=0:0:format=auto,format=yuv420p[v]'
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',st,'-i',src,'-i',png,'-t',duration,'-filter_complex_threads','2','-filter_complex',vf,'-map','[v]','-map','0:a:0','-r','30','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',dest])
    actual=probe(dest);d=float(actual['format']['duration'])
    if d>14:raise RuntimeError('Duration exceeded')
    run(['ffmpeg','-v','error','-y','-ss',min(3,d/2),'-i',dest,'-frames:v','1','-vf','scale=540:960',out/f'preview_{day}_{i}.jpg'])
    meta.append({'file':dest.name,'vod':vod,'start':st,'end':en,'duration':d,'title':title,'crop':[x,y,crop_w,crop_h],'show_layout':is_show})
    print('EXPORTED',meta[-1],flush=True)
cap.release()
(out/f'moments_{day}.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
