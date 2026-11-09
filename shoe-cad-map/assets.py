# -*- coding: utf-8 -*-
"""CSS + JS assets for the capability map."""

CSS = r"""
:root{
  --bg:#f6f4f0; --card:#ffffff; --ink:#23262b; --muted:#6b7280;
  --line:#e3ded6; --accent:#8a5a2b; --accent2:#2f6f8f;
  --shadow:0 1px 2px rgba(0,0,0,.05),0 8px 24px rgba(35,38,43,.06);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:1560px;margin:0 auto;padding:28px 22px 80px}
h1{font-size:30px;line-height:1.2;margin:0 0 6px;letter-spacing:-.4px}
h2{font-size:20px;margin:0 0 4px;letter-spacing:-.2px}
.sub{color:var(--muted);margin:0 0 20px;max-width:90ch}
section.blk{background:var(--card);border:1px solid var(--line);border-radius:14px;
  padding:22px;margin:20px 0;box-shadow:var(--shadow)}
section.blk>h2{display:flex;align-items:baseline;gap:10px}
.kick{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);
  font-weight:700;margin-bottom:6px}
.hint{color:var(--muted);font-size:13.5px;margin:2px 0 16px}

/* legend */
.legend{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0 4px}
.lg{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;color:#3c4149;
  background:#fbfaf8;border:1px solid var(--line);border-radius:999px;padding:5px 12px 5px 8px}
.lg .sw{width:20px;height:20px;border-radius:6px;display:grid;place-items:center;font-weight:700;font-size:13px}

/* pipeline */
.pipe{display:grid;grid-template-columns:repeat(6,minmax(190px,1fr));gap:14px;overflow-x:auto;padding-bottom:8px}
.stage{position:relative;background:#fcfbf9;border:1px solid var(--line);border-left:4px solid var(--sc);
  border-radius:10px;padding:12px 12px 14px;min-width:190px}
.stage header{display:flex;gap:9px;align-items:flex-start;margin-bottom:10px}
.stage .num{flex:0 0 24px;height:24px;border-radius:7px;background:var(--sc);color:#fff;
  display:grid;place-items:center;font-size:12.5px;font-weight:700}
.stage h3{margin:0;font-size:14px;line-height:1.25}
.stage p{margin:2px 0 0;font-size:11.5px;color:var(--muted);line-height:1.4}
.stage ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:6px}
.stage li{background:#fff;border:1px solid var(--line);border-radius:8px;padding:6px 8px;font-size:12px;line-height:1.35}
.stage li b{display:block;font-size:12.5px}
.stage li span{color:var(--muted);font-size:11px}
.stage .arrow{position:absolute;right:-13px;top:38px;color:#b6b0a6;font-size:16px;z-index:2}

/* routes */
.routes{display:grid;grid-template-columns:repeat(auto-fit,minmax(268px,1fr));gap:14px}
.route{background:#fcfbf9;border:1px solid var(--line);border-top:4px solid var(--rc);border-radius:10px;padding:14px}
.rt-h{display:flex;align-items:center;gap:9px;margin-bottom:8px}
.rt-tag{width:24px;height:24px;flex:0 0 24px;border-radius:7px;background:var(--rc);color:#fff;
  display:grid;place-items:center;font-weight:700;font-size:12px}
.rt-h h4{margin:0;font-size:14.5px;line-height:1.25}
.route p{margin:0 0 8px;font-size:12.8px;color:#41464d}
.rt-how{font-style:italic;color:var(--muted)}
.rt-tools{font-weight:600;color:#2b2f35}
.rt-v{border-top:1px dashed var(--line);padding-top:8px;margin-top:2px}
.rt-v b{color:var(--rc)}

/* matrix */
.matrix-wrap{overflow:auto;max-height:78vh;border:1px solid var(--line);border-radius:10px;background:#fff}
table.matrix{border-collapse:separate;border-spacing:0;font-size:12.5px;min-width:max-content}
table.matrix th,table.matrix td{border-right:1px solid #eee9e1;border-bottom:1px solid #eee9e1}
table.matrix thead th{position:sticky;top:0;z-index:5;background:#f3efe9;text-align:center;
  font-weight:600;vertical-align:bottom}
table.matrix thead tr.grp th{top:0;height:26px;font-size:11px;letter-spacing:.06em;text-transform:uppercase;
  color:#6b6255;background:#ece7df}
table.matrix thead tr:nth-child(2) th{top:26px;height:66px}
th.gt.score-col{background:#e7dfd4!important;color:#5b4630!important}
th.band{font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;color:#4b4237;
  background:#ece7df!important;padding:5px 6px 6px;position:relative}
th.band .bn{display:inline-block;margin-left:5px;font-size:9px;background:#d9d2c6;color:#5f5648;
  border-radius:5px;padding:0 4px;line-height:14px;vertical-align:1px}
tr.secrow th.sec{position:sticky;left:0;z-index:4;background:#efeae2;color:#5f5648;text-align:left;
  font-size:10.5px;letter-spacing:.11em;text-transform:uppercase;font-weight:700;
  padding:6px 12px;border-top:2px solid #ddd6ca;border-bottom:1px solid #ddd6ca}
th.tool{min-width:80px;max-width:80px;padding:6px 4px}
th.tool .tn{display:block;font-size:11.5px;line-height:1.2;font-weight:700;color:#2b2f35}
th.tool .tc{display:block;font-size:9.5px;color:var(--muted);margin-top:3px;line-height:1.2;font-weight:500}
th.sticky{position:sticky;left:0;z-index:6;background:#f7f4ef;text-align:left;min-width:270px;max-width:270px}
th.corner{z-index:8;top:0;background:#ece7df}
thead tr:nth-child(2) th.sticky{top:26px}
th.feat{padding:8px 10px;font-weight:600;font-size:12.3px;line-height:1.3}
th.feat .wt{display:block;font-size:9.5px;color:#9a9287;font-weight:600;letter-spacing:.03em;margin-top:2px}
td.c{text-align:center;padding:0;height:32px;min-width:78px;max-width:78px}
td.c .g{font-size:14px;font-weight:700}
td.cost{font-size:10.5px;color:#5c6169;padding:5px 6px;line-height:1.35;min-width:200px;max-width:200px;
  white-space:normal;text-align:left}
tr:hover td.c{filter:saturate(1.35)}
tr.dim td.c,tr.dim th.feat{opacity:.18}
tr.hl td.c{outline:1px solid #d9c9ae}
td.score,th.sc{min-width:104px;max-width:104px;padding:5px 7px;background:#faf8f5}
td.score.blank{background:repeating-linear-gradient(135deg,#faf8f5,#faf8f5 6px,#f4f1ec 6px,#f4f1ec 12px)}
.bar{position:relative;height:16px;background:#eceae5;border-radius:5px;overflow:hidden}
.bar .fill{position:absolute;inset:0 auto 0 0;border-radius:5px}
.bar .pct{position:absolute;left:6px;top:0;font-size:10.5px;font-weight:700;color:#31353b;line-height:16px}
.bar .raw{position:absolute;right:5px;top:0;font-size:9.5px;color:#6f7681;line-height:16px}
tr.scorerow th.feat{background:#f1ece4;font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;color:#6b6255}
.controls{display:flex;flex-wrap:wrap;gap:9px;align-items:center;margin:0 0 12px}
.controls input[type=search]{flex:1 1 260px;padding:9px 12px;border:1px solid var(--line);border-radius:9px;
  font:inherit;font-size:13.5px;background:#fff}
.controls button{padding:8px 13px;border:1px solid var(--line);border-radius:9px;background:#fff;
  font:inherit;font-size:12.5px;cursor:pointer;color:#3c4149;transition:.15s}
.controls button:hover{border-color:#c9c2b6;background:#fbfaf8}
.controls button.on{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
.controls .sp{flex:1}
.sortable{cursor:pointer}
.sortable:hover{background:#e7dfd4!important}
.count{font-size:12px;color:var(--muted)}

/* feature detail */
.fd-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:12px}
.fd{background:#fcfbf9;border:1px solid var(--line);border-radius:10px;padding:11px 13px}
.fd-h{display:flex;justify-content:space-between;gap:8px;align-items:baseline;margin-bottom:3px}
.fd-h b{font-size:13px}
.fd-g{font-size:9.5px;letter-spacing:.07em;text-transform:uppercase;color:#9a9287;white-space:nowrap}
.fd-n{font-size:11.8px;color:var(--muted);margin-bottom:8px;line-height:1.45}
.fd-r{display:flex;gap:8px;align-items:flex-start;margin-top:5px}
.lbl{flex:0 0 56px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;padding-top:3px}
.lbl.ok{color:#1a7f4b}.lbl.pt{color:#a5701a}.lbl.un{color:#8b62b0}
.chips{display:flex;flex-wrap:wrap;gap:4px}
.chip{font-size:10.8px;padding:2px 7px;border-radius:6px;border:1px solid;line-height:1.5}
.chip.ok{background:#e7f6ed;border-color:#bfe3cd;color:#1a5f3b}
.chip.pt{background:#fdf3e0;border-color:#ecd9b4;color:#7d5410}
.chip.un{background:#f4eefb;border-color:#ddcdf0;color:#6d4a8f}
.none{font-size:11px;color:#b3aca1}

/* ranking */
table.rank{width:100%;border-collapse:collapse;font-size:13px}
table.rank th{text-align:left;font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:#8b8377;
  padding:0 10px 8px;border-bottom:1px solid var(--line)}
table.rank td{padding:9px 10px;border-bottom:1px solid #f1ede6;vertical-align:middle}
table.rank tr:hover td{background:#fcfbf9}
.rk-name b{display:block;font-size:13.2px}
.rk-name span{display:block;font-size:11.3px;color:var(--muted);line-height:1.35;margin-top:1px}
.rk-cls{font-size:11.5px;color:#5c6169;white-space:nowrap}
.rk-bar{width:210px}
.rk-cov{font-size:11.5px;color:#8b8377;text-align:center;font-variant-numeric:tabular-nums}

/* checklist */
table.chk{width:100%;border-collapse:collapse;font-size:13px}
table.chk td{padding:7px 10px;border-bottom:1px solid #f1ede6}
table.chk td:first-child{font-weight:600;width:26%}
table.chk td:nth-child(2){color:#5c6169;width:60%}
table.chk td:last-child{width:14%;text-align:right}
table.chk input{display:none}
table.chk .box{display:inline-block;width:17px;height:17px;border:1.5px solid #c6bfb3;border-radius:5px;
  vertical-align:middle;position:relative;cursor:pointer}
table.chk input:checked+.box{background:#1a7f4b;border-color:#1a7f4b}
table.chk input:checked+.box:after{content:"\2713";color:#fff;font-size:12px;position:absolute;
  left:2.5px;top:-1px}
table.chk tr.done td{opacity:.45}

/* sources */
ol.src{columns:2;column-gap:34px;font-size:12.5px;padding-left:20px;margin:0}
ol.src li{margin-bottom:5px;break-inside:avoid;color:#4a4f57}
ol.src a{color:var(--accent2);text-decoration:none;word-break:break-all}
ol.src a:hover{text-decoration:underline}

footer{color:var(--muted);font-size:12px;margin-top:26px;text-align:center}
@media(max-width:900px){
  .pipe{grid-template-columns:1fr}
  .stage .arrow{display:none}
  ol.src{columns:1}
  th.sticky{min-width:200px;max-width:200px}
}
@media print{
  body{background:#fff}
  .matrix-wrap{max-height:none;overflow:visible}
  .controls{display:none}
  section.blk{box-shadow:none;break-inside:avoid}
}
"""

