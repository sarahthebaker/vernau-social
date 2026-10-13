#!/usr/bin/env bash
# Queue the prism reels in ~/Projects/vernau-reels/out/new/, in this order, one
# per reel slot (Tue/Thu/Sat 12:15). thumb = cover frame in ms.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="$HOME/Projects/vernau-reels/out/new"
while read -r file thumb; do
  [ -z "$file" ] && continue
  python3 tools/enqueue.py reel "$OUT/$file.mp4" --caption "captions/$file.txt" --thumb-ms "$thumb" "$@"
done <<'LIST'
three-tabs 1600
50ms 6800
the-teardown 1600
3-seconds 6800
prism 8700
first-screen 6000
steps-to-book 1600
in-the-shadow 2600
54-of-100 9000
impressum 1600
LIST
