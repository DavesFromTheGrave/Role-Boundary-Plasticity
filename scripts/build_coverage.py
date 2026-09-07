"""Render coverage/data.json into coverage/coverage.html.

One self-contained file: no server, no external libraries, no network. The JSON
is inlined so the page opens straight from disk in Edge.

    python scripts/aggregate.py && python scripts/build_coverage.py
"""
import json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent if HERE.name == "scripts" else HERE
DATA = ROOT / "coverage" / "data.json"
OUT = ROOT / "coverage" / "coverage.html"

data = json.loads(DATA.read_text(encoding="utf-8"))
payload = json.dumps(data, separators=(",", ":"))

HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Role-Boundary-Plasticity &mdash; coverage map</title>
<style>
/* ---- theme tokens -------------------------------------------------- */
:root{
  --bg:#ffffff; --panel:#f7f8fa; --panel-2:#eef1f5; --ink:#14171c; --ink-dim:#5b636e;
  --line:#d8dde5; --line-soft:#e8ecf2; --accent:#184f95; --warn-bg:#fff4e5; --warn-ink:#7a4b00;
  --warn-line:#f0c98a; --err-bg:#fdecec; --err-ink:#8d2020; --err-line:#f0b4b4;
  --v2-bg:#f3eefc; --v2-ink:#553a8b; --v2-line:#d9c9f2;
  /* Cell text: theme tokens, never a ramp colour -- but NOT theme-swapped, because
     the ramp underneath it does not swap. A light-theme ink on the pale steps and a
     dark-theme ink on the same pale steps cannot both be legible, so the ink is
     chosen against the fill: dark ink for steps 0-3, light ink for 4-6, identically
     in both themes. Deviation from "text uses the theme text color", made for
     legibility; every other surface on the page does follow the theme. */
  --cell-ink:#14171c; --cell-ink-inv:#f4f7fb;
  --hatch:rgba(20,23,28,.14); --hatch-bg:#fbfcfd;
  --r0:#cde2fb; --r1:#9ec5f4; --r2:#6da7ec; --r3:#3987e5; --r4:#256abf; --r5:#184f95; --r6:#0d366b;
  /* CoT arm gets its own ramp in the same purple family as its column headers, so a
     post-snapshot cell is never mistaken for a published one at a glance. Same
     luminance steps as the blue ramp so the two stay comparable. */
  --p0:#e4d9f8; --p1:#c9b4f0; --p2:#ab8ce6; --p3:#8b64d6; --p4:#6f48b8; --p5:#553a8b; --p6:#3a2663;
  --shadow:0 1px 2px rgba(16,24,40,.06),0 1px 3px rgba(16,24,40,.10);
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#0e1116; --panel:#161a21; --panel-2:#1d222b; --ink:#e8ecf2; --ink-dim:#9aa4b2;
    --line:#2b323d; --line-soft:#222833; --accent:#7fb0f2; --warn-bg:#2b2213; --warn-ink:#f0c98a;
    --warn-line:#5a4620; --err-bg:#2c1717; --err-ink:#f3aaaa; --err-line:#5d2a2a;
    --v2-bg:#221c31; --v2-ink:#c3aef0; --v2-line:#413259;
    --hatch:rgba(232,236,242,.16); --hatch-bg:#12161c;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 1px 3px rgba(0,0,0,.5);
  }
}
:root[data-theme="dark"]{
  --bg:#0e1116; --panel:#161a21; --panel-2:#1d222b; --ink:#e8ecf2; --ink-dim:#9aa4b2;
  --line:#2b323d; --line-soft:#222833; --accent:#7fb0f2; --warn-bg:#2b2213; --warn-ink:#f0c98a;
  --warn-line:#5a4620; --err-bg:#2c1717; --err-ink:#f3aaaa; --err-line:#5d2a2a;
  --v2-bg:#221c31; --v2-ink:#c3aef0; --v2-line:#413259;
  --hatch:rgba(232,236,242,.16); --hatch-bg:#12161c;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 1px 3px rgba(0,0,0,.5);
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{background:var(--bg);color:var(--ink);
  font:13px/1.45 ui-sans-serif,system-ui,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:100%;padding:16px 18px 28px}
h1{font-size:17px;margin:0 0 2px;letter-spacing:-.01em}
.sub{color:var(--ink-dim);font-size:12px;margin:0 0 12px}
.sub code{background:var(--panel-2);padding:1px 5px;border-radius:4px;font-size:11px}
mark{background:none;color:var(--accent);font-weight:600}

/* ---- what never ran ------------------------------------------------ */
.gapwrap{border:1px solid var(--line);background:var(--panel);border-radius:10px;
  padding:12px 14px;margin:0 0 12px;box-shadow:var(--shadow)}
.gaphead{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:8px}
.gaphead h2{font-size:13px;margin:0;letter-spacing:.02em;text-transform:uppercase}
.gaphead .note{color:var(--ink-dim);font-size:11.5px}
.gaps{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:8px}
.gap{border:1px solid var(--line);background:var(--bg);border-radius:8px;padding:8px 10px}
.gap.err{background:var(--err-bg);border-color:var(--err-line)}
.gap.ok{opacity:.72}
.gap h3{margin:0 0 4px;font-size:12px;display:flex;gap:6px;align-items:baseline;flex-wrap:wrap}
.gap h3 .n{font-variant-numeric:tabular-nums;color:var(--ink-dim);font-weight:400}
.gap .why{font-size:11px;color:var(--ink-dim);margin:3px 0 0}
.pill{display:inline-block;font-size:10.5px;padding:1px 6px;border-radius:999px;
  border:1px solid var(--line);background:var(--panel-2);color:var(--ink-dim);white-space:nowrap}
.pill.v2{background:var(--v2-bg);color:var(--v2-ink);border-color:var(--v2-line)}
.pill.bad{background:var(--err-bg);color:var(--err-ink);border-color:var(--err-line)}
.pill.warn{background:var(--warn-bg);color:var(--warn-ink);border-color:var(--warn-line)}
.mlist{font-size:11.5px;color:var(--ink);word-break:break-word}
.mlist b{font-weight:600}

/* ---- controls ------------------------------------------------------ */
.controls{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin:0 0 10px;
  padding:8px 12px;border:1px solid var(--line);background:var(--panel);border-radius:8px}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:7px;overflow:hidden}
