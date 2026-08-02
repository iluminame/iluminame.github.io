#!/usr/bin/env python3
"""Generations — the dashboard app for everything /generate makes (stdlib only).

Scans the FLAT generations folder (plus generations/refs/), reads each file's
sidecar .json for prompt/model/cost, and writes <root>/index.html: a dark
command-center media library — search, filter tabs (All / Images / Videos /
References), newest/oldest sort, pagination, a Styles panel (from the skill's
preset library) and a Models panel (from the models/ recipes), masonry wall,
hover-play videos, and a lightbox with full metadata + copy-prompt.
One file, no server: open it in a browser.

  python3 gallery.py                 # rebuild generations/index.html
  python3 gallery.py --embed         # portable build: media inlined as data URIs
  python3 gallery.py --stats         # spend by month/provider vs budget cap

Budget cap: <root>/budget.json {"monthly_cap_usd": 20} (created on first run).
"""
import argparse
import base64
import json
import mimetypes
import os
import re
from collections import defaultdict

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".svg"}
VID_EXT = {".mp4", ".webm", ".mov"}
DEFAULT_CAP = 20.0
EMBED_MAX = 3 * 1024 * 1024  # skip inlining files bigger than this
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_meta(path):
    sidecar = os.path.splitext(path)[0] + ".json"
    if os.path.exists(sidecar):
        try:
            return json.load(open(sidecar))
        except json.JSONDecodeError:
            pass
    return {}


def scan(root):
    """Media in the flat root + refs/, newest first."""
    items = []

    def add(folder, rel_prefix, section):
        if not os.path.isdir(folder):
            return
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            ext = os.path.splitext(name)[1].lower()
            if not os.path.isfile(path) or ext not in IMG_EXT | VID_EXT:
                continue
            meta = read_meta(path)
            stem = os.path.splitext(name)[0]
            project = stem.split("_")[0] if "_" in stem else ""
            items.append({
                "file": rel_prefix + name,
                "kind": "video" if ext in VID_EXT else "image",
                "section": section,          # generation | reference
                "project": project,
                "mtime": os.path.getmtime(path),
                "prompt": meta.get("prompt", ""),
                "model": meta.get("model", ""),
                "provider": meta.get("provider", ""),
                "style": meta.get("style", ""),
                "cost": meta.get("est_cost_usd"),
                "created": meta.get("created", ""),
                "params": meta.get("params") or {},
                "refs": meta.get("refs") or [],
            })

    add(root, "", "generation")
    add(os.path.join(root, "refs"), "refs/", "reference")
    return sorted(items, key=lambda i: -i["mtime"])


def parse_styles():
    """Preset cards from references/styles.md: name, description, model line."""
    path = os.path.join(SKILL_DIR, "references", "styles.md")
    if not os.path.exists(path):
        return []
    styles, current, category = [], None, "image"
    for line in open(path):
        line = line.rstrip()
        if line.startswith("## Video presets"):
            category = "video"
        elif line.startswith("### "):
            current = {"name": line[4:].split(" (")[0].strip(),
                       "desc": "", "model": "", "category": category}
            styles.append(current)
        elif current is not None:
            if not current["desc"] and line and not line.startswith((">", "#", "Model:")):
                current["desc"] = line.strip()
            elif line.startswith("Model: "):
                current["model"] = line[7:].strip()
                current = None
    return styles


def parse_models():
    """Model rows from models/*.md: name, tagline, type, cost, provider."""
    folder = os.path.join(SKILL_DIR, "models")
    if not os.path.isdir(folder):
        return []
    models = []
    for fname in sorted(os.listdir(folder)):
        if not fname.endswith(".md"):
            continue
        name = tagline = mtype = cost = provider = ""
        for line in open(os.path.join(folder, fname)):
            line = line.strip()
            if line.startswith("# ") and not name:
                name = line[2:]
            elif name and not tagline and line and not line.startswith(("|", "#")):
                tagline = line
            elif line.startswith("| Type |"):
                mtype = line.split("|")[2].strip()
            elif line.startswith("| Cost |"):
                cost = line.split("|")[2].strip()
            elif line.startswith("| Provider |"):
                provider = line.split("|")[2].strip()
        if name:
            models.append({"name": name, "desc": tagline, "type": mtype,
                           "cost": cost, "provider": provider})
    return models


