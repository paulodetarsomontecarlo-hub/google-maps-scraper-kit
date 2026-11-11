# Run the scraper on GitHub Actions

For people who want a lead list without installing anything: the scrape runs on GitHub's machines and
you download the CSV from the browser. The workflow is `.github/workflows/scrape.yml`.

> **Use a private repository.** The file holds phones and emails, and artifacts of a public
> repository can be downloaded by anyone signed in to GitHub. The run log prints counts only.

## Steps

1. Fork or copy the kit into a **private** repository and make sure Actions is enabled (repo **Settings > Actions**).
2. Open **Actions > scrape > Run workflow**.
3. Fill in the form:

| Field | Example | Notes |
|---|---|---|
| keyword | `dentistas em Curitiba` | Required. |
| city | `Curitiba, PR` | Optional: centres the map. Blank uses the place in the keyword. |
| depth | `2` | About 20 places per step; Google stops near 120 per search. |
| lang / country | `pt` / `br` | GitHub's machines are in the US, so set the country you want results for. |
| emails / socials | on | Turn off for a faster run. |
| extra_args | `--no-website --min-rating 4` | Any `scrape.py` flag, separated by spaces (no quoted values). |
| max_time | `600` | Seconds. Raise it for `--grid`, `--reviews` or high depth. |
| format | `csv` | Or `json`. |
| retention_days | `7` | How long GitHub keeps the file. |

4. When the run turns green, open it and download `leads-<run id>` under **Artifacts** (a zip with the CSV).

## Limits

- GitHub's runners share data-centre IPs, so Google may rate-limit them sooner than a home connection.
  Keep depth modest, or pass a proxy in `extra_args` (`--proxy http://user:pass@host:port`; the value
  appears in the run's inputs, so prefer a proxy without a password or a private repository you alone can read).
- Runs queue one at a time, and a run stops after 120 minutes.
- Free Actions minutes on private repositories are limited per month; see your GitHub plan.
