#!/usr/bin/env bash
# new.sh NAME - scaffold a new _fuse script folder (script + README) and index it.
set -euo pipefail

PROG="${0##*/}"
FUSE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INDEX="$FUSE_DIR/README.md"

note() { printf '  %s\n' "$*" >&2; }
die()  { printf '%s: error: %s\n' "$PROG" "$*" >&2; exit 1; }

usage() {
  cat <<EOF
$PROG - scaffold a new script in _fuse/ (${FUSE_DIR#$HOME/})

Usage:
  $PROG NAME [--py] [--desc "what it does"]

Creates NAME/NAME.sh   (or NAME.py with --py) and NAME/README.md,
makes the script executable, and adds a row to the _fuse index README.

Options:
  --sh          bash script (default)
  --py          python script
  --desc TEXT   one-line description for the README + index
  -h, --help    show this help

Examples:
  $PROG resize_images --desc "Batch-resize images in a folder"
  $PROG tally --py --desc "Sum numbers from stdin"
EOF
}

NAME=""
KIND="sh"
DESC=""
while [ $# -gt 0 ]; do
  case "$1" in
    --sh)  KIND="sh"; shift ;;
    --py|--python) KIND="py"; shift ;;
    --desc) [ -n "${2:-}" ] || die "--desc needs a value"; DESC="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    -*)    die "unknown option: $1 (try --help)" ;;
    *)     NAME="$1"; shift ;;
  esac
done

[ -n "$NAME" ] || { usage >&2; exit 2; }

SAFE="$(printf '%s' "$NAME" | LC_ALL=C tr -c 'A-Za-z0-9._-' '-' \
        | sed 's/-\{2,\}/-/g; s/^-*//; s/-*$//')"
[ -n "$SAFE" ] || die "invalid name: $NAME"
[ "$SAFE" != "$NAME" ] && note "using folder name: $SAFE"

DIR="$FUSE_DIR/$SAFE"
if [ -e "$DIR" ]; then die "already exists: $DIR"; fi
mkdir -p "$DIR"

if [ "$KIND" = "py" ]; then
  FILE="$DIR/$SAFE.py"
  cat > "$FILE" <<'PY'
#!/usr/bin/env python3
"""TODO: describe this script."""

import argparse


def main() -> int:
    ap = argparse.ArgumentParser(description="TODO")
    ap.add_argument("path", nargs="?", default=".")
    args = ap.parse_args()
    print(args.path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY
else
  FILE="$DIR/$SAFE.sh"
  cat > "$FILE" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

usage() { printf 'usage: %s ...\n' "${0##*/}"; }

main() {
  : # TODO
}

main "$@"
SH
fi
chmod +x "$FILE"

DESC="${DESC:-One-line description.}"
cat > "$DIR/README.md" <<EOF
# $SAFE

$DESC

## Usage

\`\`\`bash
$SAFE
\`\`\`

## Options

| Option | Description |
| --- | --- |
| \`-h\`, \`--help\` | show help |
EOF

ROW="| [\`$SAFE\`](./$SAFE/) | $DESC |"
if [ -f "$INDEX" ] && grep -q '<!-- scripts:begin -->' "$INDEX"; then
  tmp="$(mktemp)"
  awk -v row="$ROW" '{ print } /<!-- scripts:begin -->/{ print row }' "$INDEX" > "$tmp"
  mv "$tmp" "$INDEX"
  note "indexed in README.md"
else
  note "add a row to the _fuse README manually: $ROW"
fi

note "created $FILE"
note "created $DIR/README.md"
