#!/usr/bin/env python3
"""Extract formulas (not cached values) from an .xlsx workbook.

Zero dependencies - stdlib only, so it runs with any `python3`:

    python3 scripts/extract_formulas.py "EXCEL TEMPLATE.xlsx"
    python3 scripts/extract_formulas.py book.xlsx --format tsv --layout -o f.tsv
    python3 scripts/extract_formulas.py book.xlsx --sheet "2ND STEP -  P&L REPORT"

An .xlsx is a zip of XML. Each formula cell looks like:

    <c r="H9"><f>F9*0.25</f><v>16893.53</v></c>

`<f>` is the formula, `<v>` is the last-cached value. This script reads `<f>`.

Excel rarely writes every formula out in full. Repeated formulas are stored
once as a "shared" group and the other cells just reference it:

    <c r="K8"><f t="shared" si="1">F8-H8</f>...</c>   <- master, has the text
    <c r="K9"><f t="shared" si="1"/>...</c>            <- follower, text missing

A follower's real formula is the master's, with relative references shifted by
the offset between the two cells (absolute `$` refs don't move). This script
does that translation, which is what openpyxl gives you but raw XML does not.

With `--layout`, each row also carries where the cell sits in the sheet: its
column and row, the nearest text label to its left, the nearest text header
above it, and the merged range it belongs to (if any). TSV is flat, so this is
context per cell - it is not a 2-D grid reconstruction.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

MAX_COL = 16384      # XFD
MAX_ROW = 1048576

# A cell reference: optional $ anchors, 1-3 column letters, row digits.
# Rejects a leading name char or "!" (so "SUM(" and "'Sheet'!A1" don't match)
# and rejects a trailing name char or "(" (so the LOG in LOG10( doesn't match).
REF = re.compile(r"(?<![A-Za-z0-9_$'!])(\$?)([A-Za-z]{1,3})(\$?)(\d+)(?![A-Za-z0-9_(])")
# Quoted string literals inside a formula ("" is an escaped quote).
STR = re.compile(r'"(?:[^"]|"")*"')
# Any sheet-qualified reference, optionally a range: '1ST STEP'!C6:C13
QUALIFIED = re.compile(
    r"(?:'[^']*'|[A-Za-z_][A-Za-z0-9_.]*)!"
    r"\$?[A-Za-z]{1,3}\$?\d+(?::\$?[A-Za-z]{1,3}\$?\d+)?"
)
_ROWCOL = re.compile(r"^([A-Za-z]{1,3})(\d+)$")
_WS = re.compile(r"\s+")


def clean(text: str) -> str:
    """Collapse whitespace so a label can never break TSV (tabs/newlines)."""
    return _WS.sub(" ", text).strip()


class Sheet:
    """Everything we read from one worksheet that the outputs need."""

    def __init__(self) -> None:
        self.formulas: list[tuple[str, str]] = []      # (cell ref, formula)
        self.texts: dict[str, str] = {}                # cell ref -> label text
        self.merges: list[tuple[int, int, int, int, str]] = []  # c1,r1,c2,r2,ref

    def merged_range(self, col: int, row: int) -> str:
        for c1, r1, c2, r2, ref in self.merges:
            if c1 <= col <= c2 and r1 <= row <= r2:
                return ref
        return ""

    def row_label(self, col: int, row: int) -> str:
        """Nearest non-empty text cell to the left on the same row."""
        for c in range(col - 1, 0, -1):
            hit = self.texts.get(f"{num_to_col(c)}{row}")
            if hit:
                return hit
        return ""

    def col_header(self, col: int, row: int) -> str:
        """Nearest non-empty text cell above in the same column."""
        for r in range(row - 1, 0, -1):
            hit = self.texts.get(f"{num_to_col(col)}{r}")
            if hit:
                return hit
        return ""


def split_ref(ref: str) -> tuple[int, int]:
    m = _ROWCOL.match(ref)
    if not m:
        raise ValueError(f"bad cell reference: {ref!r}")
    return col_to_num(m.group(1)), int(m.group(2))


def col_to_num(letters: str) -> int:
    n = 0
    for ch in letters.upper():
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n


def num_to_col(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(ord("A") + r) + s
    return s


def translate(formula: str, src: str, dst: str) -> str:
    """Shift relative references in `formula` from cell `src` to cell `dst`."""
    src_c, src_r = split_ref(src)
    dst_c, dst_r = split_ref(dst)
    dc, dr = dst_c - src_c, dst_r - src_r
    if dc == 0 and dr == 0:
        return formula

    # Mask string literals and cross-sheet refs so we never shift inside them.
    stash: list[str] = []

    def stash_it(match: re.Match[str]) -> str:
        stash.append(match.group(0))
        return f"\x00{len(stash) - 1}\x00"

    masked = STR.sub(stash_it, formula)
    masked = QUALIFIED.sub(stash_it, masked)

    def repl(match: re.Match[str]) -> str:
        c_abs, letters, r_abs, digits = match.groups()
        col, row = col_to_num(letters), int(digits)
        if col > MAX_COL or row > MAX_ROW:      # not a real ref, leave as-is
            return match.group(0)
        if not c_abs:
            col += dc
        if not r_abs:
            row += dr
        if col < 1 or row < 1:
            return "#REF!"
        return f"{c_abs}{num_to_col(col)}{r_abs}{row}"

    shifted = REF.sub(repl, masked)
    return re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], shifted)


def read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    """The workbook's shared string table: index -> text."""
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    out = []
    for si in root.findall(f"{{{MAIN}}}si"):
        out.append("".join(t.text or "" for t in si.iter(f"{{{MAIN}}}t")))
    return out


