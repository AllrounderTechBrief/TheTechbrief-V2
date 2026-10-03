import subprocess,os
S=os.getcwd()
def run(c): subprocess.run(c,shell=True,check=True)
# 16:9 prepared 3840x2160 sources
def prep16(src,out):
    run(f'ffmpeg -v error -y -i {src} -vf "crop=\'min(iw,ih*16/9)\':\'min(ih,iw*9/16)\',scale=3840:2160:flags=lanczos,unsharp=5:5:0.6" -frames:v 1 {out}')
prep16('3.jpg','s3.png');prep16('4.jpg','s4.png');prep16('5.webp','s5.png')
# portrait composite: blurred fill + centered sharp portrait
run('''ffmpeg -v error -y -i 6.jpg -filter_complex "[0:v]split[a][b];[a]scale=3840:-2:flags=lanczos,crop=3840:2160,gblur=sigma=60,eq=brightness=-0.12:saturation=1.15[bg];[b]scale=-2:1980:flags=lanczos,unsharp=5:5:0.7[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2" -frames:v 1 s6.png''')
FPS=30;L=21.333;D=int(L*FPS)
# (img, z0,z1, cx0,cy0, cx1,cy1)
shots=[('s3',1.00,1.12,.50,.50,.50,.45),
       ('s6',1.00,1.10,.50,.52,.50,.40),
       ('s4',1.12,1.00,.40,.55,.52,.50),
       ('s5',1.00,1.22,.50,.50,.42,.55),
       ('s3',1.30,1.30,.72,.45,.55,.45),
       ('s5',1.18,1.45,.56,.55,.52,.38),
       ('s4',1.00,1.28,.50,.50,.50,.45),
       ('s3',1.50,1.25,.34,.72,.42,.60),
       ('s5',1.30,1.00,.50,.55,.50,.50)]
for i,(im,z0,z1,x0,y0,x1,y1) in enumerate(shots):
    p=f'(on/{D})';e=f'({p}*{p}*(3-2*{p}))'
    z=f'({z0}+({z1}-{z0})*{e})';cx=f'({x0}+({x1}-{x0})*{e})';cy=f'({y0}+({y1}-{y0})*{e})'
    zp=f"zoompan=z='{z}':x='max(0,min(iw-iw/zoom,{cx}*iw-iw/zoom/2))':y='max(0,min(ih-ih/zoom,{cy}*ih-ih/zoom/2))':d={D}:s=1920x1080:fps={FPS}"
    run(f'ffmpeg -v error -y -i {im}.png -vf "{zp},format=yuv420p" -c:v libx264 -crf 12 -preset fast -t {L} shot{i}.mp4')
    print('shot',i)