.seg button{appearance:none;border:0;background:var(--bg);color:var(--ink-dim);
  padding:5px 12px;font:inherit;font-size:12px;cursor:pointer}
.seg button+button{border-left:1px solid var(--line)}
.seg button[aria-pressed="true"]{background:var(--accent);color:#fff;font-weight:600}
label.chk{display:inline-flex;align-items:center;gap:7px;font-size:12px;cursor:pointer;color:var(--ink)}
.ctl-label{font-size:11px;color:var(--ink-dim);text-transform:uppercase;letter-spacing:.04em}
.legend{margin-left:auto;display:flex;align-items:center;gap:8px;font-size:11px;color:var(--ink-dim)}
.ramp{display:flex;border:1px solid var(--line);border-radius:4px;overflow:hidden}
.ramp i{width:16px;height:12px;display:block}
.key{display:inline-flex;align-items:center;gap:5px}
.swatch{width:13px;height:13px;border:1px solid var(--line);border-radius:3px;display:inline-block}

/* ---- grid ---------------------------------------------------------- */
.gridbox{border:1px solid var(--line);border-radius:10px;overflow:auto;background:var(--bg);
  box-shadow:var(--shadow);max-height:none}
table{border-collapse:separate;border-spacing:0;font-variant-numeric:tabular-nums}
th,td{border-right:1px solid var(--line-soft);border-bottom:1px solid var(--line-soft);
  padding:0;text-align:center;font-weight:400}
thead th{background:var(--panel);position:sticky;z-index:3;font-size:10.5px;color:var(--ink-dim);
  padding:3px 5px;white-space:nowrap}
thead tr:nth-child(1) th{top:0;z-index:4}
thead tr:nth-child(2) th{top:23px}
thead tr:nth-child(3) th{top:46px}
thead th.sc{font-size:11.5px;color:var(--ink);font-weight:700;letter-spacing:.04em;
  text-transform:uppercase;background:var(--panel-2);border-bottom:1px solid var(--line)}
thead th.lv{font-weight:600;color:var(--ink)}
thead th.v2{background:var(--v2-bg);color:var(--v2-ink)}
th.mname,td.mname{position:sticky;left:0;z-index:5;background:var(--bg);text-align:left;
  padding:3px 9px 3px 10px;white-space:nowrap;border-right:1px solid var(--line);
  min-width:206px;max-width:206px;width:206px;font-size:11.5px;
  overflow:hidden;text-overflow:ellipsis}
thead th.mname{z-index:6;background:var(--panel)}
tbody tr:hover td.mname{background:var(--panel-2)}
td.mname .mid{font-weight:600}
td.mname .prov{color:var(--ink-dim);font-size:9.5px;margin-left:5px;opacity:.85}
/* PNG export: no clipping anywhere, so a full-page screenshot shows every column */
body.export .gridbox{overflow:visible;max-height:none}
body.export .gridbox table{width:max-content}
body.export th.mname,body.export td.mname,body.export thead th,body.export tfoot th,
body.export tfoot td,body.export tr.labrow th{position:static}
tr.labrow th{background:var(--panel-2);text-align:left;padding:3px 10px;font-size:10.5px;
  font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-dim);
  position:sticky;left:0;z-index:5;border-bottom:1px solid var(--line);border-top:1px solid var(--line)}
