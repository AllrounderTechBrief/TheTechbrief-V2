import numpy as np, subprocess, sys, os, librosa, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.ndimage import gaussian_filter1d
SR=48000; rng=np.random.default_rng(11)
U,W=sys.argv[1],sys.argv[2]   # uploads dir, work dir
os.makedirs(W,exist_ok=True)
CHAIN=("highpass=f=75,afftdn=nr=8:nf=-45,equalizer=f=220:t=q:w=1.2:g=-2.5,equalizer=f=3200:t=q:w=1.0:g=2.2,"
       "equalizer=f=7500:t=q:w=3:g=-3,acompressor=threshold=-21dB:ratio=2.4:attack=12:release=180:makeup=3")
def clean(src,dst):
    subprocess.run(['ffmpeg','-v','error','-y','-i',src,'-af',CHAIN,'-ar',str(SR),'-ac','1',dst],check=True)
clean(f'{U}/4d666cc4-Starting.m4a',f'{W}/start_clean.wav'); clean(f'{U}/a23d1e32-Hanuman_chalisa_full_.m4a',f'{W}/full_clean.wav')
vs,_=librosa.load(f'{W}/start_clean.wav',sr=SR,mono=True); vf,_=librosa.load(f'{W}/full_clean.wav',sr=SR,mono=True)
CUT=18.95
vf=vf[int(CUT*SR):]
def fade(x,a=0.015,b=0.03):
    x=x.copy();n=int(a*SR);m=int(b*SR);x[:n]*=np.linspace(0,1,n);x[-m:]*=np.linspace(1,0,m);return x
def norm_rms(x,target_db=-19):
    r=np.sqrt(np.mean(x[np.abs(x)>0.02*np.abs(x).max()]**2)); return x*(10**(target_db/20)/r)
vs=fade(norm_rms(vs));vf=fade(norm_rms(vf))
T_START=6.5; T_FULL=64.0
tot=T_FULL+len(vf)/SR+14.0
N=int(tot*SR)
voc=np.zeros(N);voc[int(T_START*SR):int(T_START*SR)+len(vs)]+=vs;voc[int(T_FULL*SR):int(T_FULL*SR)+len(vf)]+=vf
def mt(tfull): return tfull-CUT+T_FULL
# ---------- tempo map ----------
L=np.load(f'{W}/lines.npy'); full_end=249.15
lines_m=[mt(x) for x in L]+[mt(full_end)]
# opening line starts from the slow take
y,_=librosa.load(f'{U}/4d666cc4-Starting.m4a',sr=16000,mono=True)
from scipy.signal import find_peaks
hop=160;rms=librosa.feature.rms(y=y,frame_length=800,hop_length=hop)[0];db=librosa.amplitude_to_db(rms+1e-9)
pk,_=find_peaks(-np.convolve(db,np.ones(5)/5,'same'),prominence=9,distance=int(4.0*16000/hop))
open_starts=[0.0]+[p*hop/16000 for p in pk if p*hop/16000>3]+[len(y)/16000]
open_starts=[T_START+x for x in open_starts]
# ---------- intensity ----------
Ik={1:.30,2:.32,3:.55,4:.40,5:.40,6:.42,7:.45,8:.48,9:.62,10:.68,11:.70,12:.65,13:.45,14:.42,15:.42,16:.45,17:.48,18:.78,19:.85,20:.82,
    21:.90,22:.92,23:.98,24:.98,25:.92,26:.82,27:.80,28:.78,29:.80,30:.78,31:.55,32:.50,33:.48,34:.45,35:.42,36:.45,37:1.0,38:.60,39:.35,40:.22}
