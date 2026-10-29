#!/usr/bin/env python3
# language: Python 3.10+
# target: Windows / Linux / macOS
# Extracts the full Free Fire item database + every icon PNG from ff-item.netlify.app.
# Source data:  https://ff-item.netlify.app/data.msgpack.gz
# Icon repo:    https://github.com/ShahGCreator/icon (PNG/{itemID}.png)

import argparse
import csv
import gzip
import json
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

# The CDN hangs on broken IPv6 routes from some networks; pin DNS to IPv4.
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)


socket.getaddrinfo = _ipv4_getaddrinfo

# The upstream icon repo stores WebP bytes inside files named *.png.
IMAGE_SIGNATURES = (b"\x89PNG\r\n\x1a\n", b"RIFF", b"\xff\xd8\xff", b"GIF8")
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
IMG_DIR = ROOT / "images"
SRC_DIR = ROOT / "source"
TYPE_DIR = DATA_DIR / "items_by_type"
IDS_TYPE_DIR = DATA_DIR / "ids_by_type"

DATA_URL = "https://ff-item.netlify.app/data.msgpack.gz"
TREE_API = "https://api.github.com/repos/ShahGCreator/icon/git/trees/main?recursive=1"
RAW_BASE = "https://raw.githubusercontent.com/ShahGCreator/icon/main/PNG/"
JSD_BASE = "https://cdn.jsdelivr.net/gh/ShahGCreator/icon@main/PNG/"
UA = "clothers-extractor/1.0 (+https://github.com/Duenss/clothers)"

RARE_NAMES = {
    "WHITE": "Common",
    "GREEN": "Uncommon",
    "BLUE": "Rare",
    "PURPLE": "Epic",
    "PURPLE_PLUS": "Epic++",
    "ORANGE": "Mythic",
    "ORANGE_PLUS": "Mythic++",
    "RED": "Artifact",
    "NONE": "None",
}


def fetch(url, retries=4, timeout=40):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001 - network retry loop
            last = exc
            time.sleep(0.6 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last}")


def github_token():
    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True,
            text=True,
            timeout=20,
        )
        for line in proc.stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception:  # noqa: BLE001 - optional token
        pass
    return None


def slug(text):
    out = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return out or "unknown"


def load_dataset():
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = SRC_DIR / "data.msgpack.gz"
    if raw_path.exists() and raw_path.stat().st_size > 0:
        blob = raw_path.read_bytes()
        print(f"[data] cached {raw_path.name} ({len(blob):,} bytes)")
    else:
        blob = fetch(DATA_URL)
        raw_path.write_bytes(blob)
        print(f"[data] downloaded {raw_path.name} ({len(blob):,} bytes)")

    import msgpack  # imported here so --help works without the dependency

    return msgpack.unpackb(gzip.decompress(blob), raw=False)


