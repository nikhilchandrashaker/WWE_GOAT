import json

with open("wrestlers.json") as f: WRESTLERS = f.read()
with open("rivalries.json") as f: RIVALRIES = f.read()
with open("title_reigns.json") as f: TITLES = f.read()
with open("model_export.json") as f: MODEL = f.read()

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Ledger — Pro Wrestling Analytics</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet">
<style>
  :root{
    --bg: #14161F;
    --bg-raised: #1C1F2C;
    --bg-inset: #0F1017;
    --canvas: #EDE6D3;
    --canvas-dim: #A9A695;
    --brass: #C9962C;
    --brass-dim: #8A6A26;
    --heat: #A63A32;
    --heat-dim: #7A2C26;
    --steel: #5B6472;
    --rope: #3A3E4C;
    --radius: 3px;
  }
  *{box-sizing:border-box;}
  html,body{margin:0;padding:0;}
  body{
    background: var(--bg);
    color: var(--canvas);
    font-family:'IBM Plex Sans', sans-serif;
    -webkit-font-smoothing: antialiased;
    min-height:100vh;
  }
  .display{font-family:'Bebas Neue', sans-serif; letter-spacing:0.02em;}
  .mono{font-family:'IBM Plex Mono', monospace; font-variant-numeric: tabular-nums;}

  ::selection{background:var(--brass); color:var(--bg-inset);}
  a{color:var(--brass);}

  .shell{max-width:1180px; margin:0 auto; padding: 28px 24px 80px;}

  header.masthead{
    display:flex; align-items:baseline; justify-content:space-between;
    border-bottom:2px solid var(--rope);
    padding-bottom:18px; margin-bottom:6px; flex-wrap:wrap; gap:10px;
  }
  header.masthead .title{
    font-size:44px; line-height:0.9; color:var(--canvas);
  }
  header.masthead .title span{color:var(--brass);}
  header.masthead .sub{color:var(--canvas-dim); font-size:13px; max-width:360px; text-align:right;}

  nav.tabs{
    display:flex; gap:2px; margin: 22px 0 28px;
    border-bottom:1px solid var(--rope);
    overflow-x:auto;
  }
  nav.tabs button{
    background:none; border:none; cursor:pointer;
    font-family:'Bebas Neue', sans-serif; font-size:20px; letter-spacing:0.03em;
    color: var(--canvas-dim);
    padding: 10px 18px 12px;
    border-bottom: 3px solid transparent;
    white-space:nowrap;
  }
  nav.tabs button:hover{color:var(--canvas);}
  nav.tabs button.active{color:var(--brass); border-bottom-color:var(--brass);}

  .panel{display:none;}
  .panel.active{display:block; animation: fadein 0.25s ease;}
  @keyframes fadein{from{opacity:0; transform:translateY(4px);} to{opacity:1; transform:none;}}

  .rope-rule{
    height:6px; margin: 20px 0;
    background: repeating-linear-gradient(90deg, var(--rope) 0 10px, transparent 10px 20px);
    opacity:0.5;
  }

  .lede{color:var(--canvas-dim); font-size:14px; max-width:680px; margin: 0 0 20px; line-height:1.55;}
  .lede b{color:var(--canvas); font-weight:600;}

  .caveat{
    border-left:3px solid var(--heat);
    background: rgba(166,58,50,0.08);
    padding: 10px 14px; font-size:12.5px; color: var(--canvas-dim);
    margin: 0 0 20px; max-width:680px; line-height:1.5;
  }
  .caveat b{color:var(--canvas);}

  input[type=text], select{
    background:var(--bg-inset); border:1px solid var(--rope); color:var(--canvas);
    font-family:'IBM Plex Sans'; font-size:14px; padding:9px 12px; border-radius:var(--radius);
  }
  input[type=text]:focus, select:focus{outline:1px solid var(--brass); border-color:var(--brass);}

  table{width:100%; border-collapse:collapse; font-size:13.5px;}
  thead th{
    text-align:left; font-weight:600; color:var(--canvas-dim);
    border-bottom:1px solid var(--rope); padding:8px 10px; cursor:pointer; user-select:none;
    font-size:12px;
  }
  thead th:hover{color:var(--canvas);}
  thead th.active-sort{color:var(--brass);}
  tbody td{padding:9px 10px; border-bottom:1px solid rgba(58,62,76,0.4);}
  tbody tr:hover{background:rgba(255,255,255,0.02);}
  .rank{color:var(--canvas-dim); width:34px;}
  .name-cell{font-weight:600; color:var(--canvas); cursor:pointer;}
  .name-cell:hover{color:var(--brass);}
  .badge-collision{
    display:inline-block; margin-left:6px; font-size:10px; padding:1px 5px;
    border:1px solid var(--heat-dim); color:var(--heat); border-radius:2px; vertical-align:middle;
  }
  .score-bar-wrap{width:90px; height:6px; background:var(--bg-inset); border-radius:3px; overflow:hidden; display:inline-block; vertical-align:middle; margin-right:8px;}
  .score-bar{height:100%; background:linear-gradient(90deg,var(--brass-dim),var(--brass));}

  .card{
    background:var(--bg-raised); border:1px solid var(--rope); border-radius:var(--radius);
    padding:20px 22px;
  }
  .grid-2{display:grid; grid-template-columns:1.1fr 1.6fr; gap:20px;}
  @media (max-width:800px){.grid-2{grid-template-columns:1fr;}}

  .stat-row{display:flex; justify-content:space-between; padding:7px 0; border-bottom:1px solid rgba(58,62,76,0.4); font-size:14px;}
  .stat-row .k{color:var(--canvas-dim);}
  .stat-row .v{font-weight:600; color:var(--canvas);}

  .cc-title{font-size:34px; margin:0 0 2px;}
  .cc-meta{color:var(--canvas-dim); font-size:13px; margin-bottom:16px;}

  #rivalryGraph{width:100%; height:520px; background:var(--bg-inset); border:1px solid var(--rope); border-radius:var(--radius);}
  .riv-tooltip{position:absolute; background:var(--bg-raised); border:1px solid var(--brass); padding:8px 10px; font-size:12.5px; border-radius:3px; pointer-events:none; display:none; z-index:10;}

  .belt-list{max-height:520px; overflow-y:auto; border:1px solid var(--rope); border-radius:var(--radius);}
  .belt-list button{
    display:block; width:100%; text-align:left; background:none; border:none; color:var(--canvas-dim);
    padding:8px 12px; font-size:13px; cursor:pointer; border-bottom:1px solid rgba(58,62,76,0.3);
    font-family:'IBM Plex Sans';
  }
  .belt-list button:hover{background:rgba(255,255,255,0.03); color:var(--canvas);}
  .belt-list button.active{color:var(--brass); background:rgba(201,150,44,0.08);}

  .reign-row{display:flex; align-items:center; gap:10px; padding:9px 0; border-bottom:1px solid rgba(58,62,76,0.35); font-size:13px;}
  .reign-num{width:26px; color:var(--canvas-dim);}
  .reign-name{flex:1; font-weight:600;}
  .reign-dates{color:var(--canvas-dim); width:150px; font-size:12px;}
  .reign-bar-wrap{flex:1.4; height:8px; background:var(--bg-inset); border-radius:2px; overflow:hidden;}
  .reign-bar{height:100%; background:var(--brass-dim);}
  .reign-days{width:70px; text-align:right; color:var(--canvas-dim); font-size:12px;}
  .flag-long{color:var(--heat);}

  .predictor-cols{display:grid; grid-template-columns:1fr auto 1fr; gap:18px; align-items:center;}
  .vs{font-family:'Bebas Neue'; font-size:28px; color:var(--brass); text-align:center;}
  .predict-btn{
    background:var(--brass); color:var(--bg-inset); border:none; font-family:'Bebas Neue';
    font-size:18px; padding:11px 0; width:100%; border-radius:var(--radius); cursor:pointer; margin-top:14px;
    letter-spacing:0.03em;
  }
  .predict-btn:hover{background:#dba63a;}
  .result-bar-wrap{height:34px; background:var(--bg-inset); border-radius:3px; overflow:hidden; display:flex; margin:18px 0 8px;}
  .result-a{background:var(--brass); display:flex; align-items:center; justify-content:flex-start; padding-left:10px; font-weight:600; color:var(--bg-inset); font-size:13px;}
  .result-b{background:var(--heat-dim); display:flex; align-items:center; justify-content:flex-end; padding-right:10px; font-weight:600; color:var(--canvas); font-size:13px;}
  .feature-breakdown{font-size:12.5px; color:var(--canvas-dim); margin-top:10px; line-height:1.7;}

  .foot{margin-top:60px; padding-top:16px; border-top:1px solid var(--rope); color:var(--steel); font-size:11.5px;}
</style>
</head>
<body>
<div class="shell">

  <header class="masthead">
    <div class="title display">THE <span>LEDGER</span></div>
    <div class="sub">88,243 matches · 5,991 wrestlers · 1963–2026. Built from box-score data, not memory — see caveats on each tab.</div>
  </header>

  <nav class="tabs">
    <button data-tab="leaderboard" class="active">Leaderboard</button>
    <button data-tab="career">Career card</button>
    <button data-tab="rivalries">Rivalries</button>
    <button data-tab="titles">Title history</button>
    <button data-tab="predictor">Predictor</button>
  </nav>

  <!-- LEADERBOARD -->
  <section class="panel active" id="panel-leaderboard">
    <p class="lede">Ranked by a draft <b>GOAT score</b> — 30% win rate, 25% championship days held, 15% each for longevity, match volume, and strength of schedule. <b>Singles matches only</b>; tag-team careers are tracked separately on each wrestler's career card. Weights are a first pass — tell me how to reweight them and I'll rebuild the ranking.</p>
    <div class="caveat"><b>Known limitation:</b> 109 wrestlers are flagged <span class="badge-collision">possible name collision</span> — a long career with a big gap can mean one legend appearing sporadically, or two unrelated people who shared a common ring name. Treat their numbers as unverified.</div>
    <div style="margin-bottom:14px; display:flex; gap:10px; flex-wrap:wrap;">
      <input type="text" id="lbSearch" placeholder="Search wrestler…" style="width:240px;">
      <select id="lbMinMatches">
        <option value="10">10+ singles matches</option>
        <option value="25">25+ singles matches</option>
        <option value="50">50+ singles matches</option>
        <option value="100">100+ singles matches</option>
      </select>
    </div>
    <table>
      <thead><tr>
        <th class="rank">#</th>
        <th data-sort="name">Wrestler</th>
        <th data-sort="sw">Record (W-L)</th>
        <th data-sort="swr">Win %</th>
        <th data-sort="years">Yrs active</th>
        <th data-sort="reigns">Reigns</th>
        <th data-sort="goat" class="active-sort">GOAT score</th>
      </tr></thead>
      <tbody id="lbBody"></tbody>
    </table>
  </section>

  <!-- CAREER CARD -->
  <section class="panel" id="panel-career">
    <p class="lede">Look up any of the 5,991 wrestlers. Singles, tag, and multi-man (battle royal / handicap) records are shown separately, per how they're actually tracked in the data.</p>
    <input type="text" id="ccSearch" placeholder="Search wrestler by name…" style="width:320px; margin-bottom:20px;">
    <div id="ccResults" style="margin-bottom:16px;"></div>
    <div id="ccCard"></div>
  </section>

  <!-- RIVALRIES -->
  <section class="panel" id="panel-rivalries">
    <p class="lede">Head-to-head network of the 200 most-fought singles pairings (3+ meetings). Node size = total matches fought by that wrestler in this set; edge thickness = number of meetings between the pair; edge color runs brass (one-sided) to red (even split — the closest, most competitive rivalries).</p>
    <div style="position:relative;">
      <svg id="rivalryGraph"></svg>
      <div class="riv-tooltip" id="rivTooltip"></div>
    </div>
  </section>

  <!-- TITLES -->
  <section class="panel" id="panel-titles">
    <p class="lede">Reign-by-reign history for every belt with a recorded title change. <b>Singles and tag title reigns both included</b> here — this view is about the championship, not individual GOAT scoring.</p>
    <div class="caveat"><b>Known limitation:</b> a reign's end date is only as good as the next recorded title change for that belt. If a belt was retired, unified, or the dataset stops tracking it, that final reign will look artificially long (flagged below in red) — it does not mean that wrestler literally held the title for that many days.</div>
    <div class="grid-2">
      <div>
        <input type="text" id="beltSearch" placeholder="Search belt…" style="width:100%; margin-bottom:10px;">
        <div class="belt-list" id="beltList"></div>
      </div>
      <div class="card" id="reignPanel"><p class="lede" style="margin:0;">Select a belt to see its reign history.</p></div>
    </div>
  </section>

  <!-- PREDICTOR -->
  <section class="panel" id="panel-predictor">
    <p class="lede">A logistic regression trained on 61,149 singles matches, predicting the winner from stats <b>known before the match</b> (no lookahead): career win rate entering, head-to-head record entering, experience gap, and title-match flag.</p>
    <div class="caveat">
      <b>Honest accuracy check:</b> the model scores <span class="mono" id="modelAcc"></span> accuracy / <span class="mono" id="modelAuc"></span> AUC on held-out matches, versus a naive baseline of just picking whoever has the better career win rate, which alone gets <span class="mono" id="modelBaseline"></span>. The model beats that baseline, but not by a landslide — wrestling booking has a lot of narrative logic that raw stats don't capture. This is career-to-date stats standing in for "entering the match," so it's illustrative, not a live handicapping tool.
    </div>
    <div class="card">
      <div class="predictor-cols">
        <div>
          <label style="font-size:12px; color:var(--canvas-dim);">Wrestler A</label>
          <input type="text" id="predA" placeholder="Search…" style="width:100%; margin-top:4px;">
          <div id="predAResults"></div>
        </div>
        <div class="vs">VS</div>
        <div>
          <label style="font-size:12px; color:var(--canvas-dim);">Wrestler B</label>
          <input type="text" id="predB" placeholder="Search…" style="width:100%; margin-top:4px;">
          <div id="predBResults"></div>
        </div>
      </div>
      <label style="display:flex; align-items:center; gap:8px; margin-top:16px; font-size:13px; color:var(--canvas-dim);">
        <input type="checkbox" id="predTitle"> Title on the line
      </label>
      <button class="predict-btn" id="predictBtn">Call it</button>
      <div id="predictResult"></div>
    </div>
  </section>

  <div class="foot">Draft build — GOAT weights, reign-end handling, and name-collision flags are all first passes meant to be tuned, not final rulings.</div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>
const WRESTLERS = __WRESTLERS__;
const RIVALRIES = __RIVALRIES__;
const TITLES = __TITLES__;
const MODEL = __MODEL__;

const byId = {};
WRESTLERS.forEach(w => byId[w.id] = w);
const byName = {};
WRESTLERS.forEach(w => { if(!byName[w.name]) byName[w.name] = w; });

// ---------- TABS ----------
document.querySelectorAll('nav.tabs button').forEach(btn=>{
  btn.addEventListener('click', ()=>{
    document.querySelectorAll('nav.tabs button').forEach(b=>b.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('panel-'+btn.dataset.tab).classList.add('active');
  });
});

// ---------- LEADERBOARD ----------
let lbSort = {key:'goat', dir:-1};
function renderLeaderboard(){
  const q = document.getElementById('lbSearch').value.toLowerCase();
  const minM = parseInt(document.getElementById('lbMinMatches').value,10);
  let rows = WRESTLERS.filter(w=> w.sm>=minM && (!q || w.name.toLowerCase().includes(q)));
  rows.sort((a,b)=> (a[lbSort.key] > b[lbSort.key] ? 1 : -1) * lbSort.dir);
  rows = rows.slice(0,150);
  const maxGoat = Math.max(...WRESTLERS.map(w=>w.goat));
  const tbody = document.getElementById('lbBody');
  tbody.innerHTML = rows.map((w,i)=>`
    <tr>
      <td class="rank mono">${i+1}</td>
      <td class="name-cell" onclick="openCareer(${w.id})">${w.name}${w.collision?'<span class="badge-collision">unverified</span>':''}</td>
      <td class="mono">${w.sw}-${w.sl}</td>
      <td class="mono">${(w.swr*100).toFixed(1)}%</td>
      <td class="mono">${w.years}</td>
      <td class="mono">${w.reigns}</td>
      <td><span class="score-bar-wrap"><span class="score-bar" style="width:${(w.goat/maxGoat*100).toFixed(0)}%"></span></span><span class="mono">${w.goat.toFixed(1)}</span></td>
    </tr>`).join('');
}
document.getElementById('lbSearch').addEventListener('input', renderLeaderboard);
document.getElementById('lbMinMatches').addEventListener('change', renderLeaderboard);
document.querySelectorAll('#panel-leaderboard thead th[data-sort]').forEach(th=>{
  th.addEventListener('click', ()=>{
    const key = th.dataset.sort;
    if(lbSort.key===key) lbSort.dir *= -1; else {lbSort.key=key; lbSort.dir = key==='name'?1:-1;}
    document.querySelectorAll('#panel-leaderboard thead th').forEach(t=>t.classList.remove('active-sort'));
    th.classList.add('active-sort');
    renderLeaderboard();
  });
});
renderLeaderboard();

// ---------- CAREER CARD ----------
function renderCareerCard(w){
  const totalTag = w.tw+w.tl, totalMM = w.mmm;
  document.getElementById('ccCard').innerHTML = `
    <div class="card">
      <div class="cc-title display">${w.name}${w.collision?'<span class="badge-collision">unverified: possible name collision</span>':''}</div>
      <div class="cc-meta mono">${w.first || '?'} → ${w.last || '?'} · ${w.years} yrs active</div>
      <div class="rope-rule"></div>
      <div class="grid-2">
        <div>
          <div style="font-family:'Bebas Neue'; font-size:18px; color:var(--brass); margin-bottom:8px;">Singles (GOAT-eligible)</div>
          <div class="stat-row"><span class="k">Record</span><span class="v mono">${w.sw}-${w.sl}</span></div>
          <div class="stat-row"><span class="k">Win rate</span><span class="v mono">${(w.swr*100).toFixed(1)}%</span></div>
          <div class="stat-row"><span class="k">Strength of schedule</span><span class="v mono">${(w.sos*100).toFixed(1)}%</span></div>
          <div class="stat-row"><span class="k">Singles title reigns</span><span class="v mono">${w.reigns}</span></div>
          <div class="stat-row"><span class="k">Days as singles champ</span><span class="v mono">${w.reign_days.toLocaleString()}</span></div>
          <div class="stat-row"><span class="k">GOAT score</span><span class="v mono">${w.goat.toFixed(1)}</span></div>
        </div>
        <div>
          <div style="font-family:'Bebas Neue'; font-size:18px; color:var(--steel); margin-bottom:8px;">Tag &amp; multi-man (separate)</div>
          <div class="stat-row"><span class="k">Tag record</span><span class="v mono">${w.tw}-${w.tl} ${totalTag? '('+(w.tw/totalTag*100).toFixed(0)+'%)':''}</span></div>
          <div class="stat-row"><span class="k">Multi-man matches</span><span class="v mono">${w.mmm}</span></div>
          <div class="stat-row"><span class="k">Multi-man wins</span><span class="v mono">${w.mmw}</span></div>
        </div>
      </div>
    </div>`;
}
window.openCareer = function(id){
  document.querySelectorAll('nav.tabs button').forEach(b=>b.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelector('nav.tabs button[data-tab="career"]').classList.add('active');
  document.getElementById('panel-career').classList.add('active');
  renderCareerCard(byId[id]);
  document.getElementById('ccResults').innerHTML='';
  document.getElementById('ccSearch').value = byId[id].name;
}
document.getElementById('ccSearch').addEventListener('input', (e)=>{
  const q = e.target.value.toLowerCase();
  if(q.length<2){document.getElementById('ccResults').innerHTML=''; return;}
  const matches = WRESTLERS.filter(w=>w.name.toLowerCase().includes(q)).slice(0,8);
  document.getElementById('ccResults').innerHTML = matches.map(w=>
    `<button onclick="openCareer(${w.id})" style="display:inline-block; margin:2px 6px 2px 0; background:var(--bg-inset); border:1px solid var(--rope); color:var(--canvas); padding:5px 10px; border-radius:3px; cursor:pointer; font-size:12.5px;">${w.name}</button>`
  ).join('');
});

// ---------- RIVALRIES (D3 force graph) ----------
function renderRivalryGraph(){
  const svgEl = document.getElementById('rivalryGraph');
  const width = svgEl.clientWidth || 900, height = 520;
  const svg = d3.select('#rivalryGraph').attr('viewBox',[0,0,width,height]);
  const nodesMap = {};
  RIVALRIES.forEach(r=>{
    nodesMap[r.a] = (nodesMap[r.a]||0) + r.total;
    nodesMap[r.b] = (nodesMap[r.b]||0) + r.total;
  });
  const nodes = Object.keys(nodesMap).map(name=>({id:name, weight:nodesMap[name]}));
  const links = RIVALRIES.map(r=>({source:r.a, target:r.b, total:r.total, closeness:r.closeness, aw:r.aw, bw:r.bw}));

  const sizeScale = d3.scaleSqrt().domain(d3.extent(nodes,d=>d.weight)).range([4,16]);
  const widthScale = d3.scaleLinear().domain(d3.extent(links,d=>d.total)).range([0.6,5]);
  const colorScale = d3.scaleLinear().domain([0,1]).range(['#8A6A26','#A63A32']);

  const sim = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d=>d.id).distance(70).strength(0.25))
    .force('charge', d3.forceManyBody().strength(-60))
    .force('center', d3.forceCenter(width/2, height/2))
    .force('collide', d3.forceCollide(d=>sizeScale(d.weight)+6));

  const link = svg.append('g').selectAll('line').data(links).join('line')
    .attr('stroke', d=>colorScale(d.closeness))
    .attr('stroke-width', d=>widthScale(d.total))
    .attr('stroke-opacity', 0.55)
    .on('mousemove', (event,d)=>{
      const tt = document.getElementById('rivTooltip');
      tt.style.display='block';
      tt.style.left = (event.offsetX+16)+'px';
      tt.style.top = (event.offsetY+16)+'px';
      tt.innerHTML = `<b>${d.source.id||d.source}</b> ${d.aw} – ${d.bw} <b>${d.target.id||d.target}</b><br>${d.total} meetings`;
    })
    .on('mouseleave', ()=>{document.getElementById('rivTooltip').style.display='none';});

  const node = svg.append('g').selectAll('circle').data(nodes).join('circle')
    .attr('r', d=>sizeScale(d.weight))
    .attr('fill', '#C9962C')
    .attr('stroke', '#14161F').attr('stroke-width',1.5)
    .call(d3.drag()
      .on('start',(e,d)=>{if(!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y;})
      .on('drag',(e,d)=>{d.fx=e.x; d.fy=e.y;})
      .on('end',(e,d)=>{if(!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null;}));

  const label = svg.append('g').selectAll('text').data(nodes).join('text')
    .text(d=>d.id).attr('font-size',10).attr('fill','#EDE6D3').attr('font-family','IBM Plex Sans')
    .attr('dx', d=>sizeScale(d.weight)+3).attr('dy', 3).style('pointer-events','none');

  sim.on('tick', ()=>{
    link.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y).attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
    node.attr('cx',d=>d.x).attr('cy',d=>d.y);
    label.attr('x',d=>d.x).attr('y',d=>d.y);
  });
}
renderRivalryGraph();

// ---------- TITLES ----------
const beltNames = [...new Set(TITLES.map(t=>t.belt))].sort();
function renderBeltList(filter){
  const q = (filter||'').toLowerCase();
  document.getElementById('beltList').innerHTML = beltNames.filter(b=>b.toLowerCase().includes(q)).map(b=>
    `<button data-belt="${b.replace(/"/g,'&quot;')}">${b}</button>`
  ).join('');
  document.querySelectorAll('#beltList button').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      document.querySelectorAll('#beltList button').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      renderReigns(btn.dataset.belt);
    });
  });
}
function renderReigns(belt){
  const reigns = TITLES.filter(t=>t.belt===belt).sort((a,b)=>a.order-b.order);
  const maxDays = Math.max(...reigns.map(r=>r.days), 1);
  document.getElementById('reignPanel').innerHTML = `
    <div style="font-family:'Bebas Neue'; font-size:22px; color:var(--brass); margin-bottom:10px;">${belt}</div>
    ${reigns.map(r=>{
      const flagged = r.end===null && r.days>1825;
      return `<div class="reign-row">
        <span class="reign-num mono">${r.order}</span>
        <span class="reign-name">${r.champ}${r.kind==='tag'?' <span style="color:var(--steel); font-size:11px;">(tag)</span>':''}</span>
        <span class="reign-dates mono">${r.start} → ${r.end||'—'}</span>
        <span class="reign-bar-wrap"><span class="reign-bar" style="width:${(r.days/maxDays*100).toFixed(0)}%; ${flagged?'background:var(--heat-dim);':''}"></span></span>
        <span class="reign-days mono ${flagged?'flag-long':''}">${r.days.toLocaleString()}d${flagged?' ⚠':''}</span>
      </div>`;
    }).join('')}
  `;
}
document.getElementById('beltSearch').addEventListener('input', e=>renderBeltList(e.target.value));
renderBeltList('');

