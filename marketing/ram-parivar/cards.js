const {chromium}=require('playwright');const path=require('path');const fs=require('fs');
(async()=>{const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--allow-file-access-from-files']});
const css=`@font-face{font-family:NSD;font-weight:400;src:url(f400.woff2)}@font-face{font-family:NSD;font-weight:700;src:url(f700.woff2)}
*{margin:0;box-sizing:border-box}html,body{background:transparent;font-family:"Liberation Sans",sans-serif;color:#fff;overflow:hidden}
.dv{font-family:NSD,serif}.c{position:absolute;left:0;right:0;text-align:center;padding:0 200px;text-shadow:0 3px 22px rgba(0,0,0,.9)}
.gold{text-shadow:none!important;background:linear-gradient(180deg,#FFF1B8,#F6B93B 55%,#C9821A);-webkit-background-clip:text;color:transparent;filter:drop-shadow(0 4px 16px rgba(0,0,0,.8))}
.scrim{position:absolute;inset:0;background:radial-gradient(ellipse at center,rgba(0,0,0,.45),rgba(0,0,0,0) 70%)}`;
async function shot(inner,file,w=1920,h=1080,omit=true){const p=await b.newPage({viewport:{width:w,height:h}});fs.writeFileSync('t.html',`<style>${css}html,body{width:${w}px;height:${h}px}</style><body>${inner}</body>`);await p.goto('file://'+path.resolve('t.html'));await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(350);await p.screenshot({path:file,omitBackground:omit});await p.close()}
const card=(hi,en,hs=84,es=40,top=380)=>`<div class="scrim"></div><div class="c dv gold" style="top:${top}px;font-size:${hs}px;font-weight:700;line-height:1.35">${hi}</div><div class="c" style="top:${top+hs*1.4*(hi.split('<br>').length)+30}px;font-size:${es}px;color:#FFE9B0;font-style:italic;line-height:1.4">${en}</div>`;
await shot(card('कैलाश पर्वत की शांत रात्रि में…','On a still night upon Mount Kailash…'),'k1.png');
await shot(card('माता पार्वती ने भगवान शिव से पूछा —','Goddess Parvati asked Lord Shiva —'),'k2.png');
await shot(card('“प्रभु! विष्णु के सहस्र नामों का फल<br>एक सरल उपाय से कैसे मिले?”','“Is there one simple way to receive the merit of Vishnu’s thousand names?”',78,38,340),'k3.png');
await shot(card('शिव मुस्कुराए और बोले —','Shiva smiled, and said —'),'k4.png');
await shot(`<div class="scrim"></div><div class="c dv gold" style="top:300px;font-size:76px;font-weight:700;line-height:1.45">श्री राम रामेति रामेति रमे रामे मनोरमे ।<br>सहस्रनाम तत् तुल्यं रामनाम वरानने ॥</div><div class="c" style="top:560px;font-size:44px;color:#fff;line-height:1.4">“Rama’s name equals a thousand names.”</div><div class="c" style="top:640px;font-size:28px;letter-spacing:5px;color:#F6B93B">AS TOLD BY SHIVA TO PARVATI · VISHNU SAHASRANAMA TRADITION</div>`,'k5.png');
await b.close()})();
