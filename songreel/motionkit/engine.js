/* Geeth Upahar Motion Kit v2 - deterministic render(t). Items: text, path, lights, fireworks, balloons. Audio-reactive via SPEC.energy. */
const NS='http://www.w3.org/2000/svg',W=SPEC.w,H=SPEC.h,FPS=SPEC.fps||24;
const E=t=>1-Math.pow(1-Math.max(0,Math.min(1,t)),3),EIO=t=>{t=Math.max(0,Math.min(1,t));return t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2};
const seg=(t,a,b)=>Math.max(0,Math.min(1,(t-a)/(b-a)));
const EN=t=>{const a=SPEC.energy;if(!a)return .3+.2*Math.sin(t*6);const i=Math.max(0,Math.min(a.length-1,Math.round(t*FPS)));return a[i]},
      BT=t=>{const a=SPEC.beat;if(!a)return Math.pow(1-((t*2)%1),3);const i=Math.max(0,Math.min(a.length-1,Math.round(t*FPS)));return a[i]};
const svg=document.getElementById('svg');svg.setAttribute('viewBox',`0 0 ${W} ${H}`);
const mk=(tag,at,par)=>{const e=document.createElementNS(NS,tag);for(const k in at)if(at[k]!==null&&at[k]!==undefined)e.setAttribute(k,at[k]);(par||svg).appendChild(e);return e};
function R(s){let x=s;return()=>{x=(x*16807)%2147483647;return(x-1)/2147483646}}const rnd=R(SPEC.seed||11);
const defs=mk('defs',{});
const bgG=mk('radialGradient',{id:'bgG',cx:'50%',cy:'34%',r:'90%'},defs);SPEC.bg.forEach((c,i)=>mk('stop',{offset:[0,.55,1][i],'stop-color':c},bgG));
const gold=mk('linearGradient',{id:'gold',x1:0,y1:0,x2:0,y2:1},defs);const gs=SPEC.gold.map((c,i)=>mk('stop',{offset:[0,.5,1][i],'stop-color':c},gold));
const shine=mk('linearGradient',{id:'shine',gradientUnits:'userSpaceOnUse',x1:-200,y1:0,x2:0,y2:60},defs);[0,.5,1].forEach(o=>mk('stop',{offset:o,'stop-color':'#fff','stop-opacity':o==.5?.85:0},shine));
const glow=mk('filter',{id:'glow',x:'-50%',y:'-50%',width:'200%',height:'200%'},defs);mk('feGaussianBlur',{stdDeviation:6,result:'b'},glow);const fm=mk('feMerge',{},glow);mk('feMergeNode',{in:'b'},fm);mk('feMergeNode',{in:'SourceGraphic'},fm);
const soft=mk('filter',{id:'soft',x:'-100%',y:'-100%',width:'300%',height:'300%'},defs);mk('feGaussianBlur',{stdDeviation:14},soft);
const grain=mk('filter',{id:'grain',x:0,y:0,width:'100%',height:'100%'},defs);mk('feTurbulence',{type:'fractalNoise',baseFrequency:.9,numOctaves:2,seed:3},grain);mk('feColorMatrix',{type:'matrix',values:'0 0 0 0 1  0 0 0 0 .95  0 0 0 0 .85  0 0 0 .5 -.12'},grain);
mk('rect',{width:W,height:H,fill:'url(#bgG)'});
const rays=mk('g',{});for(let i=0;i<(SPEC.nrays||12);i++)mk('path',{d:`M${W/2} ${H*.38} L${W/2-40} ${H} L${W/2+40} ${H}Z`,fill:`rgba(${SPEC.ray},.08)`,transform:`rotate(${i*360/(SPEC.nrays||12)} ${W/2} ${H*.38})`},rays);
const halo=mk('circle',{cx:W/2,cy:H*.45,r:240,fill:`rgba(${SPEC.ray},.16)`,filter:'url(#soft)'});
const dust=[...Array(44)].map(()=>{const o={x:rnd()*W,y:rnd()*H,s:.6+rnd()*1.8,v:6+rnd()*18,p:rnd()*6};o.e=mk('circle',{r:o.s,fill:SPEC.dust||'#ffe9a8'});return o});
const fl=SPEC.floaters,floaters=fl?[...Array(fl.n)].map((_,i)=>{const o={x:rnd()*W,v:28+rnd()*44,p:rnd()*9,sz:fl.size*(.6+rnd()*.8),sw:rnd()*6,c:fl.colors?fl.colors[i%fl.colors.length]:fl.fill};o.e=mk('path',{d:fl.d,fill:o.c},null);return o}):[];
const items=[];
for(const it of SPEC.items){const g=mk('g',{});const o={it,g,paths:[]};
 if(it.type=='text'){g.setAttribute('transform',`translate(${it.x-(it.align=='center'?it.w/2:0)} ${it.y})`);
  it.glyphs.forEach(gl=>{const p=mk('path',{d:gl.d,fill:'url(#gold)','fill-opacity':0,stroke:it.stroke||SPEC.gold[0],'stroke-width':it.sw||1.6,'stroke-linejoin':'round','stroke-linecap':'round'},g);p.L=p.getTotalLength();p.setAttribute('stroke-dasharray',p.L);p.setAttribute('stroke-dashoffset',p.L);o.paths.push(p)});
  o.shine=mk('g',{},g);it.glyphs.forEach(gl=>mk('path',{d:gl.d,fill:'url(#shine)','fill-opacity':0},o.shine));
  o.pen=mk('circle',{r:3,fill:'#fff',stroke:'rgba(255,225,150,.45)','stroke-width':9,opacity:0},g);
 }else if(it.type=='path'){
  const base=it.transform||'';if(base)g.setAttribute('transform',base);
  const p=mk('path',{d:it.d,fill:it.fill||'none','fill-opacity':0,stroke:it.stroke||'url(#gold)','stroke-width':it.sw||3,'stroke-linecap':'round','stroke-linejoin':'round',filter:it.glow?'url(#glow)':null,opacity:it.alpha||1},g);
  p.L=p.getTotalLength();if(it.mode!='fade'){p.setAttribute('stroke-dasharray',p.L);p.setAttribute('stroke-dashoffset',p.L)}
  o.paths.push(p);o.pen=mk('circle',{r:(it.pen||4)*.8,fill:'#fff',stroke:'rgba(255,225,150,.45)','stroke-width':10,opacity:0},g);
 }else if(it.type=='lights'){it.pts.forEach((pt,i)=>{const c=it.colors[i%it.colors.length];const b=mk('circle',{cx:pt[0],cy:pt[1],r:7,fill:c,filter:'url(#glow)',opacity:0},g);b.c=c;o.paths.push(b)});mk('path',{d:it.wire,fill:'none',stroke:'rgba(255,230,170,.55)','stroke-width':1.6},g);
 }else if(it.type=='fireworks'){o.parts=[];it.bursts.forEach(b=>{const r=R(Math.round(b.t*100)+5);const ps=[];for(let k=0;k<(b.n||34);k++){const a=k/(b.n||34)*6.283+r()*.2,s=(b.s||120)*(.55+r()*.45);ps.push({a,s,e:mk('circle',{r:2.4,fill:b.c,opacity:0},g)})}o.parts.push({b,ps})});
 }else if(it.type=='balloons'){o.bs=[...Array(it.n)].map((_,i)=>{const c=it.colors[i%it.colors.length];const gg=mk('g',{},g);mk('path',{d:'M0 22 C4 40 -4 56 0 82',fill:'none',stroke:'rgba(255,255,255,.55)','stroke-width':1.3},gg);mk('ellipse',{cx:0,cy:0,rx:18,ry:23,fill:c},gg);mk('path',{d:'M-3 22 L3 22 L0 27Z',fill:c},gg);mk('ellipse',{cx:-6,cy:-8,rx:3.5,ry:6,fill:'rgba(255,255,255,.38)',transform:'rotate(25 -6 -8)'},gg);return{g:gg,x:30+rnd()*480,v:44+rnd()*40,p:rnd()*14,sw:rnd()*6,s:.9+rnd()*.9}});}
 items.push(o)}
