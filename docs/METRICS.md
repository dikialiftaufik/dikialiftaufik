# How the profile metrics are computed

The activity card on the profile is generated daily by [`metrics.yml`](../.github/workflows/metrics.yml)
from GitHub API data. The code lives in [`scripts/metrics`](../scripts/metrics) and is covered by unit tests.
Nothing on the card is typed by hand.

## Metrics

| Metric | Definition |
| --- | --- |
| **Public repositories** | Non-fork repositories owned by the account, minus those listed in `metrics.config.json`. |
| **Programming languages** | Languages with at least 1,000 bytes of code across eligible repositories. |
| **Repos updated, last 90 days** | Eligible repositories with a push in the last 90 days. |
| **Consecutive active weeks** | Weeks (Mon–Sun) in a row, ending now, with at least one contribution. An empty current week is not counted against the streak. |
| **Most-used languages** | Share of code bytes per language, top 6 plus "Other". Reflects volume of code, **not proficiency**. |
| **Contributions per week** | Sum of the GitHub contribution calendar per ISO week over the last 52 weeks. |
| **Language timeline** | Creation date of the earliest eligible repository containing each language. An approximation of when a language was first used. |

## Exclusions (and why)

- **Forks** are ignored: the code is not mine.
- **HTML, CSS, Jupyter Notebook, CMake, Makefile, Dockerfile** are ignored in language statistics; markup, notebook
  outputs and build files inflate byte counts without reflecting programming effort.
- **Flutter scaffolding** (C++, Swift, Kotlin, Objective-C, Ruby, C) is ignored in repositories that contain Dart,
  because `flutter create` generates these platform folders.
- **Repositories in `metrics.config.json`** (e.g. a repo containing a large generated test report) are skipped.

## Privacy

- Only aggregates are published (counts, percentages, dates). Repository names never appear in the output.
- By default only public data is used. If the optional `METRICS_TOKEN` secret (a fine-grained, read-only token) is
  configured, private repositories are included **in aggregates only**.

## Time zone and freshness

The card is regenerated daily at 03:17 UTC and force-pushed as a single commit to the `metrics` branch, so the
branch never accumulates history. If a run fails, the previous images stay in place.

## Run locally

```powershell
pip install pytest ruff
ruff check .; pytest
$env:PYTHONPATH = "scripts"; $env:GITHUB_TOKEN = "<optional token>"
python -m metrics --user dikialiftaufik --out dist
```

Without a token the contribution calendar is skipped and the card degrades gracefully.
