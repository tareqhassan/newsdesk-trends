# Google Trends export runner

Daily GitHub Actions job that opens Google Trends "Trending now" (United States,
past 7 days), clicks **Export → Download CSV**, and commits the raw file for
Magnetic Newsdesk to pull.

## Output

| File | Contents |
|---|---|
| `trends/US/latest.csv` | Google's CSV, unchanged. Only replaced when a run succeeds. |
| `trends/US/meta.json` | `status` (`ok`/`failed`), `fetched_at` (last success, UTC), `last_attempt_at`, `row_count`, `columns`, `error` |

Raw links the app reads (replace `OWNER`/`REPO`):

```
https://raw.githubusercontent.com/OWNER/REPO/main/trends/US/latest.csv
https://raw.githubusercontent.com/OWNER/REPO/main/trends/US/meta.json
```

## Setup

1. Create a new **public** repository on GitHub (e.g. `newsdesk-trends`), with no template files.
2. Upload everything in this folder to the repository root, keeping the
   `.github/workflows/trends.yml` path intact.
3. Repository **Settings → Actions → General → Workflow permissions**: select
   **Read and write permissions** and save.
4. **Actions** tab → **Export Google Trends** → **Run workflow** to trigger the first run.
5. When it finishes green, open `trends/US/meta.json` in the repository and confirm
   `status` is `ok` and `row_count` is around 1,900.

## Schedule and failures

- Runs daily at 05:00 UTC (GitHub may start scheduled runs several minutes late).
- Each run retries up to 3 times. On failure the previous `latest.csv` is kept,
  `meta.json` is marked `failed`, the run turns red (GitHub emails the repository
  owner), and page screenshots are attached to the run under **Artifacts** for debugging.
- GitHub disables scheduled workflows in public repositories after 60 days without
  repository activity. The daily commits count as activity, but if the workflow is
  ever disabled, re-enable it from the **Actions** tab.

## Settings

Optional environment variables in the workflow's export step:

| Variable | Default | Meaning |
|---|---|---|
| `TRENDS_GEO` | `US` | Country code |
| `TRENDS_HOURS` | `168` | Time window (168 = past 7 days) |
| `TRENDS_MIN_ROWS` | `100` | Fewer rows than this counts as a failed export |
