#!/usr/bin/env python3
"""See and steer the queue.

  posts.py                 list upcoming and recent posts
  posts.py hold <id>       keep a post from publishing (until released)
  posts.py release <id>    put a held or failed post back in the queue
  posts.py move <id> "2026-10-20 12:15"
  posts.py drop <id>       remove a post that hasn't been published
Changes are committed and pushed (pass --no-push to skip the push).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "publisher"))
from common import MEDIA, QUEUE, ROOT, TZ, load_all, save  # noqa: E402

ICON = {"queued": "·", "hold": "‖", "published": "✓", "failed": "✗"}


def find(pid: str) -> dict:
    hits = [i for i in load_all() if i["id"] == pid or i["id"].startswith(pid) or pid in i["id"]]
    if len(hits) != 1:
        sys.exit(f"{len(hits)} posts match {pid!r}")
    return hits[0]


def commit(msg: str, push: bool) -> None:
    subprocess.run(["git", "-C", str(ROOT), "add", "-A", "queue", "media"], check=True)
    subprocess.run(["git", "-C", str(ROOT), "commit", "-q", "-m", msg], check=True)
    if push:
        subprocess.run(["git", "-C", str(ROOT), "push", "-q"], check=False)


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--no-push"]
    push = "--no-push" not in sys.argv
    if args and args[0] != "list":
        subprocess.run(["git", "-C", str(ROOT), "pull", "-q", "--rebase", "--autostash"], check=False)
    if not args or args[0] == "list":
        for i in load_all():
            t = datetime.fromisoformat(i["publish_at"]).astimezone(TZ)
            extra = i.get("permalink") or i.get("error") or ""
            print(f"{ICON.get(i['status'], '?')} {t:%a %d %b %H:%M}  {i['type']:<8} {i['id']}  {extra}")
        return
    cmd, pid = args[0], args[1]
    it = find(pid)
    if it["status"] == "published" and cmd != "list":
        sys.exit("already published")
    if cmd == "hold":
        it["status"] = "hold"
    elif cmd == "release":
        it.update(status="queued", attempts=0, error=None)
    elif cmd == "move":
        it["publish_at"] = datetime.strptime(args[2], "%Y-%m-%d %H:%M").replace(tzinfo=TZ).isoformat()
    elif cmd == "drop":
        (QUEUE / f"{it['id']}.json").unlink()
        shutil.rmtree(MEDIA / it["id"], ignore_errors=True)
        commit(f"queue: drop {it['id']}", push)
        print(f"dropped {it['id']}")
        return
    else:
        sys.exit(__doc__)
    save(it)
    commit(f"queue: {cmd} {it['id']}", push)
    print(f"{cmd}: {it['id']} ({it['status']}, {it['publish_at']})")


if __name__ == "__main__":
    main()
