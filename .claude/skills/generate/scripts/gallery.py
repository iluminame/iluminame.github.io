#!/usr/bin/env python3
"""The gallery wall: one local HTML page showing everything /generate makes.

Scans the FLAT generations folder (images + videos, newest first), reads each
file's sidecar .json (same basename) for prompt/model/cost, and writes
<root>/index.html — a masonry bento wall: tiles keep their own shape (no
cropping), rounded cards, 4 columns collapsing as the window narrows, videos
play quietly on hover, click opens big, click outside closes. No search, no
filters — just the wall. One file, no server: open it in a browser.

  python3 gallery.py                 # rebuild generations/index.html
  python3 gallery.py --stats         # spend by month/provider vs budget cap

Budget cap: <root>/budget.json {"monthly_cap_usd": 20} (created on first run).
"""
import argparse
import html
import json
import os
from collections import defaultdict

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif"}
VID_EXT = {".mp4", ".webm", ".mov"}
DEFAULT_CAP = 20.0


def scan(root):
    """Media files in the flat root (refs/ and subfolders excluded), newest first."""
    items = []
    for name in os.listdir(root):
        path = os.path.join(root, name)
        ext = os.path.splitext(name)[1].lower()
        if not os.path.isfile(path) or ext not in IMG_EXT | VID_EXT:
            continue
        meta = {}
        sidecar = os.path.splitext(path)[0] + ".json"
        if os.path.exists(sidecar):
            try:
                meta = json.load(open(sidecar))
            except json.JSONDecodeError:
                pass
        items.append({
            "file": name,
            "kind": "video" if ext in VID_EXT else "image",
            "mtime": os.path.getmtime(path),
            "meta": meta,
        })
    return sorted(items, key=lambda i: -i["mtime"])


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
    by_month, by_provider, total = defaultdict(float), defaultdict(float), 0.0
    for it in items:
        m = it["meta"]
        cost = float(m.get("est_cost_usd") or 0)
        total += cost
        by_month[(m.get("created") or "????-??")[:7]] += cost
        by_provider[m.get("provider", "?")] += cost
    print(f"{len(items)} generations · total ~${total:.2f}\n")
    print(f"By month (cap ${cap:.2f}/mo):")
    for month in sorted(by_month):
        spent = by_month[month]
        pct = spent / cap * 100 if cap else 0
        flag = "  ⚠ over 80% of cap" if pct >= 80 else ""
        print(f"  {month}  ${spent:6.2f}  ({pct:.0f}% of cap){flag}")
    print("By provider:")
    for prov, spent in sorted(by_provider.items(), key=lambda kv: -kv[1]):
        print(f"  {prov:10s} ${spent:6.2f}")


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Generations</title><style>
:root{color-scheme:dark}
*{box-sizing:border-box;margin:0}
body{background:#0e0e12;color:#ececef;font:15px/1.5 system-ui,sans-serif;padding:28px}
h1{font-size:1.25rem;letter-spacing:.02em}
.sub{color:#8f8f9c;font-size:.85rem;margin:.2rem 0 1.6rem}
.wall{columns:4 260px;column-gap:14px}
.tile{break-inside:avoid;margin:0 0 14px;border-radius:14px;overflow:hidden;
  background:#17171d;cursor:zoom-in;transition:transform .15s}
.tile:hover{transform:translateY(-2px)}
.tile img,.tile video{width:100%;display:block}
#lb{position:fixed;inset:0;background:rgba(8,8,10,.92);display:none;
  align-items:center;justify-content:center;flex-direction:column;padding:4vh 4vw;cursor:zoom-out}
#lb.on{display:flex}
#lb img,#lb video{max-width:92vw;max-height:80vh;border-radius:12px}
#lb .cap{color:#b9b9c6;font-size:.8rem;max-width:80ch;margin-top:14px;text-align:center;cursor:auto}
#lb .cap b{color:#ececef}
</style></head><body>
<h1>Generations</h1>
<p class="sub">__COUNT__ pieces · newest first · made with /generate</p>
<div class="wall">__TILES__</div>
<div id="lb"></div>
<script>
const lb=document.getElementById('lb');
document.querySelectorAll('.tile').forEach(t=>{
  const v=t.querySelector('video');
  if(v){t.addEventListener('mouseenter',()=>{v.muted=true;v.play()});
        t.addEventListener('mouseleave',()=>{v.pause()});}
  t.addEventListener('click',()=>{
    const kind=t.dataset.kind,src=t.dataset.src,cap=t.dataset.cap;
    lb.innerHTML=(kind==='video'
      ?`<video src="${src}" controls autoplay loop></video>`
      :`<img src="${src}">`)
      +(cap?`<div class="cap" onclick="event.stopPropagation()">${cap}</div>`:'');
    lb.classList.add('on');});
});
lb.addEventListener('click',()=>{lb.classList.remove('on');lb.innerHTML='';});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){lb.classList.remove('on');lb.innerHTML='';}});
</script></body></html>"""


def build(root, items):
    tiles = []
    for it in items:
        src = html.escape(it["file"])
        m = it["meta"]
        cap_bits = []
        if m.get("prompt"):
            cap_bits.append(html.escape(m["prompt"][:280]))
        tag = " · ".join(x for x in (
            m.get("model"), (m.get("created") or "")[:10],
            f"${float(m.get('est_cost_usd') or 0):.2f}" if m.get("est_cost_usd") is not None else None) if x)
        if tag:
            cap_bits.append(f"<b>{html.escape(tag)}</b>")
        cap = html.escape("<br>".join(cap_bits), quote=True) if cap_bits else ""
        media = (f'<video src="{src}" muted loop playsinline preload="metadata"></video>'
                 if it["kind"] == "video" else f'<img src="{src}" loading="lazy">')
        tiles.append(f'<figure class="tile" data-kind="{it["kind"]}" data-src="{src}" data-cap="{cap}">{media}</figure>')
    page = PAGE.replace("__COUNT__", str(len(items))).replace("__TILES__", "\n".join(tiles))
    out = os.path.join(root, "index.html")
    with open(out, "w") as f:
        f.write(page)
    print(f"gallery wall: {out} ({len(items)} pieces)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default="generations", help="the flat generations folder")
    p.add_argument("--stats", action="store_true")
    args = p.parse_args()

    if not os.path.isdir(args.root):
        print(f"No '{args.root}' folder yet — nothing generated.")
        return
    items = scan(args.root)
    cap = load_cap(args.root)
    if args.stats:
        stats(items, cap) if items else print("No generations yet.")
    else:
        build(args.root, items) if items else print("No generations yet — nothing to build.")


if __name__ == "__main__":
    main()
