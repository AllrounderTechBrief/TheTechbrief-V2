import numpy as np, soundfile as sf, subprocess
from scipy.signal import butter, sosfilt
SR=48000;rng=np.random.default_rng(3)
full,_=sf.read('full.wav',dtype='float32');tail,_=sf.read('tail.wav',dtype='float32')
if full.ndim==1: full=np.stack([full,full],1)
if tail.ndim==1: tail=np.stack([tail,tail],1)
X=3*SR;N=108
step=len(tail)-X
total=len(full)+(N-1)*step
out=np.zeros((total,2),np.float32)
def win(n,fin,fout):
    w=np.ones(n,np.float32)
    if fin: w[:X]=np.linspace(0,1,X)
    if fout: w[-X:]=np.linspace(1,0,X)
    return w[:,None]
out[:len(full)]+=full*win(len(full),False,True)
pos=len(full)-X
for k in range(1,N):
    seg=tail*win(len(tail),True,k<N-1)
    out[pos:pos+len(tail)]+=seg;pos+=step
print('total seconds',total/SR,flush=True)
# intro gain ramp: Ram Rameti present from the start, quiet, rising to full by 19s
t=np.arange(total)/SR
x=np.clip(t/19,0,1);ramp=0.30+0.70*(x*x*(3-2*x));out*=ramp[:,None].astype(np.float32)
# intro sfx
def bell(f0,d=7.0):
    tt=np.arange(int(d*SR))/SR;rat=[1,2.0,2.76,4.07,5.4,8.93];dec=[6,4.5,3,2,1.4,.8];amp=[1,.6,.5,.3,.2,.1]
    return sum(a*np.sin(2*np.pi*f0*r*tt+rng.random()*6)*np.exp(-tt/d_) for r,d_,a in zip(rat,dec,amp))*np.minimum(1,tt/.002)
sfx=np.zeros((26*SR,2),np.float32)
for tb,f,a in [(0.8,523,.30),(5.2,392,.20),(9.7,392,.20),(15.2,523,.22),(19.0,523,.38),(19.5,659,.2)]:
    b=bell(f).astype(np.float32);i=int(tb*SR);n=min(len(b),len(sfx)-i);sfx[i:i+n,0]+=b[:n]*a*.6;sfx[i:i+n,1]+=b[:n]*a*.4
# soft night wind: filtered noise with slow swell
wn=rng.standard_normal(len(sfx)).astype(np.float32)
wn=sosfilt(butter(2,[200,1400],'band',fs=SR,output='sos'),wn)
sw=0.5+0.5*np.sin(np.arange(len(sfx))/SR*0.7)
env=np.interp(np.arange(len(sfx))/SR,[0,2,20,26],[0,1,1,0])
wind=(wn*sw*env*0.020).astype(np.float32)
sfx[:,0]+=wind;sfx[:,1]+=wind[::-1]*0.9
out[:len(sfx)]+=sfx
sf.write('mix108.wav',out,SR,subtype='PCM_16')