JS = r"""
(function(){
  var table = document.getElementById('matrix');
  if(!table) return;
  var search = document.getElementById('q');
  var count  = document.getElementById('count');
  var rows   = Array.prototype.slice.call(table.querySelectorAll('tbody tr[data-key]'));
  var featCells = table.querySelectorAll('th.feat');

  function applyFilter(){
    var q = (search.value||'').trim().toLowerCase();
    var shown = 0;
    var pending = null;          // current section row, and how many of its features survived
    Array.prototype.slice.call(table.querySelectorAll('tbody tr')).forEach(function(r){
      if(r.classList.contains('secrow')){
        if(pending) pending.row.style.display = pending.n ? '' : 'none';
        pending = {row:r, n:0};
        return;
      }
      if(r.classList.contains('scorerow')) return;
      var label = r.querySelector('th.feat').textContent.toLowerCase();
      var hit = !q || label.indexOf(q)>-1 || r.getAttribute('data-key').indexOf(q)>-1;
      r.classList.toggle('dim', !hit);
      if(hit){ shown++; if(pending) pending.n++; }
    });
    if(pending) pending.row.style.display = pending.n ? '' : 'none';
    count.textContent = shown + ' of ' + rows.length + ' features shown';
  }
  search.addEventListener('input', applyFilter);

  // "only show what matters for a last"
  var CORE = ['scan_in','scan2d_in','measure_in','wb','meas_extract','last_gen','last_lib','allowances',
              'param_last','morph','sculpt','ortho_corr','compare','print_check','export_am'];
  var coreBtn = document.getElementById('coreOnly');
  var coreOn = false;
  coreBtn.addEventListener('click', function(){
    coreOn = !coreOn;
    coreBtn.classList.toggle('on', coreOn);
    rows.forEach(function(r){
      r.classList.toggle('hl', coreOn && CORE.indexOf(r.getAttribute('data-key'))>-1);
    });
  });

  // ---- sort tool columns by a score row -------------------------------
  var headRow = table.querySelectorAll('thead tr')[1];
  var N = headRow.querySelectorAll('th.tool').length;
  // perm[position] = original tool index currently sitting at that position
  var perm = []; for(var i0=0;i0<N;i0++){ perm.push(i0); }

  function toolCellsOf(tr){
    // child 0 is the sticky feature header; children 1..N are the tool cells
    return Array.prototype.slice.call(tr.children).slice(1, 1 + N);
  }

  function reorder(newPerm){
    Array.prototype.slice.call(table.querySelectorAll('tbody tr')).forEach(function(tr){
      var cells = toolCellsOf(tr);
      if(cells.length !== N) return;
      var tail = Array.prototype.slice.call(tr.children).slice(1 + N);
      var byOrig = {};
      perm.forEach(function(orig, pos){ byOrig[orig] = cells[pos]; });
      newPerm.forEach(function(orig){ tr.appendChild(byOrig[orig]); });
      tail.forEach(function(c){ tr.appendChild(c); });   // score column stays pinned right
    });
    // header row 2: tool ths first, the two sortable score ths pinned at the end
    var ths = Array.prototype.slice.call(headRow.children).slice(0, N);
    var tail = Array.prototype.slice.call(headRow.children).slice(N);
    var byOrig = {};
    perm.forEach(function(orig, pos){ byOrig[orig] = ths[pos]; });
    newPerm.forEach(function(orig){ headRow.appendChild(byOrig[orig]); });
    tail.forEach(function(th){ headRow.appendChild(th); });
    perm = newPerm;
  }

  Array.prototype.slice.call(headRow.querySelectorAll('th.sc')).forEach(function(th){
    th.addEventListener('click', function(){
      var kind = th.getAttribute('data-kind');
      var scoreRow = table.querySelector('tr.scorerow[data-kind="' + kind + '"]');
      if(!scoreRow) return;
      var vals = toolCellsOf(scoreRow).map(function(c){
        return parseInt(c.getAttribute('data-v') || '0', 10);
      });
      var positions = perm.map(function(_, pos){ return pos; })
        .sort(function(a, b){ return vals[b] - vals[a] || a - b; });
      reorder(positions.map(function(pos){ return perm[pos]; }));
      headRow.querySelectorAll('th.sc').forEach(function(s){
        var base = s.getAttribute('data-kind') === 'core' ? 'Last core' : 'Shoe full';
        s.textContent = (s === th) ? base + ' \u2193' : base;
      });
    });
  });

  document.getElementById('reset').addEventListener('click', function(){ location.reload(); });

  // ranking table sort
  var rankTable = document.getElementById('rank');
  if(rankTable){
    rankTable.querySelectorAll('th[data-sort]').forEach(function(th){
      th.addEventListener('click', function(){
        var key = th.getAttribute('data-sort');
        var body = rankTable.querySelector('tbody');
        var trs = Array.prototype.slice.call(body.querySelectorAll('tr'));
        trs.sort(function(a,b){ return parseInt(b.getAttribute(key),10) - parseInt(a.getAttribute(key),10); });
        trs.forEach(function(t){ body.appendChild(t); });
      });
    });
  }

  // checklist
  document.querySelectorAll('table.chk input').forEach(function(cb){
    cb.addEventListener('change', function(){
      cb.closest('tr').classList.toggle('done', cb.checked);
      var total = document.querySelectorAll('table.chk input').length;
      var done  = document.querySelectorAll('table.chk input:checked').length;
      var el = document.getElementById('chkCount');
      if(el) el.textContent = done + ' / ' + total + ' verified';
    });
  });

  applyFilter();
})();
"""
