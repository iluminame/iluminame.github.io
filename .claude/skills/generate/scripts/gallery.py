#!/usr/bin/env python3
"""Local gallery + cost tracker for /generate outputs (stdlib only).

Reads <root>/log.jsonl (written by the generate_* scripts), then:
  default      → rebuilds <root>/index.html (browsable gallery)
  --stats      → prints spend by month and provider vs. the budget cap

Budget cap lives in <root>/budget.json: {"monthly_cap_usd": 20}
(created automatically on first run).
"""
import argparse
import html
import json
import os
import sys
from collections import defaultdict

DEFAULT_CAP = 20.0


def load_log(root):
    path = os.path.join(root, "log.jsonl")
    entries = []
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return entries


def load_cap(root):
    path = os.path.join(root, "budget.json")
    if not os.path.exists(path):
        os.makedirs(root, exist_ok=True)
        with open(path, "w") as f:
            json.dump({"monthly_cap_usd": DEFAULT_CAP}, f, indent=2)
        return DEFAULT_CAP
    try:
        return float(json.load(open(path)).get("monthly_cap_usd", DEFAULT_CAP))
    except (json.JSONDecodeError, ValueError):
        return DEFAULT_CAP


def stats(entries, cap):
    by_month = defaultdict(float)
    by_provider = defaultdict(float)
    for e in entries:
        cost = float(e.get("est_cost_usd") or 0)
        by_month[(e.get("ts") or "????-??")[:7]] += cost
        by_provider[e.get("provider", "?")] += cost
    print(f"{len(entries)} generations · total ~${sum(by_provider.values()):.2f}\n")
    print("By month (cap ${:.2f}/mo):".format(cap))
    for m in sorted(by_month):
        spent = by_month[m]
        pct = spent / cap * 100 if cap else 0
        flag = "  ⚠ over 80% of cap" if pct >= 80 else ""
        print(f"  {m}  ${spent:6.2f}  ({pct:.0f}% of cap){flag}")
    print("By provider:")
    for prov, spent in sorted(by_provider.items(), key=lambda kv: -kv[1]):
        print(f"  {prov:10s} ${spent:6.2f}")


CSS = """
:root{color-scheme:dark;--bg:#101014;--card:#1a1a21;--text:#e8e8ee;--dim:#9a9aa8;--acc:#7bd88f}
*{box-sizing:border-box;margin:0}body{background:var(--bg);color:var(--text);
font:15px/1.5 system-ui,sans-serif;padding:2rem}
h1{font-size:1.4rem;margin-bottom:.3rem}.sub{color:var(--dim);margin-bottom:1.5rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1rem}
.card{background:var(--card);border-radius:12px;overflow:hidden}
.card img,.card video{width:100%;aspect-ratio:4/3;object-fit:cover;display:block;background:#000}
.meta{padding:.7rem .9rem}.prompt{font-size:.85rem;max-height:4.2em;overflow:auto}
.tags{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.5rem;font-size:.72rem;color:var(--dim)}
.tags .cost{color:var(--acc)}
"""


def rel_to_root(f, root):
    """Resolve a logged file path to a path relative to the gallery root."""
    rel = os.path.relpath(os.path.abspath(f), os.path.abspath(root))
    for candidate in (rel, f):
        if os.path.exists(os.path.join(root, candidate)):
            return candidate
    return None


def build_html(root, entries):
    cards = []
    for e in reversed(entries):  # newest first
        for f in e.get("files", []):
            rel = rel_to_root(f, root)
            if rel is None:
                continue  # file moved/deleted — skip silently
            media = (f'<video src="{html.escape(rel)}" controls muted loop></video>'
                     if e.get("type") == "video"
                     else f'<img src="{html.escape(rel)}" loading="lazy">')
            tags = [e.get("model", ""), e.get("style") or None,
                    (e.get("ts") or "")[:10],
                    f'<span class="cost">${float(e.get("est_cost_usd") or 0):.2f}</span>']
            tags_html = "".join(f"<span>{t}</span>" for t in tags if t)
            cards.append(
                f'<div class="card">{media}<div class="meta">'
                f'<div class="prompt">{html.escape(e.get("prompt", ""))}</div>'
                f'<div class="tags">{tags_html}</div></div></div>')
    total = sum(float(e.get("est_cost_usd") or 0) for e in entries)
    page = (f"<!doctype html><meta charset='utf-8'><title>Gallery — /generate</title>"
            f"<style>{CSS}</style><h1>Gallery</h1>"
            f"<p class='sub'>{len(cards)} assets · ~${total:.2f} total estimated spend · "
            f"generated locally with the /generate skill</p>"
            f"<div class='grid'>{''.join(cards)}</div>")
    out = os.path.join(root, "index.html")
    with open(out, "w") as f:
        f.write(page)
    print(f"gallery: {out} ({len(cards)} assets)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default="generations", help="gallery root folder")
    p.add_argument("--stats", action="store_true", help="print spend summary instead of building HTML")
    args = p.parse_args()

    entries = load_log(args.root)
    cap = load_cap(args.root)
    if args.stats:
        if not entries:
            print("No generations logged yet.")
            return
        stats(entries, cap)
    else:
        if not entries:
            print("No generations logged yet — nothing to build.")
            return
        build_html(args.root, entries)


if __name__ == "__main__":
    main()
