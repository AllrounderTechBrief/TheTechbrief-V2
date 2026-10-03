set -e
TOT=$(ffprobe -v error -show_entries format=duration -of csv=p=0 master108.wav)
P=$(python3 -c "print(round($TOT-24.0-10*356.4,2))")
echo "tail seconds $P"
ffmpeg -v error -y -t $P -i loop.mp4 -an -vf "fade=t=out:st=$(python3 -c "print(round($P-8,2))"):d=8" -c:v libx264 -preset veryfast -crf 19 -profile:v high -pix_fmt yuv420p -r 30 tail.mp4
{ echo "file 'intro.mp4'"; for i in 1 2 3 4 5 6 7 8 9 10; do echo "file 'loop.mp4'"; done; echo "file 'tail.mp4'"; } > list.txt
ffmpeg -v error -y -f concat -safe 0 -i list.txt -i master108.wav -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 256k -movflags +faststart ram_rameti_108_cinematic_1080p.mp4
echo FINALDONE
