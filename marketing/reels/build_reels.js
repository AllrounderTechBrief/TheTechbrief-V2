const {chromium}=require('playwright');const fs=require('fs');const path=require('path');
const OUT=process.argv[2];fs.mkdirSync(OUT,{recursive:true});
const URL='vistaimagestudio.thestreamic.in';
const base=`*{box-sizing:border-box;margin:0}html,body{width:1080px;height:1920px;background:transparent;font-family:"Liberation Sans",Arial,sans-serif;color:#fff}`;
const grad='linear-gradient(90deg,#22D3EE,#A78BFA)';
const specs={
 remove:{panel:{x:80,y:590,w:920,h:800},hook:'Messy photo<br>background?<br><span>Gone in one click.</span>',chips:['✂️ AI Background Removal','⚡ Optimize','🔍 Upscale 2×'],
  caps:[[0,2.4,'Messy background?'],[2.4,4.6,'AI cuts it out…'],[4.6,99,'Done. One click ✨']]},
 collage:{panel:{x:80,y:660,w:920,h:615},hook:'Make a photo<br>collage in<br><span>seconds.</span>',chips:['🖼️ Collage Templates','⚡ Optimize','🔍 Upscale 2×'],
  caps:[[0,2.2,'Pick a layout'],[2.2,8,'Drag &amp; drop your photos'],[8,99,'Collage done ✨']]}
};
(async()=>{const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium'});const p=await b.newPage({viewport:{width:1080,height:1920}});
async function shot(html,file,omit=true){await p.setContent(`<style>${base}</style>${html}`);await p.waitForTimeout(150);await p.screenshot({path:path.join(OUT,file),omitBackground:omit})}
const bgcss=`background:radial-gradient(900px 700px at 90% 8%,rgba(139,92,246,.55),transparent 65%),radial-gradient(900px 700px at 0% 100%,rgba(34,211,238,.35),transparent 65%),#0B0B16`;
await shot(`<div style="position:absolute;inset:0;${bgcss}"></div>`,'bg.png',false);
for(const [k,s] of Object.entries(specs)){const P=s.panel;
 await shot(`<div style="position:absolute;inset:0;background:#000"></div><div style="position:absolute;left:${P.x}px;top:${P.y}px;width:${P.w}px;height:${P.h}px;border-radius:28px;background:#fff"></div>`,`${k}_mask.png`,false);
 await shot(`
 <div style="position:absolute;left:80px;top:190px;right:80px;font-size:92px;line-height:1.02;font-weight:800;letter-spacing:-2px;text-shadow:0 4px 30px rgba(0,0,0,.4)">${s.hook.replace('<span>',`<span style="background:${grad};-webkit-background-clip:text;color:transparent">`)}</div>
 <div style="position:absolute;left:${P.x-8}px;top:${P.y-8}px;width:${P.w+16}px;height:${P.h+16}px;border-radius:34px;border:3px solid rgba(255,255,255,.35);box-shadow:0 30px 90px rgba(37,99,235,.55),0 0 0 1px rgba(0,0,0,.4)"></div>
 <div style="position:absolute;left:${P.x+20}px;top:${P.y+20}px;padding:8px 16px;border-radius:9px;background:rgba(0,0,0,.65);font-size:22px;font-weight:800;letter-spacing:1.5px"><span style="color:#EF4444">●</span> REAL APP · SCREEN RECORDING</div>
 <div style="position:absolute;left:80px;top:${P.y+P.h+44}px;width:920px;display:flex;gap:10px;flex-wrap:nowrap">${s.chips.map(c=>`<span style="padding:11px 18px;border-radius:999px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);font-size:26px;font-weight:700;white-space:nowrap">${c}</span>`).join('')}</div>
 <div style="position:absolute;left:80px;top:${P.y+P.h+150}px;width:920px;height:104px;border-radius:24px;background:linear-gradient(135deg,#2563EB,#7C3AED);display:flex;align-items:center;justify-content:center;gap:16px;font-size:44px;font-weight:800;box-shadow:0 16px 50px rgba(37,99,235,.6)">Try it FREE — link in bio →</div>
 <div style="position:absolute;left:80px;top:${P.y+P.h+280}px;width:920px;text-align:center;font-size:26px;color:rgba(255,255,255,.7)">No signup · Runs in your browser · ${URL}</div>`,`${k}_fg.png`);
 for(let i=0;i<s.caps.length;i++)await shot(`<div style="position:absolute;left:0;right:0;top:${P.y+P.h-130}px;display:flex;justify-content:center"><div style="padding:18px 36px;border-radius:20px;background:rgba(10,10,20,.82);border:2px solid rgba(255,255,255,.25);font-size:50px;font-weight:800;box-shadow:0 10px 40px rgba(0,0,0,.5)">${s.caps[i][2]}</div></div>`,`${k}_cap${i}.png`);
}
await shot(`<div style="position:absolute;inset:0;${bgcss};display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 80px">
 <div style="width:200px;height:200px;border-radius:48px;background:linear-gradient(135deg,#2563EB,#7C3AED);display:flex;align-items:center;justify-content:center;font-size:110px;box-shadow:0 20px 80px rgba(124,58,237,.7)">✨</div>
 <div style="margin-top:50px;font-size:96px;font-weight:800;letter-spacing:-2px;line-height:1.05">Vista<br>Image Studio</div>
 <div style="margin-top:26px;font-size:42px;color:rgba(255,255,255,.8)">Free AI photo editor in your browser</div>
 <div style="margin-top:60px;padding:30px 70px;border-radius:28px;background:linear-gradient(135deg,#2563EB,#7C3AED);font-size:60px;font-weight:800;box-shadow:0 16px 60px rgba(37,99,235,.6)">Try it FREE</div>
 <div style="margin-top:34px;font-size:40px;font-weight:700;color:#22D3EE">Link in bio ↑</div>
 <div style="margin-top:14px;font-size:30px;color:rgba(255,255,255,.65)">${URL}</div></div>`,'end.png',false);
await b.close()})();
