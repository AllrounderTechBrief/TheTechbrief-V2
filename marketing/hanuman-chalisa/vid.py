import subprocess,numpy as np
def run(c): subprocess.run(c,shell=True,check=True)
import subprocess as _sp
TOT=float(_sp.check_output('ffprobe -v error -show_entries format=duration -of csv=p=0 master.wav',shell=True));FPS=30;END=64.0+249.15
CUT=0.0;TF=64.0
def kk(k): return (k-1)/40*240-CUT+TF
def prep16(src,out):
    run(f'ffmpeg -v error -y -i {src} -vf "crop=\'min(iw,ih*16/9)\':\'min(ih,iw*9/16)\',scale=3840:2160:flags=lanczos,unsharp=5:5:0.6" -frames:v 1 {out}')
def portrait(src,out,h=1980):
    run(f'''ffmpeg -v error -y -i {src} -filter_complex "[0:v]split[a][b];[a]scale=3840:-2:flags=lanczos,crop=3840:2160,gblur=sigma=60,eq=brightness=-0.12:saturation=1.15[bg];[b]scale=-2:{h}:flags=lanczos,unsharp=5:5:0.7[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2" -frames:v 1 {out}''')
prep16('3.jpg','s3.png');prep16('4.jpg','s4.png');prep16('5.webp','s5.png');prep16('8.jpg','s8.png')
portrait('6.jpg','s6.png');portrait('7.webp','s7.png')
B=[0,34,64,kk(5),kk(9),kk(13),kk(15),kk(18),kk(21),kk(26),kk(31),kk(34),kk(37),kk(38),END]
# (img,z0,z1,x0,y0,x1,y1)
S=[('s7',1.00,1.10,.50,.50,.50,.42),   #0 intro dawn
   ('s7',1.55,1.35,.51,.31,.51,.33),   #1 face closeup (slow doha)
   ('s5',1.00,1.15,.50,.50,.38,.58),   #2 bhakti Hanuman bowing
   ('s3',1.00,1.12,.50,.50,.50,.45),   #3 ram parivar
   ('s8',1.05,1.30,.50,.45,.50,.35),   #4 shakti temple hanuman
   ('s6',1.00,1.10,.50,.52,.50,.42),   #5 majesty ram
   ('s4',1.00,1.20,.50,.50,.50,.45),   #6 hut parivar
   ('s8',1.25,1.50,.50,.35,.50,.28),   #7 veer 1 face
   ('s8',1.10,1.45,.55,.45,.40,.30),   #8 veer peak
   ('s8',1.35,1.00,.45,.40,.50,.50),   #9 protection pull-back (abhay hand)
   ('s3',1.20,1.00,.34,.70,.50,.50),   #10 boons Hanuman crop->wide
   ('s5',1.25,1.00,.50,.45,.50,.50),   #11 devotion
   ('s7',1.30,1.55,.51,.30,.51,.30),   #12 jai jai jai burst
   ('s7',1.45,1.00,.51,.35,.50,.50),   #13 pull-back dawn
   ('s7',1.00,1.00,.50,.50,.50,.50)]   #14 end card base (static slow)
XF=1.5
for i,(im,z0,z1,x0,y0,x1,y1) in enumerate(S):
    last=i==len(S)-1
    dur=(TOT-B[i]) if last else (B[i+1]-B[i]+XF)
    D=int(dur*FPS)+2
    p=f'(on/{D})';e=f'({p}*{p}*(3-2*{p}))'
    z=f'({z0}+({z1}-{z0})*{e})';cx=f'({x0}+({x1}-{x0})*{e})';cy=f'({y0}+({y1}-{y0})*{e})'
    zp=f"zoompan=z='{z}':x='max(0,min(iw-iw/zoom,{cx}*iw-iw/zoom/2))':y='max(0,min(ih-ih/zoom,{cy}*ih-ih/zoom/2))':d={D}:s=1920x1080:fps={FPS}"
    run(f'ffmpeg -v error -y -i {im}.png -vf "{zp},format=yuv420p" -c:v libx264 -crf 14 -preset veryfast -t {dur:.3f} shot{i}.mp4')
    print('shot',i,round(dur,1),flush=True)
# compose
n=len(S);F=[];prev='[0:v]';outlen=(B[1]-B[0]+XF)
for k in range(1,n):
    off=round(B[k],3);F.append(f'{prev}[{k}:v]xfade=transition=fade:duration={XF}:offset={off}[x{k}]');prev=f'[x{k}]'
v1,v2,v3=kk(18),kk(26),kk(37)
F.append(f"{prev}eq=contrast='1.05+0.08*between(t,{kk(18)},{kk(31)})':saturation='1.10+0.12*between(t,{kk(18)},{kk(31)})':brightness='0.22*max(0,1-abs(t-{kk(37)+.3})/1.0)':eval=frame,vignette=PI/5,format=gbrp,split[g1][g2]")
F.append('[g2]scale=480:270,gblur=sigma=6,scale=1920:1080:flags=bicubic,format=gbrp[gb];[g1][gb]blend=all_mode=screen:all_opacity=0.22[bl]')
F.append(f'[{n}:v]format=gbrp,trim=0:{TOT},setpts=PTS-STARTPTS[pt];[bl][pt]blend=all_mode=screen:all_opacity=0.85,format=yuv420p[pv]')
ti=n+1
F.append(f'[{ti}:v]format=rgba,fade=t=in:st=0.8:d=1.2:alpha=1,fade=t=out:st=5.3:d=1.2:alpha=1[tt]')
F.append(f'[{ti+1}:v]format=rgba,fade=t=in:st=8:d=1:alpha=1,fade=t=out:st=60:d=1:alpha=1[td]')
F.append(f'[{ti+2}:v]format=rgba,fade=t=in:st=65:d=1:alpha=1,fade=t=out:st={END-4}:d=1:alpha=1[tc]')
F.append(f'[{ti+3}:v]format=rgba,fade=t=in:st={END+1}:d=1.5:alpha=1[te]')
F.append('[pv][tt]overlay=0:0:eof_action=pass[o1];[o1][td]overlay=0:0:eof_action=pass[o2];[o2][tc]overlay=0:0:eof_action=pass[o3];[o3][te]overlay=0:0:eof_action=pass[o4]')
F.append(f'[o4]fade=t=in:st=0:d=1.2,fade=t=out:st={TOT-2.5}:d=2.5,format=yuv420p[vout]')
open('graph.txt','w').write(';\n'.join(F))
ins=''.join(f'-i shot{i}.mp4 ' for i in range(n))+'-stream_loop -1 -i particles.mp4 '
for f in ['title','tag_doha','tag_chaupai','end']: ins+=f'-loop 1 -framerate 30 -t {TOT} -i {f}.png '
ins+='-i master.wav'
cmd=f'ffmpeg -v error -stats -y {ins} -filter_complex_script graph.txt -map "[vout]" -map {ti+4}:a -t {TOT} -c:v libx264 -preset veryfast -crf 18 -profile:v high -pix_fmt yuv420p -r 30 -c:a aac -b:a 256k -movflags +faststart hanuman_chalisa_video_1080p.mp4'
open('run.sh','w').write(cmd)
print('boundaries',[round(x,1) for x in B])
