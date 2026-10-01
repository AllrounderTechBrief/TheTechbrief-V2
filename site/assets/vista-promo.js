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
})();