td.cell{width:38px;min-width:38px;height:23px;font-size:10.5px;color:var(--cell-ink);cursor:default}
td.cell.dark{color:var(--cell-ink-inv)}
td.cell.none{background:var(--hatch-bg);
  background-image:repeating-linear-gradient(45deg,transparent 0 3px,var(--hatch) 3px 4px)}
td.cell.errored{background:var(--err-bg);color:var(--err-ink);font-size:12px;line-height:1}
/* superseded by design: ran the arm that replaced this one. Not a gap, and must not
   look like one -- but still visibly distinct from a cell that holds real data. */
td.cell.sup{background:var(--panel-2);color:var(--ink-dim);font-size:13px;line-height:1;opacity:.8}
/* not applicable: the model cannot do what this condition measures (no tool-call
   template). A capability boundary, not a coverage failure -- and excluded from
   the arm's denominator, so the map never reports it as a study that failed to run. */
td.cell.na{background:var(--warn-bg);color:var(--warn-ink);font-size:9px;line-height:1;
  letter-spacing:.02em}
td.tot{background:var(--panel);font-size:10.5px;padding:0 7px;white-space:nowrap;
  border-left:1px solid var(--line)}
td.tot.rate{font-weight:600}
tr.dead td.cell{background:var(--err-bg);
  background-image:repeating-linear-gradient(45deg,transparent 0 3px,var(--hatch) 3px 4px)}
tr.dead td.deadnote{background:var(--err-bg);color:var(--err-ink);font-size:11px;
  text-align:left;padding:3px 10px;font-weight:600;border-bottom:1px solid var(--err-line)}
tfoot th,tfoot td{background:var(--panel);font-size:10px;color:var(--ink-dim);padding:3px 4px;
  position:sticky;bottom:0;z-index:3;border-top:1px solid var(--line)}
tfoot th.mname{z-index:5}
tfoot td.short{color:var(--err-ink);font-weight:700}