mk('rect',{width:W,height:H,filter:'url(#grain)',opacity:.35,style:'mix-blend-mode:overlay'});
function render(t){
 const en=EN(t),bt=BT(t);
 gs[1].setAttribute('offset',.4+.08*Math.sin(t*.8));
 const sw=((t*.45)%1.6-.3)*(W+300)-150;shine.setAttribute('x1',sw-120);shine.setAttribute('x2',sw+120);
 rays.setAttribute('transform',`rotate(${t*3} ${W/2} ${H*.38})`);rays.setAttribute('opacity',.6+.8*en);
 halo.setAttribute('opacity',.35+.65*en);halo.setAttribute('r',230+40*en+20*bt);
 dust.forEach(d=>{const y=(d.y-t*d.v+H*4)%H;d.e.setAttribute('cx',d.x);d.e.setAttribute('cy',y);d.e.setAttribute('r',d.s*(1+.8*en));d.e.setAttribute('opacity',.25+.6*Math.abs(Math.sin(t*2+d.p)))});
 floaters.forEach(f=>{const y=(fl.dir=='down')?-30+((t*f.v+f.p*60)%(H+80)):H+30-((t*f.v+f.p*60)%(H+80));const a=Math.min(1,seg(y,H,H-80))*Math.min(1,seg(y,-20,120))*.6;
  f.e.setAttribute('transform',`translate(${f.x+Math.sin(t*1.1+f.sw)*22} ${y}) scale(${f.sz/8}) rotate(${Math.sin(t+f.sw)*30})`);f.e.setAttribute('opacity',a)});
 for(const o of items){const it=o.it,T=t-it.t0;const out=it.t1?seg(t,it.t1,it.t1+.5):0;const vis=(T>=-.01?1:0)*(1-out);
  if(it.type=='text'){
   const n=o.paths.length,gd=Math.min(1.1,it.dur*.6),stag=n>1?(it.dur-gd)/(n-1):0;let pen=null,done=0;
   o.paths.forEach((p,i)=>{const p0=seg(T-i*stag,0,gd),e=EIO(p0);p.setAttribute('stroke-dashoffset',p.L*(1-e));const fa=seg(p0,.7,1);p.setAttribute('fill-opacity',E(fa));p.setAttribute('stroke-opacity',T<i*stag?0:(1-.75*fa));if(p0>0&&p0<1)pen={p,e};if(p0>=1)done++});
   o.shine.querySelectorAll('path').forEach(q=>q.setAttribute('fill-opacity',done==n?.22:0));
   if(pen){const pt=pen.p.getPointAtLength(pen.p.L*pen.e);o.pen.setAttribute('cx',pt.x);o.pen.setAttribute('cy',pt.y);o.pen.setAttribute('opacity',1)}else o.pen.setAttribute('opacity',0);
   o.g.setAttribute('opacity',vis);
  }else if(it.type=='path'){
   const p=o.paths[0],p0=seg(T,0,it.dur),e=EIO(p0);
   if(it.mode=='fade'){p.setAttribute('stroke-opacity',E(p0));p.setAttribute('fill-opacity',E(p0)*(it.fillA||0))}
   else{p.setAttribute('stroke-dashoffset',p.L*(1-e));if(it.fill)p.setAttribute('fill-opacity',E(seg(p0,.85,1))*(it.fillA||.9)*(1+(it.pulse||0)*(.3*en+.4*bt)))}
   if(it.mode!='fade'&&p0>0&&p0<1){const pt=p.getPointAtLength(p.L*e);o.pen.setAttribute('cx',pt.x);o.pen.setAttribute('cy',pt.y);o.pen.setAttribute('opacity',1)}else o.pen.setAttribute('opacity',0);
   let tr=it.transform||'';if(it.spin)tr+=` rotate(${t*it.spin} ${it.cx} ${it.cy})`;if(it.beatscale)tr+=` translate(${it.cx} ${it.cy}) scale(${1+it.beatscale*bt}) translate(${-it.cx} ${-it.cy})`;if(tr)o.g.setAttribute('transform',tr);
   o.g.setAttribute('opacity',vis);
  }else if(it.type=='lights'){o.g.setAttribute('opacity',vis*seg(T,0,1));o.paths.forEach((b,i)=>{const tw=.55+.45*Math.sin(t*3+i*1.7);b.setAttribute('opacity',Math.min(1,tw*(.6+en)));b.setAttribute('r',6+4*en*((i%3)==0?1:.4))});
  }else if(it.type=='fireworks'){o.parts.forEach(({b,ps})=>{const k=t-b.t;ps.forEach(q=>{if(k<0||k>1.8){q.e.setAttribute('opacity',0);return}const d=q.s*(1-Math.pow(1-k/1.8,2));q.e.setAttribute('cx',b.x+Math.cos(q.a)*d);q.e.setAttribute('cy',b.y+Math.sin(q.a)*d+60*k*k);q.e.setAttribute('opacity',Math.max(0,1-k/1.8));q.e.setAttribute('r',3*(1-k/2.2))})});
  }else if(it.type=='balloons'){o.g.setAttribute('opacity',vis);o.bs.forEach(b=>{const y=H+60-(((t-it.t0)*b.v+b.p*70)%(H+220));b.g.setAttribute('transform',`translate(${b.x+Math.sin(t*1.3+b.sw)*14} ${y}) scale(${b.s}) rotate(${Math.sin(t*1.1+b.sw)*6})`)});}
 }}
window.render=render;render(0);
