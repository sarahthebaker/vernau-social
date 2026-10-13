# vernau-social: posts @vernau.ch automatically, free

```
vernau-instagram (laptop, 09:00 + 18:00)    vernau-reels (Remotion)
        makes a carousel / single                renders reels
                 │                                    │
                 └──── tools/enqueue.py ──────────────┘
                         next free slot, ≥ 12 h ahead
                         slides → JPEG, commit + push
                                 │
                         GitHub (this repo, public)
                         ├─ GitHub Pages serves media/ at public URLs
                         └─ Actions, every 15 min: publisher/publish.py
                                 │  Instagram API (Instagram Login)
                                 ▼
                              @vernau.ch
```

Everything here is free: GitHub Actions and Pages on a public repo, and
Instagram's own publishing API. Nothing to install on the laptop beyond `gh`.

## Schedule (`schedule.json`, Europe/Zurich)

| Kind | When |
|---|---|
| Carousel | every day 08:30 |
| Single image | every day 18:30 |
| Reel | Tue, Thu, Sat 12:15 |

- Each new post takes the next free slot at least 12 hours ahead, so there's
  always a window to stop it.
- Actions runs every 15 minutes, so a post goes out up to about 20 minutes after
  its slot. GitHub's cron can lag at busy times.
- A post more than 6 hours late is marked `missed`, not published. Old posts
  never go out in a burst.

## Day to day

```bash
cd ~/Projects/vernau-social
tools/posts.py                       # what's queued, published, failed
tools/posts.py hold <id>             # stop one going out (any part of the id works)
tools/posts.py release <id>          # put it back
tools/posts.py move <id> "2026-10-20 12:15"
tools/posts.py drop <id>
tools/enqueue.py post "<post folder>"                  # queue a carousel/single by hand
tools/enqueue.py reel <file.mp4> --caption <file.txt>  # queue a reel by hand
tools/queue-reels.sh                 # queue the prism reels from vernau-reels/out/new
```

- **New posts:** the 09:00/18:00 posts from `~/Projects/vernau-instagram` are
  queued automatically once this repo is on GitHub. To turn that off, run
  `AUTO_PUBLISH=0` with run.sh.
- **Captions:** reel captions are in `captions/`.
- **Results:** published posts get their permalink in `queue/<id>.json`.
- **Failures:** when a post fails, the run fails, and GitHub emails you.

## Safety

- **Partial carousels:** a carousel is published only when every slide
  container has finished processing.
- **Uncertain publishes:** if the final publish call errors, the post is marked
  `failed`, never retried. It may already be live, so check Instagram first.
- **Retries:** other errors are retried up to 3 times, then marked `failed`.
- **Pruned media:** media of published posts is deleted from the site after 3
  days.
- **Token refresh:** the token is refreshed every Monday. Each refresh gives
  another 60 days.

Setup: see [SETUP.md](SETUP.md).
