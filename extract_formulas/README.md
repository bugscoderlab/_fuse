# extract_formulas.py

Dump **formulas** (not values) out of an `.xlsx` workbook.

Zero dependencies — stdlib only (`zipfile` + XML). Runs with any `python3`, no
venv, no `openpyxl`, no Excel. An `.xlsx` is just a zip of XML; this reads it.

```bash
python3 extract_formulas.py "EXCEL TEMPLATE.xlsx"
```

## Why not DuckDB / read the value?

Excel stores both the formula and the last-computed result in each cell:

```xml
<c r="H9"><f>F9*0.25</f><v>16893.53</v></c>
```

`<f>` is the formula, `<v>` is the cached value. DuckDB's `read_xlsx` (and most
value readers) only surface `<v>`. Worse, files written by tools that don't
recalculate (e.g. `openpyxl`) have no `<v>` at all, so those cells come back
blank. This script reads `<f>` directly, so it needs no recalculation.

## Usage

```bash
# all sheets, human-readable
python3 extract_formulas.py book.xlsx

# one sheet (repeatable); note the space, so quote it
python3 extract_formulas.py book.xlsx --sheet "2ND STEP -  P&L REPORT"

# flat TSV for piping / saving
python3 extract_formulas.py book.xlsx --format tsv --header -o formulas.tsv

# TSV with layout context columns (col/row, row label, column header, merge)
python3 extract_formulas.py book.xlsx --format tsv --header --layout

# JSON
python3 extract_formulas.py book.xlsx --format json

# help
python3 extract_formulas.py --help
```

### Options

| Option | Description |
| --- | --- |
| `xlsx` | path to the `.xlsx` file (required) |
| `-s`, `--sheet NAME` | only this sheet; repeatable; default = all sheets |
| `-f`, `--format {text,tsv,json}` | output format; default `text` |
| `--header` | emit a header row (tsv only) |
| `--layout` | add `col`, `row`, `row_label`, `col_header`, `merged` (tsv/json only) |
| `-o`, `--output PATH` | write to a file instead of stdout |

## Output formats

### `text` (default)

Grouped by sheet, one formula per line with its cell reference:

```
2ND STEP -  P&L REPORT
  H6   =F6*0.25
  K6   =F6-H6
  O6   =N6+30
  B28  =SUM(B22:B27)
  C28  =B28+150
  J35  ='1ST STEP'!F15
```

### `tsv`

```
sheet	cell	formula
2ND STEP -  P&L REPORT	H6	F6*0.25
2ND STEP -  P&L REPORT	J35	'1ST STEP'!F15
```

With `--layout`:

```
sheet	cell	col	row	formula	row_label	col_header	merged
2ND STEP -  P&L REPORT	H6	H	6	F6*0.25	NAR01515/26	Total 25% Deposit (RM)	
2ND STEP -  P&L REPORT	B6	B	6	(36535.31*4)+(16709.1*4)	S83 / BRISBANE ...	Payment received in RM	B6:B13
```

| Layout column | Meaning |
| --- | --- |
| `col`, `row` | the cell's position in the grid |
| `row_label` | nearest text cell to the **left** on the same row |
| `col_header` | nearest text cell **above** in the same column |
| `merged` | the merged range the cell belongs to, if any (`B6:B13`) |

`--layout` is context **per cell**, not a 2-D grid reconstruction. TSV cannot
represent: full adjacency, spacer columns/indentation, column widths, images or
drawings, and number formats. Label text is whitespace-collapsed so a label can
never split a TSV row.

## What it handles

- **Normal formulas** — `=SUM(F6:F13)`.
- **Shared formulas** — Excel stores a repeated formula once and lets the other
  cells reference it:

  ```xml
  <c r="K8"><f t="shared" si="1">F8-H8</f>...</c>   <!-- master, has the text -->
  <c r="K9"><f t="shared" si="1"/>...</c>            <!-- follower, text missing -->
  ```

  Follower formulas are reconstructed by shifting relative references from the
  master cell (absolute `$` refs do not move; string literals and cross-sheet
  refs are left alone). Raw `<f>` scraping alone gets these wrong.
- **Array formulas** — reported with their stored text.

## Caveats

- **`=`-looking text is not a formula.** Cells whose *text* literally starts
  with `=` (e.g. `"=(25.33*1)*A21"`) are treated as text, not reported. Some
  readers (openpyxl's `data_only=False`, value dumps) surface these as if they
  were formulas; this script only reports real `<f>` cells.
- **Formulas are relative.** `F6*0.25` only means something with the cell it
  sits in (`H6`) and the values it references. Pair it with `--layout`, or read
  the referenced values too, if something downstream must evaluate it.
- **`.xls` (old binary format) is not supported.** `.xlsx` only.
- Output is read-only — the workbook is never modified.

## Verified

Formula extraction was checked cell-by-cell against `openpyxl` on a real
workbook: **100 / 100** real formula cells matched exactly, including shared
formulas. (`openpyxl`'s naive string scan reports extra "formulas" for
`=`-looking text cells — those are correctly excluded here.)