def icon_ids_from_github(items):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": UA}
    token = github_token()
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        req = urllib.request.Request(TREE_API, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            tree = json.loads(resp.read().decode("utf-8"))
        ids = {
            int(m.group(1))
            for entry in tree.get("tree", [])
            if (m := re.fullmatch(r"PNG/(\d+)\.png", entry["path"]))
        }
        if ids:
            print(f"[icons] GitHub tree lists {len(ids):,} PNGs")
            return sorted(ids)
    except Exception as exc:  # noqa: BLE001 - fall back to dataset ids
        print(f"[icons] tree lookup failed ({exc}); falling back to item IDs")
    return sorted({int(item["itemID"]) for item in items if item.get("itemID")})


def download_icon(item_id):
    dst = IMG_DIR / f"{item_id}.png"
    if dst.exists() and dst.stat().st_size > 64:
        return "skip"
    for base in (RAW_BASE, JSD_BASE):
        for attempt in range(3):
            try:
                req = urllib.request.Request(base + f"{item_id}.png", headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    blob = resp.read()
                if any(blob.startswith(sig) for sig in IMAGE_SIGNATURES):
                    dst.write_bytes(blob)
                    return "ok"
            except Exception:  # noqa: BLE001 - try next mirror / retry
                time.sleep(0.3 * (attempt + 1))
    return "fail"


def normalize(items, icon_ids):
    available = set(icon_ids)
    rows = []
    for item in items:
        item_id = item.get("itemID")
        if not item_id:
            continue
        has_image = int(item_id) in available
        rows.append(
            {
                "itemID": int(item_id),
                "name": (item.get("name") or "").strip() or "Unknown",
                "icon": (item.get("icon") or "").strip(),
                "type": (item.get("type") or "").strip() or "Unknown",
                "rare": (item.get("Rare") or "NONE").strip().upper(),
                "tag": (item.get("tag") or "").strip().upper(),
                "description": (item.get("description") or "").strip(),
                "has_image": has_image,
                "image": f"images/{item_id}.png" if has_image else None,
                "image_url": RAW_BASE + f"{item_id}.png" if has_image else None,
            }
        )
    rows.sort(key=lambda r: r["itemID"])
    return rows


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def write_outputs(rows, icon_ids, args):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TYPE_DIR.mkdir(parents=True, exist_ok=True)
    IDS_TYPE_DIR.mkdir(parents=True, exist_ok=True)

    for r in rows:
        r["rare_name"] = RARE_NAMES.get(r["rare"], r["rare"])

    write_json(DATA_DIR / "items.json", rows)

    csv_path = DATA_DIR / "items.csv"
    fields = [
        "itemID", "name", "type", "rare", "rare_name", "tag",
        "icon", "has_image", "image", "image_url", "description",
    ]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r[k] for k in fields})

    groups = {}
    for r in rows:
        groups.setdefault(r["type"], []).append(r)
    for type_name, items in sorted(groups.items()):
        s = slug(type_name)
        write_json(TYPE_DIR / f"{s}.json", items)
        with (IDS_TYPE_DIR / f"{s}.txt").open("w", encoding="utf-8", newline="\n") as fh:
            for r in sorted(items, key=lambda x: x["itemID"]):
                fh.write(f"{r['itemID']}\n")

    with (DATA_DIR / "ids.txt").open("w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(f"{r['itemID']}\n")

    by_type = Counter(r["type"] for r in rows)
    by_rare = Counter(r["rare"] for r in rows)
    by_tag = Counter(r["tag"] or "none" for r in rows)
    with_image = sum(1 for r in rows if r["has_image"])

    summary = {
        "source": "https://ff-item.netlify.app/?o=ob55",
        "data_url": DATA_URL,
        "icon_repo": "https://github.com/ShahGCreator/icon",
        "extracted_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "items": len(rows),
        "items_with_image": with_image,
        "items_without_image": len(rows) - with_image,
        "unique_item_ids": len({r["itemID"] for r in rows}),
        "image_files_listed": len(icon_ids),
        "images_downloaded": sum(1 for _ in IMG_DIR.glob("*.png")) if IMG_DIR.exists() else 0,
        "by_type": dict(by_type.most_common()),
        "by_rarity": dict(by_rare.most_common()),
        "by_tag": dict(sorted(by_tag.items())),
    }
    write_json(DATA_DIR / "summary.json", summary)

    missing = [r["itemID"] for r in rows if not r["has_image"]]
    write_json(DATA_DIR / "missing_images.json", missing)

    print(f"[out] items.json / items.csv / {len(groups)} type groups written")
    print(f"[out] {with_image:,} items with image, {len(missing):,} without")
    return summary


README = """# clothers

Base de datos completa de items de **Free Fire** extraida de
[ff-item.netlify.app](https://ff-item.netlify.app/?o=ob55), con IDs, nombres,
tipos, rarezas, tags, descripciones e iconos PNG.

## Numeros

| Dato | Valor |
|---|---|
| Items | **{items:,}** |
| IDs unicos | {unique_item_ids:,} |
| Con icono | {items_with_image:,} |
| Sin icono | {items_without_image:,} |
| PNGs en `images/` | **{images_downloaded:,}** |
| Tipos distintos | {type_count} |
| Tags (temporadas) | {tag_count} |

## Estructura

```
data/
  items.json            dataset completo (array, un objeto por item)
  items.csv             mismo dataset en CSV (UTF-8 con BOM, abre en Excel)
  summary.json          conteos por tipo / rareza / tag
  ids.txt               todos los item IDs, uno por linea
  missing_images.json   IDs sin PNG disponible en el CDN
  items_by_type/        un JSON por tipo (bundles, top, emote, ...)
  ids_by_type/          un TXT de IDs por tipo
images/
  {{itemID}}.png         icono de cada item (nombre = item ID)
source/
  data.msgpack.gz       payload original sin tocar
scripts/
  scrape.py             extractor reproducible
gallery.html            visor local con busqueda y filtros
```

Los archivos de `images/` llevan extension `.png` igual que en el CDN original; muchos
contienen bytes WebP. Navegadores, VS Code y cualquier visor los abren sin problema.

## Campos de cada item

| Campo | Ejemplo | Nota |
|---|---|---|
| `itemID` | `909046008` | ID interno del item |
| `name` | `No Sweat` | nombre en el juego |
| `type` | `Emote` | categoria |
| `rare` | `BLUE` | codigo de rareza |
| `rare_name` | `Rare` | rareza legible |
| `tag` | `OB46` | temporada / coleccion |
| `icon` | `Icon_Emote_Meme6` | nombre interno del icono |
| `has_image` | `true` | existe PNG en `images/` |
| `image` | `images/909046008.png` | ruta local |
| `image_url` | `https://raw.githubusercontent.com/...` | origen |
| `description` | `...` | texto del item (si existe) |

## Uso rapido

```python
import json

items = json.load(open("data/items.json", encoding="utf-8"))
emotes = [i for i in items if i["type"] == "Emote"]
print(len(emotes), emotes[0]["itemID"], emotes[0]["image"])
```

Abre `gallery.html` en el navegador para buscar por nombre, ID, tipo, rareza o tag.

## Rarezas

`WHITE` Common · `GREEN` Uncommon · `BLUE` Rare · `PURPLE` Epic ·
`PURPLE_PLUS` Epic++ · `ORANGE` Mythic · `ORANGE_PLUS` Mythic++ ·
`RED` Artifact

## Regenerar

```bash
pip install msgpack
python scripts/scrape.py
```

El script descarga `data.msgpack.gz`, lista los PNG del repo de iconos,
descarga lo que falte (reanudable, con reintentos) y reescribe `data/`.

## Creditos

Datos e iconos: [ShahGCreator](https://github.com/ShahGCreator/icon) ·
Free Fire es propiedad de Garena. Este repo es un archivo de referencia.
"""


def write_readme(summary):
    text = README.format(
        items=summary["items"],
        unique_item_ids=summary["unique_item_ids"],
        items_with_image=summary["items_with_image"],
        items_without_image=summary["items_without_image"],
        images_downloaded=summary["images_downloaded"],
        type_count=len(summary["by_type"]),
        tag_count=len([k for k in summary["by_tag"] if k != "none"]),
    )
    (ROOT / "README.md").write_text(text, encoding="utf-8")


GALLERY = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>clothers — Free Fire item archive</title>
<style>
  :root { --bg:#0b0f17; --panel:#141b27; --line:#243044; --text:#e6edf7; --dim:#8b9bb4; --accent:#ffba00; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font:14px/1.5 system-ui,Segoe UI,Roboto,sans-serif; }
  header { position:sticky; top:0; z-index:5; background:rgba(11,15,23,.94); backdrop-filter:blur(8px);
           border-bottom:1px solid var(--line); padding:14px clamp(12px,3vw,32px); }
  h1 { margin:0 0 10px; font-size:18px; letter-spacing:.04em; }
  h1 span { color:var(--accent); }
  .controls { display:flex; flex-wrap:wrap; gap:8px; }
  input, select { background:var(--panel); color:var(--text); border:1px solid var(--line); border-radius:8px;
                  padding:8px 10px; font:inherit; outline:none; }
  input { flex:1 1 260px; }
  input:focus, select:focus { border-color:var(--accent); }
  #count { color:var(--dim); align-self:center; margin-left:auto; white-space:nowrap; }
  main { padding:18px clamp(12px,3vw,32px) 60px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(132px,1fr)); gap:12px; }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:10px; cursor:pointer;
          transition:border-color .15s, transform .15s; min-width:0; }
  .card:hover { border-color:var(--accent); transform:translateY(-2px); }
  .thumb { aspect-ratio:1; display:grid; place-items:center; background:#0e1420; border-radius:8px; overflow:hidden; }
  .thumb img { width:100%; height:100%; object-fit:contain; }
  .thumb .noimg { color:#3d4b60; font-size:11px; }
  .name { margin-top:8px; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .meta { display:flex; justify-content:space-between; gap:6px; color:var(--dim); font-size:11px; margin-top:3px; }
  .meta b { color:var(--accent); font-weight:600; }
  .more { display:block; margin:26px auto 0; background:var(--panel); color:var(--text); border:1px solid var(--line);
          border-radius:9px; padding:11px 26px; font:inherit; cursor:pointer; }
  .more:hover { border-color:var(--accent); }
  dialog { background:var(--panel); color:var(--text); border:1px solid var(--line); border-radius:14px;
           padding:18px; width:min(460px,92vw); }
  dialog::backdrop { background:rgba(0,0,0,.7); }
  .modal-top { display:flex; gap:14px; align-items:flex-start; }
  .modal-top img { width:128px; height:128px; object-fit:contain; background:#0e1420; border-radius:10px; }
  .modal-top h2 { margin:0 0 6px; font-size:16px; overflow-wrap:anywhere; }
  .idline { display:flex; align-items:center; gap:8px; margin:4px 0; }
  .idline code { background:#0e1420; padding:3px 7px; border-radius:6px; }
  .copy { background:var(--accent); color:#111; border:0; border-radius:6px; padding:5px 9px; cursor:pointer; font-weight:600; }
  .desc { margin-top:12px; color:var(--dim); max-height:150px; overflow:auto; }
  .close { margin-top:16px; width:100%; background:#1d2737; color:var(--text); border:1px solid var(--line);
           border-radius:8px; padding:9px; cursor:pointer; font:inherit; }
</style>
</head>
<body>
<header>
  <h1>clothers <span>·</span> Free Fire item archive</h1>
  <div class="controls">
    <input id="q" type="search" placeholder="Buscar nombre, ID, icono o descripcion...">
    <select id="type"><option value="">Todos los tipos</option></select>
    <select id="rare"><option value="">Todas las rarezas</option></select>
    <select id="tag"><option value="">Todos los tags</option></select>
    <span id="count"></span>
  </div>
</header>
<main>
  <div class="grid" id="grid"></div>
  <button class="more" id="more" hidden>Cargar mas</button>
</main>
<dialog id="modal">
  <div class="modal-top">
    <img id="mImg" alt="">
    <div>
      <h2 id="mName"></h2>
      <div class="idline">Item ID <code id="mId"></code><button class="copy" id="mCopy">Copiar</button></div>
      <div class="meta"><span id="mType"></span><b id="mRare"></b></div>
      <div class="meta"><span id="mTag"></span><span id="mIcon"></span></div>
    </div>
  </div>
  <p class="desc" id="mDesc"></p>
  <button class="close" id="mClose">Cerrar</button>
</dialog>
<script>
const PAGE = 120;
let items = [], view = [], shown = 0;
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

fetch('data/items.json').then(r => r.json()).then(data => {
  items = data;
  const uniq = (key) => [...new Set(items.map(i => i[key]).filter(Boolean))].sort();
  for (const t of uniq('type')) $('type').add(new Option(t, t));
  for (const r of uniq('rare')) $('rare').add(new Option(r, r));
  for (const t of uniq('tag')) $('tag').add(new Option(t, t));
  apply();
});

function apply() {
  const q = $('q').value.trim().toLowerCase();
  const t = $('type').value, r = $('rare').value, g = $('tag').value;
  view = items.filter(i =>
    (!t || i.type === t) && (!r || i.rare === r) && (!g || i.tag === g) &&
    (!q || (i.name + ' ' + i.itemID + ' ' + i.icon + ' ' + i.description).toLowerCase().includes(q))
  );
  $('count').textContent = view.length.toLocaleString('en-US') + ' items';
  $('grid').innerHTML = ''; shown = 0; $('more').hidden = true; render();
}

function render() {
  const batch = view.slice(shown, shown + PAGE);
  const frag = document.createDocumentFragment();
  for (const i of batch) {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML =
      '<div class="thumb">' + (i.image
        ? '<img loading="lazy" src="' + i.image + '" alt="">'
        : '<span class="noimg">sin icono</span>') + '</div>' +
      '<div class="name" title="' + esc(i.name) + '">' + esc(i.name) + '</div>' +
      '<div class="meta"><span>' + esc(i.type) + '</span><b>' + esc(i.itemID) + '</b></div>';
    card.onclick = () => openItem(i);
    frag.appendChild(card);
  }
  $('grid').appendChild(frag);
  shown += batch.length;
  $('more').hidden = shown >= view.length;
}

function openItem(i) {
  $('mName').textContent = i.name;
  $('mId').textContent = i.itemID;
  $('mType').textContent = i.type;
  $('mRare').textContent = i.rare;
  $('mTag').textContent = i.tag || '';
  $('mIcon').textContent = i.icon;
  $('mDesc').textContent = i.description || 'Sin descripcion.';
  $('mImg').src = i.image || '';
  $('mImg').style.visibility = i.image ? 'visible' : 'hidden';
  $('modal').showModal();
}

$('q').addEventListener('input', apply);
for (const id of ['type', 'rare', 'tag']) $(id).addEventListener('change', apply);
$('more').addEventListener('click', render);
$('mClose').addEventListener('click', () => $('modal').close());
$('mCopy').addEventListener('click', async () => {
  await navigator.clipboard.writeText($('mId').textContent);
  $('mCopy').textContent = 'Copiado';
  setTimeout(() => $('mCopy').textContent = 'Copiar', 1200);
});
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Extract Free Fire items and icons")
    parser.add_argument("--skip-images", action="store_true", help="only rebuild JSON/CSV")
    parser.add_argument("--workers", type=int, default=32, help="parallel downloads (default 32)")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    raw_items = load_dataset()
    print(f"[data] {len(raw_items):,} raw records")
    icon_ids = icon_ids_from_github(raw_items)

    rows = normalize(raw_items, icon_ids)

    if not args.skip_images:
        pending = [i for i in icon_ids if not (IMG_DIR / f"{i}.png").exists()]
        print(f"[icons] {len(pending):,} pending downloads, {len(icon_ids) - len(pending):,} cached")
        done = {"ok": 0, "skip": 0, "fail": 0}
        started = time.time()
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(download_icon, i): i for i in pending}
            for n, fut in enumerate(as_completed(futures), 1):
                done[fut.result()] += 1
                if n % 500 == 0 or n == len(futures):
                    rate = n / max(time.time() - started, 0.001)
                    print(f"[icons] {n:,}/{len(futures):,} ({rate:.0f}/s) ok={done['ok']:,} fail={done['fail']:,}")
        if done["fail"]:
            print(f"[icons] {done['fail']:,} failed after retries")

    summary = write_outputs(rows, icon_ids, args)
    write_readme(summary)
    (ROOT / "gallery.html").write_text(GALLERY, encoding="utf-8")
    print("[done] repo payload ready")


if __name__ == "__main__":
    sys.exit(main())
