const {chromium}=require('playwright');const path=require('path');const fs=require('fs');
(async()=>{const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--allow-file-access-from-files']});
const css=`@font-face{font-family:NSD;font-weight:400;src:url(f400.woff2)}@font-face{font-family:NSD;font-weight:700;src:url(f700.woff2)}
*{margin:0;box-sizing:border-box}html,body{background:transparent;font-family:"Liberation Sans",sans-serif;color:#fff;overflow:hidden}
.dv{font-family:NSD,serif}.c{position:absolute;left:0;right:0;text-align:center;text-shadow:0 3px 18px rgba(0,0,0,.85)}
.gold{text-shadow:none!important;background:linear-gradient(180deg,#FFF1B8,#F6B93B 55%,#C9821A);-webkit-background-clip:text;color:transparent;filter:drop-shadow(0 4px 14px rgba(0,0,0,.7))}`;
async function shot(inner,file,w=1920,h=1080,omit=true,extra=''){const p=await b.newPage({viewport:{width:w,height:h}});fs.writeFileSync('t.html',`<style>${css}html,body{width:${w}px;height:${h}px}${extra}</style><body>${inner}</body>`);await p.goto('file://'+path.resolve('t.html'));await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(400);await p.screenshot({path:file,omitBackground:omit});await p.close()}
await shot(`<div style="position:absolute;left:0;right:0;bottom:0;height:520px;background:linear-gradient(to top,rgba(10,4,0,.85),transparent)"></div>
<div class="c dv gold" style="top:610px;font-size:150px;font-weight:700;line-height:1.25">श्री हनुमान चालीसा</div>
<div class="c" style="top:850px;font-size:40px;letter-spacing:9px;color:#FFE9B0;font-weight:700">SHRI HANUMAN CHALISA</div>
<div class="c dv" style="top:925px;font-size:36px;color:#fff">॥ जय बजरंगबली · जय श्री राम ॥</div>`,'title.png');
await shot(`<div style="position:absolute;left:70px;bottom:70px;padding:12px 28px;border-radius:12px;background:rgba(10,4,0,.6);border:1px solid rgba(246,185,59,.6);color:#F6B93B;font-size:48px;font-weight:700;text-shadow:0 2px 10px #000">॥ दोहा ॥</div>`,'tag_doha.png');
await shot(`<div style="position:absolute;left:70px;bottom:70px;padding:12px 28px;border-radius:12px;background:rgba(10,4,0,.6);border:1px solid rgba(246,185,59,.6);color:#F6B93B;font-size:48px;font-weight:700;text-shadow:0 2px 10px #000">॥ चौपाई ॥</div>`,'tag_chaupai.png');
await shot(`<div style="position:absolute;inset:0;background:rgba(10,4,0,.62)"></div>
<div class="c dv gold" style="top:220px;font-size:170px;font-weight:700;line-height:1.25">॥ जय बजरंगबली ॥</div>
<div class="c" style="top:500px;font-size:48px;font-weight:700">Like 👍 · Share 🙏 · Subscribe for daily bhakti</div>
<div class="c" style="top:590px;font-size:34px;color:#FFE9B0">Comment “Jai Bajrangbali” and share with someone who needs strength today</div>
<div style="position:absolute;left:50%;top:700px;transform:translateX(-50%);padding:22px 70px;border-radius:18px;background:linear-gradient(135deg,#E11D2E,#B91C1C);font-size:46px;font-weight:800;box-shadow:0 10px 40px rgba(0,0,0,.6)">SUBSCRIBE</div>`,'end.png');
// thumbnail
await shot(`<div style="position:absolute;inset:0;background:url(file://${path.resolve('th_bg.png')}) center/cover;filter:saturate(1.25) contrast(1.1)"></div><div style="position:absolute;inset:0;background:linear-gradient(90deg,rgba(0,0,0,.82),rgba(0,0,0,.4) 45%,transparent 70%)"></div>
<div class="dv gold" style="position:absolute;left:50px;top:40px;font-size:150px;font-weight:700;line-height:1.3">हनुमान<br>चालीसा</div>
<div style="position:absolute;left:56px;top:470px;font-size:56px;font-weight:800;text-shadow:0 4px 14px #000">FULL · POWERFUL BHAKTI</div>
<div style="position:absolute;left:56px;top:560px;padding:14px 30px;border-radius:12px;background:#E11D2E;font-size:44px;font-weight:800;box-shadow:0 6px 24px rgba(0,0,0,.6)">जय बजरंगबली 🙏</div>`,'thumbnail.png',1280,720,false);
await b.close()})();