/* ---- tooltip ------------------------------------------------------- */
#tip{position:fixed;z-index:50;pointer-events:none;opacity:0;transition:opacity .08s;
  background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:8px;
  padding:9px 11px;font-size:11.5px;max-width:330px;box-shadow:0 6px 20px rgba(16,24,40,.22);
  line-height:1.5}
#tip.on{opacity:1}
#tip .t{font-weight:700;margin-bottom:3px}
#tip .c{color:var(--ink-dim);margin-bottom:5px;font-size:11px}
#tip table{border-spacing:0;width:100%}
#tip table td{border:0;padding:0 0 1px;text-align:left;font-size:11px}
#tip table td:last-child{text-align:right;font-weight:600;padding-left:14px}
#tip .src{margin-top:5px;padding-top:5px;border-top:1px solid var(--line);
  color:var(--ink-dim);font-size:10.5px;word-break:break-all}
.foot{margin-top:12px;color:var(--ink-dim);font-size:11px}
.foot b{color:var(--ink)}
</style>
</head>
<body>
<div class="wrap">
  <h1>Role-Boundary-Plasticity &mdash; coverage map</h1>
  <p class="sub" id="sub"></p>
  <div class="gapwrap" id="gapwrap"></div>
  <div class="controls">
    <span class="ctl-label">Columns</span>
    <span class="seg" role="group">
      <button id="bCompact" aria-pressed="false">Compact</button>
      <button id="bFull" aria-pressed="true">Full</button>
    </span>
    <label class="chk"><input type="checkbox" id="cSup"> Include superseded runs</label>
    <span class="legend">
      <span class="key"><span class="swatch none-sw" style="background-image:repeating-linear-gradient(45deg,transparent 0 3px,var(--hatch) 3px 4px)"></span> never run</span>
      <span class="key"><span class="swatch" style="background:var(--err-bg);border-color:var(--err-line)"></span> all errored</span>
      <span class="key"><span class="swatch" style="background:var(--panel-2)"></span> superseded by design</span>
      <span class="key"><span class="swatch" style="background:var(--warn-bg);border-color:var(--warn-line)"></span> not applicable</span>
      <span>0%</span>
      <span class="ramp"><i style="background:var(--r0)"></i><i style="background:var(--r1)"></i><i style="background:var(--r2)"></i><i style="background:var(--r3)"></i><i style="background:var(--r4)"></i><i style="background:var(--r5)"></i><i style="background:var(--r6)"></i></span>
      <span class="ramp"><i style="background:var(--p0)"></i><i style="background:var(--p1)"></i><i style="background:var(--p2)"></i><i style="background:var(--p3)"></i><i style="background:var(--p4)"></i><i style="background:var(--p5)"></i><i style="background:var(--p6)"></i></span>
      <span>100% compromised (purple = CoT arm)</span>
    </span>
  </div>
  <div class="gridbox" id="gridbox"></div>
  <p class="foot" id="foot"></p>
</div>
<div id="tip"></div>
<span id="sizetag" hidden></span>
<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
const D = JSON.parse(document.getElementById('payload').textContent);
const RAMP  = ['--r0','--r1','--r2','--r3','--r4','--r5','--r6'];
const PRAMP = ['--p0','--p1','--p2','--p3','--p4','--p5','--p6'];
let compact = false, withSup = false;

const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const cellsNow = () => withSup ? D.cells_all : D.cells;
const filesNow = () => withSup ? D.cell_files_all : D.cell_files;

/* ---- columns ------------------------------------------------------- */
const LVL_LABEL = {control:'control', L1:'L1', L2:'L2', L3:'L3', L3_notags:'L3 notags',
  L3_forged:'L3 forged', forged_generic:'generic', forged_chatml:'chatml', forged_llama3:'llama3',
  forged_json:'json', forged_xml_anthropic:'xml', forged_plain_label:'plain', bare_command:'bare cmd',
  think_forged:'think forged', think_forged_destyled:'think destyled', forged_any:'forged, any syntax'};
