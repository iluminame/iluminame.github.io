#!/usr/bin/env python3
"""Generate images via Google AI Studio, Kie.ai, fal.ai, or WaveSpeed (stdlib only).

Implements the /generate pipeline: call the API per the model recipe, save
every file FLAT into the generations folder as {project}_{description}_{timestamp}.{ext},
and write a sidecar log (same basename + .json) next to each file.

Examples:
  python3 generate_image.py --check-keys
  python3 generate_image.py --provider google --model gemini-3.1-flash-lite-image \
      --prompt "..." --aspect 4:5 --project acme --desc hero-draft --cost 0.02
  python3 generate_image.py --provider fal --model openai/gpt-image-2 \
      --prompt "..." --project acme --desc poster --cost 0.05 --dry-run
  python3 generate_image.py --provider kie --model google/nano-banana-pro \
      --prompt "..." --ref generations/refs/logo.png --cost 0.05
"""
import argparse
import base64
import datetime as dt
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

KEYS = {
    "google": "GEMINI_API_KEY",
    "kie": "KIE_API_KEY",
    "fal": "FAL_KEY",
    "wavespeed": "WAVESPEED_API_KEY",
}

# Values that mean "the user hasn't pasted a real key yet"
PLACEHOLDERS = ("pega_tu_clave", "tu_clave", "your_key", "your_api_key", "xxx")


def load_env(start=None):
    """Load KEY=VALUE lines from .env (or env.txt) in the cwd or a parent.

    Keys live in a file rather than the shell so the workflow survives new
    terminal windows; real environment variables always win over the file.
    Returns (path_loaded_or_None, [keys_set]).
    """
    d = os.path.abspath(start or os.getcwd())
    for _ in range(4):
        for name in (".env", "env.txt"):
            path = os.path.join(d, name)
            if not os.path.isfile(path):
                continue
            loaded = []
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if not k or not v or os.environ.get(k):
                        continue
                    if any(ph in v.lower() for ph in PLACEHOLDERS):
                        continue  # still the template value
                    os.environ[k] = v
                    loaded.append(k)
            return path, loaded
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None, []

FAL_SIZES = {
    "1:1": "square_hd", "4:3": "landscape_4_3", "3:4": "portrait_4_3",
    "16:9": "landscape_16_9", "9:16": "portrait_16_9", "4:5": "portrait_4_3",
}


def http_json(url, payload=None, headers=None, timeout=180):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers or {})
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:2000]
        sys.exit(f"HTTP {e.code} from {url.split('?')[0]}\n{body}")


def b64_file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def to_data_uri(path):
    mime = mimetypes.guess_type(path)[0] or "image/png"
    return f"data:{mime};base64," + b64_file(path)


def slugify(text, maxlen=40):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:maxlen].rstrip("-") or "gen"


def out_basename(out_dir, project, desc):
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, f"{project}_{desc}_{int(time.time())}")


def write_sidecar(media_path, args, refs):
    sidecar = os.path.splitext(media_path)[0] + ".json"
    with open(sidecar, "w") as f:
        json.dump({
            "model": args.model,
            "provider": args.provider,
            "type": "image",
            "prompt": args.prompt,
            "refs": refs,
            "params": {"aspect": args.aspect or None, "size": args.resolution or None},
            "est_cost_usd": round(args.cost, 4),
            "created": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        }, f, indent=2, ensure_ascii=False)


def download(url, path_base, index):
    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1] or ".png"
    path = f"{path_base}-{index}{ext}" if index else f"{path_base}{ext}"
    with urllib.request.urlopen(url, timeout=300) as r, open(path, "wb") as f:
        f.write(r.read())
    return path


# ---------- providers ----------

