/* Geeth Upahar Motion Kit engine: vector write-on / draw-on / shimmer / sparkles. render(t) is deterministic. */
const NS='http://www.w3.org/2000/svg',W=SPEC.w,H=SPEC.h;
const E=t=>1-Math.pow(1-Math.max(0,Math.min(1,t)),3), EIO=t=>{t=Math.max(0,Math.min(1,t));return t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2};
const seg=(t,a,b)=>Math.max(0,Math.min(1,(t-a)/(b-a)));
const svg=document.getElementById('svg');svg.setAttribute('viewBox',`0 0 ${W} ${H}`);
const mk=(tag,at,par)=>{const e=document.createElementNS(NS,tag);for(const k in at)e.setAttribute(k,at[k]);(par||svg).appendChild(e);return e};
// ---- defs
const defs=mk('defs',{});
const bgG=mk('radialGradient',{id:'bgG',cx:'50%',cy:'30%',r:'90%'},defs);
SPEC.bg.forEach((c,i)=>mk('stop',{offset:[0,.55,1][i],'stop-color':c},bgG));
const gold=mk('linearGradient',{id:'gold',x1:0,y1:0,x2:0,y2:1},defs);
const goldStops=[['#fff3c4',0],['#f6c453',.45],['#c98a1a',1]].map(([c,o])=>mk('stop',{offset:o,'stop-color':c},gold));
const shine=mk('linearGradient',{id:'shine',gradientUnits:'userSpaceOnUse',x1:-200,y1:0,x2:0,y2:60},defs);
[['#fff',0],['#fff',.5],['#fff',1]].forEach(([c,o],i)=>mk('stop',{offset:o,'stop-color':c,'stop-opacity':i==1?.85:0},shine));
const glow=mk('filter',{id:'glow',x:'-50%',y:'-50%',width:'200%',height:'200%'},defs);
mk('feGaussianBlur',{stdDeviation:6,result:'b'},glow);const fm=mk('feMerge',{},glow);mk('feMergeNode',{in:'b'},fm);mk('feMergeNode',{in:'SourceGraphic'},fm);
mk('rect',{width:W,height:H,fill:'url(#bgG)'});
// ---- dust & rays
const rays=mk('g',{});
for(let i=0;i<12;i++)mk('path',{d:`M${W/2} ${H*.38} L${W/2-40} ${H} L${W/2+40} ${H}Z`,fill:`rgba(${SPEC.ray},.07)`,transform:`rotate(${i*30} ${W/2} ${H*.38})`},rays);
function R(s){let x=s;return()=>{x=(x*16807)%2147483647;return(x-1)/2147483646}}const rnd=R(11);
const dust=[...Array(46)].map(()=>{const o={x:rnd()*W,y:rnd()*H,s:.6+rnd()*1.8,v:6+rnd()*18,p:rnd()*6};o.e=mk('circle',{r:o.s,fill:'#ffe9a8'});return o});
const floaters=[...Array(14)].map((_,i)=>{const o={x:rnd()*W,v:30+rnd()*40,p:rnd()*9,sz:6+rnd()*9,sw:rnd()*6,kind:i%3};o.e=mk('path',{d:'M0 6 C-10 -4 -6 -10 0 -5 C6 -10 10 -4 0 6Z',fill:'#ff7aa8'});return o});
// ---- items
const items=[];
for(const it of SPEC.items){
  const g=mk('g',{});const o={it,g,paths:[]};
  if(it.type=='text'){
    g.setAttribute('transform',`translate(${it.x - (it.align=='center'?it.w/2:0)} ${it.y})`);
    it.glyphs.forEach(gl=>{const p=mk('path',{d:gl.d,fill:'url(#gold)','fill-opacity':0,stroke:it.stroke||'#ffe9a8','stroke-width':it.sw||1.6,'stroke-linejoin':'round','stroke-linecap':'round'},g);p.L=p.getTotalLength();p.setAttribute('stroke-dasharray',p.L);p.setAttribute('stroke-dashoffset',p.L);o.paths.push(p);});
    const sh=mk('g',{},g);o.shine=sh; // shimmer overlay (same glyphs filled with moving highlight)
    it.glyphs.forEach(gl=>mk('path',{d:gl.d,fill:'url(#shine)','fill-opacity':0},sh));
    o.pen=mk('circle',{r:3,fill:'#fff',stroke:'rgba(255,225,150,.45)','stroke-width':9,opacity:0},g);
  }else if(it.type=='path'){
    const p=mk('path',{d:it.d,fill:it.fill||'none','fill-opacity':0,stroke:it.stroke||'url(#gold)','stroke-width':it.sw||3,'stroke-linecap':'round','stroke-linejoin':'round',filter:it.glow?'url(#glow)':null},g);
    if(it.transform)g.setAttribute('transform',it.transform);
    p.L=p.getTotalLength();p.setAttribute('stroke-dasharray',p.L);p.setAttribute('stroke-dashoffset',p.L);o.paths.push(p);
    o.pen=mk('circle',{r:(it.pen||4)*.8,fill:'#fff',stroke:'rgba(255,225,150,.45)','stroke-width':10,opacity:0},g);
  }
  items.push(o);
}
function render(t){
  // gold gradient drift + shine sweep
  goldStops[1].setAttribute('offset',.38+.1*Math.sin(t*.8));
  const sw=((t*.45)%1.6-.3)*(W+300)-150;shine.setAttribute('x1',sw-120);shine.setAttribute('x2',sw+120);
  rays.setAttribute('transform',`rotate(${t*3} ${W/2} ${H*.38})`);
  dust.forEach(d=>{const y=(d.y-t*d.v+H*4)%H;d.e.setAttribute('cx',d.x);d.e.setAttribute('cy',y);d.e.setAttribute('opacity',.25+.6*Math.abs(Math.sin(t*2+d.p)))});
  floaters.forEach(f=>{const y=H+30-((t*f.v+f.p*60)%(H+80));const a=Math.min(1,seg(y,H,H-80))*Math.min(1,seg(y,-20,120))*.55;
    f.e.setAttribute('transform',`translate(${f.x+Math.sin(t*1.1+f.sw)*18} ${y}) scale(${f.sz/8}) rotate(${Math.sin(t+f.sw)*18})`);f.e.setAttribute('opacity',a)});
  for(const o of items){const it=o.it,T=t-it.t0;
    if(it.type=='text'){
      const n=o.paths.length,gd=Math.min(1.1,it.dur*.6),stag=n>1?(it.dur-gd)/(n-1):0;let pen=null,done=0;
      o.paths.forEach((p,i)=>{const p0=seg(T-i*stag,0,gd),e=EIO(p0);
        p.setAttribute('stroke-dashoffset',p.L*(1-e));
        const fa=seg(p0,.7,1);p.setAttribute('fill-opacity',E(fa));
        p.setAttribute('stroke-opacity',T<i*stag?0:(1-.75*fa));
        if(p0>0&&p0<1)pen={p,e};if(p0>=1)done++;});
      o.shine.setAttribute('opacity',done==n?1:0);o.shine.querySelectorAll('path').forEach(q=>q.setAttribute('fill-opacity',done==n?.22:0));
      if(pen){const pt=pen.p.getPointAtLength(pen.p.L*pen.e);o.pen.setAttribute('cx',pt.x);o.pen.setAttribute('cy',pt.y);o.pen.setAttribute('opacity',1)}else o.pen.setAttribute('opacity',0);
      const out=it.t1?seg(t,it.t1,it.t1+.5):0;o.g.setAttribute('opacity',(T>=-.01?1:0)*(1-out));
    }else{
      const p=o.paths[0],p0=seg(T,0,it.dur),e=EIO(p0);p.setAttribute('stroke-dashoffset',p.L*(1-e));
      if(it.fill)p.setAttribute('fill-opacity',E(seg(p0,.85,1))*(it.fillA||.9)*(1+.05*Math.sin(t*5)));
      if(p0>0&&p0<1){const pt=p.getPointAtLength(p.L*e);o.pen.setAttribute('cx',pt.x);o.pen.setAttribute('cy',pt.y);o.pen.setAttribute('opacity',1)}else o.pen.setAttribute('opacity',0);
      const out=it.t1?seg(t,it.t1,it.t1+.5):0;o.g.setAttribute('opacity',(T>=-.01?1:0)*(1-out));
    }}
}
window.render=render;render(0);
