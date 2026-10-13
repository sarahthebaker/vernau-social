#!/usr/bin/env python3
"""Add a post or a reel to the publishing queue, in the next free slot.

  enqueue.py post "<post folder>"                    carousel (2+ slides) or single (1 slide)
  enqueue.py reel <video.mp4> --caption <file.txt> [--thumb-ms 6000]
  options: --at "2026-10-20 12:15"  (fixed time, Europe/Zurich)   --no-push   --dry

A post folder is what ~/Projects/vernau-instagram makes: slide-*.png + caption.txt.
Slides are converted to JPEG (the Instagram API takes JPEG only). The queue entry
and media are committed and pushed; GitHub Actions publishes them on time.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "publisher"))
from common import MEDIA, ROOT, SCHEDULE, TZ, load_all, next_slot, now, save  # noqa: E402


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def git(*args: str) -> None:
    subprocess.run(["git", "-C", str(ROOT), *args], check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["post", "reel"])
    ap.add_argument("path")
    ap.add_argument("--caption")
    ap.add_argument("--thumb-ms", type=int)
    ap.add_argument("--at")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    src = Path(a.path).expanduser().resolve()
    items = load_all()
    taken = {i["publish_at"] for i in items if i["status"] != "failed"}

    if a.kind == "post":
        slides = sorted(src.glob("slide-*.png")) or sorted(src.glob("slide-*.jpg"))
        if not slides:
            print(f"no slides in {src}")
            return 1
        kind = "carousel" if len(slides) > 1 else "single"
        caption = (src / "caption.txt").read_text().strip()
        base = slug(src.name.replace(" - ", "-"))
    else:
        if not a.caption:
            print("--caption is required for a reel")
            return 1
        kind = "reel"
        caption = Path(a.caption).expanduser().read_text().strip()
        base = f"reel-{slug(src.stem)}"

    if len(caption) > 2200:
        print(f"caption is {len(caption)} characters; Instagram allows 2,200")
        return 1
    if caption.count("#") > 30:
        print("more than 30 hashtags")
        return 1
    sources = {i.get("source") for i in items if i["status"] != "failed"}
    if str(src) in sources:
        print(f"already queued: {src}")
        return 0

    if a.at:
        when = datetime.strptime(a.at, "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
    else:
        when = next_slot(kind, taken, now() + timedelta(hours=SCHEDULE["min_lead_hours"]))
    pid = f"{when:%Y-%m-%d-%H%M}-{base}"[:80]

    if a.dry:
        print(f"[dry] {kind} {pid} at {when:%a %d %b %H:%M}")
        return 0

    out = MEDIA / pid
    out.mkdir(parents=True, exist_ok=True)
    media: list[str] = []
    if kind == "reel":
        dst = out / "reel.mp4"
        shutil.copy2(src, dst)
        media.append(str(dst.relative_to(ROOT)))
    else:
        for i, s in enumerate(slides, 1):
            dst = out / f"{i:02d}.jpg"
            subprocess.run(["magick", str(s), "-background", "#1F1F1F", "-flatten", "-quality", "92", "-strip", str(dst)], check=True)
            media.append(str(dst.relative_to(ROOT)))

    item = {
        "id": pid,
        "type": kind,
        "caption": caption,
        "media": media,
        "publish_at": when.isoformat(),
        "status": "queued",
        "attempts": 0,
        "error": None,
        "published_at": None,
        "ig_media_id": None,
        "permalink": None,
        "source": str(src),
    }
    if a.thumb_ms is not None:
        item["thumb_offset_ms"] = a.thumb_ms
    save(item)
    print(f"queued {kind} {pid} for {when:%a %d %b %H:%M}")

    git("add", "queue", "media")
    git("commit", "-q", "-m", f"queue: {pid}")
    if not a.no_push:
        try:
            git("push", "-q")
        except subprocess.CalledProcessError:
            print("push failed; it will go out with the next push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
