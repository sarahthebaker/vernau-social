"""Publish every queued post whose time has come. Runs on GitHub Actions.

Environment:
  IG_USER_ID, IG_TOKEN   Instagram professional account id and long-lived token (GitHub Secrets)
  PAGES_BASE             public base URL of this repo on GitHub Pages, e.g. https://you.github.io/vernau-social
  DRY_RUN=1              log what would happen, publish nothing (also the default when the secrets are missing)

Exit code 1 if anything failed, so GitHub emails the repo owner.
"""

from __future__ import annotations

import os
import shutil
import sys
import urllib.request
from datetime import datetime, timedelta

from common import MEDIA, ROOT, SCHEDULE, load_all, now, save
from ig import IGError, Instagram


class Uncertain(RuntimeError):
    """The publish call itself failed: the post may be live. Never retried automatically."""


def public_url(rel: str) -> str:
    return f"{os.environ['PAGES_BASE'].rstrip('/')}/{rel}"


def reachable(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200
    except Exception:
        return False


def publish_one(ig: Instagram, item: dict) -> str:
    urls = [public_url(m) for m in item["media"]]
    kind = item["type"]
    if kind == "reel":
        c = ig.reel(urls[0], item["caption"], item.get("thumb_offset_ms"))
        ig.wait(c, timeout=900, every=20)
    elif kind == "single":
        c = ig.image(urls[0], item["caption"])
        ig.wait(c, timeout=180, every=5)
    elif kind == "carousel":
        if not 2 <= len(urls) <= 10:
            raise IGError(f"carousel needs 2–10 images, has {len(urls)}")
        children = [ig.image(u, carousel_item=True) for u in urls]
        for ch in children:  # never publish a partial carousel
            ig.wait(ch, timeout=180, every=5)
        c = ig.carousel(children, item["caption"])
        ig.wait(c, timeout=300, every=5)
    else:
        raise IGError(f"unknown type {kind}")
    try:
        return ig.publish(c)
    except Exception as e:  # noqa: BLE001
        raise Uncertain(f"publish call failed, check Instagram before retrying: {e}") from None


def prune(items: list[dict]) -> None:
    """Media of posts published a few days ago no longer needs a public URL."""
    cutoff = now() - timedelta(days=SCHEDULE["prune_media_after_days"])
    for it in items:
        if it["status"] == "published" and it.get("published_at") and datetime.fromisoformat(it["published_at"]) < cutoff:
            d = MEDIA / it["id"]
            if d.exists():
                shutil.rmtree(d)
                print(f"pruned media of {it['id']}")


def main() -> int:
    user, token = os.environ.get("IG_USER_ID"), os.environ.get("IG_TOKEN")
    dry = os.environ.get("DRY_RUN") == "1" or not (user and token)
    if "PAGES_BASE" not in os.environ:
        print("PAGES_BASE is not set")
        return 1
    ig = None if dry else Instagram(user, token)
    t = now()
    items = load_all()
    due = [i for i in items if i["status"] == "queued" and datetime.fromisoformat(i["publish_at"]) <= t]
    print(f"{t:%Y-%m-%d %H:%M %Z} · {len(due)} due · {'DRY RUN' if dry else 'LIVE'}")
    failed = False
    for it in due:
        missing = [m for m in it["media"] if not (ROOT / m).exists()]
        if missing:
            it.update(status="failed", error=f"missing files: {missing}")
            save(it)
            failed = True
            print(f"✗ {it['id']}: {it['error']}")
            continue
        urls = [public_url(m) for m in it["media"]]
        if not all(reachable(u) for u in urls):
            print(f"… {it['id']}: media not live on Pages yet, will retry next run")
            continue
        if dry:
            print(f"[dry] would publish {it['type']} {it['id']} ({len(urls)} file(s)) — {it['caption'][:60]!r}")
            continue
        try:
            media_id = publish_one(ig, it)
            it.update(status="published", published_at=now().isoformat(timespec="seconds"), ig_media_id=media_id, permalink=ig.permalink(media_id), error=None)
            print(f"✓ {it['id']} → {it['permalink'] or media_id}")
        except Exception as e:  # noqa: BLE001 — record any failure on the item
            it["attempts"] = it.get("attempts", 0) + 1
            it["error"] = str(e)[:800]
            if isinstance(e, Uncertain) or it["attempts"] >= SCHEDULE["max_attempts"]:
                it["status"] = "failed"
            failed = True
            print(f"✗ {it['id']} (attempt {it['attempts']}): {e}")
        save(it)
    if not dry:
        prune(items)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