def run_google(args, key, refs_local):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{args.model}:generateContent?key={urllib.parse.quote(key)}")
    parts = [{"text": args.prompt}]
    for p in refs_local:
        parts.append({"inline_data": {
            "mime_type": mimetypes.guess_type(p)[0] or "image/png",
            "data": b64_file(p)}})
    payload = {"contents": [{"parts": parts}]}
    if args.aspect:
        payload["generationConfig"] = {"imageConfig": {"aspectRatio": args.aspect}}
    if args.dry_run:
        return url.split("?")[0] + "?key=…", payload, None
    resp = http_json(url, payload)
    paths = []
    base = out_basename(args.out, args.project, args.desc)
    n = 0
    for cand in resp.get("candidates", []):
        for part in (cand.get("content") or {}).get("parts", []):
            blob = part.get("inlineData") or part.get("inline_data")
            if not blob:
                continue
            n += 1
            ext = mimetypes.guess_extension(blob.get("mimeType", "image/png")) or ".png"
            path = f"{base}-{n}{ext}" if n > 1 else f"{base}{ext}"
            with open(path, "wb") as f:
                f.write(base64.b64decode(blob["data"]))
            paths.append(path)
    if not paths:
        sys.exit(f"No image in Google reply (safety block?): {json.dumps(resp)[:800]}")
    return None, None, paths


def run_kie(args, key, ref_uris):
    inp = {"prompt": args.prompt}
    if args.aspect:
        inp["aspect_ratio"] = args.aspect
    if args.resolution:
        inp["resolution"] = args.resolution
    if ref_uris:
        inp["image_urls"] = ref_uris
    if args.input_json:
        inp.update(json.loads(args.input_json))
    url, payload = "https://api.kie.ai/api/v1/jobs/createTask", {"model": args.model, "input": inp}
    if args.dry_run:
        return url, payload, None
    headers = {"Authorization": f"Bearer {key}"}
    resp = http_json(url, payload, headers)
    if resp.get("code") != 200:
        sys.exit(f"Kie.ai error: {resp.get('msg') or resp}")
    poll = ("https://api.kie.ai/api/v1/jobs/recordInfo?taskId="
            + urllib.parse.quote(resp["data"]["taskId"]))
    while True:
        d = http_json(poll, headers=headers).get("data") or {}
        if d.get("state") == "success":
            urls = json.loads(d.get("resultJson") or "{}").get("resultUrls") or []
            break
        if d.get("state") == "fail":
            sys.exit(f"Kie.ai job failed: {d.get('failMsg')}")
        print(f"  … {d.get('state')}", flush=True)
        time.sleep(5)
    base = out_basename(args.out, args.project, args.desc)
    return None, None, [download(u, base, i if len(urls) > 1 else 0)
                        for i, u in enumerate(urls, 1)]


def run_fal(args, key, ref_uris):
    inp = {"prompt": args.prompt, "num_images": args.count}
    if args.aspect:
        inp["image_size"] = FAL_SIZES.get(args.aspect, args.aspect)
    if ref_uris:
        inp["image_url" if len(ref_uris) == 1 else "image_urls"] = (
            ref_uris[0] if len(ref_uris) == 1 else ref_uris)
    if args.input_json:
        inp.update(json.loads(args.input_json))
    url = f"https://queue.fal.run/{args.model}"
    if args.dry_run:
        return url, inp, None
    headers = {"Authorization": f"Key {key}"}
    resp = http_json(url, inp, headers)
    while True:
        s = http_json(resp["status_url"], headers=headers)
        if s.get("status") == "COMPLETED":
            r = http_json(resp["response_url"], headers=headers)
            imgs = r.get("images") or ([r["image"]] if r.get("image") else [])
            urls = [i["url"] if isinstance(i, dict) else i for i in imgs]
            break
        print(f"  … {s.get('status')}", flush=True)
        time.sleep(4)
    base = out_basename(args.out, args.project, args.desc)
    return None, None, [download(u, base, i if len(urls) > 1 else 0)
                        for i, u in enumerate(urls, 1)]


