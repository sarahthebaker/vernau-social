"""Shared bits: paths, the schedule, the queue files."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "queue"
MEDIA = ROOT / "media"
SCHEDULE = json.loads((ROOT / "schedule.json").read_text())
TZ = ZoneInfo(SCHEDULE["timezone"])
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Queue item (queue/<id>.json):
# {
#   "id": "2026-10-14-reel-50ms",
#   "type": "reel" | "carousel" | "single",
#   "caption": "...",
#   "media": ["media/<id>/video.mp4"]          # paths in this repo, served by GitHub Pages
#   "publish_at": "2026-10-14T12:15:00+02:00",
#   "status": "queued" | "hold" | "published" | "failed",
#   "thumb_offset_ms": 6000,                   # reels only, optional
#   "attempts": 0, "error": null,
#   "published_at": null, "ig_media_id": null, "permalink": null,
#   "source": "where it came from"
# }


def now() -> datetime:
    return datetime.now(TZ)


def load_all() -> list[dict]:
    items = [json.loads(p.read_text()) for p in sorted(QUEUE.glob("*.json"))]
    return sorted(items, key=lambda i: i["publish_at"])


def save(item: dict) -> None:
    (QUEUE / f"{item['id']}.json").write_text(json.dumps(item, indent=2, ensure_ascii=False) + "\n")


def next_slot(kind: str, taken: set[str], after: datetime) -> datetime:
    """First slot for this kind of post after `after` that nothing else holds."""
    slot = SCHEDULE["slots"][kind]
    hh, mm = (int(x) for x in slot["time"].split(":"))
    day = after.astimezone(TZ).date()
    for _ in range(400):
        if DAYS[day.weekday()] in slot["days"]:
            t = datetime(day.year, day.month, day.day, hh, mm, tzinfo=TZ)
            if t > after and t.isoformat() not in taken:
                return t
        day += timedelta(days=1)
    raise RuntimeError(f"no free {kind} slot found")
