// ---------- Community map ----------
(async function(){
  if(!window.L){ const m=document.getElementById('map'); if(m) m.textContent='The map library could not load. Check your connection and reload the page.'; return; }
  const [MD, D] = await Promise.all([fetch('assets/mapdata.json?v=79d518e9').then(r=>r.json()), fetch('assets/data.json?v=cde582a8').then(r=>r.json())]);
  const IND = D.ind, KI = Object.fromEntries(IND.map((x,i)=>[x.k,i]));
  const SC = Object.fromEntries(D.comms.map(c=>[c.c,c]));      // study communities by code
  const $ = s => document.querySelector(s);
  const el = (t,a,...k)=>{const n=document.createElement(t); if(a) for(const x in a){ if(x==='class') n.className=a[x]; else if(x==='text') n.textContent=a[x]; else if(x==='style') n.style.cssText=a[x]; else n.setAttribute(x,a[x]); } for(const c of k){ if(c==null) continue; n.append(c.nodeType?c:document.createTextNode(c)); } return n; };
  const fmt = (n,d=0) => n==null ? '–' : Number(n).toLocaleString('en-CA',{minimumFractionDigits:d,maximumFractionDigits:d});
  const show = (k,v) => { const x=IND[KI[k]]; if(v==null) return '–'; if(x.u==='$') return '$'+fmt(v,0); if(x.u==='%±') return Math.round(v)===0?'0%':(v>0?'+':'')+fmt(v,0)+'%'; if(x.u==='yr') return String(Math.round(v)); return fmt(v,x.d)+(x.u==='%'?'%':''); };
  const val = (code,k) => { const c=SC[code]; return c ? c.v[KI[k]] : null; };
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

  // decode delta-encoded rings: [x0,y0,dx,dy,...] in 1/scale degrees, x = longitude
  function ring(a, s){ const out=new Array(a.length/2); let x=0,y=0; for(let i=0;i<a.length;i+=2){ x+=a[i]; y+=a[i+1]; out[i/2]=[y/s, x/s]; } return out; }

  // ----- metrics -----
  const METRICS = [
    {k:'report_gap_pct', l:'Reporting gap: reports vs similar communities', div:true, bins:[-25,-10,10,25], lab:['Much less','Less','As expected','More','Much more']},
    {k:'all_rate', l:'All 311 requests per 1,000 residents a year'},
    {k:'infra_rate', l:'Infrastructure reports per 1,000 residents a year'},
    {k:'income', l:'Median income (area)'},
    {k:'noeng', l:'No knowledge of English (area)'},
    {k:'newcomer', l:'Recent newcomers (area)'},
    {k:'app_share', l:'Share of requests made through the 311 app'},
    {k:'med_home_value', l:'Median assessed home value (2026)'},
    {k:'equity_score', l:'City equity score (higher = better off)'},
  ];
  const sel = $('#mm');
  METRICS.forEach((m,i)=>sel.append(el('option',{value:String(i),text:m.l})));
  let metric = METRICS[0];
  function breaks(m){
    if(m.bins) return m.bins;
    const v = D.comms.map(c=>c.v[KI[m.k]]).filter(x=>x!=null).sort((a,b)=>a-b);
    return [0.2,0.4,0.6,0.8].map(q=>v[Math.floor(q*(v.length-1))]);
  }
  let BR = breaks(metric), PAL = [];
  function palette(){ PAL = metric.div ? ['--g1','--g2','--g3','--g4','--g5'].map(css) : ['--s1','--s2','--s3','--s4','--s5'].map(css); }
  function color(code){
    const v = val(code, metric.k); if(v==null) return css('--nodata');
    let i=0; while(i<BR.length && v>=BR[i]) i++; return PAL[i];
  }

  // ----- map -----
  const B = L.latLngBounds([MD.bbox[1],MD.bbox[0]],[MD.bbox[3],MD.bbox[2]]);
  const map = L.map('map',{zoomSnap:0.25, zoomDelta:0.5, wheelPxPerZoomLevel:90, minZoom:9.5, maxZoom:18, maxBounds:B.pad(0.35), maxBoundsViscosity:0.8, attributionControl:true, zoomControl:true});
  map.attributionControl.setPrefix(false).addAttribution('Boundaries, roads, water and facilities: City of Calgary Open Data');
  ['water','roads','sel','labels'].forEach((p,i)=>{ const pane=map.createPane(p); pane.style.zIndex=String(410+i*10); pane.style.pointerEvents='none'; });
  const rComm = L.canvas({padding:0.3, tolerance:2}), rWater=L.canvas({pane:'water',padding:0.3}), rRoad=L.canvas({pane:'roads',padding:0.3});

  const layers = {};   // code -> polygon
  const commByCode = {};
  MD.comms.forEach(c=>{
    commByCode[c.c]=c;
    const latlngs = c.g.map(poly=>poly.map(r=>ring(r, MD.s)));
    const p = L.polygon(latlngs,{renderer:rComm, weight:0.7, color:'#000', opacity:0.35, fillOpacity:0.88, fillColor:'#ccc', smoothFactor:0.6});
    p.on('click',()=>select(c.c,false));
    p.on('mouseover',()=>{ if(c.c!==cur) p.setStyle({weight:2}); hover(c); });
    p.on('mouseout',()=>{ if(c.c!==cur) p.setStyle({weight:0.7}); hover(null); });
    p.addTo(map); layers[c.c]=p;
  });
  const water = L.layerGroup(MD.water.map(poly=>L.polygon(poly.map(r=>ring(r,MD.ws)),{renderer:rWater, stroke:false, fillOpacity:1, interactive:false}))).addTo(map);
  const roads = MD.roads.map(r=>({cls:r[0], line:L.polyline(ring(r[1],MD.ws),{renderer:rRoad, interactive:false, lineCap:'round', lineJoin:'round'})}));
  const roadLayer = L.layerGroup(roads.map(r=>r.line)).addTo(map);

  function styleAll(){
    palette();
    const line = css('--bound'), wc = css('--water'), rc = css('--road'), rc2 = css('--road2');
    MD.comms.forEach(c=>layers[c.c].setStyle({fillColor:color(c.c), color:line, opacity:1}));
    water.eachLayer(l=>l.setStyle({fillColor:wc}));
    styleRoads(rc, rc2);
    if(cur) highlight(cur);
    legend();
  }
  function styleRoads(rc, rc2){
    const z = map.getZoom(); rc = rc || css('--road'); rc2 = rc2 || css('--road2');
    roads.forEach(r=>r.line.setStyle({color: r.cls===1?rc:rc2, weight: r.cls===1 ? Math.max(1.2,(z-9)*0.75) : Math.max(0.6,(z-10)*0.45), opacity: r.cls===1?0.9:(z<11.5?0:0.75)}));
  }

  // labels (shown when zoomed in)
  const labelLayer = L.layerGroup(MD.comms.filter(c=>c.cls==='Residential').map(c=>L.marker(c.lp,{icon:L.divIcon({className:'',html:'<div class="clabel">'+c.n.replace(/&/g,'&amp;').replace(/</g,'&lt;')+'</div>',iconSize:[0,0]}),pane:'labels',interactive:false,keyboard:false})));
  function zoomed(){ const z=map.getZoom(); map.getContainer().classList.toggle('zin', z>=12.5); if(z>=12.5 && !streetsOn){ if(!map.hasLayer(labelLayer)) labelLayer.addTo(map); } else if(map.hasLayer(labelLayer)) map.removeLayer(labelLayer); styleRoads(); }
  map.on('zoomend',zoomed);

  const dark = () => document.documentElement.dataset.theme==='dark' || (document.documentElement.dataset.theme!=='light' && matchMedia('(prefers-color-scheme: dark)').matches);
  const tpane = map.createPane('tlabels'); tpane.style.zIndex='405'; tpane.style.pointerEvents='none';
  const tu = kind => 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_'+(dark()?'Dark':'Light')+'_Gray_'+kind+'/MapServer/tile/{z}/{y}/{x}';
  const ATTR = 'Basemap &copy; Esri, HERE, Garmin, &copy; OpenStreetMap contributors';
  const tiles = L.tileLayer(tu('Base'), {maxNativeZoom:16, maxZoom:20, attribution:ATTR});
  const tlab = L.tileLayer(tu('Reference'), {maxNativeZoom:16, maxZoom:20, pane:'tlabels'});
  const streets = document.getElementById('streets');
  var streetsOn = false;
  function setStreets(on){ streetsOn = on;
    if(on){ tiles.addTo(map); tlab.addTo(map); map.removeLayer(water); map.removeLayer(roadLayer); if(map.hasLayer(labelLayer)) map.removeLayer(labelLayer); }
    else { map.removeLayer(tiles); map.removeLayer(tlab); water.addTo(map); roadLayer.addTo(map); zoomed(); }
    MD.comms.forEach(c=>layers[c.c].setStyle({fillOpacity: on?0.5:0.88})); }
  if(streets){ streets.addEventListener('change', ()=>setStreets(streets.checked)); }
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', ()=>{ tiles.setUrl(tu('Base')); tlab.setUrl(tu('Reference')); });
  map.fitBounds(B,{padding:[8,8]});

  // legend
  const lg = el('div',{class:'mlegend','aria-live':'polite'});
  $('#mwrap').append(lg);
  function legend(){
    lg.textContent='';
    const x = IND[KI[metric.k]];
    lg.append(el('div',{class:'t',text:metric.l}));
    const sw = el('div',{class:'sw',style:'--n:5'}); PAL.forEach(c=>sw.append(el('i',{style:'background:'+c}))); lg.append(sw);
    if(metric.div) lg.append(el('div',{class:'lb'}, el('span',{text:'Reports less'}), el('span',{text:'as expected'}), el('span',{text:'more'})));
    else { const f=v=>show(metric.k,v); lg.append(el('div',{class:'lb'}, el('span',{text:'< '+f(BR[0])}), el('span',{text:f(BR[1])+'–'+f(BR[2])}), el('span',{text:'> '+f(BR[3])}))); }
    lg.append(el('div',{class:'nd'}, el('i'), 'Not in study: industrial, parks, under 500 residents or built after 2021'));
  }
  sel.addEventListener('change',()=>{ metric=METRICS[+sel.value]; BR=breaks(metric); styleAll(); if(cur) panel(cur); });

  // theme changes repaint the canvas colours
  const mq = matchMedia('(prefers-color-scheme: dark)'); mq.addEventListener && mq.addEventListener('change',styleAll);
  new MutationObserver(styleAll).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});

  // ----- selection, highlight, service pins -----
  let cur=null; const selLayer=L.layerGroup().addTo(map);
  function highlight(code){
    selLayer.clearLayers();
    const c=commByCode[code];
    L.polygon(c.g.map(poly=>poly.map(r=>ring(r,MD.s))),{pane:'sel',interactive:false,fill:false,color:css('--ink'),weight:3,opacity:1}).addTo(selLayer);
    const pin=(key,letter,label,colorVar)=>{ const s=c.near[key]; if(!s) return; const p=MD.pl[key][s[0]]; L.marker([p[2],p[3]],{pane:'labels',interactive:false,keyboard:false,icon:L.divIcon({className:'',iconSize:[0,0],html:'<div class="svcpin"><i style="background:'+css(colorVar)+'">'+letter+'</i><span>'+label+'</span></div>'})}).addTo(selLayer); };
    pin('f','F','Fire','--pin-fire'); pin('h','H','Hospital','--pin-health'); pin('u','+','Clinic','--pin-health'); pin('l','L','Library','--pin-civic'); pin('cc','C','Community hall','--pin-civic');
  }
  function select(code, fly){
    if(cur && layers[cur]) layers[cur].setStyle({weight:0.7});
    cur=code; highlight(code); panel(code);
    const c=commByCode[code];
    if(fly){ map.flyToBounds(layers[code].getBounds(),{padding:[40,40],maxZoom:15,duration:0.6}); }
    $('#ms').value=c.n;
  }

  // ----- side panel -----
  const P = $('#mpanel');
  function hover(c){ const h=$('#mhover'); if(h) h.textContent = c ? c.n + (SC[c.c] ? ' · ' + show(metric.k, val(c.c,metric.k)) : ' · not in study') : 'Hover or tap a community'; }
  function km(d){ return d<1 ? fmt(d*1000,0)+' m' : fmt(d,1)+' km'; }
  function panel(code){
    const c=commByCode[code], s=SC[code]; P.textContent='';
    P.append(el('div',{class:'stack',style:'gap:6px'},
      el('h3',{text:c.n}),
      el('div',{class:'sub',text:[c.sec ? c.sec.charAt(0)+c.sec.slice(1).toLowerCase() : null, c.cls!=='Residential'?c.cls:null, c.w?'Ward '+c.w+(MD.wards[c.w]?' · Councillor '+MD.wards[c.w]:''):null, c.pd?'Police District '+c.pd:null].filter(Boolean).join(' · ')})));
    if(s){
      const gap=s.v[KI.report_gap_pct];
      const g = gap==null?null: gap<-25?['lo','Reports much less than similar communities']: gap<-10?['lo','Reports less than similar communities']: gap>10?['ok','Reports more than similar communities']:['ok','Reports about as expected'];
      if(g) P.append(el('div',{class:'chips'}, el('span',{class:'pill '+g[0],text:g[1]+' ('+show('report_gap_pct',gap)+')'}), s.g?el('span',{class:'pill',text:'Grown a lot since 2021'}):null));
      const F=(k,lab)=>el('div',null, el('b',{text:show(k,s.v[KI[k]])}), el('span',{text:lab}), el('span',{class:'cmp',text:'Calgary '+(k==='pop'?fmt(D.city.pop)+' avg':show(k,D.city[k]))}));
      P.append(el('h4',{text:'People'}), el('div',{class:'facts'}, F('pop','Residents (2021)'), F('income','Median income (area)'), F('noeng','No English (area)'), F('newcomer','Recent newcomers (area)'), F('renter','Renters (area)'), F('med_home_value','Median home value')));
      const total = c.q ? c.q[0] : null;
      P.append(el('h4',{text:'311 requests, Oct 2024 – Sep 2026'}), el('div',{class:'facts'},
        el('div',null, el('b',{text:fmt(total)}), el('span',{text:'Requests in two years'}), el('span',{class:'cmp',text:'excluding duplicates'})),
        F('all_rate','Requests per 1,000 a year'), F('infra_rate','Infrastructure reports per 1,000 a year'), F('expected_rate','Expected for a community like this'), F('app_share','Made through the 311 app'), F('close7_pct','Closed within 7 days')));
      if(s.top && s.top.length) P.append(el('p',{class:'sub'}, el('b',{text:'Most reported: '}), s.top.map(t=>t[0]+' ('+fmt(t[1])+')').join(', ')));
    } else {
      P.append(el('p',{class:'sub',text: c.cls!=='Residential' ? 'This is a '+c.cls.toLowerCase()+' area, so it is not part of the study.' : 'This community had fewer than 500 residents in the 2021 Census, or was built after it, so it is not part of the study.'}));
      if(c.q && c.q[0]) P.append(el('div',{class:'facts'}, el('div',null, el('b',{text:fmt(c.q[0])}), el('span',{text:'311 requests, Oct 2024 – Sep 2026'})), el('div',null, el('b',{text:c.q[0]?fmt(c.q[1]/c.q[0]*100,0)+'%':'–'}), el('span',{text:'Made through the 311 app'}))));
    }
    // nearby services
    const near = el('ul',{class:'mlist'});
    const item=(key,title)=>{ const n=c.near[key]; if(!n) return; const p=MD.pl[key][n[0]]; near.append(el('li',null, el('span',{class:'k',text:title}), el('span',null, el('b',{text:p[0]}), p[1]?el('br'):null, p[1]?el('span',{class:'sub',text:p[1]}):null), el('span',{class:'d',text:km(n[1])}))); };
    item('f','Nearest fire station'); item('h','Nearest hospital'); item('u','Nearest public health clinic'); item('l','Nearest library'); item('cc', (c.near.cc && c.near.cc[2]) ? 'Community association hall' : 'Nearest community association hall'); item('r','Nearest City recreation centre');
    P.append(el('h4',{text:'Nearby'}), near, el('p',{class:'sub',text:'Straight-line distance from the middle of the community. In an emergency, always call 911.'}));
    if(s){ P.append(el('a',{class:'mbtn',href:'communities.html#'+c.c,text:'Open the full profile (52 indicators)'})); }
    P.append(phones());
    P.scrollTop=0;
  }
  function phones(){
    const box=el('div',{class:'stack',style:'gap:6px'}, el('h4',{text:'Emergency and help lines'}));
    const ul=el('ul',{class:'mlist phones'});
    MD.phones.forEach(([what,num,big])=>ul.append(el('li',null, el('span',{text:what}), el('span',{class:'num'+(big?' big':''),text:num}))));
    box.append(ul, el('p',{class:'sub',text:'Numbers are the same across Calgary. Select a number to copy it.'}));
    return box;
  }

  // search
  const names = MD.comms.slice().sort((a,b)=>a.n.localeCompare(b.n));
  names.forEach(c=>$('#mlist').append(el('option',{value:c.n})));
  $('#ms').addEventListener('change',e=>{ const v=e.target.value.trim().toLowerCase(); const c=names.find(x=>x.n.toLowerCase()===v); if(c) select(c.c,true); });
  $('#ms').addEventListener('input',e=>{ const v=e.target.value.trim().toLowerCase(); const c=names.find(x=>x.n.toLowerCase()===v); if(c) select(c.c,true); });

  styleAll(); zoomed();
  // start with an empty panel that explains itself, plus the phone list
  P.append(el('div',{class:'stack',style:'gap:8px'}, el('h3',{text:'Pick a community'}), el('p',{class:'sub',text:'Click any community on the map, or search above, to see its people, 311 requests, councillor, nearest fire station, hospital, library and community hall.'})), phones());
  if(streets && streets.checked) setStreets(true);
  const h = decodeURIComponent(location.hash.slice(1)); const start = commByCode[h] ? h : (SC['MRT'] ? 'MRT' : null); if(start) select(start, !!commByCode[h]);
})();
