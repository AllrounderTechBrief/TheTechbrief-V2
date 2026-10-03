import random,math
random.seed(5);W,H=3840,2160
def ridge(base,amp,n,seed,jag=1.0):
    random.seed(seed);pts=[(0,H)];x=0
    step=W/n
    for i in range(n+1):
        y=base-amp*(0.5+0.5*math.sin(i*0.37+seed))*random.uniform(.5,1.1)*jag
        pts.append((i*step,y))
    pts.append((W,H));return ' '.join(f'{a:.0f},{b:.0f}' for a,b in pts)
stars=''.join(f'<circle cx="{random.uniform(0,W):.0f}" cy="{random.uniform(0,H*0.68)**1:.0f}" r="{random.choice([.7,.9,1.2,1.6,2.2]):.1f}" fill="#fff" opacity="{random.uniform(.25,.95):.2f}"/>' for _ in range(520))
kail_lit='1380,1500 1920,640 1960,640 2020,700 2060,720 2100,820 2160,900 2200,1500'
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#02030a"/><stop offset=".35" stop-color="#0a0f2e"/><stop offset=".62" stop-color="#241b52"/><stop offset=".8" stop-color="#6a3f5c"/><stop offset="1" stop-color="#d6955a"/></linearGradient>
<radialGradient id="moon" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fffdf0"/><stop offset=".7" stop-color="#f6e6b8"/><stop offset="1" stop-color="#e8cf95"/></radialGradient>
<radialGradient id="halo" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ffe8a8" stop-opacity=".55"/><stop offset="1" stop-color="#ffe8a8" stop-opacity="0"/></radialGradient>
<linearGradient id="litface" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f5ecd2"/><stop offset=".5" stop-color="#b9bde0"/><stop offset="1" stop-color="#4a4f8a"/></linearGradient>
<linearGradient id="shadeface" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5a5f9c"/><stop offset="1" stop-color="#171a45"/></linearGradient>
<linearGradient id="mist" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d9c3d8" stop-opacity="0"/><stop offset="1" stop-color="#e6b88a" stop-opacity=".55"/></linearGradient>
<filter id="b60"><feGaussianBlur stdDeviation="60"/></filter><filter id="b8"><feGaussianBlur stdDeviation="6"/></filter>
</defs>
<rect width="{W}" height="{H}" fill="url(#sky)"/>
{stars}
<circle cx="2950" cy="520" r="420" fill="url(#halo)"/>
<circle cx="2950" cy="520" r="150" fill="url(#moon)"/>
<polygon points="{ridge(1450,260,60,1)}" fill="#1b2150" opacity=".9"/>
<polygon points="{ridge(1560,300,48,2)}" fill="#141944"/>
<polygon points="1100,1620 1920,560 2740,1620" fill="url(#shadeface)"/>
<polygon points="1100,1620 1920,560 1930,1500 1700,1620" fill="url(#litface)" opacity=".95"/>
<polygon points="1760,930 1830,840 1860,880 1905,700 1920,560 1950,700 1990,860 2020,820 2060,900 2010,880 1970,930 1920,880 1880,940 1830,900" fill="#ffffff" opacity=".6"/>
<ellipse cx="1920" cy="1520" rx="1900" ry="260" fill="url(#mist)" filter="url(#b60)"/>
<polygon points="{ridge(1800,240,40,3,1.2)}" fill="#0b0d28"/>
<polygon points="{ridge(1960,200,36,4,1.4)}" fill="#04050f"/>
<ellipse cx="1920" cy="2100" rx="2100" ry="260" fill="url(#mist)" filter="url(#b60)" opacity=".7"/>
</svg>'''
open('kailash.svg','w').write(svg)