line_I=[Ik[i//2+1] for i in range(80)]+[.12,.12]
def intensity_at(t):
    for i in range(82):
        if lines_m[i]<=t<lines_m[i+1]: return line_I[i]
    return 0.12 if t<T_FULL else 0.0
# ---------- instruments ----------
def tt(d): return np.arange(int(d*SR))/SR
def lp(x,f,o=2): return sosfilt(butter(o,f,'low',fs=SR,output='sos'),x)
def hp(x,f,o=2): return sosfilt(butter(o,f,'high',fs=SR,output='sos'),x)
def bp(x,a,b): return sosfilt(butter(2,[a,b],'band',fs=SR,output='sos'),x)
def noise(n): return rng.standard_normal(n)
def bayan(open_=1.0):
    t=tt(.9);f=88*(1+.45*np.exp(-t/.06));ph=2*np.pi*np.cumsum(f)/SR
    x=np.sin(ph)*np.exp(-t/(.28*open_))+.25*np.sin(2*ph)*np.exp(-t/.15)+lp(noise(len(t)),600)*np.exp(-t/.006)*.5
    return x
def dayan_na(F=330.0):
    t=tt(.35);x=(np.sin(2*np.pi*F*t)*np.exp(-t/.07)+.5*np.sin(2*np.pi*2*F*t)*np.exp(-t/.05)+.3*np.sin(2*np.pi*3*F*t)*np.exp(-t/.04))
    return x+bp(noise(len(t)),2000,6000)*np.exp(-t/.006)*.35
def dayan_ti():
    t=tt(.12);return bp(noise(len(t)),2500,6500)*np.exp(-t/.018)*.8+np.sin(2*np.pi*700*t)*np.exp(-t/.03)*.3
def dhol_bass():
    t=tt(.45);f=72*(1+.4*np.exp(-t/.04));ph=2*np.pi*np.cumsum(f)/SR
    return np.sin(ph)*np.exp(-t/.16)+lp(noise(len(t)),300)*np.exp(-t/.008)*.6
def dhol_tak():
    t=tt(.2);return bp(noise(len(t)),900,2600)*np.exp(-t/.03)+np.sin(2*np.pi*260*t)*np.exp(-t/.05)*.5
def pakhawaj():
    t=tt(1.0);f=60*(1+.5*np.exp(-t/.1));ph=2*np.pi*np.cumsum(f)/SR
    return np.sin(ph)*np.exp(-t/.4)+.3*np.sin(2*ph)*np.exp(-t/.22)+lp(noise(len(t)),500)*np.exp(-t/.01)*.5
def nagara():
    t=tt(1.6);f=46*(1+.3*np.exp(-t/.15));ph=2*np.pi*np.cumsum(f)/SR
    return np.sin(ph)*np.exp(-t/.7)+lp(noise(len(t)),200)*np.exp(-t/.02)*.6
def bell(f0=523.0,d=7.0):
    t=tt(d);rat=[1,2.0,2.76,4.07,5.4,8.93];dec=[6,4.5,3,2,1.4,.8];amp=[1,.6,.5,.3,.2,.1]
    x=sum(a*np.sin(2*np.pi*f0*r*t+rng.random()*6)*np.exp(-t/d_) for r,d_,a in zip(rat,dec,amp))
    return x*np.minimum(1,t/.002)
L_=np.zeros(N);R_=np.zeros(N)
def put(t,sig,amp,pl=.5,pr=.5):
    i=int(t*SR)
    if i<0 or i+len(sig)>=N: return
    L_[i:i+len(sig)]+=sig*amp*pl;R_[i:i+len(sig)]+=sig*amp*pr
def jit(): return rng.normal(0,.005)
def hum(): return 1+rng.normal(0,.07)
def bar(a,b,I,beats=6,tier_force=None):
    for j in range(beats):
        t=a+(b-a)*j/beats+jit(); h=hum()
        if I<.25:
            if j==0: put(t,bayan(1.3),.30*h*(.4+I*2),.6,.4)
            continue
        if j in(0,3): put(t,bayan(),(.45+.45*I)*h,.6,.4)
        put(t,dayan_na(),(.10+.22*I)*h*(1.0 if j not in(0,3) else .8),.4,.6) if I<.5 or j!=0 else put(t,dayan_na(),(.32+.2*I)*h,.4,.6)
        if I>=.5:
            if j in(0,3): put(t,dhol_bass(),(.40+.35*I)*h,.5,.5)
            if j in(1,4): put(t,dayan_ti(),.18*h,.35,.65)
        if I>=.75:
            if j==0: put(t,pakhawaj(),(.55+.3*I)*h,.5,.5)
            if j in(2,5): put(t,dhol_tak(),.28*h,.55,.45)
            put(t+(b-a)/beats/2+jit(),dayan_ti(),.11*h,.3,.7)
        if I>=.9:
            if j in(0,3): put(t,nagara(),.5*h,.5,.5)
            if j==5:
                for q in(1,2): put(t+(b-a)/beats*q/3,dayan_na(380),.22*h,.4,.6)
# opening: slow pulse
for a,b in zip(open_starts[:-1],open_starts[1:]):
    nb=max(4,int(round((b-a)/.857)))
    bar(a,b,.2,beats=nb)
# main
for i in range(82):
    a,b=lines_m[i],lines_m[i+1]
    bar(a,b,line_I[i],beats=6)
# bells
def kk(k): return lines_m[2*(k-1)]
bells=[(0.5,523,.5),(3.8,392,.25),(7.0,523,.15),(61.6,523,.45),(63.0,392,.25),(kk(9),523,.3),(kk(13),392,.2),(kk(18),523,.35),(kk(21),523,.4),(kk(26),392,.35),(kk(31),392,.25),
       (kk(37),523,.6),(kk(37)+.45,659,.35),(kk(37)+.9,784,.3),(kk(38),392,.2),(lines_m[80],392,.3),(tot-13.0,523,.55),(tot-10.0,392,.3)]
for t,f,a in bells: put(t,bell(f),a,.35 if f==523 else .65,.65 if f==523 else .35)
# ambience bed
n=N;amb=lp(noise(n),900,2)+0.6*lp(noise(n),300,2)
env=np.interp(np.arange(n)/SR,[0,6,T_FULL-4,T_FULL,tot-16,tot-6,tot],[.9,.35,.35,.25,.25,.9,0])
amb=amb*env*0.006
L_+=amb*(1+.1*np.sin(np.arange(n)/SR*.3));R_+=amb*(1-.1*np.sin(np.arange(n)/SR*.3))
# ---------- reverbs ----------
def ir(d,lpf,hpf,pre=0.0):
    t=tt(d);x=noise(len(t))*np.exp(-t*6.9/d);x=hp(lp(x,lpf),hpf);x=np.r_[np.zeros(int(pre*SR)),x];return x/np.sqrt((x**2).sum())
irm=ir(1.3,6000,150,.01);irv=ir(1.5,4500,250,.025)
def rev(x,ir_,wet):
    return x*(1-wet)+fftconvolve(x,ir_)[:len(x)]*wet*3.5
musL=rev(L_,irm,.22);musR=rev(R_,irm,.22)
# vocal reverb (wet 11%) mono->stereo
vr=fftconvolve(voc,irv)[:N]; vocL=voc*.9+vr*.11*3.0; vocR=voc*.9+np.r_[np.zeros(37),vr[:-37]]*.11*3.0
# ---------- sidechain duck + mix ----------
env=np.sqrt(gaussian_filter1d(voc**2,0.15*SR))
env=env/np.percentile(env[env>0.001],90);duck=1-.30*np.clip(env,0,1);duck=gaussian_filter1d(duck,0.05*SR)
rv=np.sqrt(np.mean(voc[np.abs(voc)>.01]**2));rm=np.sqrt(np.mean((musL**2+musR**2)/2))+1e-9
MG=(rv*10**(-12/20))/rm   # music at -12 dB vs vocal overall
mixL=vocL+musL*duck*MG;mixR=vocR+musR*duck*MG
stereo=np.stack([mixL,mixR],1);pk=np.abs(stereo).max();stereo=stereo/pk*.9
sf.write(f'{W}/mix_pre.wav',stereo,SR,subtype='PCM_24')
print('duration',round(tot,1),'peak',pk,'music gain',MG)
