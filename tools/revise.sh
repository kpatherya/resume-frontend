#!/usr/bin/env bash
#
# Revision workflow helper for rewriting project write-ups in your own voice.
#
#   ./tools/revise.sh list             show every project and its branch state
#   ./tools/revise.sh start <slug>     switch to kausar/<slug> (creating it off main)
#   ./tools/revise.sh preview          build the manifest and serve the site locally
#   ./tools/revise.sh save <slug> [msg] commit + push the current branch
#   ./tools/revise.sh ship <slug>      push and open a pull request into main
#   ./tools/revise.sh sync             rebase the current branch onto the latest main
#
# Each branch edits exactly one file -- content/projects/<slug>.json -- so the
# seven revisions can land in any order without conflicting.

set -euo pipefail

cd "$(dirname "$0")/.."

PROJECT_DIR="content/projects"
PORT="${PORT:-8000}"

die() { printf 'error: %s\n' "$1" >&2; exit 1; }

slugs() { find "$PROJECT_DIR" -name '*.json' -exec basename {} .json \; | sort; }

require_slug() {
  [ -n "${1:-}" ] || die "missing <slug>. Run './tools/revise.sh list' to see them."
  [ -f "$PROJECT_DIR/$1.json" ] || die "unknown project '$1'. Known: $(slugs | tr '\n' ' ')"
}

cmd_list() {
  printf '%-32s %-10s %s\n' SLUG TIER BRANCH
  for slug in $(slugs); do
    tier=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['tier'])" "$PROJECT_DIR/$slug.json")
    if git show-ref --verify --quiet "refs/heads/kausar/$slug"; then
      ahead=$(git rev-list --count "main..kausar/$slug")
      state="kausar/$slug (+$ahead)"
    else
      state="-"
    fi
    printf '%-32s %-10s %s\n' "$slug" "$tier" "$state"
  done
}

cmd_start() {
  require_slug "${1:-}"
  local slug="$1" branch="kausar/$1"
  git diff --quiet && git diff --cached --quiet || die "commit or stash your changes first."
  git fetch --quiet origin main
  if git show-ref --verify --quiet "refs/heads/$branch"; then
    git switch "$branch"
  else
    git switch --create "$branch" origin/main
  fi
  printf '\nOn %s. Rewrite this file in your own voice:\n  %s/%s.json\n\nThen: ./tools/revise.sh preview   ->   ./tools/revise.sh ship %s\n' \
    "$branch" "$PROJECT_DIR" "$slug" "$slug"
}

cmd_preview() {
  python3 tools/build_manifest.py
  printf '\nServing http://localhost:%s -- Ctrl+C to stop.\n\n' "$PORT"
  python3 -m http.server "$PORT" --directory public
}

cmd_save() {
  require_slug "${1:-}"
  local slug="$1"
  local message="${2:-Rewrite $slug write-up in my own voice}"
  python3 tools/build_manifest.py --check
  git add "$PROJECT_DIR/$slug.json"
  git diff --cached --quiet && die "nothing staged for $slug."
  git commit -m "$message"
  git push --set-upstream origin "kausar/$slug"
}

cmd_ship() {
  require_slug "${1:-}"
  local slug="$1" branch="kausar/$1"
  [ "$(git rev-parse --abbrev-ref HEAD)" = "$branch" ] || die "switch to $branch first."
  python3 tools/build_manifest.py --check
  git push --set-upstream origin "$branch"
  if command -v gh >/dev/null 2>&1; then
    gh pr create --base main --head "$branch" \
      --title "Rewrite $slug write-up in my own voice" \
      --body "Revises \`content/projects/$slug.json\`. Touches no other project." \
      2>/dev/null || gh pr view "$branch" --web
  else
    printf 'Install the GitHub CLI (brew install gh) or open a PR for %s manually.\n' "$branch"
  fi
}

cmd_sync() {
  git fetch --quiet origin main
  git rebase origin/main
}

case "${1:-}" in
  list)    shift; cmd_list "$@" ;;
  start)   shift; cmd_start "$@" ;;
  preview) shift; cmd_preview "$@" ;;
  save)    shift; cmd_save "$@" ;;
  ship)    shift; cmd_ship "$@" ;;
  sync)    shift; cmd_sync "$@" ;;
  *)       sed -n '3,14p' "$0" | sed 's/^# \{0,1\}//' ;;
esac