def run_wavespeed(args, key, ref_uris):
    inp = {"prompt": args.prompt}
    if ref_uris:
        inp["images"] = ref_uris
    if args.input_json:
        inp.update(json.loads(args.input_json))
    url = f"https://api.wavespeed.ai/api/v3/{args.model}"
    if args.dry_run:
        return url, inp, None
    headers = {"Authorization": f"Bearer {key}"}
    resp = http_json(url, inp, headers)
    poll = f"https://api.wavespeed.ai/api/v3/predictions/{resp['data']['id']}/result"
    while True:
        d = http_json(poll, headers=headers).get("data") or {}
        if d.get("status") == "completed":
            urls = d.get("outputs") or []
            break
        if d.get("status") == "failed":
            sys.exit(f"WaveSpeed job failed: {d.get('error')}")
        print(f"  … {d.get('status')}", flush=True)
        time.sleep(4)
    base = out_basename(args.out, args.project, args.desc)
    return None, None, [download(u, base, i if len(urls) > 1 else 0)
                        for i, u in enumerate(urls, 1)]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--provider", choices=list(KEYS))
    p.add_argument("--model", help="exact model ID from the recipe file in models/")
    p.add_argument("--prompt")
    p.add_argument("--aspect", default="", help="e.g. 1:1, 4:5, 16:9")
    p.add_argument("--resolution", default="", help="e.g. 1K, 2K (model permitting)")
    p.add_argument("--count", type=int, default=1, help="images per call (fal batches natively)")
    p.add_argument("--ref", action="append", default=[],
                   help="reference image: local path (generations/refs/...) or URL; repeatable")
    p.add_argument("--input-json", help="extra provider-specific input fields as JSON")
    p.add_argument("--cost", type=float, default=0.0, help="estimated USD for this run (goes in the sidecar log)")
    p.add_argument("--project", default="gen", help="project tag for the filename")
    p.add_argument("--desc", default="", help="short description for the filename (defaults to prompt slug)")
    p.add_argument("--out", default="generations", help="flat output folder")
    p.add_argument("--dry-run", action="store_true", help="print the request, spend nothing")
    p.add_argument("--check-keys", action="store_true")
    args = p.parse_args()

    env_path, _ = load_env()
    if args.check_keys:
        print(f"keys file: {env_path or 'none found (looked for .env / env.txt here and in parent folders)'}\n")
        for prov, var in KEYS.items():
            print(f"{prov:10s} {var:20s} {'SET' if os.environ.get(var) else 'missing'}")
        return
    for req in ("provider", "model", "prompt"):
        if not getattr(args, req):
            p.error(f"--{req} is required (or use --check-keys)")
    args.desc = slugify(args.desc or args.prompt)
    args.project = slugify(args.project)

    key = os.environ.get(KEYS[args.provider], "")
    if not key and not args.dry_run:
        where = f"in {env_path}" if env_path else "in a .env file next to your generations folder"
        sys.exit(f"Missing {KEYS[args.provider]} for provider '{args.provider}' — set it {where}. "
                 "Run with --check-keys to see what was found.")

    refs_local = [r for r in args.ref if os.path.exists(r)]
    ref_uris = [to_data_uri(r) if os.path.exists(r) else r for r in args.ref]

    runner = {"google": run_google, "kie": run_kie, "fal": run_fal,
              "wavespeed": run_wavespeed}[args.provider]
    ref_arg = refs_local if args.provider == "google" else ref_uris
    url, payload, paths = runner(args, key, ref_arg)

    if args.dry_run:
        print(f"POST {url}")
        print(json.dumps(payload, indent=2)[:3000])
        print(f"estimated cost: ~${args.cost:.2f}")
        return

    for path in paths:
        write_sidecar(path, args, args.ref)
        print(f"saved: {path}  (+ sidecar .json)")
    print(f"\ndone: {len(paths)} file(s), estimated ~${args.cost:.2f}")


if __name__ == "__main__":
    main()