const CH_LABEL = {tool_result:'tool', user_turn:'user', user_turn_matched:'user matched'};
const DF_LABEL = {none:'', brief:'brief', explicit:'explicit', strict:'strict', defended_any:'defended, any'};

function buildCols(){
  if(!compact) return D.conditions.map(c => ({...c, members:[c.key]}));
  const seen = new Map();
  for(const c of D.conditions){
    if(!seen.has(c.compact_key)){
      const p = c.compact_key.split('|');
      seen.set(c.compact_key, {key:c.compact_key, scaffold:p[0], level:p[1], channel:p[2],
                               defense:p[3], arm:c.arm, members:[]});
    }
    const g = seen.get(c.compact_key);
    g.members.push(c.key);
    if(c.arm === 'v1') g.arm = 'v1';           // a folded column is v1 if any member is
  }
  return [...seen.values()];
}

/* sum a model's cells across the members of one column */
function agg(model, col){
  const C = cellsNow(), F = filesNow();
  let n=0, comp=0, ref=0, det=0, err=0; const src=new Set();
  for(const m of col.members){
    const k = model + '||' + m;
    const v = C[k];
    if(v){ n+=v[0]; comp+=v[1]; ref+=v[2]; det+=v[3]; (F[k]||[]).forEach(f=>src.add(f)); }
    const e = D.cells_err[k];
    if(e) err += e;
  }
  return {n, comp, ref, det, err, src:[...src].sort()};
}

/* ---- what never ran ------------------------------------------------ */
function gapPanel(){
  const g = D.gaps, box = document.getElementById('gapwrap');
  const dead = new Set(g.no_usable_rows);
  const byId = Object.fromEntries(D.models.map(m => [m.id, m]));
  const cards = [];

  const notes = [];
  for(const kind of ['scaffold','level']){
    for(const [name, v] of Object.entries(g[kind])){
      if(!v.all.length) continue;
      const real = v.real || v.all, sup = v.superseded || [], na = v.not_applicable || [];
      const denom = v.n_applicable || D.models.length;
      if(!real.length && sup.length){
        // every absence here is a model that ran the arm which replaced this one
        notes.push(`<b>${esc(name)}</b> is absent for ${sup.length} models because they ran the
          six-syntax sweep that replaced it &mdash; not a gap.`);
        continue;
      }
      const parts = [];
      if(v.never_attempted.length)
        parts.push(`<div class="mlist"><b>never attempted (${v.never_attempted.length}):</b> ${esc(v.never_attempted.join(', '))}</div>`);
      if(v.errored.length)
        parts.push(`<div class="mlist"><b>attempted, every call errored (${v.errored.length}):</b> ${esc(v.errored.join(', '))}</div>`);
      if(sup.length)
        parts.push(`<div class="why">${sup.length} further models superseded this level by running the six-syntax sweep.</div>`);
      if(na.length)
        parts.push(`<div class="why">Excluded from the denominator: ${esc(na.join(', '))} &mdash;
          no tool-call capability, so this cannot be measured on them. Not a gap.</div>`);
      if(!real.length) continue;
      cards.push({n:real.length, html:
        `<div class="gap err"><h3><span class="pill bad">${esc(kind)}</span> <b>${esc(name)}</b>
         <span class="n">&mdash; ${real.length} of ${denom} ${na.length ? 'applicable ' : ''}models have no usable rows</span></h3>
         ${parts.join('')}</div>`});
    }
  }
  for(const id of g.no_usable_rows){
    const m = byId[id] || {};
    cards.push({n:1e6, html:
      `<div class="gap err"><h3><span class="pill bad">model</span> <b>${esc(id)}</b>
       <span class="n">&mdash; zero usable rows in the entire study</span></h3>
       <div class="mlist">${m.errors||0} logged calls, all failed.</div>
       <div class="why">${esc(m.err_top || 'unknown error')}</div></div>`});
  }
  cards.sort((a,b) => b.n - a.n);
  if(!cards.length) cards.push({html:'<div class="gap ok"><h3>Nothing missing.</h3></div>'});

  const clean = Object.entries(g.scaffold).filter(([,v]) => !v.all.length).map(([k]) => k);
  box.innerHTML =
    `<div class="gaphead"><h2>What never ran</h2>
       <span class="note">every model &times; scaffold and model &times; payload level with no usable
       rows, over the ${D.models.length} models in the main (non-superseded) set.
       ${clean.length ? 'Complete across all models: <b>' + esc(clean.join(', ')) + '</b>.' : ''}
       ${notes.join(' ')}</span>
     </div><div class="gaps">${cards.map(c => c.html).join('')}</div>`;
}