def sheet_files(zf: zipfile.ZipFile) -> list[tuple[str, str, str]]:
    """Return (sheet_name, sheet_file, part) for every worksheet, in order."""
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    target = {
        r.get("Id"): r.get("Target")
        for r in rels
        if r.get("Type", "").endswith("/worksheet")
    }
    out = []
    for sheet in wb.find(f"{{{MAIN}}}sheets"):
        name = sheet.get("name")
        rid = sheet.get(f"{{{OFFICE_REL}}}id")
        raw = target.get(rid, "")
        # Targets are relative to xl/ and may or may not be prefixed.
        path = raw if raw.startswith("xl/") else "xl/" + raw.lstrip("/")
        out.append((name, path, path.rsplit("/", 1)[-1]))
    return out


def extract_sheet(zf: zipfile.ZipFile, path: str, shared: list[str]) -> Sheet:
    """Read formulas, label text and merged ranges from one worksheet."""
    root = ET.fromstring(zf.read(path))
    sheet = Sheet()
    follow: list[tuple[str, str]] = []          # (ref, si) shared followers
    masters: dict[str, tuple[str, str]] = {}    # si -> (formula, master ref)
    row_no = 0

    for row in root.iter(f"{{{MAIN}}}row"):
        implicit_col = 0
        row_no = int(row.get("r") or row_no + 1)
        for cell in row.findall(f"{{{MAIN}}}c"):
            ref = cell.get("r")
            if ref:                             # explicit position: trust it
                implicit_col = split_ref(ref)[0]
            else:                               # cell without r: next column
                implicit_col += 1
                ref = f"{num_to_col(implicit_col)}{row_no}"

            ctype = cell.get("t")
            value = cell.find(f"{{{MAIN}}}v")

            f = cell.find(f"{{{MAIN}}}f")
            if f is not None:
                text = f.text
                kind = f.get("t")        # None | "shared" | "array" | "dataTable"
                si = f.get("si")
                if text:                 # has the formula written out
                    sheet.formulas.append((ref, text))
                    if kind == "shared" and si is not None:
                        masters[si] = (text, ref)
                elif kind == "shared" and si is not None:
                    follow.append((ref, si))
                continue                 # formula cells are not labels

            # Non-formula cell: keep only visible text, used as layout labels.
            if ctype == "s" and value is not None and value.text is not None:
                idx = int(value.text)
                if 0 <= idx < len(shared):
                    label = clean(shared[idx])
                    if label:
                        sheet.texts[ref] = label
            elif ctype == "inlineStr":
                is_el = cell.find(f"{{{MAIN}}}is")
                if is_el is not None:
                    label = clean("".join(t.text or "" for t in is_el.iter(f"{{{MAIN}}}t")))
                    if label:
                        sheet.texts[ref] = label

    for ref, si in follow:                       # resolve inherited formulas
        master = masters.get(si)
        if master:
            sheet.formulas.append((ref, translate(master[0], master[1], ref)))

    merges = root.find(f"{{{MAIN}}}mergeCells")
    if merges is not None:
        for mc in merges.findall(f"{{{MAIN}}}mergeCell"):
            ref = mc.get("ref", "")             # e.g. A1:B2
            if ":" in ref:
                (a, b) = ref.split(":", 1)
                try:
                    c1, r1 = split_ref(a)
                    c2, r2 = split_ref(b)
                except ValueError:
                    continue
                sheet.merges.append((c1, r1, c2, r2, ref))

    sheet.formulas.sort(key=lambda rc: (split_ref(rc[0])[1], split_ref(rc[0])[0]))
    return sheet


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Extract formulas (not values) from an .xlsx workbook."
    )
    ap.add_argument("xlsx", help="path to the .xlsx file")
    ap.add_argument("-s", "--sheet", action="append", default=None,
                    help="only this sheet (repeatable); default: all")
    ap.add_argument("-f", "--format", choices=("text", "tsv", "json"),
                    default="text", help="output format (default: text)")
    ap.add_argument("--header", action="store_true",
                    help="emit a header row (tsv only)")
    ap.add_argument("--layout", action="store_true",
                    help="add col/row + row-label/col-header + merged-range "
                         "columns (tsv/json only)")
    ap.add_argument("-o", "--output", default=None,
                    help="write to this file instead of stdout")
    args = ap.parse_args(argv)

    with zipfile.ZipFile(args.xlsx) as zf:
        shared = read_shared_strings(zf)
        sheets = sheet_files(zf)
        if args.sheet:
            wanted = set(args.sheet)
            unknown = wanted - {name for name, _, _ in sheets}
            if unknown:
                print(f"error: no such sheet: {', '.join(sorted(unknown))}",
                      file=sys.stderr)
                print(f"       available: {', '.join(n for n, _, _ in sheets)}",
                      file=sys.stderr)
                return 2
            sheets = [s for s in sheets if s[0] in wanted]

        extracted = [(name, extract_sheet(zf, path, shared))
                     for name, path, _ in sheets]

    records = []
    for name, sheet in extracted:
        for cell, formula in sheet.formulas:
            col, row = split_ref(cell)
            rec = {"sheet": name, "cell": cell, "formula": formula}
            if args.layout:
                rec["col"] = num_to_col(col)
                rec["row"] = row
                rec["row_label"] = sheet.row_label(col, row)
                rec["col_header"] = sheet.col_header(col, row)
                rec["merged"] = sheet.merged_range(col, row)
            records.append(rec)

    if args.format == "json":
        text = json.dumps(records, indent=2)
    elif args.format == "tsv":
        fields = (["sheet", "cell", "formula"] if not args.layout else
                  ["sheet", "cell", "col", "row", "formula",
                   "row_label", "col_header", "merged"])
        lines = ["\t".join(fields)] if args.header else []
        lines += ["\t".join(str(r[k]) for k in fields) for r in records]
        text = "\n".join(lines)
    else:  # text
        blocks = []
        for name, sheet in extracted:
            blocks.append(name)
            if not sheet.formulas:
                blocks.append("  (no formulas)")
                continue
            craft = [c for c, _ in sheet.formulas]
            width = max(len(c) for c in craft)
            for cell, formula in sheet.formulas:
                blocks.append(f"  {cell.ljust(width)}  ={formula}")
        text = "\n".join(blocks)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"{len(records)} formulas -> {args.output}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
