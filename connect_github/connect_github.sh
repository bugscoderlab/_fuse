#!/usr/bin/env bash
# connect_github.sh - create a GitHub repo for a folder and push to it.
#
# Defaults: repo name = folder name, visibility = public, remote = origin,
#           and it pushes the current branch (setting upstream).
set -euo pipefail

PROG="${0##*/}"

say()  { printf '  %s\n' "$*"; }
note() { printf '  %s\n' "$*" >&2; }
die()  { printf '%s: error: %s\n' "$PROG" "$*" >&2; exit 1; }

usage() {
  cat <<EOF
$PROG - put this folder on GitHub.

Usage:
  $PROG [options]

Options:
  -n, --name NAME     repo name (default: folder name)
  -p, --private       create a private repo
      --public        create a public repo (default)
  -o, --org ORG       create under an organisation instead of your account
  -d, --dir PATH      operate on PATH instead of the current directory
  -r, --remote NAME   git remote name to use (default: origin)
  -m, --message MSG   initial commit message (default: "Initial commit")
      --no-push       create the repo but do not push
  -y, --yes           do not ask for confirmation
  -h, --help          show this help

Examples:
  $PROG                          current folder -> public repo, same name
  $PROG --private                private repo
  $PROG -n billing -o acme       acme/billing
  $PROG -d ~/code/api --private  operate on another folder
EOF
}

need_val() { [ -n "${2:-}" ] || die "$1 needs a value"; }

DIR="."
NAME=""
VIS="public"
ORG=""
REMOTE="origin"
PUSH=1
MSG="Initial commit"
ASSUME_YES=0

while [ $# -gt 0 ]; do
  case "$1" in
    -n|--name)    need_val "$1" "${2:-}"; NAME="$2"; shift 2 ;;
    -p|--private) VIS="private"; shift ;;
    --public)     VIS="public"; shift ;;
    -o|--org)     need_val "$1" "${2:-}"; ORG="$2"; shift 2 ;;
    -d|--dir)     need_val "$1" "${2:-}"; DIR="$2"; shift 2 ;;
    -r|--remote)  need_val "$1" "${2:-}"; REMOTE="$2"; shift 2 ;;
    -m|--message) need_val "$1" "${2:-}"; MSG="$2"; shift 2 ;;
    --no-push)    PUSH=0; shift ;;
    -y|--yes)     ASSUME_YES=1; shift ;;
    -h|--help)    usage; exit 0 ;;
    *)            die "unknown option: $1 (try --help)" ;;
  esac
done

# ---- resolve target folder -------------------------------------------------
[ -d "$DIR" ] || die "no such directory: $DIR"
DIR="$(cd "$DIR" && pwd)"

if [ -z "$NAME" ]; then
  NAME="$(basename "$DIR")"
fi
# GitHub repo names: letters, digits, '.', '-', '_'
NAME="$(printf '%s' "$NAME" | LC_ALL=C tr -c 'A-Za-z0-9._-' '-' \
        | sed 's/-\{2,\}/-/g; s/^-*//; s/-*$//')"
[ -n "$NAME" ] || die "could not derive a repo name; pass --name"

# ---- prerequisites ---------------------------------------------------------
command -v git >/dev/null 2>&1 || die "git is not installed"
command -v gh  >/dev/null 2>&1 || die \
  "GitHub CLI (gh) is not installed - see https://cli.github.com"
gh auth status >/dev/null 2>&1 || die "not logged in to gh - run: gh auth login"

FULL="$NAME"
if [ -n "$ORG" ]; then FULL="$ORG/$NAME"; fi
OWNER="${ORG:-$(gh api user -q .login 2>/dev/null || echo 'your account')}"

# ---- confirm ---------------------------------------------------------------
printf '\nCreate GitHub repo:\n'
say "name:       $NAME"
say "owner:      $OWNER"
say "visibility: $VIS"
say "source:     $DIR"
say "remote:     $REMOTE"
say "push:       $([ "$PUSH" -eq 1 ] && echo yes || echo no)"

if [ "$ASSUME_YES" -ne 1 ]; then
  printf '\nProceed? [Y/n] '
  read -r ans || ans=""
  case "$ans" in ""|y|Y|yes|YES) ;; *) echo "aborted."; exit 0 ;; esac
fi

cd "$DIR"

# ---- make sure it is a git repo with at least one commit -------------------
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  note "no git repo here - initialising"
  git init -q -b main 2>/dev/null || { git init -q; git symbolic-ref HEAD refs/heads/main; }
fi

if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
  if [ -z "$(git config user.email || true)" ] || [ -z "$(git config user.name || true)" ]; then
    die "git identity not set - run:
       git config --global user.name  'Your Name'
       git config --global user.email 'you@example.com'"
  fi
  note "no commits yet - creating initial commit"
  git add -A
  if git diff --cached --quiet; then
    git commit -q --allow-empty -m "$MSG"
  else
    git commit -q -m "$MSG"
  fi
fi

BRANCH="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || echo main)"

# ---- remote + repo ---------------------------------------------------------
if git remote get-url "$REMOTE" >/dev/null 2>&1; then
  note "remote '$REMOTE' already exists -> $(git remote get-url "$REMOTE")"
elif gh repo view "$FULL" >/dev/null 2>&1; then
  note "GitHub repo $FULL already exists - adding it as '$REMOTE'"
  proto="$(gh config get git_protocol 2>/dev/null || echo https)"
  if [ "$proto" = "ssh" ]; then
    url="git@github.com:$FULL.git"
  else
    url="https://github.com/$FULL.git"
  fi
  git remote add "$REMOTE" "$url"
else
  gh repo create "$FULL" --source=. --remote="$REMOTE" "--$VIS"
fi

if [ "$PUSH" -eq 1 ]; then
  note "pushing '$BRANCH' to '$REMOTE'"
  git push -u "$REMOTE" "$BRANCH"
else
  note "skipping push (--no-push)"
fi

URL="$(gh repo view "$FULL" --json url -q .url 2>/dev/null || true)"
[ -n "$URL" ] || URL="https://github.com/$FULL"
printf '\nDone:  %s\n' "$URL"
