(function(){
if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
var c=document.createElement('canvas');c.id='fx';c.setAttribute('aria-hidden','true');document.body.prepend(c);
var x=c.getContext('2d'),W,H,P=[],cols=['#f6c96b','#ffdf9a','#ff6f91','#ff9a3c','#d63aa8','#ffffff'],N=Math.min(46,Math.floor(innerWidth/22));
function size(){W=c.width=innerWidth;H=c.height=innerHeight}size();addEventListener('resize',size);
function mk(top){return{x:Math.random()*W,y:top?-20:Math.random()*H,s:4+Math.random()*7,v:.35+Math.random()*.9,w:Math.random()*2*Math.PI,ws:.01+Math.random()*.02,r:Math.random()*6.28,rs:(Math.random()-.5)*.06,c:cols[Math.random()*cols.length|0],t:Math.random()<.14?'n':(Math.random()<.5?'r':'o')}}
for(var i=0;i<N;i++)P.push(mk(false));
function step(){x.clearRect(0,0,W,H);for(var i=0;i<P.length;i++){var p=P[i];p.y+=p.v;p.w+=p.ws;p.x+=Math.sin(p.w)*.6;p.r+=p.rs;
if(p.y>H+20){P[i]=mk(true);continue}
x.save();x.translate(p.x,p.y);x.rotate(p.r);x.fillStyle=p.c;x.globalAlpha=.75;
if(p.t==='n'){x.font=(p.s*2.4)+'px serif';x.fillText('♪',0,0)}else if(p.t==='r'){x.fillRect(-p.s/2,-p.s/4,p.s,p.s/2)}else{x.beginPath();x.arc(0,0,p.s/3,0,6.28);x.fill()}
x.restore()}requestAnimationFrame(step)}
step();
})();