/* ---- grid ---------------------------------------------------------- */
function grid(){
  const cols = buildCols(), C = cellsNow();
  const scSpan = [], lvSpan = [];
  for(const c of cols){
    const last = scSpan[scSpan.length-1];
    if(last && last.name === c.scaffold) last.span++; else scSpan.push({name:c.scaffold, span:1});
    const lk = c.scaffold + '|' + c.level;
    const l2 = lvSpan[lvSpan.length-1];
    if(l2 && l2.k === lk) l2.span++; else lvSpan.push({k:lk, name:c.level, span:1, arm:c.arm});
  }
  const sub = c => {
    const bits = [];
    if(c.channel && c.channel !== 'tool_result') bits.push(CH_LABEL[c.channel] || c.channel);
    if(c.defense && c.defense !== 'none') bits.push(DF_LABEL[c.defense] || c.defense);
    if(!bits.length) bits.push(CH_LABEL[c.channel] || '&middot;');
    return bits.join(' / ');
  };

  let h = '<table><thead><tr><th class="mname" rowspan="3">model</th>';
  for(const s of scSpan) h += `<th class="sc" colspan="${s.span}">${esc(s.name)}</th>`;
  h += '<th class="sc" rowspan="3">usable</th><th class="sc" rowspan="3">compromised</th></tr><tr>';
  for(const l of lvSpan)
    h += `<th class="lv${l.arm==='v2'?' v2':''}" colspan="${l.span}">${LVL_LABEL[l.name]||esc(l.name)}</th>`;
  h += '</tr><tr>';
  for(const c of cols) h += `<th${c.arm==='v2'?' class="v2"':''}>${sub(c)}</th>`;
  h += '</tr></thead><tbody>';

  let lab = null;
  for(const m of D.models){
    if(m.lab !== lab){
      lab = m.lab;
      h += `<tr class="labrow"><th colspan="${cols.length+3}">${esc(lab)}</th></tr>`;
    }
    const dead = m.usable === 0;
    h += `<tr${dead?' class="dead"':''}><td class="mname"><span class="mid">${esc(m.id)}</span>`
       + `${m.provider?`<span class="prov">${esc(m.provider)}</span>`:''}</td>`;
    if(dead){
      h += `<td class="deadnote" colspan="${cols.length}">all ${m.errors} calls errored &mdash; `
         + `${esc(m.err_top||'unknown error')}</td>`
         + `<td class="tot">0</td><td class="tot rate">&mdash;</td></tr>`;
      continue;
    }
    let tn=0, tc=0;
    for(const c of cols){
      const a = agg(m.id, c);
      tn += a.n; tc += a.comp;
      const dk = `data-m="${esc(m.id)}" data-c="${esc(c.key)}"`;
      const supLv = (D.design_superseded[m.id] || []);
      const naLv = (D.not_applicable[m.id] || []);
      if(a.n === 0 && (naLv.includes(c.scaffold) || naLv.includes(c.level))){
        h += `<td class="cell na" ${dk}>n/a</td>`;
      } else if(a.n === 0 && a.err > 0){
        h += `<td class="cell errored" ${dk} title="">&times;</td>`;
      } else if(a.n === 0 && supLv.includes(c.level)){
        h += `<td class="cell sup" ${dk}>&ndash;</td>`;
      } else if(a.n === 0){
        h += `<td class="cell none" ${dk}></td>`;
      } else {
        const rate = a.comp / a.n, i = Math.min(6, Math.round(rate*6));
        const ramp = c.arm === 'v2' ? PRAMP : RAMP;
        h += `<td class="cell${i>=4?' dark':''}" style="background:var(${ramp[i]})" ${dk}>`
           + `${a.comp}/${a.n}</td>`;
      }
    }
    const rate = tn ? (100*tc/tn) : 0;
    h += `<td class="tot">${tn}</td><td class="tot rate">${tn?rate.toFixed(1)+'%':'&mdash;'}</td></tr>`;
  }
  h += '</tbody><tfoot><tr><th class="mname">models run</th>';
  const live = D.models.filter(m => m.usable > 0).length;
  for(const c of cols){
    let k = 0;
    for(const m of D.models) if(agg(m.id, c).n > 0) k++;
    h += `<td class="${k < D.models.length ? 'short' : ''}">${k}<span style="opacity:.55">/${D.models.length}</span></td>`;
  }
  h += `<td>${live}/${D.models.length}</td><td></td></tr></tfoot></table>`;
  document.getElementById('gridbox').innerHTML = h;
  wireTips();
}

