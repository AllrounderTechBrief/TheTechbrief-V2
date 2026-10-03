#!/bin/bash
# usage: make_reels.sh <assets_dir> <src_dir> <out_dir>
set -e
A=$1; U=$2; O=$3; mkdir -p $O
enc="-c:v libx264 -preset slow -crf 16 -profile:v high -pix_fmt yuv420p -r 30 -movflags +faststart -c:a aac -b:a 128k"
common() { echo "-loop 1 -framerate 30 -t $1 -i $A/bg.png"; }

# REMOVE BACKGROUND: 6.8s action + 2.6s end card
ffmpeg -v error -y -i $U/7f084d71-Real_remove_background.mp4 $(common 9.4) -i $A/remove_mask.png -i $A/remove_fg.png -i $A/remove_cap0.png -i $A/remove_cap1.png -i $A/remove_cap2.png -loop 1 -framerate 30 -t 14 -i $A/end.png -f lavfi -i anullsrc=r=44100:cl=stereo -filter_complex "
[0:v]crop=1056:919:700:56,scale=920:800:flags=lanczos,fps=30,split=3[a][b][c];
[a]trim=0:2.4,setpts=PTS-STARTPTS[v1];[b]trim=2.4:7.2,setpts=(PTS-STARTPTS)/4[v2];[c]trim=7.2,setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=4[v3];
[v1][v2][v3]concat=n=3:v=1:a=0,format=yuv420p[vid];
[2:v]crop=920:800:80:590,format=gray[m];[vid][m]alphamerge[vm];
[1:v]format=yuv420p[bg];[bg][vm]overlay=80:590[t0];
[t0][3:v]overlay=0:0[t1];
[t1][4:v]overlay=0:0:enable='between(t,0,2.4)'[t2];[t2][5:v]overlay=0:0:enable='between(t,2.4,4.6)'[t3];[t3][6:v]overlay=0:0:enable='gte(t,4.6)'[t4];
[7:v]format=rgba,fade=in:st=6.8:d=0.4:alpha=1[e];[t4][e]overlay=0:0:enable='gte(t,6.8)'[o]" -map "[o]" -map 8:a -t 9.4 $enc $O/vista-reel-remove-background-9x16.mp4

# COLLAGE: 15s at 1.4x ≈ 10.7s + 2.6s end card
ffmpeg -v error -y -i $U/24fcac31-Drag_and_drop_collage.mp4 $(common 13.4) -i $A/collage_mask.png -i $A/collage_fg.png -i $A/collage_cap0.png -i $A/collage_cap1.png -i $A/collage_cap2.png -loop 1 -framerate 30 -t 14 -i $A/end.png -f lavfi -i anullsrc=r=44100:cl=stereo -filter_complex "
[0:v]crop=1340:896:60:70,scale=920:615:flags=lanczos,setpts=PTS/1.4,fps=30,tpad=stop_mode=clone:stop_duration=4,format=yuv420p[vid];
[2:v]crop=920:615:80:660,format=gray[m];[vid][m]alphamerge[vm];
[1:v]format=yuv420p[bg];[bg][vm]overlay=80:660[t0];
[t0][3:v]overlay=0:0[t1];
[t1][4:v]overlay=0:0:enable='between(t,0,2.2)'[t2];[t2][5:v]overlay=0:0:enable='between(t,2.2,8)'[t3];[t3][6:v]overlay=0:0:enable='gte(t,8)'[t4];
[7:v]format=rgba,fade=in:st=10.8:d=0.4:alpha=1[e];[t4][e]overlay=0:0:enable='gte(t,10.8)'[o]" -map "[o]" -map 8:a -t 13.4 $enc $O/vista-reel-collage-9x16.mp4