def load_cap(root):
    path = os.path.join(root, "budget.json")
    if not os.path.exists(path):
        os.makedirs(root, exist_ok=True)
        json.dump({"monthly_cap_usd": DEFAULT_CAP}, open(path, "w"), indent=2)
        return DEFAULT_CAP
    try:
        return float(json.load(open(path)).get("monthly_cap_usd", DEFAULT_CAP))
    except (json.JSONDecodeError, ValueError):
        return DEFAULT_CAP


def stats(items, cap):
    gens = [i for i in items if i["section"] == "generation"]
    by_month, by_provider, total = defaultdict(float), defaultdict(float), 0.0
    for it in gens:
        cost = float(it["cost"] or 0)
        total += cost
        by_month[(it["created"] or "????-??")[:7]] += cost
        by_provider[it["provider"] or "?"] += cost
    print(f"{len(gens)} generations · total ~${total:.2f}\n")
    print(f"By month (cap ${cap:.2f}/mo):")
    for month in sorted(by_month):
        spent = by_month[month]
        pct = spent / cap * 100 if cap else 0
        flag = "  ⚠ over 80% of cap" if pct >= 80 else ""
        print(f"  {month}  ${spent:6.2f}  ({pct:.0f}% of cap){flag}")
    print("By provider:")
    for prov, spent in sorted(by_provider.items(), key=lambda kv: -kv[1]):
        print(f"  {prov:10s} ${spent:6.2f}")


def embed_media(root, items):
    for it in items:
        path = os.path.join(root, it["file"])
        size = os.path.getsize(path)
        if size > EMBED_MAX:
            print(f"  ⚠ not embedding {it['file']} ({size // 1024} KB > cap) — "
                  "tile will need the file next to the HTML")
            continue
        mime = mimetypes.guess_type(path)[0] or (
            "video/mp4" if it["kind"] == "video" else "image/png")
        with open(path, "rb") as f:
            it["src"] = f"data:{mime};base64," + base64.b64encode(f.read()).decode()


PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Generations</title>
<style>
:root{color-scheme:dark;
  --bg:#0a0a0d;--panel:#131317;--panel2:#17171c;--line:rgba(255,255,255,.08);
  --txt:#ececf1;--dim:#8b8b98;--acc:#ff6a2b;--acc2:#ffb182;
  --mono:ui-monospace,"Cascadia Code","JetBrains Mono",Menlo,Consolas,monospace;
  --sans:system-ui,-apple-system,"Segoe UI",sans-serif}
*{box-sizing:border-box;margin:0}
html{scrollbar-color:#333 var(--bg)}
body{background:var(--bg);color:var(--txt);font:15px/1.5 var(--sans);min-height:100vh;
  background-image:radial-gradient(circle at 18% -8%,rgba(255,106,43,.09),transparent 45%),
  radial-gradient(rgba(255,255,255,.035) 1px,transparent 1px);
  background-size:100% 100%,26px 26px}
a{color:var(--acc2)}
header{display:flex;align-items:center;gap:18px;flex-wrap:wrap;
  padding:26px 30px 10px}
.brand{font:700 19px/1 var(--mono);letter-spacing:.14em}
.brand .dot{display:inline-block;width:9px;height:9px;background:var(--acc);
  border-radius:2px;margin-right:10px;box-shadow:0 0 12px var(--acc);
  animation:pulse 2.6s ease-in-out infinite}
@keyframes pulse{50%{opacity:.45}}
.brand small{color:var(--dim);font-weight:400;letter-spacing:.02em;margin-left:10px}
.hright{margin-left:auto;display:flex;gap:8px;align-items:center}
#count{font:11px var(--mono);color:var(--dim);letter-spacing:.08em;margin-right:6px}
.btn{font:11px var(--mono);letter-spacing:.1em;color:var(--txt);background:transparent;
  border:1px solid var(--line);border-radius:8px;padding:8px 13px;cursor:pointer;
  transition:.15s}
.btn:hover{border-color:var(--acc);color:var(--acc2)}
.btn.on{border-color:var(--acc);color:var(--acc);background:rgba(255,106,43,.08)}
.panel{display:none;margin:10px 30px 4px;border:1px solid var(--line);
  border-radius:14px;background:var(--panel);padding:18px;
  animation:drop .18s ease-out}
.panel.on{display:block}
@keyframes drop{from{opacity:0;transform:translateY(-6px)}}
.panel h2{font:11px var(--mono);letter-spacing:.16em;color:var(--dim);margin:0 0 12px}
.pgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:10px}
.pcard{border:1px solid var(--line);border-radius:10px;background:var(--panel2);
  padding:12px 14px;transition:.15s}