/* ---- hover --------------------------------------------------------- */
const tip = document.getElementById('tip');
function wireTips(){
  const cols = Object.fromEntries(buildCols().map(c => [c.key, c]));
  const box = document.getElementById('gridbox');
  box.addEventListener('mousemove', e => {
    const td = e.target.closest('td.cell');
    if(!td){ tip.classList.remove('on'); return; }
    const mid = td.dataset.m, ck = td.dataset.c, c = cols[ck];
    const a = agg(mid, c);
    const cond = [c.scaffold, c.level, CH_LABEL[c.channel]||c.channel,
                  c.defense === 'none' ? 'no defense' : (DF_LABEL[c.defense]||c.defense)].join(' &middot; ');
    let rows;
    if(a.n === 0 && a.err > 0)
      rows = `<tr><td>calls attempted</td><td>${a.err}</td></tr>
              <tr><td>usable</td><td>0 &mdash; every call errored</td></tr>`;
    else if(a.n === 0 && ((D.not_applicable[mid] || []).includes(c.scaffold)
                       || (D.not_applicable[mid] || []).includes(c.level)))
      rows = `<tr><td colspan="2">not applicable &mdash; this model has no tool-call template,
              so it cannot fire <code>issue_refund</code> at all. Excluded from this arm's
              denominator rather than counted as a gap.${a.err?` ${a.err} calls were sent
              before this was known, and all 400'd.`:''}</td></tr>`;
    else if(a.n === 0 && (D.design_superseded[mid] || []).includes(c.level))
      rows = `<tr><td colspan="2">superseded by design &mdash; this model ran all six forged
              syntaxes, the sweep that replaced <code>L3_forged</code>. Not a gap.</td></tr>`;
    else if(a.n === 0)
      rows = `<tr><td colspan="2">never run &mdash; no rows logged for this cell</td></tr>`;
    else
      rows = `<tr><td>usable n</td><td>${a.n}</td></tr>
              <tr><td>compromised</td><td>${a.comp} (${(100*a.comp/a.n).toFixed(0)}%)</td></tr>
              <tr><td>provider-refused</td><td>${a.ref}</td></tr>
              <tr><td>detected in answer</td><td>${a.det}</td></tr>
              ${a.err?`<tr><td>errored (excluded)</td><td>${a.err}</td></tr>`:''}`;
    tip.innerHTML = `<div class="t">${esc(mid)}</div><div class="c">${cond}</div>`
      + `<table>${rows}</table>`
      + (a.src.length ? `<div class="src">${esc(a.src.join(', '))}</div>` : '');
    tip.classList.add('on');
    const r = tip.getBoundingClientRect();
    let x = e.clientX + 16, y = e.clientY + 16;
    if(x + r.width > innerWidth - 8) x = e.clientX - r.width - 14;
    if(y + r.height > innerHeight - 8) y = e.clientY - r.height - 14;
    tip.style.left = Math.max(8,x) + 'px'; tip.style.top = Math.max(8,y) + 'px';
  });
  box.addEventListener('mouseleave', () => tip.classList.remove('on'));
}

