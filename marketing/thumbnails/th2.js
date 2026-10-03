const {chromium}=require('playwright');const path=require('path');const fs=require('fs');
(async()=>{const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--allow-file-access-from-files']});
const base=`@font-face{font-family:NSD;font-weight:700;src:url(f700.woff2)}*{margin:0;box-sizing:border-box}
html,body{width:1280px;height:720px;overflow:hidden;background:#000;font-family:"Liberation Sans",sans-serif;color:#fff}
.bg{position:absolute;inset:0;background:radial-gradient(900px 600px at 70% 40%,#ffb340,#d9560f 55%,#5a1608 100%)}
.rays{position:absolute;inset:-200px;background:repeating-conic-gradient(from 0deg at 70% 45%,rgba(255,235,170,.14) 0 6deg,transparent 6deg 14deg);mix-blend-mode:screen}
.vig{position:absolute;inset:0;background:radial-gradient(ellipse at 60% 50%,transparent 55%,rgba(0,0,0,.55))}
.dv{font-family:NSD,serif;font-weight:700}
.hero{background:linear-gradient(180deg,#FFF6C8,#FFD25A 50%,#E8981C);-webkit-background-clip:text;color:transparent;-webkit-text-stroke:0;filter:drop-shadow(0 0 2px #3a0d00) drop-shadow(0 5px 0 #6b1d05) drop-shadow(0 10px 18px rgba(0,0,0,.6));line-height:1.12;padding-top:60px;padding-bottom:20px}
.top{color:#fff;text-shadow:0 3px 0 #5a1608,0 0 14px rgba(0,0,0,.7);}
.badge{display:inline-block;padding:10px 30px 14px;border-radius:14px;background:linear-gradient(180deg,#e0212c,#9b0f18);border:4px solid #ffd25a;box-shadow:0 8px 0 #5a0a10,0 12px 24px rgba(0,0,0,.6);color:#fff3c4;white-space:nowrap}
.art{position:absolute;border:6px solid #ffd25a;border-radius:10px;box-shadow:0 0 0 3px #7a2a06,0 18px 40px rgba(0,0,0,.65);background-size:cover}
.ring{position:absolute;border:7px solid #ffd25a;border-radius:50%;box-shadow:0 0 0 3px #7a2a06,0 10px 28px rgba(0,0,0,.6);background-size:cover;background-position:50% 22%}`;
async function render(name,html){const p=await b.newPage({viewport:{width:1280,height:720}});fs.writeFileSync('t.html',`<style>${base}</style><body>${html}</body>`);await p.goto('file://'+path.resolve('t.html'));await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(500);await p.screenshot({path:name+'.png'});await p.close()}
const sp=path.resolve('shivparvati.jpg');const r6=path.resolve('ram6.jpg');const r3=path.resolve('ram.jpg');
const insetSP=(l,t,w)=>`<div class="ring" style="left:${l}px;top:${t}px;width:${w}px;height:${w}px;background-image:url(file://${sp});background-size:${w*1.9}px;background-position:-${w*0.38}px -${w*0.05}px"></div><div class="dv" style="position:absolute;left:${l-20}px;top:${t+w+6}px;width:${w+40}px;text-align:center;font-size:30px;color:#fff;text-shadow:0 2px 0 #5a1608,0 0 10px #000">शिवजी → पार्वती</div>`;
// A: Ram portrait big left, text right, Shiva-Parvati small inset bottom right of text zone
await render('A',`<div class="bg"></div><div class="rays"></div>
<div class="art" style="left:28px;top:22px;width:540px;height:676px;background-image:url(file://${r6});background-position:50% 30%;filter:saturate(1.08) contrast(1.05)"></div>
<div class="dv top" style="position:absolute;left:600px;top:22px;font-size:44px;width:660px;line-height:1.2">शिवजी ने पार्वती से कहा…</div>
<div class="dv hero" style="position:absolute;left:590px;top:70px;font-size:184px;width:700px;line-height:1.02">श्री राम<br>रामेति</div>
<div style="position:absolute;left:600px;top:575px"><div class="badge dv" style="font-size:54px">1000 नामों के बराबर</div></div>
${insetSP(1040,330,170)}<div class="vig"></div>`);
// B: Ram parivar wide right, big; text left; small inset
await render('B',`<div class="bg"></div><div class="rays"></div>
<div class="art" style="left:600px;top:22px;width:652px;height:676px;background-image:url(file://${r3});background-size:auto 100%;background-position:42% 50%;filter:saturate(1.08) contrast(1.05)"></div>
<div class="dv top" style="position:absolute;left:40px;top:24px;font-size:44px;width:560px;line-height:1.2">शिवजी ने पार्वती से कहा…</div>
<div class="dv hero" style="position:absolute;left:34px;top:74px;font-size:186px;width:620px;line-height:1.02">श्री राम<br>रामेति</div>
<div style="position:absolute;left:44px;top:575px"><div class="badge dv" style="font-size:52px">1000 नामों के बराबर</div></div>
${insetSP(1068,420,150)}<div class="vig"></div>`);
// C: Ram close-up large right (face), text left, inset small
await render('C',`<div class="bg"></div><div class="rays"></div>
<div class="art" style="left:640px;top:0;width:640px;height:720px;border-radius:0;border-width:0 0 0 8px;background-image:url(file://${r6});background-size:640px auto;background-position:50% 18%;filter:saturate(1.1) contrast(1.06)"></div>
<div class="dv top" style="position:absolute;left:40px;top:24px;font-size:44px;width:600px;line-height:1.2">शिवजी ने पार्वती से कहा…</div>
<div class="dv hero" style="position:absolute;left:30px;top:76px;font-size:178px;width:640px;line-height:1.02">श्री राम<br>रामेति</div>
<div style="position:absolute;left:44px;top:575px"><div class="badge dv" style="font-size:52px">1000 नामों के बराबर</div></div>
${insetSP(1070,455,150)}<div class="vig"></div>`);
await b.close()})();
