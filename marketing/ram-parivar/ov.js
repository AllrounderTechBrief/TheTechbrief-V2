const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--allow-file-access-from-files']});const p=await b.newPage({viewport:{width:1920,height:1080}});
const base=path.resolve('ov.html');
async function shot(inner,file){await p.goto('file://'+base);await p.evaluate(h=>{document.body.innerHTML=h},inner);await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(300);await p.screenshot({path:file,omitBackground:true})}
await shot(`<div class="scrim"></div>
<div class="c dv gold" style="bottom:300px;font-size:76px;font-weight:700;line-height:1.35">श्री राम रामेति रामेति रमे रामे मनोरमे ।<br>सहस्रनाम तत् तुल्यं रामनाम वरानने ॥</div>
<div class="c" style="bottom:190px;font-size:34px;letter-spacing:.5px;color:#FFE9B0;font-style:italic;line-height:1.5">Shri Rama Rameti Rameti, Rame Rame Manorame<br>Sahasranama Tat Tulyam, Rama-Nama Varanane</div>`,'lyricA.png');
await shot(`<div class="scrim"></div>
<div class="c" style="bottom:210px;font-size:30px;letter-spacing:6px;color:#F6B93B;font-weight:700">MEANING</div>
<div class="c" style="bottom:120px;font-size:44px;line-height:1.4;padding:0 260px;color:#fff">Chanting “Rama, Rama”, I rejoice in the divine name —<br>the single name of Rama equals a thousand names of the Lord.</div>`,'lyricB.png');
await shot(`<div style="position:absolute;inset:0;background:radial-gradient(ellipse at center,rgba(0,0,0,.35),rgba(0,0,0,.65))"></div>
<div class="c dv gold" style="top:300px;font-size:230px;font-weight:700;line-height:1.1">श्री राम</div>
<div class="c" style="top:600px;font-size:46px;letter-spacing:10px;color:#FFE9B0;font-weight:700">RAM NAAM JAAP</div>
<div class="c dv" style="top:690px;font-size:40px;color:#fff">श्री राम रामेति रामेति रमे रामे मनोरमे</div>
<div class="c" style="top:770px;font-size:26px;color:#F6B93B;letter-spacing:3px">SHRI RAM PARIVAR · SITA · LAKSHMAN · HANUMAN</div>`,'title.png');
await shot(`<div style="position:absolute;inset:0;background:rgba(10,4,0,.62)"></div>
<div class="c dv gold" style="top:230px;font-size:190px;font-weight:700;line-height:1.1">॥ जय श्री राम ॥</div>
<div class="c" style="top:520px;font-size:48px;color:#fff;font-weight:700">Like 👍 · Share 🙏 · Subscribe for daily bhakti</div>
<div class="c" style="top:610px;font-size:34px;color:#FFE9B0">Chant “Shri Ram” with us — comment “Jai Shri Ram” below</div>
<div style="position:absolute;left:50%;top:720px;transform:translateX(-50%);padding:22px 70px;border-radius:18px;background:linear-gradient(135deg,#E11D2E,#B91C1C);font-size:46px;font-weight:800;box-shadow:0 10px 40px rgba(0,0,0,.6)">SUBSCRIBE</div>`,'end.png');
await b.close()})();