/* ---- chrome -------------------------------------------------------- */
function chrome(){
  const usable = D.models.reduce((s,m) => s + m.usable, 0);
  const main = D.models.reduce((s,m) => s + m.usable_main, 0);
  const dirs = D.raw_dirs.map(d => `<code>${esc(d.dir)}</code>`).join(' + ');
  document.getElementById('sub').innerHTML =
    `${D.models.length} models &times; ${D.conditions.length} conditions &middot; `
    + `<mark>${main.toLocaleString()}</mark> usable trials in the main set `
    + `(${usable.toLocaleString()} including superseded runs) &middot; from ${dirs} &middot; `
    + `commit ${esc(D.commit||'?')} &middot; built ${esc((D.generated||'').replace('T',' '))}`;
  const nsup = D.files.filter(f => f.superseded).length;
  const nder = D.files.filter(f => f.derived).length;
  document.getElementById('foot').innerHTML =
    `<b>Reading it.</b> A hatched cell was never run. A red &times; cell was attempted and every `
    + `call errored. Columns tinted purple are the CoT-forgery arm, which is <b>not</b> in the `
    + `published 5,270-row snapshot. Scoring is the study's own `
    + `<code>rescore.py</code> (<code>detected_injection</code>, <code>refund_tool_called</code>, `
    + `<code>api_refusal</code>, <code>CANARY</code>) &mdash; nothing reimplemented. `
    + `${nsup} superseded files are excluded unless the toggle is on; ${nder} derived rollup files `
    + `are excluded always (wrong schema, would double-count).`;
}

document.getElementById('bCompact').onclick = () => setMode(true);
document.getElementById('bFull').onclick = () => setMode(false);
function setMode(v){
  compact = v;
  document.getElementById('bCompact').setAttribute('aria-pressed', v);
  document.getElementById('bFull').setAttribute('aria-pressed', !v);
  grid();
}
document.getElementById('cSup').onchange = e => { withSup = e.target.checked; grid(); };

/* Export mode: ?export=1 unclips the grid so a headless screenshot captures every
   column, and publishes the exact page size so the shot can be sized to fit. */
if(location.search.includes('export')) document.body.classList.add('export');
if(location.search.includes('compact')) compact = true;
if(location.search.includes('sup')) withSup = true;
document.getElementById('bCompact').setAttribute('aria-pressed', compact);
document.getElementById('bFull').setAttribute('aria-pressed', !compact);
document.getElementById('cSup').checked = withSup;
chrome(); gapPanel(); grid();
if(document.body.classList.contains('export')){
  requestAnimationFrame(() => {
    const d = document.documentElement, b = document.body;
    const w = Math.max(d.scrollWidth, b.scrollWidth) + 24;
    const h = Math.max(d.scrollHeight, b.scrollHeight) + 24;
    document.getElementById('sizetag').textContent = `PAGESIZE ${w} ${h} ENDSIZE`;
  });
}
</script>
</body>
</html>
"""

OUT.write_text(HTML.replace("__PAYLOAD__", payload), encoding="utf-8")
kb = OUT.stat().st_size / 1024
print(f"wrote {OUT}  ({kb:.0f} KB, self-contained)")
