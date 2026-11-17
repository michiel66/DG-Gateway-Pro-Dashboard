/* DG Gateway Pro Windows viewer: no external JavaScript, no voice or microphone. */
"use strict";
const mapLocations = [
  {code:100,name:"Noord-Holland",x:291,y:276},
  {code:101,name:"Utrecht",x:413,y:401},
  {code:102,name:"Zeeland",x:179,y:556},
  {code:103,name:"Zuid-Holland",x:266,y:451},
  {code:104,name:"Noord-Brabant",x:413,y:554},
  {code:105,name:"Limburg",x:609,y:613},
  {code:106,name:"Gelderland",x:540,y:496},
  {code:107,name:"Overijssel",x:588,y:355},
  {code:108,name:"Drenthe",x:573,y:241},
  {code:109,name:"Groningen",x:588,y:135},
  {code:110,name:"Friesland",x:420,y:137},
  {code:111,name:"Flevoland",x:441,y:282},
];
const $ = id => document.getElementById(id);
let lastStatus = null;
let activeDialog = "demo";
let regionFilter = 0;
let lastSelectSignature = "";
let firstLoad = true;

function regionLabel(code) {
  const row = mapLocations.find(g => g.code === Number(code));
  return row ? row.name : "Overige gebruikers";
}
function node(tag, css, text) {
  const el = document.createElement(tag);
  if (css) el.className = css;
  if (text != null) el.textContent = String(text);
  return el;
}
function child(parent, tag, css, text) {
  const el = node(tag, css, text);
  parent.append(el);
  return el;
}
function svg(tag, attrs={}) {
  const el = document.createElementNS("http://www.w3.org/2000/svg",tag);
  Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,String(v)));
  return el;
}
function createMarkers() {
  const root=$("mapMarkers");
  root.replaceChildren();
  mapLocations.forEach(loc=>{
    const g=svg("g",{"class":"marker", "data-code":loc.code, role:"button",tabindex:"0",
      "aria-label":"DG-"+loc.code+" "+loc.name});
    const x=loc.x, y=loc.y;
    const icon=svg("use",{href:"#tower", x:x-27,y:y-24,width:54,height:54,"class":"tower-icon"});
    g.append(icon);
    const name=svg("text",{x,y:y+43,"text-anchor":"middle","class":"province-name"});
    name.textContent=loc.name;
    g.append(name);
    const width=87;
    g.append(svg("rect",{x:x-width/2,y:y+49,width,height:29,rx:7}));
    const code=svg("text",{x,y:y+70,"class":"dg-code"});
    code.textContent="DG-"+loc.code;
    g.append(code);
    g.addEventListener("click",()=>selectRegion(loc.code));
    g.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();selectRegion(loc.code)}});
    root.append(g);
  });
  document.querySelectorAll(".region[data-code]").forEach(path=>{
    path.addEventListener("click",()=>selectRegion(Number(path.dataset.code)));
    path.setAttribute("role","button");
    path.setAttribute("tabindex","0");
    path.setAttribute("aria-label","Selecteer DG-"+path.dataset.code+" "+regionLabel(path.dataset.code));
    path.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();selectRegion(Number(path.dataset.code))}});
  });
}
function selectRegion(num){
  regionFilter= regionFilter===num?0:num;
  if(lastStatus)render(lastStatus);
}
function putText(id,text){$(id).textContent=text}
function setChannelList(s){
  const rows=s.mode==="client" ? (s.channels||[]) : [{id:0,name:"Alle kanalen"},...(s.channels||[])];
  const key=JSON.stringify(rows)+"/"+s.selected_channel;
  if(key===lastSelectSignature)return;
  lastSelectSignature=key;
  const el=$("channelSelect");
  el.replaceChildren();
  rows.forEach(r=>{const opt=document.createElement("option");opt.value=String(r.id);opt.textContent=r.name;el.append(opt)});
  el.value=String(s.selected_channel||0);
}
function renderMap(s){
  for(const item of s.groups||[]){
    const code=item.code;
    document.querySelectorAll('[data-code="'+code+'"]').forEach(el=>{
      const on=Boolean(item.active);
      el.classList.toggle("active",on);
      el.classList.toggle("selected",regionFilter===code);
      el.classList.toggle("unavailable",!s.speaker_data&&item.count>0);
    });
  }
}
function renderGroups(s){
  const grid=$("regionList");grid.replaceChildren();
  const groups=(s.groups||[]).filter(g=>g.code!==999);
  groups.forEach(group=>{
    const el=child(grid,"div","region-entry"+(group.active?" active":"")+(regionFilter===group.code?" selected":""));
    el.title=group.name+": "+group.count+" gebruikers";
    child(el,"strong",null,"DG-"+group.code);
    child(el,"span",null,group.name);
    el.addEventListener("click",()=>selectRegion(group.code));
  });
  const other=(s.groups||[]).find(g=>g.code===999);
  putText("otherGroup","DG-999   Overige gebruikers · "+(other?.count||0));
  $("otherGroup").classList.toggle("selected",regionFilter===999);
  $("otherGroup").onclick=()=>selectRegion(999);
}
function renderUsers(s){
  const root=$("userList");root.replaceChildren();
  const shown=(s.users||[]).filter(u=>!regionFilter || Number(u.region)===regionFilter);
  const filteredSuffix=regionFilter?" · DG-"+regionFilter:"";
  putText("userFilterText","("+shown.length+")"+filteredSuffix);
  if(!shown.length){child(root,"p","empty",regionFilter?"Geen gebruikers in deze DG-regio":"Geen gebruikers in dit kanaal");return}
  shown.forEach(user=>{
    const el=child(root,"div","user-row"+(user.speaking===true?" speaking":""));
    child(el,"span","user-dot");
    child(el,"strong",null,user.name);
    child(el,"span","uid",user.channel_id?"Kanaal "+user.channel_id:"Online");
  });
}
function renderHeard(s){
  const root=$("heardList");root.replaceChildren();
  if(!s.speaker_data){
    child(root,"p","empty","ServerQuery kan geen betrouwbare actieve spreekstatus leveren. Last Heard blijft leeg totdat een compatibele Android- of serverbron spraak meldt.");
    return;
  }
  if(!s.heard?.length){child(root,"p","empty","Nog geen afgelopen gesprekken");return}
  s.heard.slice(0,5).forEach(e=>{
    const row=child(root,"div","heard-row");
    child(row,"span","user-dot");
    child(row,"strong",null,"DG-"+e.region);
    const name=String(e.name).replace(/^DG-\d{3}\s*/,"");
    child(row,"strong",null,name);
    child(row,"time",null,e.time);
  });
}
function renderOnAir(s){
  const panel=$("onAirPanel");panel.classList.remove("talking");
  const hasRx=s.speaker_data;
  const active=s.active_users||[];
  panel.classList.toggle("no-voice",!hasRx||!active.length);
  $("onairWarning").hidden=hasRx;
  if(!hasRx){
    putText("onairTitle","RX-STATUS ONBEKEND");
    putText("onairRegion","Niet beschikbaar via ServerQuery");
    putText("onairName","—");
    return;
  }
  if(!active.length){
    putText("onairTitle","GEEN ACTIEVE TRANSMISSIE");
    putText("onairRegion","Alle DG-regio's in stand-by");
    putText("onairName","—");
    return;
  }
  const u=active[0];
  putText("onairTitle",s.demo?"VOORBEELD TRANSMISSIE":"ACTIEVE TRANSMISSIE");
  putText("onairRegion","DG-"+u.region+" · "+regionLabel(u.region));
  putText("onairName",String(u.name).replace(/^DG-\d{3}\s*/,""));
  panel.classList.add("talking");
}
function render(s){
  lastStatus=s;
  putText("usersCount",s.all_users_count||0);
  putText("activeCount",s.speaker_data ? (s.groups||[]).filter(g=>g.code!==999&&g.active).length : "—");
  const source = s.mode==="demo"?"VOORBEELD":s.mode==="android"?"ANDROID":s.mode==="client"?"TEAMSPEAK DIRECT":"SERVERQUERY";
  putText("modeName",s.mode==="demo"?"VOORBEELD":s.mode==="android"?(s.connected?"GEKOPPELD":"WACHT OP ANDROID"):s.mode==="client"?(s.connected?"LIVE · TEAMSPEAK":"VERBINDEN..."):(s.connected?"LIVE · QUERY":"NIET VERBONDEN"));
  $("modeDot").style.background=s.mode==="demo"?"#ffc44c":s.connected?"#50fb84":"#fa4e55";
  $("modeDot").style.boxShadow=s.mode==="demo"?"0 0 11px #ffc44c":s.connected?"0 0 11px #50fb84":"0 0 10px #fa4e55";
  const monitor=s.monitor||{};
  const serverWide=s.talk_scope==="hele_server";
  const msg=s.error||(
      s.mode==="demo"?"VOORBEELDGEGEVENS — dit is geen live TeamSpeak-verbinding":
      s.mode==="android"?(s.connected?"Android stuurt echte ontvangergegevens":"Android-koppeling vereist een toekomstige app-update"):
      s.mode==="client"?(s.connected?(serverWide?
          "LIVE · SERVERBREDE RX/TX VIA SERVERQUERY · geen pc-audio":
          "LIVE · alleen RX/TX eigen TeamSpeak-kanaal"):"Niet verbonden met TeamSpeak"):
      s.connected?(serverWide?"SERVERQUERY LIVE · ALLE TOEGANKELIJKE KANALEN":
                   "SERVERQUERY VERBONDEN · spreekstatus ontbreekt"):"Niet verbonden met ServerQuery"
  );
  putText("sourceNote",msg);
  putText("connectionState",msg);
  $("monitorTools").hidden=s.mode!=="client";
  const monText=monitor.live?
    "SERVERBREDE RX/TX · "+(monitor.query_users||0)+" gebruikers gecontroleerd":
    monitor.enabled?"ALLEEN EIGEN KANAAL · MONITOR NIET BESCHIKBAAR":
                    "ALLEEN EIGEN KANAAL · MONITOR UIT";
  putText("monitorStatus",monText);
  $("monitorStatus").classList.toggle("online",Boolean(monitor.live));
  $("monitorStatus").title=monitor.live?
    "ServerQuery -voice leest elke 2 seconden de toegankelijke kanalen.":
    (monitor.error||"RX/TX is beperkt tot het geselecteerde kanaal.");
  if(s.mode==="client") putText("monitorExplain",monitor.error||
    (monitor.live?"Serverbrede spreekstatus is actief. Polling elke 2 seconden.":
     "Automatisch proberen zonder login; als de server geen toegang geeft, vraag leesrechten."));
  putText("legendFoot",serverWide?
    "Groen = echte spreekstatus uit toegankelijke TeamSpeak-kanalen (ServerQuery -voice)":
    s.speaker_data?"Groen = spreekstatus in het waargenomen TeamSpeak-kanaal":
                   "Geen spreekstatus beschikbaar; geen fictieve groenverlichting.");
  $("channelControls").hidden=!["query","client"].includes(s.mode)||!s.connected;
  putText("channelLabel",s.mode==="client"?"TS-kanaal kiezen":"Kanaalfilter");
  document.querySelectorAll(".mode-chip").forEach(b=>b.classList.toggle("active",b.dataset.mode===s.mode));
  setChannelList(s);
  renderMap(s);renderGroups(s);renderOnAir(s);renderHeard(s);renderUsers(s);
  const pair=s.pair||{};
  putText("pairCode",pair.code?pair.code.replace(/^(\d{3})(\d{3})$/,"$1 $2"):(pair.paired?"GEKOPPELD":"VERLOPEN"));
  putText("pairInfo",pair.error||((pair.host&&pair.port)?pair.host+":"+pair.port+" · "+(pair.paired?"Gekoppeld: "+pair.device:"Eenmalige koppeling, maximaal 5 minuten"):"LAN-koppeling niet beschikbaar"));
  if(pair.qr){$("qrImage").src=pair.qr;$("qrImage").hidden=false}else{$("qrImage").hidden=true}
  $("mapCaption").textContent = s.demo?
    "SCHEMATISCHE KAART · VOORBEELDGEGEVENS · GEEN ECHTE TRANSMISSIE":
    serverWide?"SERVERBREDE RX/TX · 2 SEC PEILING · ALLEEN TOEGANKELIJKE KANALEN":
    s.mode==="client"?"RX/TX alleen in huidig kanaal · stel Serverbrede RX/TX in":
                       "Schematische provincies · DG-groepen zijn virtuele TeamSpeak-regio's";
  if(firstLoad){ firstLoad=false; }
}
async function request(path,data){
  const res=await fetch(path,{
    method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify(data)
  });
  let payload={};
  try{payload=await res.json()}catch{}
  if(!res.ok)throw new Error(payload.error||"Er ging iets mis.");
  return payload;
}
async function poll(){
  try{
    const res=await fetch("/api/status",{cache:"no-store"});
    if(!res.ok)throw Error("API niet beschikbaar");
    render(await res.json());
  }catch(e){putText("sourceNote","Dashboard kan de lokale achtergrondservice niet bereiken: "+String(e.message))}
}
function showDialog(tab){
  $("dialogBackdrop").hidden=false;
  dialogTab(tab);
}
function dialogTab(tab){
  activeDialog=tab;
  $("dialogDemo").hidden=tab!=="demo";
  $("dialogAndroid").hidden=tab!=="android";
  $("clientForm").hidden=tab!=="client";
  $("monitorForm").hidden=tab!=="monitor";
  $("queryForm").hidden=tab!=="query";
  $("monitorTab").hidden=lastStatus?.mode!=="client";
  document.querySelectorAll(".dialog-tabs button").forEach(b=>b.classList.toggle("active",b.dataset.dialogTab===tab));
  $("dialogError").hidden=true;
}
function closeDialog(){$("dialogBackdrop").hidden=true}
function dialogError(error){$("dialogError").textContent=error.message||String(error);$("dialogError").hidden=false}
function wireEvents(){
  createMarkers();
  document.querySelectorAll(".mode-chip").forEach(b=>b.addEventListener("click",()=>{
    if(b.dataset.mode==="demo"){request("/api/mode",{mode:"demo"}).then(poll).catch(dialogError);regionFilter=0}
    else showDialog(b.dataset.mode)
  }));
  document.querySelectorAll(".dialog-tabs button").forEach(b=>b.addEventListener("click",()=>dialogTab(b.dataset.dialogTab)));
  $("settingsBtn").addEventListener("click",()=>showDialog(lastStatus?.mode==="client"?"monitor":lastStatus?.mode||"demo"));
  $("monitorCfgBtn").addEventListener("click",()=>showDialog("monitor"));
  $("modeBtn").addEventListener("click",()=>showDialog(lastStatus?.mode||"demo"));
  $("closeDialog").addEventListener("click",closeDialog);
  $("dialogBackdrop").addEventListener("click",e=>{if(e.target===$("dialogBackdrop"))closeDialog()});
  $("activateDemo").addEventListener("click",async()=>{
    try{await request("/api/mode",{mode:"demo"});regionFilter=0;closeDialog();await poll()}catch(e){dialogError(e)}
  });
  $("activateAndroid").addEventListener("click",async()=>{
    try{await request("/api/mode",{mode:"android"});closeDialog();await poll()}catch(e){dialogError(e)}
  });
  $("returnDemo").addEventListener("click",()=>dialogTab("demo"));
  $("clientForm").addEventListener("submit",async e=>{
    e.preventDefault();
    $("connectClientBtn").disabled=true;
    try{
      await request("/api/connect-client",{
        display_name:$("viewerName").value,
        global_monitor:$("startGlobalRx").checked,
        query_port:Number($("clientQueryPort").value||10011),
        voice_port:Number($("clientVoicePort").value||9987),
        login:$("clientQueryLogin").value,
        password:$("clientQueryPassword").value
      });
      $("clientQueryPassword").value="";
      regionFilter=0;closeDialog();await poll();
    }catch(err){dialogError(err)}
    finally{$("connectClientBtn").disabled=false}
  });
  $("monitorForm").addEventListener("submit",async e=>{
    e.preventDefault();
    $("saveGlobalBtn").disabled=true;
    try{
      await request("/api/global-monitor",{
        global_monitor:$("updateGlobalRx").checked,
        query_port:Number($("monitorQueryPort").value||10011),
        voice_port:Number($("monitorVoicePort").value||9987),
        login:$("monitorQueryLogin").value,
        password:$("monitorQueryPassword").value
      });
      $("monitorQueryPassword").value="";
      closeDialog();await poll();
    }catch(err){dialogError(err)}
    finally{$("saveGlobalBtn").disabled=false}
  });
  $("queryForm").addEventListener("submit",async e=>{
    e.preventDefault();
    $("connectBtn").disabled=true;
    try{
      await request("/api/connect",{
        display_name:$("displayName").value,host:$("queryHost").value,
        query_port:$("queryPort").value,voice_port:$("voicePort").value,
        login:$("queryLogin").value,password:$("queryPassword").value
      });
      $("queryPassword").value="";
      regionFilter=0;closeDialog();await poll()
    }catch(err){dialogError(err)}
    finally{$("connectBtn").disabled=false}
  });
  $("channelSelect").addEventListener("change",async e=>{
    try{await request("/api/channel",{id:Number(e.target.value)});await poll()}catch(err){putText("sourceNote",String(err))}
  });
  $("fullscreenBtn").addEventListener("click",async()=>{
    try{
      if(window.pywebview?.api?.toggle_fullscreen){
        await window.pywebview.api.toggle_fullscreen();
      }else if(document.fullscreenElement){
        await document.exitFullscreen();
      }else{
        await document.documentElement.requestFullscreen();
      }
    }catch(e){putText("sourceNote","Fullscreen aanpassen kan ook met Alt+Enter of via Windows-vensterbediening.")}
  });
  document.addEventListener("keydown",e=>{
    if(e.key==="Escape"&&!$("dialogBackdrop").hidden)closeDialog();
    if(e.key==="Backspace"&&e.target.tagName!=="INPUT"&&regionFilter){regionFilter=0;if(lastStatus)render(lastStatus)}
  });
  const tick=()=>{
    const d=new Date();
    putText("clock",d.toLocaleTimeString("nl-NL",{hour:"2-digit",minute:"2-digit",second:"2-digit"}));
    putText("date",d.toLocaleDateString("nl-NL",{weekday:"short",day:"2-digit",month:"short",year:"numeric"}));
  };
  tick();setInterval(tick,1000);
  poll();setInterval(poll,3000);
}
document.addEventListener("DOMContentLoaded",wireEvents);
