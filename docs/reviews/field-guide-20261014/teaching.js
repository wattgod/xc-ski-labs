(function(){'use strict';
const assetPath=path=>window.GUIDE_ASSETS?.[path]||path;
const brand=document.body.dataset.brand,el=id=>document.getElementById(id);let choice=0,step=0,labels=true;
const modes={gravel:['Climbing','Surface','Race logistics'],road:['Hazard ahead','Changing pace','Before a corner'],ski:['V1','V2','V2 alternate','Classic stride']};
const lessons={gravel:[['Read the climbing','Check the total gain alongside distance and the recorded course description.','Use the named race profile to check the event edition and the sources behind its demands.'],['Read the surface','Smooth gravel, loose corners and sustained rough terrain ask different things of your handling and equipment.','Match your practice terrain to the event description. A high score is a flag to investigate the course.'],['Read the logistics','Travel, supplies, access and entry commitments belong in the race decision.','Check the current organizer information before committing. A course rating does not confirm this year’s logistics.']],road:[['Communicate early','Point out a hazard while leaving space for the riders behind you to react.','Look ahead. Keep changes gradual, and avoid overlapping wheels.'],['Change pace gradually','An abrupt change can travel through the group.','Agree on the purpose and pace before riding, then practise the change in a controlled group.'],['Choose position before the corner','Look ahead and make a predictable choice while there is space.','Wind and corners do not give you permission to cross the centre line or squeeze through a gap.']],ski:[['Both poles and the poling-side ski meet together','V1 uses a poling side in a two-skate cycle. The course’s cue is “3–1.”','Check that the other side still transfers weight and contributes to the movement.'],['Double pole, push. Repeat on both sides.','For V2, the pole plant leads the skate push.','Compare the sequence on each side; the rhythm repeats symmetrically.'],['Pole–glide–drive','V2 alternate keeps a distinct glide phase.','Coordinate the arm return with the skate back toward the poling side.'],['Opposite arm and leg','Commit your weight to one gliding ski before the next stride.','Use the original diagonal-stride drills and a short video to review balance and glide.']]};
function node(tag,attrs,text){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs||{}).forEach(([k,v])=>n.setAttribute(k,k==='href'?assetPath(v):v));if(text)n.textContent=text;return n;}
function drawLegacy(){const svg=el('scene-diagram');svg.replaceChildren();el('scene-label').textContent=modes[brand][choice]+' / '+(brand==='ski'?'timing schematic':'situation schematic');svg.setAttribute('aria-label',modes[brand][choice]+', step '+(step+1));const add=(tag,a,t)=>svg.append(node(tag,a,t));
 if(brand==='gravel'){const races=[{"name": "Unbound 200", "scores": [5, 4, 4]}, {"name": "Mid South", "scores": [2, 2, 3]}, {"name": "Crusher in the Tushar", "scores": [5, 4, 3]}];const metric=['Elevation','Technicality','Logistics'][choice];races.forEach((r,i)=>{const y=55+i*72;const score=Number(r.scores[choice]);if(labels)add('text',{x:22,y:y-12},r.name);for(let j=0;j<5;j++)add('rect',{x:24+j*78,y,width:58,height:22,class:j<score?'mark':'notch'});if(labels)add('text',{x:428,y:y+17},score+'/5');});if(labels)add('text',{x:22,y:252},metric.toUpperCase()+' · CATALOGUE RATINGS');
 }else if(brand==='road'){add('path',{d:'M70 15V245M430 15V245',class:'thin',fill:'none'});for(let i=0;i<5;i++){let y=220-i*38;let x=choice===2?240+i*12:250;add('circle',{cx:x,cy:y,r:11,class:i===step?'accent':'notch'});}if(choice===0)add('path',{d:'M290 70L315 110H265Z',class:'mark'});if(choice===1)add('path',{d:'M340 190V90M330 105L340 90L350 105',class:'heavy'});if(choice===2)add('path',{d:'M170 200Q170 70 360 55',class:'heavy','stroke-dasharray':'7 5'});if(labels){add('text',{x:85,y:28},'STAY IN YOUR LANE');add('text',{x:85,y:245},'SPACING IS SCHEMATIC');}
 }else{const sx=choice===1?(step<2?190:310):(step%2===0?190:310);add('path',{d:'M175 65L195 200M325 65L305 200',class:'heavy'});add('circle',{cx:sx,cy:155,r:18,class:'accent'});let pole=(choice===0&&step%2===0)||(choice===1&&step%2===0)||(choice===2&&step===0)||(choice===3&&step%2===0);if(pole){add('path',{d:'M120 70L150 180M380 70L350 180',class:'heavy'});add('circle',{cx:150,cy:180,r:7,class:'mark'});add('circle',{cx:350,cy:180,r:7,class:'mark'});}if(labels){add('text',{x:160,y:235},'LEFT');add('text',{x:290,y:235},'RIGHT');add('text',{x:35,y:26},'TIMING ONLY · NOT A BODY MODEL');}}
 const l=lessons[brand][choice];el('step-label').textContent=['Notice','Prepare','Execute','Review'][step];el('scene-answer').textContent=l[0];el('scene-explanation').textContent=l[1]+' '+l[2];el('coach').src=assetPath('assets/coach-'+(step===3?'arms_crossed':'point')+'.svg');el('labels').textContent=labels?'Labels on':'Labels off';el('labels').setAttribute('aria-pressed',String(labels));
}
// Brand teaching scenes: explicit situations and contact phases, not dots.
let comparison=false,polingSide=1,playTimer=null;
const roadSteps=[
 [['Spot the hazard','Look through the rider ahead.'],['Signal while holding your line','Give the riders behind time to respond.'],['Move gradually within the lane','Keep room for the rider beside you.'],['Let the warning travel back','Every rider still looks ahead.']],
 [['Keep a steady group','The riders have room to react.'],['Increase pace progressively','Make the change readable to the next wheel.'],['Let the group settle','Avoid snapping the gap shut.'],['Review the group behind','A surge is not a substitute for a shared pace.']],
 [['Look through the corner','Choose position while there is space.'],['Set speed before turning','Keep both wheels inside your lane.'],['Follow a predictable arc','Avoid squeezing between another rider and the edge.'],['Exit without a sudden surge','Let the group re-form with space.']]
];
const skiSteps=[
 [['Plant + load the poling ski','Both poles and the poling-side ski meet together.'],['Push from the loaded ski','Move across; do not stay between the skis.'],['Glide on the other ski','The non-poling side carries your weight too.'],['Recover for the next plant','Return the arms as you move to the poling side.']],
 [['Pole, then push left','The pole plant leads the skate push.'],['Glide left; recover the arms','Balance on the ski you are riding.'],['Pole, then push right','Repeat the same rhythm on the other side.'],['Glide right; recover the arms','One double pole accompanies each skate push.']],
 [['Pole before the poling-side push','One double-pole action in a two-skate cycle.'],['Hold the glide','Give the loaded ski a clear glide phase.'],['Push from the other ski','There is no second pole plant on this side.'],['Bring the arms forward','Recover toward the next poling-side cycle.']],
 [['Glide left; right pole','Opposite arm and leg work together.'],['Kick and move forward','Finish the transfer before rushing the next stride.'],['Glide right; left pole','Swap the supporting ski and opposite arm.'],['Kick and return','Keep the alternating rhythm.']]
];
function teachingDraw(){
 const svg=el('scene-diagram'),mobile=window.innerWidth<701,W=mobile?520:720,H=520;
 svg.setAttribute('viewBox',`0 0 ${W} ${H}`);svg.replaceChildren();
 const add=(tag,a,t)=>{let n=node(tag,a,t);svg.append(n);return n;};
 const text=(x,y,t,size=20,extra={})=>add('text',{x,y,style:`font-size:${size}px`,...extra},t);
 const path=(d,stroke='#263842',width=4,fill='none',extra={})=>add('path',{d,stroke,'stroke-width':width,fill,'stroke-linecap':'round','stroke-linejoin':'round',...extra});
 const computed=getComputedStyle(document.documentElement),ink=computed.getPropertyValue('--ink').trim(),accent=computed.getPropertyValue('--accent').trim();
 const defs=node('defs'),marker=node('marker',{id:'teaching-arrow',viewBox:'0 0 10 10',refX:8,refY:5,markerWidth:6,markerHeight:6,orient:'auto-start-reverse'});marker.append(node('path',{d:'M0 0L10 5L0 10Z',fill:accent}));defs.append(marker);svg.append(defs);

 add('rect',{x:0,y:0,width:W,height:H,fill:brand==='ski'?'#f7f4ed':'#f6f4ed'});
 let title,explanation;
 if(brand==='road'){
  const lane=W*.31,right=W-25,own=(lane+right)/2;
  add('rect',{x:24,y:36,width:W-48,height:390,rx:22,fill:'#dddeda'});
  path(`M${lane} 38V425`,'#c3ad71',3,'none',{'stroke-dasharray':'16 13'});
  path(`M${right} 45V415`,'#fafaf5',4);path('M28 45V415','#fafaf5',4);
  if(labels){text(44,68,'ONCOMING',mobile?22:17);text(lane+20,68,'YOUR LANE',mobile?22:19);}
  path(`M75 125V190`,ink,3,'none',{'marker-end':'url(#teaching-arrow)'});
  function rider(x,y,color,rotation=0,number=null){
   const g=node('g',{transform:`translate(${x} ${y}) rotate(${rotation})`});
   g.append(node('image',{href:`assets/road-rider-${step===1&&number===1?'signal':'normal'}.png`,x:-47,y:-57,width:94,height:108}));
   if(number===1)g.append(node('ellipse',{cx:0,cy:0,rx:37,ry:49,fill:'none',stroke:accent,'stroke-width':2,'stroke-dasharray':'5 5'}));
   if(number!==null){g.append(node('circle',{cx:32,cy:0,r:13,fill:'#fff',stroke:ink}));g.append(node('text',{x:32,y:5,'text-anchor':'middle',style:'font-size:15px'},number));}
   svg.append(g);
  }

  if(choice===0){
   const hazardX=own+45;add('path',{d:`M${hazardX-22} 113L${hazardX+20} 104L${hazardX+29} 124L${hazardX+8} 137L${hazardX-24} 129Z`,fill:'#9b7260',stroke:'#685348','stroke-width':2});
   const shift=step<2?0:-45;
   [0,1,2].forEach(i=>rider(own+shift+(comparison&&step===2&&i===0?70:0),177+i*90, i===0?accent:'#72848a',step===2?(comparison?24:-8):0,i+1));
   if(step>0){path(`M${own-25} 174L${own-65} 154`,accent,4,'none',{'marker-end':'url(#teaching-arrow)'});if(labels)text(lane+15,102,'EARLY SIGNAL',mobile?22:20);}
   if(step>=2)path(`M${own} 385Q${own-80} 270 ${own-50} 100`,accent,4,'none',{'stroke-dasharray':'8 8','marker-end':'url(#teaching-arrow)'});
   if(comparison&&step>=2){path(`M${own+90} 140L${own+120} 180M${own+120} 140L${own+90} 180`,'#ad4933',5);}
  }else if(choice===1){
   const gaps=comparison&&step>0?[0,58,112]:[0,92,184];
   gaps.forEach((offset,i)=>rider(own,160+offset,i===0?accent:'#72848a',0,i+1));
   if(step>0){path(`M${own+70} 260V125`,accent,4,'none',{'marker-end':'url(#teaching-arrow)'});if(labels)text(lane+15,100,comparison?'GAPS COMPRESS':'CHANGE GRADUALLY',mobile?22:20);}
  }else{
   // An inset corner uses one marked lane; no racing line crosses its boundary.
   add('rect',{x:25,y:74,width:W-50,height:348,fill:'#eeeae0'});
   path(`M${own-65} 390Q${own-65} 165 ${right-45} 135`,'#ccd1cf',106);
   path(`M${own-65} 390Q${own-65} 165 ${right-45} 135`,'#fdfcf7',2,'none',{'stroke-dasharray':'14 12'});
   const positions=[[own-65,345,0],[own-58,274,10],[own-28,205,35],[right-95,157,65]];
   let pos=positions[step];rider(pos[0]+(comparison&&step===2?55:0),pos[1],accent,pos[2],1);
   rider(own-68,Math.min(405,pos[1]+88),'#72848a',0,2);
   path(`M${own-65} 385Q${own-65} 175 ${right-65} 140`,accent,4,'none',{'stroke-dasharray':'7 8','marker-end':'url(#teaching-arrow)'});
   if(labels)text(42,106,comparison?'LATE MOVE: LESS ROOM':'POSITION BEFORE THE TURN',mobile?22:20);
  }
  [title,explanation]=roadSteps[choice][step];
  if(comparison&&step>0)explanation=choice===0?'A late swerve uses space another rider may already occupy.':choice===1?'An abrupt change compresses reaction space behind the lead rider.':'A late change can put your wheel into another rider’s path.';
  text(24,466,comparison?'COMPARE: ABRUPT MOVE':'PRACTISE: PREDICTABLE MOVE',mobile?21:20,{fill:accent});
  if(!mobile)text(24,497,'Positions illustrate the choice; no fixed safe gap.',mobile?17:18);
 }else{
  const cx=W/2,classic=choice===3;
  let side=choice===1||classic?(step<2?1:-1):(step<2?polingSide:-polingSide);
  const planting=choice===1||classic?step%2===0:step===0;svg.dataset.supportingSide=side===1?'left':'right';
  add('image',{href:`assets/skier-${choice}-${polingSide}-${step}.png`,x:cx-222,y:36,width:444,height:444});
  if(labels){text(20,28,planting?'POLE CONTACT':'ARM RECOVERY',mobile?22:22,{fill:accent});text(W-20,63,side===1?'LOAD LEFT':'LOAD RIGHT',mobile?22:22,{'text-anchor':'end',fill:accent});}
  [title,explanation]=skiSteps[choice][step];
  text(20,503,'RUST SKI = SUPPORTING SIDE',mobile?22:20);
  const option=el('lesson-option');if(option){option.disabled=choice===1||classic;option.textContent=option.disabled?'Alternating sides':'Switch poling side';}
 }

 el('scene-label').textContent=modes[brand][choice]+' / '+(brand==='ski'?'contact & weight transfer':'riders & road space');
 svg.setAttribute('aria-label',`${modes[brand][choice]}, step ${step+1}: ${title}. ${explanation}${brand==='ski'?`. Supporting side: skier's ${svg.dataset.supportingSide}.`:''}`);
 el('step-label').textContent=`${step+1} / 4`;el('scene-answer').textContent=title;el('scene-explanation').textContent=explanation;
 el('coach').src=assetPath(`assets/coach-${brand}-${step===3?'arms_crossed':'point'}.png`);
 el('scene-step').value=step;
 el('labels').textContent=labels?'Labels on':'Labels off';el('labels').setAttribute('aria-pressed',String(labels));
 const sequence=el('phase-sequence');if(sequence){sequence.replaceChildren();(brand==='ski'?skiSteps:roadSteps)[choice].forEach((row,i)=>{let b=document.createElement('button');b.type='button';b.textContent=`${i+1}. ${row[0]}`;b.setAttribute('aria-pressed',String(i===step));b.addEventListener('click',()=>{step=i;draw();});sequence.append(b);});}
}
function draw(){if(brand==='gravel'){el('scene-diagram').setAttribute('viewBox','0 0 500 260');drawLegacy();}else teachingDraw();}
function pauseLesson(){if(playTimer){clearInterval(playTimer);playTimer=null;}const b=el('play-lesson');if(b)b.textContent='Play sequence';}
if(brand!=='gravel'){
 const tools=el('scene-controls').parentElement,bar=document.createElement('div');bar.className='controls';
 const play=document.createElement('button');play.id='play-lesson';play.type='button';play.textContent='Play sequence';play.addEventListener('click',()=>{if(playTimer){pauseLesson();return;}if(matchMedia('(prefers-reduced-motion: reduce)').matches){el('scene-explanation').textContent='Use the numbered steps with reduced motion enabled.';return;}play.textContent='Pause sequence';playTimer=setInterval(()=>{step=(step+1)%4;draw();},1800);});bar.append(play);
 const option=document.createElement('button');option.id='lesson-option';option.type='button';option.textContent=brand==='road'?'Compare abrupt move':'Switch poling side';option.setAttribute('aria-pressed','false');option.addEventListener('click',()=>{if(brand==='road'){comparison=!comparison;step=Math.max(step,1);}else polingSide*=-1;option.setAttribute('aria-pressed',String(brand==='road'?comparison:polingSide===-1));draw();});bar.append(option);tools.append(bar);
 const sequence=document.createElement('div');sequence.id='phase-sequence';sequence.className='phase-sequence';el('scene-diagram').after(sequence);
 document.addEventListener('visibilitychange',()=>{if(document.hidden)pauseLesson();});window.addEventListener('pagehide',pauseLesson);let frame;window.addEventListener('resize',()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(draw);});
 const observer=new IntersectionObserver(entries=>{if(!entries[0].isIntersecting)pauseLesson();});observer.observe(el('scene-diagram'));
}

modes[brand].forEach((name,i)=>{let b=document.createElement('button');b.type='button';b.textContent=name;b.setAttribute('aria-pressed',String(i===choice));b.addEventListener('click',()=>{choice=i;step=0;el('scene-controls').querySelectorAll('button').forEach((x,j)=>x.setAttribute('aria-pressed',String(i===j)));draw();});el('scene-controls').append(b);});el('scene-step').addEventListener('input',event=>{step=Number(event.target.value);draw();});el('labels').addEventListener('click',()=>{labels=!labels;draw();});
document.querySelectorAll('.quiz').forEach(q=>q.querySelectorAll('.answer').forEach(b=>b.addEventListener('click',()=>{q.querySelectorAll('.answer').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));q.querySelector('.quiz-result').textContent=(b.dataset.correct==='true'?'Correct. ':'Try again. ')+b.dataset.feedback;})));
document.querySelectorAll('.decision').forEach(root=>{const tree=JSON.parse(root.querySelector('.decision-data').textContent);function show(key){const branch=tree[key],dest=root.querySelector('[data-decision-options]');dest.replaceChildren();root.querySelector('[data-decision-question]').textContent=branch.question;branch.options.forEach(o=>{const b=document.createElement(o.result?'a':'button');b.textContent=o.text;if(o.result){b.href='https://gravelgodcycling.com/race/'+encodeURIComponent(o.result)+'/';}else{b.type='button';b.addEventListener('click',()=>show(o.next));}dest.append(b);});}root.querySelector('[data-decision-reset]').addEventListener('click',()=>show('root'));show('root');});draw();})();