// ---------- PREDICTOR ----------
let predASel=null, predBSel=null;
function wireSearch(inputId, resultsId, onPick){
  document.getElementById(inputId).addEventListener('input', e=>{
    const q = e.target.value.toLowerCase();
    const box = document.getElementById(resultsId);
    if(q.length<2){box.innerHTML=''; return;}
    const matches = WRESTLERS.filter(w=>w.sm>=5 && w.name.toLowerCase().includes(q)).slice(0,6);
    box.innerHTML = matches.map(w=>`<button data-id="${w.id}" style="display:block; width:100%; text-align:left; background:var(--bg-inset); border:1px solid var(--rope); color:var(--canvas); padding:6px 10px; margin-top:4px; border-radius:3px; cursor:pointer; font-size:12.5px;">${w.name} <span class="mono" style="color:var(--canvas-dim);">(${w.sw}-${w.sl})</span></button>`).join('');
    box.querySelectorAll('button').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        const w = byId[parseInt(btn.dataset.id,10)];
        onPick(w);
        document.getElementById(inputId).value = w.name;
        box.innerHTML='';
      });
    });
  });
}
wireSearch('predA','predAResults', w=>predASel=w);
wireSearch('predB','predBResults', w=>predBSel=w);

function findRivalry(nameA,nameB){
  return RIVALRIES.find(r=> (r.a===nameA&&r.b===nameB) || (r.a===nameB&&r.b===nameA) );
}

