"""A small client for Instagram content publishing (Instagram API with Instagram Login).

Docs: https://developers.facebook.com/docs/instagram-platform/content-publishing
Media must sit at a public URL when the container is created: Meta fetches it.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

HOST = "https://graph.instagram.com"
VERSION = "v25.0"


class IGError(RuntimeError):
    pass


class Instagram:
    def __init__(self, user_id: str, token: str, version: str = VERSION):
        self.user_id = user_id
        self.token = token
        self.base = f"{HOST}/{version}"

    def _call(self, method: str, path: str, params: dict) -> dict:
        params = {**params, "access_token": self.token}
        data = urllib.parse.urlencode(params).encode()
        url = f"{self.base}/{path}"
        if method == "GET":
            req = urllib.request.Request(f"{url}?{data.decode()}")
        else:
            req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            raise IGError(f"{method} {path} → HTTP {e.code}: {body[:500]}") from None

    # --- containers
    def image(self, url: str, caption: str | None = None, carousel_item: bool = False) -> str:
        p = {"image_url": url}
        if caption is not None:
            p["caption"] = caption
        if carousel_item:
            p["is_carousel_item"] = "true"
        return self._call("POST", f"{self.user_id}/media", p)["id"]

    def reel(self, url: str, caption: str, thumb_offset_ms: int | None = None) -> str:
        p = {"media_type": "REELS", "video_url": url, "caption": caption, "share_to_feed": "true"}
        if thumb_offset_ms is not None:
            p["thumb_offset"] = str(thumb_offset_ms)
        return self._call("POST", f"{self.user_id}/media", p)["id"]

    def carousel(self, children: list[str], caption: str) -> str:
        return self._call("POST", f"{self.user_id}/media", {"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption})["id"]

    def wait(self, container: str, timeout: int = 600, every: int = 15) -> None:
        """Poll a container until it's FINISHED (videos take a while to process)."""
        t0 = time.time()
        while True:
            s = self._call("GET", container, {"fields": "status_code,status"})
            code = s.get("status_code")
            if code == "FINISHED":
                return
            if code in ("ERROR", "EXPIRED"):
                raise IGError(f"container {container} {code}: {s.get('status')}")
            if time.time() - t0 > timeout:
                raise IGError(f"container {container} still {code} after {timeout}s")
            time.sleep(every)

    def publish(self, container: str) -> str:
        return self._call("POST", f"{self.user_id}/media_publish", {"creation_id": container})["id"]

    def permalink(self, media_id: str) -> str | None:
        try:
            return self._call("GET", media_id, {"fields": "permalink"}).get("permalink")
        except IGError:
            return None

    def limit(self) -> dict:
        return self._call("GET", f"{self.user_id}/content_publishing_limit", {"fields": "quota_usage,config"})
