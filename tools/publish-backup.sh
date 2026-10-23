#!/usr/bin/env bash
# Local backup for the GitHub "publish" cron (GitHub's schedule can be late or skip on new repos).
# Runs from the systemd user timer vernau-publish-backup every 15 min: if a queued post is 10+ min
# overdue and no publish run is active, it triggers the workflow. Needs `gh` logged in; no Claude.
set -euo pipefail
cd "$(dirname "$0")/.."
git pull -q --rebase --autostash || true
DUE=$(python3 -I -c '
import json, glob, datetime
n = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=10)
print(sum(1 for f in glob.glob("queue/*.json") for i in [json.load(open(f))]
          if i["status"] == "queued" and datetime.datetime.fromisoformat(i["publish_at"]) <= n))')
[ "$DUE" -gt 0 ] || exit 0
ACTIVE=$(gh run list -w publish -L 5 --json status -q '[.[] | select(.status != "completed")] | length')
[ "$ACTIVE" -eq 0 ] || { echo "publish run already active"; exit 0; }
echo "[$(date '+%F %T')] $DUE post(s) overdue, triggering publish"
gh workflow run publish
