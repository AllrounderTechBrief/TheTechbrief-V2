set -e
# base: slow push on Kailash (24s=720 frames), particles, bloom, text cards, then dissolve into Ram scene head
ffmpeg -v error -stats -y -loop 1 -framerate 30 -t 24 -i kailash.png -stream_loop -1 -i particles2.mp4 \
 -loop 1 -framerate 30 -t 24 -i k1.png -loop 1 -framerate 30 -t 24 -i k2.png -loop 1 -framerate 30 -t 24 -i k3.png -loop 1 -framerate 30 -t 24 -i k4.png -loop 1 -framerate 30 -t 24 -i k5.png -i head.mp4 \
 -filter_complex "
[0:v]zoompan=z='1.0+0.16*(on/720)':x='iw*0.5-iw/zoom/2':y='ih*0.52-ih/zoom/2':d=720:s=1920x1080:fps=30,eq=contrast=1.08:saturation=1.1,vignette=PI/5,format=gbrp,split[g1][g2];
[g2]scale=480:270,gblur=sigma=7,scale=1920:1080:flags=bicubic,format=gbrp[gb];[g1][gb]blend=all_mode=screen:all_opacity=0.25[bl];
[1:v]format=gbrp,trim=0:24,setpts=PTS-STARTPTS[pt];[bl][pt]blend=all_mode=screen:all_opacity=0.9,format=yuv420p[pv];
[2:v]format=rgba,fade=t=in:st=0.8:d=1.0:alpha=1,fade=t=out:st=4.0:d=0.9:alpha=1[c1];
[3:v]format=rgba,fade=t=in:st=5.0:d=1.0:alpha=1,fade=t=out:st=8.6:d=0.9:alpha=1[c2];
[4:v]format=rgba,fade=t=in:st=9.5:d=1.0:alpha=1,fade=t=out:st=14.1:d=0.9:alpha=1[c3];
[5:v]format=rgba,fade=t=in:st=15.0:d=1.0:alpha=1,fade=t=out:st=18.1:d=0.9:alpha=1[c4];
[6:v]format=rgba,fade=t=in:st=19.0:d=1.2:alpha=1,fade=t=out:st=21.8:d=0.7:alpha=1[c5];
[pv][c1]overlay=0:0:eof_action=pass[o1];[o1][c2]overlay=0:0:eof_action=pass[o2];[o2][c3]overlay=0:0:eof_action=pass[o3];[o3][c4]overlay=0:0:eof_action=pass[o4];[o4][c5]overlay=0:0:eof_action=pass,format=yuv420p[ib];
[ib][7:v]xfade=transition=fade:duration=1.5:offset=22.5,format=yuv420p[vout]" \
 -map "[vout]" -t 24 -c:v libx264 -preset veryfast -crf 19 -profile:v high -pix_fmt yuv420p -r 30 intro.mp4