document.getElementById('predictBtn').addEventListener('click', ()=>{
  const box = document.getElementById('predictResult');
  if(!predASel || !predBSel){
    box.innerHTML = `<p class="lede" style="color:var(--heat); margin-top:14px;">Pick both wrestlers from the search results first.</p>`;
    return;
  }
  const a = predASel, b = predBSel;
  const riv = findRivalry(a.name,b.name);
  let h2h_a = 0.5;
  if(riv){
    const aWins = riv.a===a.name ? riv.aw : riv.bw;
    const total = riv.total;
    h2h_a = aWins/total;
  }
  const titleFlag = document.getElementById('predTitle').checked ? 1 : 0;
  const expDiff = a.sm - b.sm;

  function score(wr, oppWr, h2h, exp, title){
    const feats = [wr, oppWr, h2h, exp, title];
    let z = MODEL.intercept;
    for(let i=0;i<feats.length;i++){
      const norm = (feats[i]-MODEL.scaler_mean[i])/MODEL.scaler_scale[i];
      z += norm * MODEL.coefficients[i];
    }
    return 1/(1+Math.exp(-z));
  }
  const pA = score(a.swr, b.swr, h2h_a, expDiff, titleFlag);
  const pct = (pA*100).toFixed(1);

  box.innerHTML = `
    <div class="result-bar-wrap">
      <div class="result-a" style="width:${pct}%">${a.name} ${pct}%</div>
      <div class="result-b" style="width:${(100-pct).toFixed(1)}%">${b.name} ${(100-pct).toFixed(1)}%</div>
    </div>
    <div class="feature-breakdown">
      Win rate entering: ${a.name} ${(a.swr*100).toFixed(1)}% vs ${b.name} ${(b.swr*100).toFixed(1)}%<br>
      Head-to-head (${riv?riv.total:0} meetings on record): ${a.name} has won ${(h2h_a*100).toFixed(0)}% of those<br>
      Experience gap: ${expDiff>0?a.name:b.name} has ${Math.abs(expDiff)} more career singles matches<br>
      ${titleFlag? 'Title match — small positive weight in the model.' : 'Non-title bout.'}
    </div>`;
});

document.getElementById('modelAcc').textContent = (MODEL.test_accuracy*100).toFixed(1)+'%';
document.getElementById('modelAuc').textContent = MODEL.test_auc.toFixed(3)+' AUC';
document.getElementById('modelBaseline').textContent = (MODEL.baseline_accuracy*100).toFixed(1)+'%';
</script>
</body>
</html>
"""

html = HTML_TEMPLATE.replace("__WRESTLERS__", WRESTLERS).replace("__RIVALRIES__", RIVALRIES).replace("__TITLES__", TITLES).replace("__MODEL__", MODEL)

with open("/mnt/user-data/outputs/wwe_analytics_dashboard.html", "w") as f:
    f.write(html)

print("Written, size MB:", len(html)/1024/1024)
