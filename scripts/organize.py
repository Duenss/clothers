#!/usr/bin/env python3
# language: Python 3.10+
# target: Windows / Linux / macOS
# Reorganiza el dataset extraido en carpetas por categoria (ROPA, EMOTES, ARMAS, ...),
# cada una con subcarpetas `imagenes/` y `TXT/`.
#
# Uso: python scripts/organize.py

import csv
import json
import os
import shutil
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
IMG_ROOT = ROOT / "images"

# tipo del juego -> carpeta en espanol
CATEGORY_BY_TYPE = {
    # ropa
    "Bundles": "ROPA",
    "Bundle Create": "ROPA",
    "Top": "ROPA",
    "Bottom": "ROPA",
    "Shoe": "ROPA",
    "Head": "ROPA",
    "Mask": "ROPA",
    "Facepaint": "ROPA",
    "Bag Skins": "ROPA",
    "Look Changer": "ROPA",
    # emotes y animaciones
    "Emote": "EMOTES",
    "Super Emote": "EMOTES",
    "Arrival Animation": "EMOTES",
    "Posture": "EMOTES",
    "Finishing Move": "EMOTES",
    "Final Shot": "EMOTES",
    # armas
    "Weapon Skins": "ARMAS",
    "Fist Skins": "ARMAS",
    "Grenade Skin": "ARMAS",
    "Gloo Walls": "ARMAS",
    "Weapon Crates": "ARMAS",
    # personajes
    "Characters": "PERSONAJES",
    "Skill Skins": "PERSONAJES",
    # mascotas
    "Pets": "MASCOTAS",
    "Pet Skin": "MASCOTAS",
    "Pet Skill": "MASCOTAS",
    "Pet Emote": "MASCOTAS",
    "Pyro Pet": "MASCOTAS",
    # vehiculos y paracaidas
    "Vehicle Skins": "VEHICULOS",
    "Skyboard": "VEHICULOS",
    "Skywings": "VEHICULOS",
    "Parachute": "VEHICULOS",
    # avatares, banners y cosmeticos de perfil
    "Avatars": "AVATARES",
    "Avatar Frame": "AVATARES",
    "Banners": "AVATARES",
    "Photo Frame": "AVATARES",
    "Photo Pose": "AVATARES",
    "Profile Pin": "AVATARES",
    "Battle Card": "AVATARES",
    "Titles": "AVATARES",
    "Sticker": "AVATARES",
    "Stickers": "AVATARES",
    # musica y voz
    "Music": "MUSICA",
    "Voice Packs": "MUSICA",
    # cajas, fichas y cupones
    "Loot Crates": "CAJAS",
    "Choice Crates": "CAJAS",
    "Loot Box": "CAJAS",
    "Vouchers": "CAJAS",
    "Exchange Tokens": "CAJAS",
}

CATEGORY_ORDER = [
    "ROPA", "EMOTES", "ARMAS", "PERSONAJES", "MASCOTAS",
    "VEHICULOS", "AVATARES", "MUSICA", "CAJAS", "OTROS",
]

CATEGORY_DESC = {
    "ROPA": "conjuntos, tops, bottoms, zapatos, cabeza, mascaras, facepaint, bolsos, look changer",
    "EMOTES": "emotes, super emotes, animaciones de llegada, posturas, remates",
    "ARMAS": "skins de armas, puños, granadas, gloo walls y cajas de armas",
    "PERSONAJES": "personajes y skins de habilidad",
    "MASCOTAS": "mascotas, skins, habilidades y emotes de mascota",
    "VEHICULOS": "skins de vehiculos, skyboards, skywings y paracaidas",
    "AVATARES": "avatares, marcos, banners, titulos, stickers y tarjetas",
    "MUSICA": "musica y paquetes de voz",
    "CAJAS": "loot crates, choice crates, loot box, vouchers y tokens",
    "OTROS": "items sin tipo, hyper books y elementos sin clasificar",
}


def category_for(item):
    return CATEGORY_BY_TYPE.get(item.get("type", ""), "OTROS")


def fmt_rare(item):
    code = item.get("rare") or "NONE"
    name = item.get("rare_name") or code
    return f"{code} ({name})" if name and name != code else code


