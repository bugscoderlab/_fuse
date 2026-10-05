# _fuse

My frequently-used scripts, one folder each — script + its own README, indexed
below.

## Layout

```
_fuse/
├── README.md              # this index
├── AGENTS.md              # agent instructions (how to add a script)
├── extract_formulas/      # one folder per script
│   ├── extract_formulas.py
│   └── README.md
├── connect_github/
│   ├── connect_github.sh
│   └── README.md
└── new/
    ├── new.sh             # scaffolder for new entries
    └── README.md
```

**The convention:** every tool lives in its own folder, holds the runnable file
plus a `README.md`, and gets one row in the table below. Nothing at the root
except this index, `AGENTS.md`, and the script folders.

## Scripts

| Script | What it does |
| --- | --- |
<!-- scripts:begin -->
| [`connect_github`](./connect_github/) | Create a GitHub repo for a folder (public by default) and push. |
| [`extract_formulas`](./extract_formulas/) | Dump formulas (not values) from an `.xlsx` workbook, zero deps. |
| [`new`](./new/) | Scaffold a new `_fuse` script folder + README and index it. |
<!-- scripts:end -->

## Adding a script

`new/` is the **scaffolder**: its job is to make adding the next script a
one-liner and keep every entry in the same shape, so the folder stays consistent
as it grows. Run it instead of creating folders and files by hand:

```bash
new/new.sh my_tool --desc "What it does"
```

It creates `my_tool/my_tool.sh` (executable) plus `my_tool/README.md`, and
inserts a row into the index table above. Add `--py` for a Python stub, then
edit the generated script and README to fill in the real behaviour.

**Using an AI agent to write the script?** Point it at
[`AGENTS.md`](./AGENTS.md). That file carries the same convention in
agent-readable form — use `new.sh` to scaffold, write the script, complete the
README, keep the index valid — so a generated script lands in the right shape
without you restating the rules.

See [`new/`](./new/) for the full options.

## Running them

Call them by path, e.g.:

```bash
~/Documents/_fuse/connect_github/connect_github.sh --private
~/Documents/_fuse/extract_formulas/extract_formulas.py book.xlsx
```

To run by bare name from anywhere, add each script folder to your `PATH`, for
example in `~/.zshrc`:

```sh
export PATH="$HOME/Documents/_fuse/connect_github:$HOME/Documents/_fuse/extract_formulas:$PATH"
```

Or symlink the ones you use most into `~/.local/bin` (already on most `PATH`s):

```bash
ln -s ~/Documents/_fuse/connect_github/connect_github.sh ~/.local/bin/connect_github
```
