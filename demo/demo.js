/* DG Gateway Pro: visual demonstration ONLY.
   There is intentionally no TeamSpeak client, microphone, networking, RSS,
   PTT, audio stream or real user data in this page. */
"use strict";
const REGIONS=[
  {code:100,name:"Noord-Holland",abbr:"NH",online:5,x:60.0,y:34.1,people:["Kees","Karin"]},
  {code:101,name:"Utrecht",abbr:"UT",online:4,x:69.6,y:49.7,people:["Sandra","Wim"]},
  {code:102,name:"Zeeland",abbr:"ZE",online:2,x:44.5,y:68.0,people:["Theo","Jan"]},
  {code:103,name:"Zuid-Holland",abbr:"ZH",online:7,x:57.3,y:54.2,people:["Ruud","Michiel"]},
  {code:104,name:"Noord-Brabant",abbr:"NB",online:6,x:65.1,y:71.6,people:["Peter","Marcel"]},
  {code:105,name:"Limburg",abbr:"LB",online:4,x:76.0,y:79.1,people:["Marco","Gerard"]},
  {code:106,name:"Gelderland",abbr:"GL",online:6,x:78.0,y:57.4,people:["Henk","Bas"]},
  {code:107,name:"Overijssel",abbr:"OV",online:3,x:83.1,y:45.9,people:["Arie","Willem"]},
  {code:108,name:"Drenthe",abbr:"DR",online:2,x:82.0,y:33.1,people:["Jan","Erik"]},
  {code:109,name:"Groningen",abbr:"GR",online:2,x:89.0,y:19.4,people:["Wim","Roel"]},
  {code:110,name:"Friesland",abbr:"FR",online:3,x:78.2,y:20.7,people:["Ron","Jelle"]},
  {code:111,name:"Flevoland",abbr:"FL",online:2,x:71.0,y:37.1,people:["Bert","Patrick"]}
];
const $=id=>document.getElementById(id);
const screen=$("screen");
const positionsKey="dg-dashboard-demo-positions-v1";
let offsets={};
try{const v=JSON.parse(localStorage.getItem(positionsKey)||"{}");if(v&&typeof v==="object")offsets=v}catch{}
let playing=false, editing=false, interval=null, index=0, current=null, heard=[];
const schedule=[103,106,104,110,100,105,101,107,109,102,111,108];
let lastStartedAt=0;
const nowTime=()=>new Date().toLocaleTimeString("nl-NL",{hour:"2-digit",minute:"2-digit",second:"2-digit"});
function persist(){try{localStorage.setItem(positionsKey,JSON.stringify(offsets))}catch{}}
function place(el,key,defx,defy){
  const pos=offsets[key]||{x:defx,y:defy};
  el.style.left=pos.x+"%";el.style.top=pos.y+"%";
}
function fmtRegion(code){const r=REGIONS.find(x=>x.code===code);return r?r.name:"Onbekend"}
function addRegionList(){
  const root=$("regionList");root.replaceChildren();
  for(const r of REGIONS){
    const b=document.createElement("button");
    b.type="button";b.className="region-line";b.dataset.region=String(r.code);
    b.title="Simuleer een uitzending in "+r.name;
    const c=document.createElement("span");c.className="code";c.textContent="DG-"+r.code;
    const n=document.createElement("span");n.className="name";n.textContent=r.name;
    const ct=document.createElement("span");ct.className="count";ct.textContent=r.online;
    const led=document.createElement("span");led.className="regled";
    b.append(c,n,ct,led);
    b.addEventListener("click",()=>setActive(r.code));
    root.append(b);
  }
}
function createMarkers(){
  const root=$("markers");root.replaceChildren();
  for(const r of REGIONS){
    const b=document.createElement("button");
    b.className="marker";b.type="button";b.dataset.region=String(r.code);
    b.title="DG-"+r.code+" "+r.name+" · "+r.online+" voorbeeldgebruikers";
    b.setAttribute("aria-label",b.title);
    b.innerHTML='<span class="ring"></span><span class="ring"></span>'+
      '<span class="tooltip"></span>'+
      '<span class="antenna"><span></span><span></span><span></span></span>'+
      '<span class="marker-badge"><strong></strong><small></small></span>';
    b.querySelector(".tooltip").textContent=r.name;
    b.querySelector("strong").textContent="DG-"+r.code;
    b.querySelector("small").textContent=r.abbr+" · "+r.online;
    place(b,"region-"+r.code,r.x,r.y);
    b.addEventListener("click",()=>{if(!editing&&!b.dataset.wasDragged)setActive(r.code);delete b.dataset.wasDragged});
    root.append(b);
    makeDraggable(b,"region-"+r.code,r.x,r.y,true);
  }
}
function makeDraggable(el,key,defaultX,defaultY,whole=false){
  const handle=whole?el:(el.querySelector(".drag-handle")||el);
  handle.addEventListener("pointerdown",e=>{
    if(!editing||e.button!==0)return;
    if(e.target.closest("button")&& !whole)return;
    e.preventDefault();e.stopPropagation();
    const rect=screen.getBoundingClientRect();
    const startX=e.clientX,startY=e.clientY;
    const first=offsets[key]||{x:defaultX,y:defaultY};
    let moved=false;
    handle.setPointerCapture(e.pointerId);
    const onMove=ev=>{
      if(Math.hypot(ev.clientX-startX,ev.clientY-startY)>4)moved=true;
      const x=Math.max(2,Math.min(97,first.x+(ev.clientX-startX)/rect.width*100));
      const y=Math.max(4,Math.min(94,first.y+(ev.clientY-startY)/rect.height*100));
      offsets[key]={x,y};place(el,key,defaultX,defaultY);
    };
    const onDone=ev=>{
      handle.removeEventListener("pointermove",onMove);
      handle.removeEventListener("pointerup",onDone);
      handle.removeEventListener("pointercancel",onDone);
      if(moved){el.dataset.wasDragged="1";persist()}
      setTimeout(()=>{delete el.dataset.wasDragged},150);
    };
    handle.addEventListener("pointermove",onMove);
    handle.addEventListener("pointerup",onDone);
    handle.addEventListener("pointercancel",onDone);
  });
}
function updateActive(){
  document.querySelectorAll("[data-region]").forEach(el=>{
    el.classList.toggle("active",Number(el.dataset.region)===current);
  });
  const active=REGIONS.find(r=>r.code===current);
  const has=Boolean(active);
  $("activeCount").textContent=has?1:0;
  $("radioStatus").textContent=has?"DEMO RX/TX ACTIEF":"DEMO RX/TX STAND-BY";
  document.querySelector(".rx-indicator").classList.toggle("talking",has);
  document.querySelector(".livecard").classList.toggle("active",has);
  $("liveName").textContent=has?"DG-"+active.code+" "+active.people[index%active.people.length]:"Niemand spreekt";
  $("liveRegion").textContent=has?active.name+" · voorbeeld TX":"Stand-by";
  $("bannerText").textContent=has?
    "VOORBEELD: DG-"+active.code+" ("+active.abbr+") is aan het zenden":
    "Kaartmarkers tonen voorbeeldactiviteit";
}
function updateHeard(){
  const root=$("heardList");root.replaceChildren();
  if(!heard.length){
    const p=document.createElement("p");p.style.cssText="font-size:12px;color:#b5dafa";
    p.textContent="Nog geen voorbeeldgesprekken";root.append(p);return;
  }
  heard.slice(0,5).forEach(item=>{
    const row=document.createElement("div");row.className="heard-row";
    const t=document.createElement("time");t.textContent=item.time;
    const name=document.createElement("strong");name.textContent=item.name;
    const tag=document.createElement("em");tag.textContent=item.abbr+" / TX";
    row.append(t,name,tag);root.append(row);
  });
}
function setActive(code){
  if(current!==null){
    const prev=REGIONS.find(r=>r.code===current);
    const secs=Math.max(1,Math.round((Date.now()-lastStartedAt)/1000));
    heard.unshift({time:nowTime(),name:"DG-"+prev.code+" "+prev.people[(index-1+24)%prev.people.length],
      abbr:prev.abbr,duration:secs});
    heard=heard.slice(0,12);
    updateHeard();
  }
  current=code;
  lastStartedAt=Date.now();
  index++;
  updateActive();
}
function nextTransmission(){setActive(schedule[(index)%schedule.length])}
function stopDemo(){
  playing=false;clearInterval(interval);interval=null;
  $("playBtn").textContent="▶ Demo starten";
}
function startDemo(){
  if(playing)return;
  playing=true;$("playBtn").textContent="Ⅱ Demo pauzeren";
  if(current===null)nextTransmission();
  interval=setInterval(nextTransmission,6800);
}
function toggleDemo(){playing?stopDemo():startDemo()}
function createBars(){
  const root=$("bars");for(let i=0;i<21;i++){const x=document.createElement("span");
    x.style.animationDelay=(i*.056)+"s";root.append(x)}
}
function clock(){ $("time").textContent=nowTime() }
function layout(){
  document.querySelectorAll(".movable").forEach(el=>{
    const key=el.dataset.layout;
    if(key==="lastheard")place(el,key,78,61.5);
    if(key==="livecard")place(el,key,71.5,15);
    makeDraggable(el,key,key==="lastheard"?78:71.5,key==="lastheard"?61.5:15);
  });
}
function toggleEdit(){
  editing=!editing;
  screen.classList.toggle("editing",editing);
  $("editBtn").setAttribute("aria-pressed",String(editing));
  $("editBtn").textContent=editing?"✓ Indeling opslaan":"⌖ Indeling aanpassen";
  $("editHint").style.display=editing?"inline":"none";
  $("editHint").textContent=editing?
    "Sleep kaartmarkers en panelen; posities blijven op deze pc bewaard":
    "";
  if(!editing)persist();
}
function resetLayout(){
  offsets={};persist();
  document.querySelectorAll(".marker").forEach(el=>{
    const r=REGIONS.find(x=>x.code===Number(el.dataset.region));
    place(el,"region-"+r.code,r.x,r.y);
  });
  layoutResetPanel("lastheard",78,61.5);
  layoutResetPanel("livecard",71.5,15);
}
function layoutResetPanel(key,x,y){const el=document.querySelector('[data-layout="'+key+'"]');if(el)place(el,key,x,y)}
function init(){
  addRegionList();createMarkers();createBars();layout();clock();updateHeard();updateActive();
  $("onlineCount").textContent=REGIONS.reduce((sum,r)=>sum+r.online,0);
  $("channelCount").textContent="9";
  $("playBtn").addEventListener("click",toggleDemo);
  $("nextBtn").addEventListener("click",nextTransmission);
  $("editBtn").addEventListener("click",toggleEdit);
  $("resetBtn").addEventListener("click",resetLayout);
  setInterval(clock,1000);
  // Start clearly labelled fictitious activity to allow immediate visual review.
  setTimeout(startDemo,650);
}
document.addEventListener("DOMContentLoaded",init);