def item_txt(item):
    lines = [
        f"ITEM ID: {item['itemID']}",
        f"ICON ID: {item.get('icon') or '(sin icon id)'}",
        f"NOMBRE: {item['name']}",
        f"TIPO: {item.get('type') or 'Unknown'}",
        f"RAREZA: {fmt_rare(item)}",
        f"TAG: {item.get('tag') or '(sin tag)'}",
        f"DESCRIPCION: {item.get('description') or '(sin descripcion)'}",
        f"IMAGEN: {item.get('image') or '(no disponible)'}",
    ]
    return "\n".join(lines) + "\n"


def move_image(item_id, categoria):
    src = IMG_ROOT / f"{item_id}.png"
    dst = ROOT / categoria / "imagenes" / f"{item_id}.png"
    if dst.exists() and dst.stat().st_size > 64:
        if src.exists():
            src.unlink()
        return True
    if src.exists() and src.stat().st_size > 64:
        os.replace(src, dst)
        return True
    return False


def main():
    items_path = DATA_DIR / "items.json"
    items = json.loads(items_path.read_text(encoding="utf-8"))
    print(f"[load] {len(items):,} items")

    for cat in CATEGORY_ORDER:
        (ROOT / cat / "imagenes").mkdir(parents=True, exist_ok=True)
        (ROOT / cat / "TXT").mkdir(parents=True, exist_ok=True)

    groups = defaultdict(list)
    moved = 0
    missing = []
    for item in items:
        cat = category_for(item)
        item["categoria"] = cat
        dst = ROOT / cat / "imagenes" / f"{item['itemID']}.png"
        has = move_image(item["itemID"], cat)
        if has:
            item["image"] = f"{cat}/imagenes/{item['itemID']}.png"
            item["has_image"] = True
            moved += 1
        else:
            item["image"] = None
            item["has_image"] = False
            missing.append(item["itemID"])
        groups[cat].append(item)

    print(f"[img] {moved:,} moved into category folders, {len(missing):,} without image")

    ts_lines = ["ITEM_ID\tICON_ID\tNOMBRE\tTIPO\tRAREZA\tTAG\tIMAGEN\tDESCRIPCION"]
    for cat in CATEGORY_ORDER:
        cat_items = sorted(groups.get(cat, []), key=lambda x: x["itemID"])
        txt_dir = ROOT / cat / "TXT"
        for item in cat_items:
            (txt_dir / f"{item['itemID']}.txt").write_text(item_txt(item), encoding="utf-8")
            ts_lines.append(
                "\t".join(
                    [
                        str(item["itemID"]),
                        item.get("icon") or "",
                        item["name"],
                        item.get("type") or "Unknown",
                        fmt_rare(item),
                        item.get("tag") or "",
                        item.get("image") or "",
                        (item.get("description") or "").replace("\t", " ").replace("\r", " ").replace("\n", " "),
                    ]
                )
            )
        with (txt_dir / "_TODOS.txt").open("w", encoding="utf-8-sig", newline="\n") as fh:
            fh.write("\n".join(ts_lines) + "\n")
        ts_lines = ["ITEM_ID\tICON_ID\tNOMBRE\tTIPO\tRAREZA\tTAG\tIMAGEN\tDESCRIPCION"]
        print(f"[txt] {cat}: {len(cat_items):,} items")

    # iconos del CDN que no aparecen en el dataset: se conservan aparte
    orphan = []
    if IMG_ROOT.exists():
        for p in sorted(IMG_ROOT.glob("*.png")):
            dst = ROOT / "OTROS" / "imagenes" / p.name
            if not dst.exists():
                os.replace(p, dst)
            orphan.append(p.stem)
        root_index = ROOT / "OTROS" / "TXT" / "_sin_metadata.txt"
        if orphan:
            root_index.write_text(
                "Estos iconos existen en el CDN pero no aparecen en data.msgpack.gz,\n"
                "por lo que no tienen nombre, tipo ni descripcion asociados.\n\n"
                + "\n".join(orphan)
                + "\n",
                encoding="utf-8",
            )
        print(f"[img] {len(orphan):,} orphan icons kept in OTROS/imagenes")

    # master dataset actualizado
    items.sort(key=lambda x: (CATEGORY_ORDER.index(x["categoria"]), x["itemID"]))
    items_path.write_text(json.dumps(items, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    fields = ["itemID", "name", "categoria", "type", "rare", "rare_name", "tag",
              "icon", "has_image", "image", "image_url", "description"]
    with (DATA_DIR / "items.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for item in items:
            writer.writerow({k: item.get(k, "") for k in fields})

    counts = Counter(x["categoria"] for x in items)
    images = Counter(x["categoria"] for x in items if x.get("has_image"))
    summary = {
        "fuente": "https://ff-item.netlify.app/?o=ob55",
        "data_url": "https://ff-item.netlify.app/data.msgpack.gz",
        "icon_repo": "https://github.com/ShahGCreator/icon",
        "extraido_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "items": len(items),
        "items_con_imagen": sum(images.values()),
        "items_sin_imagen": len(missing),
        "imagenes_en_disco": sum(1 for p in ROOT.glob("*/imagenes/*.png")),
        "categorias": {
            cat: {
                "items": counts.get(cat, 0),
                "con_imagen": images.get(cat, 0),
                "descripcion": CATEGORY_DESC[cat],
            }
            for cat in CATEGORY_ORDER
        },
        "por_tipo": dict(Counter(x.get("type") or "Unknown" for x in items).most_common()),
        "por_rareza": dict(Counter(x.get("rare") or "NONE" for x in items).most_common()),
        "por_tag": dict(sorted(Counter(x.get("tag") or "none" for x in items).items())),
    }
    (DATA_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (DATA_DIR / "missing_images.json").write_text(
        json.dumps(missing, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    # limpieza de salidas viejas
    for old in (DATA_DIR / "items_by_type", DATA_DIR / "ids_by_type"):
        if old.exists():
            shutil.rmtree(old)
    if IMG_ROOT.exists() and not any(IMG_ROOT.iterdir()):
        IMG_ROOT.rmdir()

    write_readme(summary)
    write_gallery()
    print("[done] estructura final lista")


def write_readme(s):
    order_rows = "\n".join(
        f"| [{cat}]({cat}/) | {s['categorias'][cat]['descripcion']} | "
        f"{s['categorias'][cat]['items']:,} | {s['categorias'][cat]['con_imagen']:,} |"
        for cat in CATEGORY_ORDER
    )
    total_img = s["items_con_imagen"]
    readme = f"""# clothers

Archivo completo de items de **Free Fire** extraido de
[ff-item.netlify.app](https://ff-item.netlify.app/?o=ob55): nombre, **item ID**,
**icon ID**, descripcion, tipo, rareza, tag e **imagen** de cada item.

## Numeros

| Dato | Valor |
|---|---|
| Items | **{s['items']:,}** |
| Items con imagen | **{total_img:,}** |
| Items sin imagen en el CDN | {s['items_sin_imagen']:,} |
| Imagenes en disco | {s['imagenes_en_disco']:,} |
| Carpetas | {len(CATEGORY_ORDER)} |

## Carpetas

Cada carpeta tiene dos subcarpetas:

- **`imagenes/`** — un archivo por item, nombrado con su item ID (`909046008.png`).
- **`TXT/`** — un `.txt` por item con **ITEM ID**, **ICON ID**, nombre, tipo, rareza,
  tag, descripcion e imagen; mas `_TODOS.txt` con todo el listado en columnas.

| Carpeta | Contenido | Items | Con imagen |
|---|---|---:|---:|
{order_rows}

## Ejemplo de TXT

`EMOTES/TXT/909046008.txt`

```text
ITEM ID: 909046008
ICON ID: Icon_Emote_Meme6
NOMBRE: No Sweat
TIPO: Emote
RAREZA: BLUE (Rare)
TAG: OB46
DESCRIPCION: ...
IMAGEN: EMOTES/imagenes/909046008.png
```

## Dataset maestro

| Archivo | Que es |
|---|---|
| `data/items.json` | todos los items con `itemID`, `name`, `categoria`, `image`, etc. |
| `data/items.csv` | el mismo dataset en CSV (UTF-8 con BOM, abre en Excel) |
| `data/summary.json` | conteos por categoria, tipo, rareza y tag |
| `data/missing_images.json` | IDs sin imagen disponible |
| `data/ids.txt` | todos los item IDs, uno por linea |
| `source/data.msgpack.gz` | payload original de la web, sin tocar |
| `gallery.html` | visor local con busqueda, filtros y copia de ID |

## Uso rapido

```python
import json

items = json.load(open("data/items.json", encoding="utf-8"))
emotes = [i for i in items if i["categoria"] == "EMOTES"]
print(len(emotes), emotes[0]["name"], emotes[0]["itemID"], emotes[0]["image"])
```

Para abrir el visor, sirve la carpeta con un servidor local (el navegador bloquea
`fetch` sobre `file://`):

```bash
python -m http.server 8000
# http://localhost:8000/gallery.html
```

Busca por nombre, item ID, icon ID, tipo, rareza, tag o categoria, y copia el ID
con un clic.

## Notas

- Los archivos de `imagenes/` llevan extension `.png` igual que en el CDN original;
  muchos contienen bytes WebP. Navegadores, VS Code y visores normales los abren igual.
- `OTROS/TXT/_sin_metadata.txt` lista iconos del CDN que no aparecen en el dataset.
- Rarezas: `WHITE` Common · `GREEN` Uncommon · `BLUE` Rare · `PURPLE` Epic ·
  `PURPLE_PLUS` Epic++ · `ORANGE` Mythic · `ORANGE_PLUS` Mythic++ · `RED` Artifact.

## Regenerar

```bash
pip install msgpack
python scripts/scrape.py     # descarga datos + iconos a images/
python scripts/organize.py   # arma carpetas, TXT y dataset final
```

## Creditos

Datos e iconos: [ShahGCreator](https://github.com/ShahGCreator/icon).
Free Fire es propiedad de Garena. Este repositorio es un archivo de referencia.
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")


GALLERY = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>clothers — archivo de items Free Fire</title>
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
  input { flex:1 1 240px; }
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
  .idline { display:flex; align-items:center; gap:8px; margin:4px 0; flex-wrap:wrap; }
  .idline code { background:#0e1420; padding:3px 7px; border-radius:6px; }
  .copy { background:var(--accent); color:#111; border:0; border-radius:6px; padding:5px 9px; cursor:pointer; font-weight:600; }
  .desc { margin-top:12px; color:var(--dim); max-height:150px; overflow:auto; }
  .close { margin-top:16px; width:100%; background:#1d2737; color:var(--text); border:1px solid var(--line);
           border-radius:8px; padding:9px; cursor:pointer; font:inherit; }
</style>
</head>
<body>
<header>
  <h1>clothers <span>·</span> archivo de items Free Fire</h1>
  <div class="controls">
    <input id="q" type="search" placeholder="Buscar nombre, item ID, icon ID o descripcion...">
    <select id="cat"><option value="">Todas las carpetas</option></select>
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
      <div class="idline">Item ID <code id="mId"></code><button class="copy" id="mCopy">Copiar ID</button></div>
      <div class="idline">Icon ID <code id="mIcon"></code></div>
      <div class="meta"><span id="mCat"></span><span id="mType"></span><b id="mRare"></b></div>
      <div class="meta"><span id="mTag"></span><span></span></div>
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
  for (const c of uniq('categoria')) $('cat').add(new Option(c, c));
  for (const t of uniq('type')) $('type').add(new Option(t, t));
  for (const r of uniq('rare')) $('rare').add(new Option(r, r));
  for (const t of uniq('tag')) $('tag').add(new Option(t, t));
  apply();
});

function apply() {
  const q = $('q').value.trim().toLowerCase();
  const c = $('cat').value, t = $('type').value, r = $('rare').value, g = $('tag').value;
  view = items.filter(i =>
    (!c || i.categoria === c) && (!t || i.type === t) && (!r || i.rare === r) && (!g || i.tag === g) &&
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
        : '<span class="noimg">sin imagen</span>') + '</div>' +
      '<div class="name" title="' + esc(i.name) + '">' + esc(i.name) + '</div>' +
      '<div class="meta"><span>' + esc(i.categoria) + '</span><b>' + esc(i.itemID) + '</b></div>';
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
  $('mIcon').textContent = i.icon || '(sin icon id)';
  $('mCat').textContent = i.categoria;
  $('mType').textContent = i.type;
  $('mRare').textContent = i.rare;
  $('mTag').textContent = i.tag || '';
  $('mDesc').textContent = i.description || 'Sin descripcion.';
  $('mImg').src = i.image || '';
  $('mImg').style.visibility = i.image ? 'visible' : 'hidden';
  $('modal').showModal();
}

$('q').addEventListener('input', apply);
for (const id of ['cat', 'type', 'rare', 'tag']) $(id).addEventListener('change', apply);
$('more').addEventListener('click', render);
$('mClose').addEventListener('click', () => $('modal').close());
$('mCopy').addEventListener('click', async () => {
  await navigator.clipboard.writeText($('mId').textContent);
  $('mCopy').textContent = 'Copiado';
  setTimeout(() => $('mCopy').textContent = 'Copiar ID', 1200);
});
</script>
</body>
</html>
"""


def write_gallery():
    (ROOT / "gallery.html").write_text(GALLERY, encoding="utf-8")


if __name__ == "__main__":
    main()
