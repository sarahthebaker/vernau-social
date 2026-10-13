# Setup: about 20 minutes, once

You need the @vernau.ch login, a Facebook account (for Meta's developer site)
and a GitHub account.

## 1. GitHub (terminal)

```bash
gh auth login          # GitHub.com → HTTPS → log in with a browser
gh auth setup-git
~/Projects/vernau-social/tools/setup-github.sh
```

`setup-github.sh` does four things:
1. Creates the **public** repo `vernau-social`.
2. Pushes the repo to it.
3. Turns on GitHub Pages.
4. Sets `PAGES_BASE`.

The repo is public so it can serve images and videos to Instagram for free.
Upcoming posts are visible there about a day early.

## 2. Instagram account

In the Instagram app on @vernau.ch: **Settings → Account type and tools → Switch
to professional account** (Business). Skip this if it's already professional.

## 3. Meta app and token

1. Go to <https://developers.facebook.com/apps> → **Create app**.
   - Use case: **Manage messaging & content on Instagram**.
   - Name: `Vernau Publisher`.
2. In the app, open **Instagram → API setup with Instagram login**.
3. Under **Generate access tokens**, click **Add account** and log in as **@vernau.ch**.
4. Copy two things from that page:
   - the **Instagram user ID**, a number
   - the **access token**, which is long-lived and valid for 60 days
5. The app can stay in development mode. It only posts to your own account,
   which has a role on the app, so no App Review is needed.

## 4. Secrets in GitHub (terminal)

```bash
cd ~/Projects/vernau-social
gh secret set IG_USER_ID      # paste the number
gh secret set IG_TOKEN        # paste the token
```

To let the weekly job store refreshed tokens, create a fine-grained token:
1. Go to <https://github.com/settings/personal-access-tokens/new>.
2. Repository access: **only vernau-social**.
3. Permissions: **Secrets → Read and write**.
4. Then run:

```bash
gh secret set GH_PAT          # paste the token
```

## 5. Test

```bash
gh workflow run publish -f dry_run=true && sleep 60 && gh run view --log | tail -20
gh workflow run refresh-token                      # needs the token to be at least 24 h old
```

The dry run lists what it *would* publish.

After that, posts go out by themselves. To start with the reels:

```bash
tools/queue-reels.sh
```

## Stop everything

```bash
gh variable set DRY_RUN --body 1     # publish nothing (runs only log)
gh variable delete DRY_RUN           # back on
```

Or disable the `publish` workflow in the repo's **Actions** tab.
