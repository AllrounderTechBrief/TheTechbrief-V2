const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--allow-file-access-from-files']});const p=await b.newPage({viewport:{width:1280,height:720}});
require('fs').writeFileSync('th.html',`<style>@font-face{font-family:NSD;font-weight:700;src:url(file://${path.resolve('f700.woff2')})}*{margin:0}body{width:1280px;height:720px;position:relative;overflow:hidden;background:#000;font-family:"Liberation Sans",sans-serif}
.bg{position:absolute;inset:0;background:url(file://${path.resolve('s5.png')}) center/cover;filter:saturate(1.2) contrast(1.08)}
.sh{position:absolute;inset:0;background:linear-gradient(90deg,rgba(0,0,0,.82) 0%,rgba(0,0,0,.45) 42%,transparent 70%)}
.t{position:absolute;left:50px;top:70px;font-family:NSD;font-weight:700;font-size:210px;line-height:1.25;padding-top:10px;background:linear-gradient(180deg,#FFF1B8,#F6B93B 55%,#C9821A);-webkit-background-clip:text;color:transparent;filter:drop-shadow(0 6px 16px #000)}
.s{position:absolute;left:56px;top:370px;font-size:64px;font-weight:800;color:#fff;letter-spacing:2px;text-shadow:0 4px 14px #000}
.b{position:absolute;left:56px;top:470px;padding:14px 30px;border-radius:12px;background:#E11D2E;color:#fff;font-size:44px;font-weight:800;box-shadow:0 6px 24px rgba(0,0,0,.6)}
.c{position:absolute;left:56px;top:570px;font-size:34px;color:#FFE9B0;font-weight:700;text-shadow:0 3px 10px #000}</style>
<div class="bg"></div><div class="sh"></div><div class="t">श्री राम</div><div class="s">RAM NAAM JAAP</div><div class="b">3 MIN · SHRI RAM PARIVAR</div><div class="c">Peaceful Bhakti · Chant Along 🙏</div>`);await p.goto('file://'+path.resolve('th.html'));
await p.waitForTimeout(800);await p.screenshot({path:'thumbnail.png'});await b.close()})();