.pcard:hover{border-color:rgba(255,106,43,.5);transform:translateY(-1px)}
.pcard b{font:600 13.5px var(--sans);display:block;margin-bottom:3px}
.pcard p{font-size:12px;color:var(--dim);line-height:1.45}
.pcard .chip{display:inline-block;font:10px var(--mono);color:var(--acc2);
  border:1px solid rgba(255,106,43,.35);border-radius:99px;padding:2px 8px;margin-top:8px}
.toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:14px 30px}
#q{background:var(--panel);border:1px solid var(--line);border-radius:9px;
  color:var(--txt);font:13px var(--sans);padding:9px 13px;width:230px;outline:none}
#q:focus{border-color:var(--acc)}
.tabs{display:flex;gap:2px;border:1px solid var(--line);border-radius:9px;
  padding:3px;background:var(--panel)}
.tab{font:11px var(--mono);letter-spacing:.07em;color:var(--dim);background:none;
  border:0;border-radius:6px;padding:6px 12px;cursor:pointer;transition:.15s}
.tab:hover{color:var(--txt)}
.tab.on{background:rgba(255,106,43,.14);color:var(--acc2)}
#sort{margin-left:auto}
.pager{display:flex;gap:4px}
.pager .btn{padding:7px 10px}
.wall{columns:4 250px;column-gap:13px;padding:8px 30px 60px}
.tile{break-inside:avoid;margin:0 0 13px;border-radius:13px;overflow:hidden;
  background:var(--panel);border:1px solid var(--line);cursor:zoom-in;
  transition:transform .16s,border-color .16s,box-shadow .16s;
  animation:up .35s ease-out backwards}
.tile:nth-child(-n+12){animation-delay:calc(var(--i)*35ms)}
@keyframes up{from{opacity:0;transform:translateY(10px)}}
.tile:hover{transform:translateY(-3px);border-color:rgba(255,106,43,.55);
  box-shadow:0 10px 28px rgba(0,0,0,.5)}
.tile img,.tile video{width:100%;display:block;background:#000}
.tmeta{padding:10px 12px 11px}
.tmeta b{font:600 13px var(--sans);display:block;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis}
.tmeta p{font-size:11.5px;color:var(--dim);line-height:1.4;max-height:2.8em;
  overflow:hidden;margin-top:2px}
.tags{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;
  font:10px var(--mono);color:var(--dim);letter-spacing:.03em}
.tags .cost{color:var(--acc)}
.tags .ref{color:var(--acc2)}
#empty{display:none;text-align:center;color:var(--dim);padding:80px 20px;
  font:13px var(--mono);letter-spacing:.06em}
#lb{position:fixed;inset:0;background:rgba(6,6,8,.94);display:none;z-index:9;
  align-items:center;justify-content:center;padding:3vh 3vw;cursor:zoom-out;
  backdrop-filter:blur(6px)}
#lb.on{display:flex}
.lbox{display:flex;gap:0;max-width:94vw;max-height:90vh;cursor:auto;
  background:var(--panel);border:1px solid var(--line);border-radius:16px;
  overflow:hidden;animation:drop .2s ease-out}
