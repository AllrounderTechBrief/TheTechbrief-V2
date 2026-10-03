import subprocess
L=21.333;XF=1.5;N=9;T=180;step=L-XF
wA=[];wB=[]
wA.append((9,16));wB.append((16.5,19.5))
for k in range(1,N):
    t=k*step
    wA.append((t+2.5,t+10.5))
    if k<N-1: wB.append((t+11.5,t+18.5))
wA[-1]=(N-1)*step+1.5,(N-1)*step+9
ins=''.join(f'-i shot{i}.mp4 ' for i in range(N))
ins+='-stream_loop -1 -i particles.mp4 '
for f in ['lyricA','lyricB','title','end']: ins+=f'-loop 1 -framerate 30 -t {T} -i {f}.png '
ins+='-i raw_audio.wav'
F=[]
# xfade chain
prev='[0:v]'
for k in range(1,N):
    off=round(k*step,3);out=f'[x{k}]'
    F.append(f'{prev}[{k}:v]xfade=transition=fade:duration={XF}:offset={off}{out}');prev=out
F.append(f'{prev}eq=contrast=1.06:saturation=1.12:gamma=1.02,vignette=PI/5,format=gbrp,split[g1][g2]')
F.append('[g2]scale=480:270,gblur=sigma=6,scale=1920:1080:flags=bicubic,format=gbrp[gb];[g1][gb]blend=all_mode=screen:all_opacity=0.22[bl]')
F.append(f'[9:v]format=gbrp,trim=0:{T},setpts=PTS-STARTPTS[pt];[bl][pt]blend=all_mode=screen:all_opacity=0.9,format=yuv420p[pv]')
cur='[pv]'
def win(src,idx,a,b,lab,d=0.9):
    F.append(f'{src}fade=t=in:st={a}:d={d}:alpha=1,fade=t=out:st={b-d}:d={d}:alpha=1[{lab}]')
F.append(f'[10:v]format=rgba,split={len(wA)}'+''.join(f'[a{i}]' for i in range(len(wA))))
F.append(f'[11:v]format=rgba,split={len(wB)}'+''.join(f'[b{i}]' for i in range(len(wB))))
F.append('[12:v]format=rgba[t0];[13:v]format=rgba[e0]')
ov=[]
win('[t0]',0,0.8,7.5,'tt',1.2);ov.append('tt')
for i,(a,b) in enumerate(wA): win(f'[a{i}]',i,round(a,2),round(b,2),f'la{i}');ov.append(f'la{i}')
for i,(a,b) in enumerate(wB): win(f'[b{i}]',i,round(a,2),round(b,2),f'lb{i}');ov.append(f'lb{i}')
F.append(f'[e0]fade=t=in:st=168:d=1.5:alpha=1[ee]');ov.append('ee')
for j,o in enumerate(ov):
    F.append(f'{cur}[{o}]overlay=0:0:format=auto:eof_action=pass[o{j}]');cur=f'[o{j}]'
F.append(f'{cur}fade=t=in:st=0:d=1.2,fade=t=out:st=178:d=2,format=yuv420p[vout]')
open('graph.txt','w').write(';\n'.join(F))
cmd=f'ffmpeg -v error -stats -y {ins} -filter_complex_script graph.txt -map "[vout]" -map 14:a -t {T} -c:v libx264 -preset medium -crf 18 -profile:v high -pix_fmt yuv420p -r 30 -c:a aac -b:a 192k -movflags +faststart ram_parivar_video_1080p.mp4'
open('run.sh','w').write(cmd)
