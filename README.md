# Hugging Face Daily Papers Archive

This project fetches Hugging Face Daily Papers, stores the raw and generated data locally, asks an OpenAI-compatible model for a Chinese one-sentence summary plus two tags, and builds a static website.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Edit `.env`:

```text
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-key
OPENAI_MODEL=your-model
```

Any OpenAI-compatible endpoint can be used as long as it supports chat completions and JSON output.

## Daily Workflow

Fetch one date:

```powershell
python -m hf_daily fetch --date 2026-05-28
```

Generate summaries and tags:

```powershell
python -m hf_daily generate --date 2026-05-28
```

Build the static site:

```powershell
python -m hf_daily build
```

Or run everything:

```powershell
python -m hf_daily run --date 2026-05-28
```

Open `site/index.html` in your browser after building.

To edit incorrect institution or topic tags from the browser, start the local admin site:

```powershell
python -m hf_daily admin
```

Open the printed local URL, click `Edit tags` on a paper card, update the tags, and click `Save draft`. In admin mode the save is written to `data/tags/tag_overrides.json` and the site is rebuilt automatically. The original `data/daily/*.json` files are not rewritten.

## Local Data

- `data/raw/YYYY-MM-DD.json`: raw Hugging Face API response.
- `data/daily/YYYY-MM-DD.json`: normalized papers with generated summaries and tags.
- `data/tags/topics.json`: local medium-granularity topic tag library.
- `data/tags/institutions.json`: local institution tag library.
- `data/tags/topic_aliases.json`: reviewed topic tag merge aliases.
- `data/tags/institution_aliases.json`: reviewed institution tag merge aliases.
- `data/tags/tag_overrides.json`: manual per-paper institution/topic tag corrections.
- `site/`: generated static website.

Each paper gets exactly two final tags:

- `institution_tag`: from Hugging Face `organization` when present, otherwise conservatively inferred by the model.
- `topic_tag`: English, medium-granularity method/research-direction tag. Existing local topic tags are reused when close enough.

## Static Site

The homepage defaults to the latest generated date with papers. Use the `Year`, `Month`, and `Day` selectors in `Date Archive` to switch the paper cards in place without opening another page. The selectors only expose dates that have at least one paper; empty weekend dates are ignored during site build.

Institution and topic tag filters search across all generated dates, not just the currently selected date. Clearing filters returns the homepage to the selected date view.

Daily pages are still generated under `site/daily/YYYY-MM-DD.html` as standalone archive pages.

## Windows Task Scheduler Example

Create a daily task that runs from this project directory:

```powershell
$Action = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"cd D:\Github\huggingface_daily; .\.venv\Scripts\Activate.ps1; python -m hf_daily run`""

$Trigger = New-ScheduledTaskTrigger -Daily -At 9:00AM

Register-ScheduledTask `
  -TaskName "HuggingFaceDailyPapers" `
  -Action $Action `
  -Trigger $Trigger `
  -Description "Fetch Hugging Face daily papers and rebuild the static archive."
```

The default date uses the local Asia/Shanghai date. Pass `--date YYYY-MM-DD` if you want a fixed date.

## GitHub Actions Example

Save this as `.github/workflows/daily.yml` if you want automated generation in GitHub:

```yaml
name: Daily Hugging Face Papers

on:
  schedule:
    - cron: "0 1 * * *"
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install -e .
      - run: python -m hf_daily run
        env:
          OPENAI_BASE_URL: ${{ secrets.OPENAI_BASE_URL }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          OPENAI_MODEL: ${{ secrets.OPENAI_MODEL }}
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site
```

## Testing

```powershell
python -m pytest -q
```