.lbox .media{display:flex;align-items:center;background:#000;max-width:64vw}
.lbox img,.lbox video{max-width:64vw;max-height:90vh;display:block}
.lmeta{width:300px;min-width:240px;padding:20px;overflow-y:auto}
.lmeta h3{font:11px var(--mono);letter-spacing:.16em;color:var(--dim);margin:14px 0 4px}
.lmeta h3:first-child{margin-top:0}
.lmeta .val{font-size:13px;word-wrap:break-word}
.lmeta .prompt{font-size:12.5px;line-height:1.55;color:var(--txt)}
.copy{margin-top:14px;width:100%}
@media(max-width:760px){.lbox{flex-direction:column}.lbox .media,.lbox img,.lbox video{max-width:94vw}
.lmeta{width:auto}}
</style></head><body>
<header>
  <div class="brand"><span class="dot"></span>GENERATIONS<small>made with /generate</small></div>
  <div class="hright">
    <span id="count"></span>
    <button class="btn" id="bStyles">STYLES ▾</button>
    <button class="btn" id="bModels">MODELS ▾</button>
  </div>
</header>
<section class="panel" id="pStyles"><h2>STYLE PRESETS — ask for any of these by name</h2><div class="pgrid" id="styleCards"></div></section>
<section class="panel" id="pModels"><h2>WIRED MODELS — one recipe file each</h2><div class="pgrid" id="modelCards"></div></section>
<div class="toolbar">
  <input id="q" type="search" placeholder="Search prompts, models, files…">
  <nav class="tabs" id="tabs"></nav>
  <button class="btn" id="sort">NEWEST ↓</button>
  <nav class="pager" id="pager"></nav>
</div>
<div class="wall" id="wall"></div>
<div id="empty">NOTHING HERE YET — TYPE /generate AND ASK FOR SOMETHING</div>
<div id="lb"></div>
<script>
const DATA=__DATA__;
const PER=30;
const state={tab:"all",q:"",sort:-1,page:1};
const $=id=>document.getElementById(id);
const esc=s=>(s||"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const TABS=[["all","ALL"],["image","IMAGES"],["video","VIDEOS"],["reference","REFERENCES"]];

function filtered(){
  const q=state.q.toLowerCase();
  let xs=DATA.items.filter(it=>{
    if(state.tab==="reference"){if(it.section!=="reference")return false}
    else if(state.tab!=="all"){if(it.section==="reference"||it.kind!==state.tab)return false}
    if(!q)return true;
    return (it.prompt+" "+it.model+" "+it.file+" "+it.style+" "+it.project).toLowerCase().includes(q);
  });
  xs.sort((a,b)=>state.sort*((b.created||"")+b.mtime).localeCompare((a.created||"")+a.mtime)||state.sort*(b.mtime-a.mtime));
  return xs;
}
function title(it){
  if(it.style)return it.style;
  const stem=it.file.replace(/^refs\//,"").replace(/\.[^.]+$/,"");
  const parts=stem.split("_");
  return (parts.length>2?parts.slice(1,-1).join(" "):stem).replace(/-/g," ");
}
function render(){
  const xs=filtered(),pages=Math.max(1,Math.ceil(xs.length/PER));
  state.page=Math.min(state.page,pages);
  const slice=xs.slice((state.page-1)*PER,state.page*PER);
  $("count").textContent=`${slice.length} OF ${xs.length} ITEMS`;
  $("wall").innerHTML=slice.map((it,i)=>{
    const src=esc(it.src||it.file);
    const media=it.kind==="video"
      ?`<video src="${src}" muted loop playsinline preload="metadata"></video>`
      :`<img src="${src}" loading="lazy" alt="${esc(title(it))}">`;
    const tags=[it.model&&`<span>${esc(it.model.split("/").pop())}</span>`,
      (it.created||"").slice(0,10)&&`<span>${esc((it.created||"").slice(0,10))}</span>`,
      it.cost!=null&&`<span class="cost">$${(+it.cost).toFixed(2)}</span>`,
      it.section==="reference"&&`<span class="ref">REF</span>`].filter(Boolean).join("");
    return `<figure class="tile" style="--i:${i}" data-id="${DATA.items.indexOf(it)}">${media}
      <figcaption class="tmeta"><b>${esc(title(it))}</b>
      ${it.prompt?`<p>${esc(it.prompt)}</p>`:""}
      <div class="tags">${tags}</div></figcaption></figure>`;
  }).join("");
  $("empty").style.display=xs.length?"none":"block";
  $("pager").innerHTML=pages<2?"":Array.from({length:pages},(_,i)=>
    `<button class="btn${i+1===state.page?" on":""}" data-p="${i+1}">${i+1}</button>`).join("");
  $("wall").querySelectorAll("video").forEach(v=>{
    const t=v.closest(".tile");
    t.addEventListener("mouseenter",()=>{v.play().catch(()=>{})});
    t.addEventListener("mouseleave",()=>v.pause());
  });
}
function lightbox(it){
  const src=esc(it.src||it.file);
  const media=it.kind==="video"
    ?`<video src="${src}" controls autoplay loop></video>`:`<img src="${src}">`;
  const row=(l,v)=>v?`<h3>${l}</h3><div class="val">${v}</div>`:"";
  $("lb").innerHTML=`<div class="lbox" onclick="event.stopPropagation()">
    <div class="media">${media}</div>
    <div class="lmeta">
      ${row("PROMPT",it.prompt?`<span class="prompt">${esc(it.prompt)}</span>`:"")}
      ${row("MODEL",esc(it.model))}${row("PROVIDER",esc(it.provider))}
      ${row("STYLE",esc(it.style))}
      ${row("PARAMS",esc(Object.entries(it.params||{}).filter(([,v])=>v!=null).map(([k,v])=>k+": "+v).join(" · ")))}
      ${row("REFS",(it.refs||[]).map(esc).join("<br>"))}
      ${row("COST",it.cost!=null?`<span style="color:var(--acc);font-family:var(--mono)">$${(+it.cost).toFixed(2)}</span>`:"")}
      ${row("CREATED",esc(it.created))}${row("FILE",esc(it.file))}
      ${it.prompt?`<button class="btn copy" id="cp">COPY PROMPT</button>`:""}
    </div></div>`;
  $("lb").classList.add("on");
  const cp=$("cp");
  if(cp)cp.onclick=()=>{navigator.clipboard.writeText(it.prompt);cp.textContent="COPIED ✓";
    setTimeout(()=>cp.textContent="COPY PROMPT",1200)};
}
$("tabs").innerHTML=TABS.map(([k,l])=>`<button class="tab${k==="all"?" on":""}" data-t="${k}">${l}</button>`).join("");
$("tabs").onclick=e=>{const b=e.target.closest(".tab");if(!b)return;
  document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("on",x===b));
  state.tab=b.dataset.t;state.page=1;render()};
$("q").oninput=e=>{state.q=e.target.value;state.page=1;render()};
$("sort").onclick=()=>{state.sort*=-1;$("sort").textContent=state.sort>0?"NEWEST ↓":"OLDEST ↑";render()};
$("pager").onclick=e=>{const b=e.target.closest("[data-p]");if(b){state.page=+b.dataset.p;render();scrollTo({top:0,behavior:"smooth"})}};
$("wall").onclick=e=>{const t=e.target.closest(".tile");if(t)lightbox(DATA.items[+t.dataset.id])};
$("lb").onclick=()=>{$("lb").classList.remove("on");$("lb").innerHTML=""};
document.addEventListener("keydown",e=>{if(e.key==="Escape"){$("lb").classList.remove("on");$("lb").innerHTML=""}});
const mkCards=(el,xs,f)=>{$(el).innerHTML=xs.map(f).join("")||"<p style='color:var(--dim);font-size:12px'>none found</p>"};
mkCards("styleCards",DATA.styles,s=>`<div class="pcard"><b>${esc(s.name)}</b><p>${esc(s.desc)}</p>${s.model?`<span class="chip">${esc(s.model)}</span>`:""}</div>`);
mkCards("modelCards",DATA.models,m=>`<div class="pcard"><b>${esc(m.name)}</b><p>${esc(m.desc)}</p>${m.type?`<span class="chip">${esc(m.type)}</span>`:""} ${m.cost?`<span class="chip">${esc(m.cost.split("—")[0].trim())}</span>`:""}</div>`);
const toggle=(btn,panel,other)=>{$(btn).onclick=()=>{$(other).classList.remove("on");
  const on=$(panel).classList.toggle("on");$(btn).classList.toggle("on",on);
  $(btn===("bStyles")?"bModels":"bStyles").classList.remove("on")}};
toggle("bStyles","pStyles","pModels");toggle("bModels","pModels","pStyles");
render();
</script></body></html>"""


def build(root, items, embed):
    if embed:
        embed_media(root, items)
    data = {"items": items, "styles": parse_styles(), "models": parse_models()}
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out = os.path.join(root, "index.html")
    with open(out, "w") as f:
        f.write(PAGE.replace("__DATA__", payload))
    gens = sum(1 for i in items if i["section"] == "generation")
    refs = len(items) - gens
    print(f"Generations app: {out} ({gens} generations, {refs} refs"
          f"{', media embedded — portable' if embed else ''})")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default="generations", help="the flat generations folder")
    p.add_argument("--embed", action="store_true",
                   help="inline media as data URIs → one portable file (bigger)")
    p.add_argument("--stats", action="store_true")
    args = p.parse_args()

    if not os.path.isdir(args.root):
        print(f"No '{args.root}' folder yet — nothing generated.")
        return
    items = scan(args.root)
    cap = load_cap(args.root)
    if args.stats:
        stats(items, cap) if items else print("No generations yet.")
    elif items:
        build(args.root, items, args.embed)
    else:
        print("No generations yet — nothing to build.")


if __name__ == "__main__":
    main()
