"""Refresh the long-lived Instagram token (valid 60 days from each refresh).

Prints the new token to $GITHUB_OUTPUT as `token` (masked in logs); the
workflow then stores it back into the IG_TOKEN secret.
Docs: https://developers.facebook.com/docs/instagram-platform/reference/refresh_access_token
"""

import json
import os
import sys
import urllib.parse
import urllib.request

token = os.environ["IG_TOKEN"]
q = urllib.parse.urlencode({"grant_type": "ig_refresh_token", "access_token": token})
with urllib.request.urlopen(f"https://graph.instagram.com/refresh_access_token?{q}", timeout=60) as r:
    data = json.loads(r.read())
new = data["access_token"]
print(f"::add-mask::{new}")
print(f"refreshed; expires in {int(data['expires_in']) // 86400} days")
out = os.environ.get("GITHUB_OUTPUT")
if out:
    with open(out, "a") as f:
        f.write(f"token={new}\n")
sys.exit(0)
