#!/usr/bin/env bash
# Pull the current branch when GitHub moves. Does not push to the Linux server.
#
# Leave a Terminal window open in this repo:
#   ./watch_git_pull.sh
#
# Every 10 seconds it fetches this branch's upstream. A new upstream commit
# runs git pull --ff-only. While nothing has moved, the status stays on one
# line. Ctrl+C stops the loop.

set -u

INTERVAL="${1:-10}"
cd "$(dirname "$0")"
export GIT_TERMINAL_PROMPT=0

quiet=0

end_quiet() {
  if [[ "$quiet" -eq 1 ]]; then
    printf '\n'
    quiet=0
  fi
}

stamp() {
  end_quiet
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
}

quiet_line() {
  printf '\r%-72s' "[$(date '+%H:%M:%S')] $1"
  quiet=1
}

trap 'end_quiet; exit 0' INT TERM

branch="$(git rev-parse --abbrev-ref HEAD)"
stamp "watching ${branch} every ${INTERVAL}s. Ctrl+C to stop. git pull only."

while true; do
  upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)"
  if [[ -z "$upstream" ]]; then
    stamp "this branch has no upstream; nothing to pull"
    sleep "$INTERVAL"
    continue
  fi

  remote="${upstream%%/*}"
  remote_branch="${upstream#*/}"
  if ! git fetch "$remote" "$remote_branch" --quiet; then
    stamp "fetch ${upstream} failed; will retry"
    sleep "$INTERVAL"
    continue
  fi

  head="$(git rev-parse HEAD)"
  remote_sha="$(git rev-parse "$upstream")"
  if [[ "$head" == "$remote_sha" ]]; then
    quiet_line "no change (${head:0:7})"
    sleep "$INTERVAL"
    continue
  fi

  if git merge-base --is-ancestor "$remote_sha" "$head"; then
    quiet_line "local is ahead (${head:0:7}); not pulling"
    sleep "$INTERVAL"
    continue
  fi

  if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    stamp "upstream moved but tracked files are modified; not pulling"
    sleep "$INTERVAL"
    continue
  fi

  stamp "upstream ${remote_sha:0:7}; git pull --ff-only"
  if git pull --ff-only; then
    pulled="$(git rev-parse HEAD)"
    stamp "pulled ${pulled:0:7}"
  else
    stamp "git pull failed; will retry"
  fi
  sleep "$INTERVAL"
done
