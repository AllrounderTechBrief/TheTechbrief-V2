(function(){
var V={hero:["Vista Image Studio: remove backgrounds, upscale and optimize photos in your browser. Free to try.","Need a cleaner photo? Our own AI photo editor does background removal, upscaling and optimizing. Free to try."],
article_card:["Editing photos for your own site or channel? Try our AI background remover and upscaler. Free.","Built by us: AI background removal, upscaling and optimize in your browser. Free to try."]};
function ev(n,d){try{window.umami&&window.umami.track&&window.umami.track(n,d)}catch(e){}}
var v='A';try{v=localStorage.getItem('vp_v');if(v!=='A'&&v!=='B'){v=Math.random()<.5?'A':'B';localStorage.setItem('vp_v',v)}}catch(e){v='A'}
document.querySelectorAll('[data-vista-promo]').forEach(function(el){
var p=el.getAttribute('data-vista-promo'),a=el.tagName==='A'?el:el.querySelector('a'),t=el.querySelector('.vista-promo-text');
if(v==='B'){if(a)a.href=a.href.replace('utm_term=A','utm_term=B');if(t&&V[p])t.textContent=V[p][1]}
function view(){ev('vista_promo_view',{placement:p,variant:v})}
if('IntersectionObserver' in window){var o=new IntersectionObserver(function(e){if(e[0].isIntersecting){view();o.disconnect()}},{threshold:.5});o.observe(el)}
if(a)a.addEventListener('click',function(){ev('vista_promo_click',{utm_content:p,placement:p,variant:v,destination:a.getAttribute('data-dest')||el.getAttribute('data-dest')})});
});

if('IntersectionObserver' in window){var vo=new IntersectionObserver(function(es){es.forEach(function(e){var m=e.target;if(e.isIntersecting){if(!m.dataset.l){m.dataset.l=1;m.load()}m.play&&m.play().catch(function(){})}else m.pause()})},{threshold:.35});document.querySelectorAll('.vad-screen video').forEach(function(m){m.removeAttribute('autoplay');vo.observe(m)})}
document.querySelectorAll('[data-vad-demo]').forEach(function(d){var r=d.querySelector('input');r.addEventListener('input',function(){d.style.setProperty('--pos',r.value+'%')});var t=0,n=0;(function a(){if(d.dataset.used)return;n=(n+.03)%6.283;var x=50+Math.sin(n)*18;d.style.setProperty('--pos',x+'%');r.value=x;t=requestAnimationFrame(a)})();['pointerdown','touchstart','keydown'].forEach(function(e){r.addEventListener(e,function(){d.dataset.used=1;cancelAnimationFrame(t)},{once:true})})});
(function(){var K='vad_bar_x';try{if(Date.now()-(+localStorage.getItem(K)||0)<864e5)return}catch(e){}
if(document.querySelector('.vad-bar'))return;
var u='https://vistaimagestudio.thestreamic.in/?utm_source=thetechbrief&utm_medium=owned_media&utm_campaign=vista_launch&utm_content=sticky_bar&utm_term='+v;
var b=document.createElement('div');b.className='vad-bar';b.setAttribute('data-vista-promo','sticky_bar');b.setAttribute('data-dest','https://vistaimagestudio.thestreamic.in/');b.setAttribute('role','complementary');
b.innerHTML='<div class="vad-bar-ico">✨</div><div class="vad-bar-txt"><strong>Remove backgrounds in one click. Free.</strong><span>Vista Image Studio, our AI photo editor</span></div><a class="vad-cta" rel="noopener" href="'+u+'">Try Free</a><button type="button" aria-label="Close">×</button>';
var shown=false;function show(){if(shown)return;shown=true;document.body.appendChild(b);requestAnimationFrame(function(){requestAnimationFrame(function(){b.classList.add('show')})});ev('vista_promo_view',{placement:'sticky_bar',variant:v})}
b.querySelector('button').addEventListener('click',function(){b.classList.remove('show');try{localStorage.setItem(K,Date.now())}catch(e){}});
b.querySelector('a').addEventListener('click',function(){ev('vista_promo_click',{utm_content:'sticky_bar',placement:'sticky_bar',variant:v,destination:'https://vistaimagestudio.thestreamic.in/'})});
setTimeout(show,10000);window.addEventListener('scroll',function(){if(scrollY>innerHeight*.5)show()},{passive:true});})();
})();
