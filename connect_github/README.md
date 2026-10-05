# connect_github.sh

Put the current folder on GitHub in one command: initialise git if needed,
create the repo, and push — repo name defaults to the folder name, **public by
default**.

```bash
cd ~/code/my-project
connect_github.sh            # -> github.com/<you>/my-project (public), pushed
```

## Requirements

- `git` — https://git-scm.com
- `gh` (GitHub CLI) — https://cli.github.com
- Logged in once: `gh auth login`
- A git identity set:

  ```bash
  git config --global user.name  "Your Name"
  git config --global user.email "you@example.com"
  ```

## Options

| Option | Description |
| --- | --- |
| `-n`, `--name NAME` | repo name; default = folder name |
| `-p`, `--private` | create a **private** repo |
| `--public` | create a public repo (**default**) |
| `-o`, `--org ORG` | create under an organisation instead of your account |
| `-d`, `--dir PATH` | operate on `PATH` instead of the current directory |
| `-r`, `--remote NAME` | git remote name (default `origin`) |
| `-m`, `--message MSG` | initial commit message (default `Initial commit`) |
| `--no-push` | create the repo but do not push |
| `-y`, `--yes` | skip the confirmation prompt |
| `-h`, `--help` | show help |

## Examples

```bash
# public repo named after the folder, pushed
connect_github.sh

# private
connect_github.sh --private

# custom name, under an organisation
connect_github.sh -n billing -o acme        # -> github.com/acme/billing

# another folder, no confirmation
connect_github.sh -d ~/code/api --private -y

# create but push later yourself
connect_github.sh --no-push
```

## What it does, in order

1. Resolves the target folder (default: current directory).
2. Derives the repo name from the folder name (sanitising spaces/invalid chars
   to `-`) unless `--name` is given.
3. Checks `git` and `gh` are present and that you're authenticated.
4. Shows the plan and asks to confirm (skip with `-y`).
5. `git init` if the folder isn't a repo yet (branch `main`).
6. Creates an initial commit if there are none yet — identity must be set.
7. Creates the GitHub repo and wires it up as the `origin` remote, then pushes
   the current branch and sets its upstream.

It is safe to re-run: if the remote already exists it just pushes; if the
GitHub repo already exists it adds it as the remote instead of failing.

## Notes

- **Repo name sanitising.** Folder names like `My Project (v2)` become
  `My-Project-v2`. GitHub also lowercases names on display. Pass `--name` to
  control it exactly.
- **Remote protocol.** When it has to add an existing repo as a remote, it
  follows your `gh` protocol setting (`gh config get git_protocol`); otherwise
  `gh repo create` decides.
- **`--no-push`** leaves the local branch unpushed; run
  `git push -u origin main` when ready.
- **Non-git folder with files already there** — all files are added in the
  initial commit. Add a `.gitignore` first if there's anything to exclude.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `not logged in to gh` | `gh auth login` |
| `git identity not set` | set `user.name` / `user.email` (see above) |
| `remote 'origin' already exists` | it still pushes; to retarget, `git remote set-url origin <url>` |
| wrong repo name | pass `-n NAME` |
| want it private and already created | `gh repo edit <owner>/<repo> --visibility private` |
