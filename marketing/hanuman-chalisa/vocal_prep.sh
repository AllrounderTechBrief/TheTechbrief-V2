#!/bin/bash
# usage: vocal_prep.sh in.(wav|m4a) out.m4a   -- dry-vocal polish only, no pitch/time change
ffmpeg -v error -y -i "$1" -af "\
highpass=f=75,\
afftdn=nr=8:nf=-45,\
equalizer=f=220:t=q:w=1.2:g=-2.5,\
equalizer=f=3200:t=q:w=1.0:g=2.2,\
equalizer=f=7500:t=q:w=3:g=-3,\
acompressor=threshold=-21dB:ratio=2.4:attack=12:release=180:makeup=3,\
aecho=0.85:0.25:42|71|113:0.16|0.11|0.07,\
alimiter=limit=0.89,\
loudnorm=I=-16:TP=-1.5:LRA=8" -ar 48000 -ac 2 -c:a aac -b:a 192k "$2"
