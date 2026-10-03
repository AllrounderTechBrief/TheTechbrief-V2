import numpy as np, math, subprocess
W,H,FPS=1920,1080,30;NF=594;T=NF/FPS
rng=np.random.default_rng(7);N=140
x=rng.random(N)*W;y0=rng.random(N)*H;r=rng.uniform(2,9,N)
sp=(H/NF)*rng.integers(1,3,N);ph=rng.random(N)*6.283;sw=rng.uniform(8,30,N);al=rng.uniform(.35,1,N)
def sprite(rad):
    s=int(rad*6)|1;a=np.arange(s)-s//2;X,Y=np.meshgrid(a,a);return np.exp(-(np.sqrt(X**2+Y**2)/rad)**2*1.2)
cache=[sprite(rr) for rr in r]
p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-c:v','libx264','-crf','14','-pix_fmt','yuv420p','particles2.mp4'],stdin=subprocess.PIPE)
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
