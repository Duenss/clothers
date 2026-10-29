# clothers

Archivo de items de Free Fire con **nombre, item ID, icon ID, descripcion e imagen**,
organizado por categoria.

## Cantidades

| Carpeta | Items | Imagenes |
|---|---:|---:|
| ROPA | 17.624 | 17.541 |
| EMOTES | 597 | 597 |
| ARMAS | 3.448 | 3.447 |
| PERSONAJES | 97 | 97 |
| MASCOTAS | 389 | 389 |
| VEHICULOS | 987 | 987 |
| AVATARES | 2.374 | 2.374 |
| MUSICA | 797 | 797 |
| CAJAS | 6.750 | 6.750 |
| OTROS | 1.147 | 1.205 |
| **TOTAL** | **34.210** | **34.184** |

- 34.107 items tienen imagen.
- 103 items no tienen imagen en el CDN.
- `OTROS/imagenes` incluye 77 iconos sin datos asociados (`OTROS/TXT/_sin_metadata.txt`).

## Como esta organizado

Cada carpeta (`ROPA`, `EMOTES`, `ARMAS`, `PERSONAJES`, `MASCOTAS`, `VEHICULOS`,
`AVATARES`, `MUSICA`, `CAJAS`, `OTROS`) tiene dos subcarpetas:

### `imagenes/`

Un archivo por item, nombrado con su item ID:

```text
ROPA/imagenes/101000001.png
EMOTES/imagenes/909046008.png
```

Los archivos llevan extension `.png`; algunos contienen bytes WebP. Navegadores,
Excel, VS Code y visores normales los abren sin problema.

### `TXT/`

Un archivo por item, nombrado con su item ID:

```text
ROPA/TXT/101000001.txt
EMOTES/TXT/909046008.txt
```

Cada TXT trae estos campos:

```text
ITEM ID: 909046008
ICON ID: Icon_Emote_Meme6
NOMBRE: No Sweat
TIPO: Emote
RAREZA: BLUE (Rare)
TAG: OB46
DESCRIPCION: (sin descripcion)
IMAGEN: EMOTES/imagenes/909046008.png
```

### `TXT/_TODOS.txt`

Listado completo de la carpeta, una linea por item, columnas separadas por tabulador:

```text
ITEM_ID  ICON_ID  NOMBRE  TIPO  RAREZA  TAG  IMAGEN  DESCRIPCION
```

Sirve para importar directo a Excel, Google Sheets, SQL o cualquier script.

## Integracion rapida

1. Cada item se identifica por su **item ID**, que es el nombre del PNG y del TXT.
2. La imagen esta en `{CARPETA}/imagenes/{itemID}.png`.
3. Los datos estan en `{CARPETA}/TXT/{itemID}.txt`.
4. Para cargar todo de una vez, usa `{CARPETA}/TXT/_TODOS.txt`.

## Rarezas

`WHITE` Common · `GREEN` Uncommon · `BLUE` Rare · `PURPLE` Epic ·
`PURPLE_PLUS` Epic++ · `ORANGE` Mythic · `ORANGE_PLUS` Mythic++ ·
`RED` Artifact
