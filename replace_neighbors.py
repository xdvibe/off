import json, subprocess, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.io.wavfile import write
from faster_whisper import WhisperModel
out=Path('finished');out.mkdir(exist_ok=True)
src=Path('source.mp4')
def run(cmd): subprocess.run(list(map(str,cmd)),check=True)
def probe(path):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
url='https://www.twitch.tv/videos/2937332065'
base=['yt-dlp','--no-playlist','--no-part','-S','res:1080','--retries','5','--fragment-retries','5','--merge-output-format','mp4']
origin=2520
try:
 run(base+['--download-sections','*00:42:00-00:42:22','--force-keyframes-at-cuts','-o',src,url])
 if float(probe(src)['format']['duration'])<16:raise RuntimeError('Short excerpt')
except Exception as e:
 print('Fallback full source',e,flush=True);src.unlink(missing_ok=True);run(base+['-o',src,url]);origin=0
st,en=2523.0,2535.5
length=en-st
run(['ffmpeg','-v','error','-y','-ss',st-origin,'-i',src,'-t',length,'-vn','-ac','1','-ar','16000','review.wav'])
audio=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i','review.wav','-f','f32le','-']),dtype=np.float32).copy()
model=WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=4)
segs,_=model.transcribe(audio,language='ru',beam_size=5,word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
records=[{'start':round(st+s.start,2),'end':round(st+s.end,2),'text':s.text} for s in segs]
(out/'transcript.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print('VERIFIED',records,flush=True)
run(['ffmpeg','-v','error','-y','-ss',st-origin+4,'-i',src,'-frames:v','1','frame.jpg'])
im=Image.open('frame.jpg').convert('RGB');W,H=im.size
rgb=np.asarray(im.resize((480,270)),dtype=np.int16)
pink=np.mean((rgb[:,:,0]>125)&(rgb[:,:,0]-rgb[:,:,1]>35)&(rgb[:,:,2]-rgb[:,:,1]>15))
print('PINK',pink,'SIZE',W,H,flush=True)
def even(v):return max(2,int(v)//2*2)
def crop(x,y,w,h):return f'crop={even(W*w)}:{even(H*h)}:{int(W*x)//2*2}:{int(H*y)//2*2}'
# Preserve all participants in this punchline, not just the host.
if pink>.10:
 c1=crop(.09,.12,.40,.39);c2=crop(.49,.12,.40,.39);ch=crop(.335,.535,.33,.34)
 vf=(f'[0:v]split=4[bg][l][r][h];[bg]scale=540:960:force_original_aspect_ratio=increase,crop=540:960,gblur=sigma=24,eq=brightness=-0.18,scale=1080:1920[b];'
 f'[l]{c1},scale=540:420:force_original_aspect_ratio=increase,crop=540:420[L];[r]{c2},scale=540:420:force_original_aspect_ratio=increase,crop=540:420[R];'
 f'[h]{ch},scale=1080:650:force_original_aspect_ratio=increase,crop=1080:650[H];[b][L]overlay=0:402[v1];[v1][R]overlay=540:402[v2];[v2][H]overlay=0:822[v3]')
else:
 vf='[0:v]split=2[bg][fg];[bg]scale=540:960:force_original_aspect_ratio=increase,crop=540:960,gblur=sigma=24,eq=brightness=-0.18,scale=1080:1920[b];[fg]scale=1080:1116:force_original_aspect_ratio=decrease[front];[b][front]overlay=(W-w)/2:(H-h)/2[v3]'
ov=Image.new('RGBA',(1080,1920));d=ImageDraw.Draw(ov)
fp='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
font=ImageFont.truetype(fp,76)
for i,l in enumerate(['ДЕВУШКИ ЗАКОНЧИЛИСЬ','НА СВИДАНИЯХ']):
 d.text((540,272+80*i),l,font=font,anchor='mt',fill='white',stroke_width=6,stroke_fill='black')
d.rectangle((194,1456,948,1586),fill='#a33df5')
ix,iy=222,1477
d.polygon([(ix,iy+15),(ix+14,iy),(ix+73,iy),(ix+73,iy+50),(ix+51,iy+72),(ix+35,iy+72),(ix+18,iy+91),(ix+18,iy+69),(ix,iy+69)],fill='#141018')
d.polygon([(ix+18,iy+10),(ix+63,iy+10),(ix+63,iy+45),(ix+47,iy+60),(ix+32,iy+60),(ix+24,iy+68),(ix+24,iy+56),(ix+18,iy+56)],fill='white')
for px in (ix+35,ix+49):d.rectangle((px,iy+18,px+6,iy+34),fill='#141018')
d.text((348,1522),'FANTIK_69',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',105),fill='white',anchor='lm')
ov.save('overlay.png')
sr=48000; x=np.zeros(sr*24); rng=np.random.default_rng(42); beat=60/104
def add(at,s):
 i=round(at*sr);n=min(len(s),len(x)-i)
 if n>0:x[i:i+n]+=s[:n]
def t(n):return np.arange(round(n*sr))/sr
for i in range(int(24/beat)):
 at=i*beat
 if i%4 in (0,2):
  a=t(.18);add(at,.34*np.sin(2*np.pi*(46*a+3.3*(1-np.exp(-a*37))))*np.exp(-a*25))
 if i%4 in (1,3):
  a=t(.12);n=rng.normal(0,1,len(a));n=np.r_[0,np.diff(n)];add(at,.07*n*np.exp(-a*37)+.04*np.sin(2*np.pi*175*a)*np.exp(-a*42))
 for j in (0,.5):
  a=t(.043);n=rng.normal(0,1,len(a));add(at+j*beat,.027*np.r_[0,np.diff(n)]*np.exp(-a*80))
 midi=[45,45,48,43,45,45,50,48][i%8];f=440*2**((midi-69)/12);a=t(.35)
 if i%4!=3:add(at,.15*(np.sin(2*np.pi*f*a)+.18*np.sin(4*np.pi*f*a))*(1-np.exp(-a*110))*np.exp(-a*8))
 if i%4 in (0,1,3):
  m=[69,72,76,74,67,71,74,72][i%8];f=440*2**((m-69)/12);a=t(.29)
  add(at+(.25*beat if i%2 else .08),.07*(np.sin(2*np.pi*f*a)+.2*np.sin(4*np.pi*f*a)+.08*np.sin(6*np.pi*f*a))*(1-np.exp(-a*140))*np.exp(-a*13))
x=np.tanh(x*1.2);x*=.25/(np.sqrt(np.mean(x*x))+1e-8);write('bed.wav',sr,np.int16(np.clip(x,-.96,.96)*32767))
vf+=';[v3][1:v]overlay=0:0:format=auto,format=yuv420p[v];'
vf+=f'[0:a]aresample=48000,highpass=f=70,acompressor=threshold=0.055:ratio=3:attack=10:release=150:makeup=2,loudnorm=I=-16:TP=-1.5:LRA=8,aresample=48000[voice];[2:a]volume=0.075,afade=t=in:st=0:d=0.12,afade=t=out:st={length-.35}:d=0.35[bed];[voice][bed]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.93:level=false[a]'
dest=out/'FANTIK69_03_DATING_MUSIC.mp4'
run(['ffmpeg','-v','error','-y','-ss',st-origin,'-i',src,'-i','overlay.png','-i','bed.wav','-t',length,'-filter_complex_threads','2','-filter_complex',vf,'-map','[v]','-map','[a]','-r','30','-c:v','libx264','-preset','fast','-crf','18','-c:a','aac','-b:a','192k','-movflags','+faststart',dest])
run(['ffmpeg','-v','error','-y','-ss','4','-i',dest,'-frames:v','1','-vf','scale=540:960',out/'preview.jpg'])
print('EXPORTED',probe(dest)['format']['duration'],flush=True)
