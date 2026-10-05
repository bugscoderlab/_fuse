# AGENTS.md — `_fuse`

`_fuse` is the user's collection of frequently-used scripts. Each script lives
in its own folder with its own `README.md`, and every one is listed in the index
in [`README.md`](./README.md). Keep that shape.

## Adding a script

When the user asks for a new script in this folder, **scaffold it with `new.sh`**
so it lands in the standard shape:

```bash
new/new.sh NAME --desc "one-line description"
```

`--py` for Python; bash is the default. This creates `NAME/NAME.sh` (or
`NAME/NAME.py`) and `NAME/README.md`, and inserts the index row. Then:

1. Write the real tool into `NAME/NAME.<ext>`.
2. Fill in `NAME/README.md`: what it does, usage, options, and one example.
3. Leave the index row in `README.md` accurate.

Done when the script runs end to end, its README shows how to run it, and the
script appears in the index table.

## Layout

- One folder per script: `NAME/NAME.sh` + `NAME/README.md`.
- The root holds only `README.md`, `AGENTS.md`, and the script folders.
- The index table sits between `<!-- scripts:begin -->` and `<!-- scripts:end -->`.

`new.sh` derives and sanitises the name (spaces become `-`) and stops if the
folder already exists. For the human-facing guide — layout, running scripts,
`PATH` setup — see [`README.md`](./README.md); for the scaffolder's options see
[`new/README.md`](./new/README.md).
