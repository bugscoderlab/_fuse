# new.sh

Scaffold a new script in `_fuse/` so every script lands with the same shape:
its own folder, the runnable file, a `README.md`, and a row in the top-level
index. One command instead of remembering the convention.

```bash
new/new.sh resize_images --desc "Batch-resize images in a folder"
```

That creates:

```
_fuse/resize_images/
├── resize_images.sh     # executable, ready to edit
└── README.md            # stub, prefilled heading + usage
```

…and inserts `| [resize_images](./resize_images/) | Batch-resize images in a folder |`
into `_fuse/README.md`.

## Usage

```bash
new/new.sh NAME [--py] [--desc "one-line description"]
```

| Option | Description |
| --- | --- |
| `NAME` | folder + script name (required) |
| `--sh` | bash script (default) |
| `--py` | python script |
| `--desc TEXT` | one-line description for the README and the index |
| `-h`, `--help` | show help |

## Examples

```bash
new/new.sh backup_notes --desc "Snapshot a folder to a dated tarball"
new/new.sh tally --py --desc "Sum numbers from stdin"
new/new.sh clean_downloads                       # description placeholder
```

## Notes

- **Names are sanitised** the same way as `connect_github.sh`: spaces and
  invalid characters become `-`, so `My Tool` → folder `My-Tool`.
- **It refuses to overwrite** an existing folder.
- **The index row is inserted** immediately after the `<!-- scripts:begin -->`
  marker in `_fuse/README.md`. If that marker is missing it prints the row for
  you to paste instead.
- After scaffolding, replace the `TODO`s in the script and fill in its README.
