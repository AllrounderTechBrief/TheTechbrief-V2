import subprocess
def run(c): subprocess.run(c,shell=True,check=True)
F=639;X=45;FPS=30
# audio: 10 crossfaded copies -> trim -> master
run('cp full.wav cur.wav')
for i in range(10):
    run('ffmpeg -v error -y -i cur.wav -i tail.wav -filter_complex "acrossfade=d=3:c1=tri:c2=tri" -c:a pcm_s16le nxt.wav && mv nxt.wav cur.wav')
TOT=(594+8*F+9*F+45-18*X)/FPS
print('video seconds',TOT,flush=True)
run(f'ffmpeg -v error -y -i cur.wav -af "atrim=0:{TOT},highpass=f=40,acompressor=threshold=-20dB:ratio=2:attack=20:release=250,afade=t=in:st=0:d=0.6,afade=t=out:st={TOT-3.5}:d=3.5,loudnorm=I=-14:TP=-1.5:LRA=9" -ar 48000 -c:a pcm_s16le loop_audio.wav')
# shots: s0t (from frame X*... i.e. 1.5s), head (first 1.5s)
run(f'ffmpeg -v error -y -i shot0.mp4 -vf "select=gte(n\\,{X}),setpts=N/{FPS}/TB" -c:v libx264 -crf 14 -preset veryfast s0t.mp4')
run(f'ffmpeg -v error -y -i shot0.mp4 -vf "select=lt(n\\,{X}),setpts=N/{FPS}/TB" -c:v libx264 -crf 14 -preset veryfast head.mp4')
els=['s0t']+[f'shot{i}' for i in range(1,9)]+[f'shot{i}' for i in range(0,9)]+['head']
lens=[]
for e in els:
    n=int(subprocess.check_output(f'ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 {e}.mp4',shell=True))
    lens.append(n/FPS)
starts=[0.0]
for i in range(1,len(els)): starts.append(starts[-1]+lens[i-1]-1.5)
total=starts[-1]+lens[-1]
print('chain total',total,flush=True)
G=[];prev='[0:v]';outlen=lens[0]
for k in range(1,len(els)):
    off=round(outlen-1.5,4);G.append(f'{prev}[{k}:v]xfade=transition=fade:duration=1.5:offset={off}[x{k}]');prev=f'[x{k}]';outlen=off+lens[k]
G.append(f"{prev}eq=contrast=1.06:saturation=1.12:gamma=1.02,vignette=PI/5,format=gbrp,split[g1][g2]")
G.append('[g2]scale=480:270,gblur=sigma=6,scale=1920:1080:flags=bicubic,format=gbrp[gb];[g1][gb]blend=all_mode=screen:all_opacity=0.22[bl]')
n=len(els)
G.append(f'[{n}:v]format=gbrp,trim=0:{total},setpts=PTS-STARTPTS[pt];[bl][pt]blend=all_mode=screen:all_opacity=0.9,format=yuv420p[pv]')
# lyric alpha envelopes (16x16 gray -> scale -> alphamerge)
def env(wins): 
    terms=[f'clip(min((T-{a:.2f})/0.9,({b:.2f}-T)/0.9),0,1)' for a,b in wins]
    e=terms[0]
    for t in terms[1:]: e=f'max({e},{t})'
    return e
wA=[];wB=[]
for i,s in enumerate(starts[:-1]):
    if i==0: wA.append((s+1.0,s+8.0));wB.append((s+9.0,s+16.5))
    else: wA.append((s+2.5,s+10.5));wB.append((s+11.5,s+18.5))
for tag,w,idx in (('A',wA,n+1),('B',wB,n+2)):
    G.append(f"color=c=black:s=16x16:r=30:d={total},format=gray,geq=lum='255*({env(w)})',scale=1920:1080,format=gray[env{tag}]")
    G.append(f"[{idx}:v]format=rgba,split[c{tag}1][c{tag}2];[c{tag}2]alphaextract,format=gray[a{tag}1];[a{tag}1][env{tag}]blend=all_mode=multiply,format=gray[a{tag}2];[c{tag}1]format=rgb24[c{tag}r];[c{tag}r][a{tag}2]alphamerge[ov{tag}]")
G.append('[pv][ovA]overlay=0:0:format=auto[oA];[oA][ovB]overlay=0:0:format=auto,format=yuv420p[vout]')
open('graph.txt','w').write(';\n'.join(G))
ins=''.join(f'-i {e}.mp4 ' for e in els)+'-stream_loop -1 -i particles2.mp4 '
ins+=f'-loop 1 -framerate 30 -t {total} -i lyricA.png -loop 1 -framerate 30 -t {total} -i lyricB.png -i loop_audio.wav'
open('run.sh','w').write(f'ffmpeg -v error -stats -y {ins} -filter_complex_script graph.txt -map "[vout]" -map {n+3}:a -t {total} -c:v libx264 -preset veryfast -crf 19 -profile:v high -pix_fmt yuv420p -r 30 -c:a aac -b:a 256k -movflags +faststart ram_parivar_clean_loop_6min_1080p.mp4')
print('ready')
