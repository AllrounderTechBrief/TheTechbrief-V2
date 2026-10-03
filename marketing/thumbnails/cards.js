const {chromium}=require('playwright');const path=require('path');const fs=require('fs');
(async()=>{const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--allow-file-access-from-files']});
const css=`@font-face{font-family:NSD;font-weight:700;src:url(f700.woff2)}*{margin:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;background:transparent;font-family:"Liberation Sans",sans-serif;color:#fff;overflow:hidden}
.dv{font-family:NSD,serif;font-weight:700}.c{position:absolute;left:0;right:0;text-align:center;padding:0 70px}
.gold{background:linear-gradient(180deg,#FFF6C8,#FFD25A 50%,#E8981C);-webkit-background-clip:text;color:transparent;padding-top:50px;padding-bottom:16px;filter:drop-shadow(0 0 2px #3a0d00) drop-shadow(0 5px 0 #6b1d05) drop-shadow(0 10px 20px rgba(0,0,0,.7));line-height:1.15}
.sub{color:#FFE9B0;text-shadow:0 3px 0 #4a1405,0 0 16px #000;font-style:italic}
.white{color:#fff;text-shadow:0 4px 0 #5a1608,0 0 18px rgba(0,0,0,.85)}
.scrim{position:absolute;left:0;right:0;height:900px;background:linear-gradient(to top,rgba(10,4,0,.0),rgba(10,4,0,.0))}
.shade{position:absolute;inset:0;background:linear-gradient(to bottom,rgba(0,0,0,.55),rgba(0,0,0,0) 38%,rgba(0,0,0,0) 55%,rgba(0,0,0,.75))}
.badge{display:inline-block;padding:14px 40px 18px;border-radius:18px;background:linear-gradient(180deg,#e0212c,#9b0f18);border:5px solid #ffd25a;box-shadow:0 8px 0 #5a0a10,0 14px 28px rgba(0,0,0,.6);color:#fff3c4;white-space:nowrap}`;
async function shot(inner,file,omit=true){const p=await b.newPage({viewport:{width:1080,height:1920}});fs.writeFileSync('t.html',`<style>${css}</style><body>${inner}</body>`);await p.goto('file://'+path.resolve('t.html'));await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(400);await p.screenshot({path:file,omitBackground:omit});await p.close()}
const T=(top,hi,size,cls='gold')=>`<div class="c dv ${cls}" style="top:${top}px;font-size:${size}px">${hi}</div>`;
const E=(top,t,size)=>`<div class="c sub" style="top:${top}px;font-size:${size}px;line-height:1.3">${t}</div>`;
await shot('<div class="shade"></div>','shade.png');
// A
await shot(`${T(480,'शिवजी ने पार्वती<br>से कहा…',128)}${E(960,'Shiva told Parvati…',56)}`,'a1.png');
await shot(`${T(430,'राम का एक नाम',92,'white')}${T(560,'1000 नामों',170)}${T(790,'के बराबर!',140)}${E(1030,'One name of Rama equals a thousand names',44)}`,'a2.png');
await shot(`${T(1130,'श्री राम रामेति रामेति<br>रमे रामे मनोरमे ।',66,'gold')}${T(1330,'सहस्रनाम तत् तुल्यं<br>रामनाम वरानने ॥',66,'gold')}`,'a3.png');
await shot(`${T(1300,'॥ जय श्री राम ॥',118)}${E(1530,'Full jaap on the channel · Subscribe',46)}`,'a4.png');
// B
await shot(`${T(60,'श्री राम<br>रामेति',140)}`,'b1.png');
await shot(`${T(1230,'श्री राम रामेति रामेति<br>रमे रामे मनोरमे ।',64)}`,'b2.png');
await shot(`${T(1230,'श्री राम रामेति रामेति<br>रमे रामे मनोरमे ।',64)}${T(1400,'सहस्रनाम तत् तुल्यं<br>रामनाम वरानने ॥',64)}`,'b3.png');
await shot(`${T(1230,'श्री राम रामेति रामेति<br>रमे रामे मनोरमे ।',64)}${T(1400,'सहस्रनाम तत् तुल्यं<br>रामनाम वरानने ॥',64)}${E(1590,'“Rama’s name equals a thousand names.”',46)}`,'b4.png');
// C
await shot(`${T(1130,'सुबह का<br>पहला काम…',128)}${E(1590,'The first thing to do each morning…',48)}`,'c1.png');
await shot(`${T(1130,'1 मिनट<br>राम नाम',136)}${T(1560,'मन शांत, दिन शुभ 🙏',72,'white')}`,'c2.png');
await shot(`${T(1130,'श्री राम रामेति',124)}${T(1330,'॥ जय श्री राम ॥',92,'white')}${E(1530,'Full jaap on the channel · Subscribe',44)}`,'c3.png');
// covers
const r6=path.resolve('ram6.jpg'),sp='',k=path.resolve('kailash.png'),rp=path.resolve('ram.jpg');
const bgImg=(u,pos)=>`<div style="position:absolute;inset:0;background:url(file://${u}) ${pos}/cover"></div>`;
await shot(`${bgImg(r6,'50% 25%')}<div class="shade"></div>${T(130,'शिवजी का<br>दिव्य मंत्र',112,'white')}${T(1050,'श्री राम<br>रामेति',190)}<div class="c" style="top:1620px"><div class="badge dv" style="font-size:64px">1000 नामों के बराबर</div></div>`,'coverA.png',false);
await shot(`${bgImg(r6,'50% 20%')}<div class="shade"></div>${T(160,'श्री राम<br>रामेति',190)}<div class="c" style="top:1500px"><div class="badge dv" style="font-size:60px">सुनिए · जपिए · शांति पाइए</div></div>`,'coverB.png',false);
await shot(`${bgImg(rp,'38% 50%')}<div class="shade"></div>${T(140,'सुबह 1 मिनट<br>राम नाम',130)}${T(1250,'श्री राम रामेति',120,'white')}<div class="c" style="top:1500px"><div class="badge dv" style="font-size:60px">मन शांत, दिन शुभ</div></div>`,'coverC.png',false);
await b.close()})();
