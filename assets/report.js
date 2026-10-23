(async function(){
  const D = await (await fetch('assets/data.json?v=cde582a8')).json(), R = D.R;
  const $ = s => document.querySelector(s);
  const el = (t,a,...k)=>{const n=document.createElement(t); if(a) for(const x in a){ if(x==='class') n.className=a[x]; else if(x==='text') n.textContent=a[x]; else if(x==='style') n.style.cssText=a[x]; else n.setAttribute(x,a[x]); } for(const c of k){ if(c==null) continue; n.append(c.nodeType?c:document.createTextNode(c)); } return n; };
  const fmt = (n,d=0) => n==null ? '–' : Number(n).toLocaleString('en-CA',{minimumFractionDigits:d,maximumFractionDigits:d});
  const IND = D.ind, KI = Object.fromEntries(IND.map((x,i)=>[x.k,i]));
  const show = (x,v) => v==null ? '–' : x.u==='$' ? '$'+fmt(v,0) : x.u==='%±' ? (Math.round(v)===0?'0%':(v>0?'+':'')+fmt(v,0)+'%') : x.u==='yr' ? String(Math.round(v)) : fmt(v,x.d)+(x.u==='%'?'%':'');
  function toast(m){ const t=$('#toast'); t.textContent=m; t.hidden=false; clearTimeout(toast.t); toast.t=setTimeout(()=>t.hidden=true,2600); }

  if($('#meta')) $('#meta').textContent = 'Independent analysis of '+fmt(R.req_all)+' City of Calgary 311 requests, October 2024 to September 2026, across '+R.n_comm+' communities home to '+fmt(R.pop)+' residents. Data retrieved October 21, 2026. Not affiliated with The City of Calgary.';
  const nq=R.neq, mq=R.matched, bs=R.bootstrap_M2;
  const raw = Math.round((1-nq[4].rate/nq[1].rate)*100);
  if($('#key')) $('#key').append(
    el('div',null, el('b',{text:raw+'% fewer'}), el('span',{text:'infrastructure reports per resident where the most residents don\'t speak English, compared with the fewest'})),
    el('div',null, el('b',{text:'~'+Math.round(-bs.point)+'% fewer'}), el('span',{text:'comparing like with like (95% range '+Math.round(-bs.eff_lo)+'–'+Math.round(-bs.eff_hi)+'%)'})),
    el('div',null, el('b',{text:'Equal'}), el('span',{text:'response speed across income and language groups once a problem is reported'})));

  function bars(t, rows, o){ if(!t) return; rows.forEach(r=>{ const tr=el('div',{class:'track'}); tr.append(el('div',{class:'fill'+(r.dim?' dim':''),style:'width:'+Math.max(0,r.v/o.max*100)+'%'})); if(o.ref!=null) tr.append(el('div',{class:'ref',style:'left:'+(o.ref/o.max*100)+'%'})); t.append(el('div',{class:'bar-row',title:r.tip||''}, el('div',{class:'lab'}, r.label, r.sub?el('small',{text:r.sub}):null), tr, el('div',{class:'val',text:r.vt}))); }); }
  const neL={1:'Fewest',2:'Fewer',3:'More',4:'Most'};
  bars($('#c1'), [1,2,3,4].map(k=>({label:neL[k]+' non-English speakers', sub:'avg '+fmt(nq[k].ne,1)+'% · '+nq[k].comms+' communities · area median income about $'+fmt(nq[k].inc), v:nq[k].rate, vt:fmt(nq[k].rate,1), dim:k<4})), {max:100});
  bars($('#c1b'), [[1,'Fewest'],[2,'Middle'],[3,'Most']].map(([k,l])=>({label:l+' non-English speakers', sub:'avg '+fmt(mq[k].ne,1)+'% · '+mq[k].comms+' communities', v:mq[k].rate, vt:fmt(mq[k].rate,1), dim:k<3})), {max:100});
  // dot plot
  const labels = {'M1 community: income, renters, no-English, distance':'Without community age','M2 + community age (first census year)':'Main model (with community age)','M3 + median year homes built (assessments)':'Age from home construction years','M4 + age + growth since 2021 (new housing units)':'Plus growth since 2021','M5 + age + home value':'Plus home values','M6 M2 excluding NE quadrant':'Excluding northeast Calgary','M7 M2 roads only':'Roads only','M8 M2 water & sewer only':'Water & sewer only','M9 M2 parks & trees only':'Parks & trees only','M10 M2 all 30 request types':'All 30 request types','M11 M2 all request types (every 311 service)':'Every 311 request type','M12 M2 excluding communities within 3 km of downtown':'Excluding downtown','M13 M2 unweighted':'Not weighted by population','M16 area level (CSA), with age':'Area level instead of community'};
  const pos = v => (v+40)/40*100;
  if($('#c1c')) Object.entries(R.effects).forEach(([k,v])=>{ const main = k.startsWith('M2 '); const tr=el('div',{class:'dot-track'}); if(main){ tr.append(el('div',{class:'ci',style:'left:'+pos(bs.eff_hi)+'%;width:'+(pos(bs.eff_lo)-pos(bs.eff_hi))+'%'})); } tr.append(el('div',{class:'dot'+(main?' main':''),style:'left:'+pos(v)+'%'})); $('#c1c').append(el('div',{class:'dot-row',title:(labels[k]||k)+': '+v+'%'}, el('div',{text:labels[k]||k, style: main?'font-weight:700':''}), tr, el('div',{class:'val',text:Math.round(v)+'%'}))); });
  const qn={1:'Lowest income',2:'Lower',3:'Middle',4:'Higher',5:'Highest income'};
  bars($('#c2'), [1,2,3,4,5].map(k=>({label:qn[k], sub:fmt(R.closure_inc[k].p7,1)+'% closed within 7 days', v:R.closure_inc[k].r7, vt:fmt(R.closure_inc[k].r7,1), dim:true})), {max:110, ref:100});
  bars($('#c3'), [1,2,3,4,5].map(k=>({label:qn[k], v:R.app_inc[k], vt:fmt(R.app_inc[k],1)+'%', dim:k!==1})).concat([4,1].map(k=>({label:(k===4?'Most':'Fewest')+' non-English speakers', sub:'language group', v:R.app_ne[k], vt:fmt(R.app_ne[k],1)+'%', dim:k!==4}))), {max:30});

  if(!$('#card')) return;
  // profile
  const comms = D.comms.slice().sort((a,b)=>a.n.localeCompare(b.n));
  comms.forEach(c=>$('#clist').append(el('option',{value:c.n})));
  const sorted = IND.map((x,i)=> D.comms.map(c=>c.v[i]).filter(v=>v!=null).sort((a,b)=>a-b));
  const rank = (i,v) => { const s=sorted[i]; if(v==null||!s.length) return null; let lo=0; while(lo<s.length && s[lo]<v) lo++; return lo/(s.length-1||1); };
  const groups = [...new Set(IND.map(x=>x.g))];
  function profile(c){
    const card=$('#card'); card.textContent='';
    if(!c){ card.append(el('p',{class:'note',text:'Pick a community to see its full profile.'})); return; }
    const gap = c.v[KI.report_gap_pct];
    const gapTxt = gap==null ? null : gap < -25 ? ['lo','Reports much less than similar communities'] : gap < -10 ? ['lo','Reports less than similar communities'] : gap > 10 ? ['ok','Reports more than similar communities'] : ['ok','Reports about as expected'];
    card.append(el('h3',{text:c.n}), el('div',{class:'chips'}, el('span',{class:'pill',text:c.q+' Calgary'}), c.b?el('span',{class:'pill',text:'First reached 500 residents: '+(c.b===1968?'1968 or earlier':c.b)}):null, gapTxt?el('span',{class:'pill '+gapTxt[0],text:gapTxt[1]}):null, c.g?el('span',{class:'pill',text:'Residential properties now '+c.g+'× its 2021 households: per-resident rates may be overstated'}):null));
    if(c.top.length) card.append(el('p',null, el('b',{text:'Most reported here: '}), c.top.map(t=>t[0]+' ('+fmt(t[1])+')').join(', ')));
    if(c.ind) card.append(el('p',{class:'note',text:'Largest industry: '+c.ind+'. Most common occupation group: '+c.occ+' (2021 Census).'}));
    groups.forEach(g=>{
      const box=el('div',{class:'grp'}, el('h4',{text:g}), el('div',{class:'ind head'}, el('span',{text:'Indicator'}), el('span',{class:'v',text:c.n.length>12?'Community':c.n}), el('span',{class:'c',text:'Calgary'}), el('span',{class:'p',text:'Rank'})));
      IND.forEach((x,i)=>{ if(x.g!==g) return; const v=c.v[i]; const r=rank(i,v); const pb=el('div',{class:'pbar'}); if(r!=null) pb.append(el('i',{style:'left:'+(r*100)+'%'}));
        box.append(el('div',{class:'ind',title:x.l+' · source: '+x.s}, el('span',null, x.l, el('small',{text:x.s})), el('span',{class:'v',text:show(x,v)}), el('span',{class:'c',text: x.k==='pop'?fmt(D.city.pop)+' (avg community)':show(x,D.city[x.k])}), el('span',{class:'p'},pb))); });
      card.append(box);
    });
    card.append(el('p',{class:'note',text:'Indicators marked "area" come from the Calgary Equity Index, measured for areas that group several neighbouring communities, so nearby communities share values. Years vary from 2014 to 2026 as shown.'}));
  }
  const find = v => comms.find(c=>c.n.toLowerCase()===v.trim().toLowerCase());
  $('#cq').addEventListener('input', e=>{ const c=find(e.target.value); if(c) profile(c); });
  ['Martindale','Saddle Ridge','Forest Lawn','Bowness','Beltline','Tuscany'].forEach(n=>{ const c=find(n); if(c){ const b=el('button',{type:'button',text:n}); b.onclick=()=>{ $('#cq').value=n; profile(c); }; $('#sugg').append(b);} });
  const h0 = decodeURIComponent(location.hash.slice(1));
  const pick = () => { const h = decodeURIComponent(location.hash.slice(1)); const c = comms.find(x=>x.c===h) || find(h.replace(/-/g,' ')); if(c){ $('#cq').value=c.n; profile(c); } };
  profile(comms.find(x=>x.c===h0) || find(h0.replace(/-/g,' ')) || find('Martindale')); if(h0) { const c=comms.find(x=>x.c===h0); if(c) $('#cq').value=c.n; }
  window.addEventListener('hashchange', pick);

  // table
  const cols = [['n','Community'],['q','Quad'],['pop','Residents'],['income','Median income (area)'],['noeng','No English % (area)'],['renter','Renters % (area)'],['med_home_value','Median home value'],['infra_rate','Infra reports /1k'],['expected_rate','Expected'],['report_gap_pct','Reporting gap'],['all_rate','All 311 /1k'],['app_share','App %'],['close7_ratio','Speed vs expected'],['walk_score','Walk Score (area)'],['equity_score','Equity score (area)']];
  let sortK='n', dir=1, filt='';
  const val = (c,k) => k==='n'?c.n : k==='q'?c.q : c.v[KI[k]];
  function table(){
    const t=$('#tbl'); t.textContent='';
    const hr=el('tr'); cols.forEach(([k,l])=>{ const th=el('th',{class:'sort'+(k!=='n'&&k!=='q'?' num':''),tabindex:'0',scope:'col',text:l}); if(k===sortK) th.setAttribute('aria-sort',dir>0?'ascending':'descending'); const go=()=>{ if(sortK===k) dir=-dir; else { sortK=k; dir=(k==='n'||k==='q')?1:-1; } table(); }; th.onclick=go; th.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); go(); } }; hr.append(th); });
    t.append(el('thead',null,hr));
    const tb=el('tbody');
    D.comms.filter(c=>!filt || c.n.toLowerCase().includes(filt) || c.q.toLowerCase()===filt)
      .sort((a,b)=>{ const x=val(a,sortK), y=val(b,sortK); if(x==null) return 1; if(y==null) return -1; return (typeof x==='string'? x.localeCompare(y) : x-y)*dir; })
      .forEach(c=>{ const tr=el('tr'); cols.forEach(([k])=>{ const v=val(c,k); const x=IND[KI[k]]; tr.append(el('td',{class:(k!=='n'&&k!=='q')?'num':'',text: k==='n'||k==='q' ? v : show(x,v)})); }); tr.style.cursor='pointer'; tr.onclick=()=>{ $('#cq').value=c.n; profile(c); $('#cq').scrollIntoView({behavior:'smooth',block:'center'}); }; tb.append(tr); });
    t.append(tb);
  }
  $('#tq').addEventListener('input', e=>{ filt=e.target.value.trim().toLowerCase(); table(); });
  table();

})();
