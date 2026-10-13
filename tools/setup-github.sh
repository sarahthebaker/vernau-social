#!/usr/bin/env bash
# One-time: create the public GitHub repo, push, turn on GitHub Pages (which
# serves the media at public URLs for Instagram), and set PAGES_BASE.
# Needs: gh auth login (and gh auth setup-git) done first.
set -euo pipefail
cd "$(dirname "$0")/.."
owner=$(gh api user -q .login)
gh repo view "$owner/vernau-social" >/dev/null 2>&1 || gh repo create vernau-social --public --source . --push --description "Scheduled posts for @vernau.ch"
git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/$owner/vernau-social.git"
git push -u origin main
gh api -X POST "repos/$owner/vernau-social/pages" -f "source[branch]=main" -f "source[path]=/" >/dev/null 2>&1 || echo "(Pages already on)"
gh variable set PAGES_BASE --repo "$owner/vernau-social" --body "https://$owner.github.io/vernau-social"
echo "Repo: https://github.com/$owner/vernau-social"
echo "Media base: https://$owner.github.io/vernau-social"
