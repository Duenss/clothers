# clothers

Archivo completo de items de **Free Fire** extraido de
[ff-item.netlify.app](https://ff-item.netlify.app/?o=ob55): nombre, **item ID**,
**icon ID**, descripcion, tipo, rareza, tag e **imagen** de cada item.

## Numeros

| Dato | Valor |
|---|---|
| Items | **34,210** |
| Items con imagen | **34,107** |
| Items sin imagen en el CDN | 103 |
| Imagenes en disco | 34,184 |
| Carpetas | 10 |

## Carpetas

Cada carpeta tiene dos subcarpetas:

- **`imagenes/`** — un archivo por item, nombrado con su item ID (`909046008.png`).
- **`TXT/`** — un `.txt` por item con **ITEM ID**, **ICON ID**, nombre, tipo, rareza,
  tag, descripcion e imagen; mas `_TODOS.txt` con todo el listado en columnas.

| Carpeta | Contenido | Items | Con imagen |
|---|---|---:|---:|
| [ROPA](ROPA/) | conjuntos, tops, bottoms, zapatos, cabeza, mascaras, facepaint, bolsos, look changer | 17,624 | 17,541 |
| [EMOTES](EMOTES/) | emotes, super emotes, animaciones de llegada, posturas, remates | 597 | 597 |
| [ARMAS](ARMAS/) | skins de armas, puños, granadas, gloo walls y cajas de armas | 3,448 | 3,447 |
| [PERSONAJES](PERSONAJES/) | personajes y skins de habilidad | 97 | 97 |
| [MASCOTAS](MASCOTAS/) | mascotas, skins, habilidades y emotes de mascota | 389 | 389 |
| [VEHICULOS](VEHICULOS/) | skins de vehiculos, skyboards, skywings y paracaidas | 987 | 987 |
| [AVATARES](AVATARES/) | avatares, marcos, banners, titulos, stickers y tarjetas | 2,374 | 2,374 |
| [MUSICA](MUSICA/) | musica y paquetes de voz | 797 | 797 |
| [CAJAS](CAJAS/) | loot crates, choice crates, loot box, vouchers y tokens | 6,750 | 6,750 |
| [OTROS](OTROS/) | items sin tipo, hyper books y elementos sin clasificar | 1,147 | 1,128 |

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

Abre `gallery.html` en el navegador para buscar por nombre, ID, icon ID, tipo,
rareza, tag o categoria.

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
