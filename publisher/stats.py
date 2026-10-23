"""Pull Instagram insights for every post on the account into stats/insights.json.

Runs daily in GitHub Actions (stats.yml). The daily reel maker reads the file to
learn which hooks, topics and formats work. Needs instagram_business_manage_insights.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ig import IGError, Instagram  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "stats" / "insights.json"
REEL_METRICS = ["reach", "views", "saved", "shares", "comments", "likes", "total_interactions", "ig_reels_avg_watch_time", "ig_reels_video_view_total_time"]
FEED_METRICS = ["reach", "views", "saved", "shares", "comments", "likes", "total_interactions"]


def insights(ig: Instagram, media_id: str, metrics: list[str]) -> dict:
    """Ask for all metrics at once; if Meta rejects one, fall back to one by one."""
    def ask(ms: list[str]) -> dict:
        r = ig._call("GET", f"{media_id}/insights", {"metric": ",".join(ms)})
        return {d["name"]: (d.get("values") or [{}])[0].get("value", d.get("total_value", {}).get("value")) for d in r.get("data", [])}

    try:
        return ask(metrics)
    except IGError:
        out = {}
        for m in metrics:
            try:
                out.update(ask([m]))
            except IGError:
                pass
        return out


def main() -> int:
    ig = Instagram(os.environ["IG_USER_ID"], os.environ["IG_TOKEN"])
    acct = ig._call("GET", "me", {"fields": "username,followers_count,media_count"})
    media, after = [], None
    while True:
        p = {"fields": "id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count", "limit": "50"}
        if after:
            p["after"] = after
        r = ig._call("GET", "me/media", p)
        media += r.get("data", [])
        after = r.get("paging", {}).get("cursors", {}).get("after") if r.get("paging", {}).get("next") else None
        if not after or len(media) >= 200:
            break

    # queue files link our slug to the Instagram media id
    slug_by_id = {}
    for q in (ROOT / "queue").glob("*.json"):
        item = json.loads(q.read_text())
        if item.get("ig_media_id"):
            slug_by_id[str(item["ig_media_id"])] = item.get("id", q.stem)

    posts = []
    for m in media:
        reel = m.get("media_product_type") == "REELS"
        posts.append({
            "media_id": m["id"],
            "slug": slug_by_id.get(m["id"]),
            "type": "reel" if reel else m.get("media_type", "").lower(),
            "posted": m.get("timestamp"),
            "permalink": m.get("permalink"),
            "hook": (m.get("caption") or "").split("\n")[0][:140],
            **insights(ig, m["id"], REEL_METRICS if reel else FEED_METRICS),
        })

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({
        "pulled": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "account": {k: acct.get(k) for k in ("username", "followers_count", "media_count")},
        "posts": posts,
    }, indent=2) + "\n")
    print(f"{len(posts)} posts, {acct.get('followers_count')} followers → {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
