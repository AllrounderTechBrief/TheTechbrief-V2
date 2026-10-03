import subprocess,numpy as np,math
def run(c): subprocess.run(c,shell=True,check=True)
# vertical particles (450 frames loop)
W,H,FPS,NF=1080,1920,30,450
rng=np.random.default_rng(9);N=90
x=rng.random(N)*W;y0=rng.random(N)*H;r=rng.uniform(2,8,N);sp=(H/NF)*rng.integers(1,3,N);ph=rng.random(N)*6.283;sw=rng.uniform(8,26,N);al=rng.uniform(.35,1,N)
def sprite(rad):
    s=int(rad*6)|1;a=np.arange(s)-s//2;X,Y=np.meshgrid(a,a);return np.exp(-(np.sqrt(X**2+Y**2)/rad)**2*1.2)
cache=[sprite(rr) for rr in r]
import os
SKIP=os.path.exists('pv.mp4')

import os
if not os.path.exists('pv.mp4'):
  exec("""
p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','30','-i','-','-c:v','libx264','-crf','14','-pix_fmt','yuv420p','pv.mp4'],stdin=subprocess.PIPE)
col=np.array([255,205,110],dtype=np.float32)
for f in range(NF):
    t=f/NF;fr=np.zeros((H,W,3),np.float32)
    for i in range(N):
        py=(y0[i]-sp[i]*f)%H;px=x[i]+math.sin(ph[i]+t*6.283*2)*sw[i];tw=al[i]*(0.55+0.45*math.sin(ph[i]*3+t*6.283*3))
        s=cache[i];h=s.shape[0];c=h//2;xi=int(px)-c;yi=int(py)-c
        for oy in ((0,-H) if yi+h>H else (0,)):
            ya=yi+oy;ys0=max(0,ya);ys1=min(H,ya+h);xs0=max(0,xi);xs1=min(W,xi+h)
            if ys1<=ys0 or xs1<=xs0: continue
            fr[ys0:ys1,xs0:xs1]+=s[ys0-ya:ys1-ya,xs0-xi:xs1-xi,None]*tw*col
    p.stdin.write(np.clip(fr,0,255).astype(np.uint8).tobytes())
p.stdin.close();p.wait()
""")
print('particles done',flush=True)
# stills 2160x3840
run('ffmpeg -v error -y -i kailash.png -vf "crop=1215:2160:1312:0,scale=2160:3840:flags=lanczos" -frames:v 1 s_kail.png')
def framed(src,out,w,dy=0):
    run(f'''ffmpeg -v error -y -i {src} -filter_complex "[0:v]split[a][b];[a]scale=-2:3840:flags=lanczos,crop=2160:3840,gblur=sigma=70,eq=brightness=-0.15:saturation=1.2[bg];[b]scale={w}:-2:flags=lanczos,unsharp=5:5:0.7[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2+{dy}" -frames:v 1 {out}''')
framed('ram6.jpg','s_ram.png',2160,240)
run('ffmpeg -v error -y -i ram.jpg -vf "scale=-2:3840:flags=lanczos,crop=2160:3840:2440:0,unsharp=5:5:0.7" -frames:v 1 s_par.png')
def clip(img,z0,z1,fy0,fy1,dur,out):
    D=int(dur*FPS);pp=f'(on/{D})';e=f'({pp}*{pp}*(3-2*{pp}))'
    z=f'({z0}+({z1}-{z0})*{e})';cy=f'({fy0}+({fy1}-{fy0})*{e})'
    run(f'ffmpeg -v error -y -i {img} -vf "zoompan=z=\'{z}\':x=\'iw*0.5-iw/zoom/2\':y=\'max(0,min(ih-ih/zoom,{cy}*ih-ih/zoom/2))\':d={D}:s=1080x1920:fps={FPS},format=yuv420p" -c:v libx264 -crf 14 -preset veryfast -t {dur} {out}')
clip('s_kail.png',1.0,1.18,.55,.45,7.5,'clipA1.mp4')
clip('s_ram.png',1.0,1.14,.5,.46,8.5,'clipA2.mp4')
clip('s_ram.png',1.0,1.14,.5,.46,15,'clipB.mp4')
clip('s_par.png',1.0,1.12,.5,.5,15,'clipC.mp4')
print('clips done',flush=True)
G='format=gbrp,split[g1][g2];[g2]scale=270:480,gblur=sigma=5,scale=1080:1920:flags=bicubic,format=gbrp[gb];[g1][gb]blend=all_mode=screen:all_opacity=0.22[bl];[PT][bl]'
def build(name,base_inputs,base_filter,cards,audio_ss):
    ins=' '.join(f'-i {b}' for b in base_inputs)
    n=len(base_inputs)
    ins+=' -stream_loop -1 -i pv.mp4'
    for c,_,_ in cards: ins+=f' -loop 1 -framerate 30 -t 15 -i {c}.png'
    ins+=f' -ss {audio_ss} -t 15 -i track.mp3'
    F=[base_filter+',eq=contrast=1.08:saturation=1.12,vignette=PI/5,format=gbrp,split[g1][g2]']
    F.append('[g2]scale=270:480,gblur=sigma=5,scale=1080:1920:flags=bicubic,format=gbrp[gb];[g1][gb]blend=all_mode=screen:all_opacity=0.22[bl]')
    F.append(f'[{n}:v]format=gbrp,trim=0:15,setpts=PTS-STARTPTS[pt];[bl][pt]blend=all_mode=screen:all_opacity=0.9,format=yuv420p[pv0]')
    cur='[pv0]'
    for i,(c,a,b) in enumerate(cards):
        idx=n+1+i
        F.append(f'[{idx}:v]format=rgba,fade=t=in:st={a}:d=0.35:alpha=1,fade=t=out:st={b-0.35}:d=0.35:alpha=1[o{i}]')
        F.append(f'{cur}[o{i}]overlay=0:0:eof_action=pass[v{i}]');cur=f'[v{i}]'
    F.append(f'{cur}fade=t=in:st=0:d=0.15,fade=t=out:st=14.7:d=0.3,format=yuv420p[vout]')
    aidx=n+1+len(cards)
    F.append(f'[{aidx}:a]afade=t=in:st=0:d=0.15,afade=t=out:st=13.8:d=1.2,loudnorm=I=-14:TP=-1.5:LRA=7[aout]')
    open(f'g_{name}.txt','w').write(';\n'.join(F))
    run(f'ffmpeg -v error -y {ins} -filter_complex_script g_{name}.txt -map "[vout]" -map "[aout]" -t 15 -c:v libx264 -preset medium -crf 18 -profile:v high -pix_fmt yuv420p -r 30 -c:a aac -b:a 192k -ar 48000 -movflags +faststart short_{name}.mp4')
    print('built',name,flush=True)
build('A_ShivParvati_Secret',['clipA1.mp4','clipA2.mp4'],'[0:v][1:v]xfade=transition=fade:duration=1.0:offset=6.5',[('shade',0,15),('a1',0.3,3.2),('a2',3.4,6.7),('a3',7.2,12.8),('a4',13.0,15.0)],1.5)
build('B_Shloka_Reveal',['clipB.mp4'],'[0:v]null',[('shade',0,15),('b1',0.1,15.0),('b2',1.5,15.0),('b3',5.0,15.0),('b4',9.0,15.0)],9.5)
build('C_Morning_1Minute',['clipC.mp4'],'[0:v]null',[('shade',0,15),('c1',0.2,3.8),('c2',4.0,8.6),('c3',9.0,15.0)],17.5)
