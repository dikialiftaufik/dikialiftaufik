"""Pure metric computations. No I/O, no network: everything is unit-testable."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

# Markup, notebooks and build files inflate byte counts without reflecting
# programming effort, so they are excluded from language statistics.
EXCLUDED_LANGUAGES = frozenset({"HTML", "CSS", "Jupyter Notebook", "CMake", "Makefile", "Dockerfile"})
MIN_LANGUAGE_BYTES = 1_000  # ignore trivial usage when counting languages

# `flutter create` generates native platform folders; their languages are
# scaffolding rather than hand-written code, so they are ignored in Dart repos.
FLUTTER_SCAFFOLD = frozenset({"C++", "Swift", "Kotlin", "Objective-C", "Ruby", "C"})

Repo = dict[str, Any]


def _parse_date(value: str) -> date:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def _eligible(repos: list[Repo], skip: frozenset[str]) -> list[Repo]:
    return [r for r in repos if not r.get("fork") and r["name"] not in skip]


def _repo_languages(repo: Repo, excluded: frozenset[str] = EXCLUDED_LANGUAGES) -> dict[str, int]:
    """Language bytes for one repo after removing noise and generated scaffolding."""
    langs = repo.get("languages", {})
    drop = excluded | (FLUTTER_SCAFFOLD if "Dart" in langs else frozenset())
    return {lang: size for lang, size in langs.items() if lang not in drop}


def language_totals(
    repos: list[Repo],
    skip: frozenset[str] = frozenset(),
    excluded: frozenset[str] = EXCLUDED_LANGUAGES,
) -> dict[str, int]:
    """Sum code bytes per language across non-fork repos."""
    totals: dict[str, int] = {}
    for repo in _eligible(repos, skip):
        for lang, size in _repo_languages(repo, excluded).items():
            totals[lang] = totals.get(lang, 0) + size
    return totals


def language_mix(repos: list[Repo], top_n: int = 6, skip: frozenset[str] = frozenset()) -> list[tuple[str, float]]:
    """Top languages as (name, percent), remainder folded into 'Other'."""
    totals = language_totals(repos, skip)
    grand = sum(totals.values())
    if grand == 0:
        return []
    ranked = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    mix = [(name, size / grand * 100) for name, size in ranked[:top_n]]
    rest = sum(size for _, size in ranked[top_n:])
    if rest:
        mix.append(("Other", rest / grand * 100))
    return mix


def polyglot_count(repos: list[Repo], skip: frozenset[str] = frozenset()) -> int:
    """Number of languages with a meaningful amount of code."""
    totals = language_totals(repos, skip)
    return sum(1 for size in totals.values() if size >= MIN_LANGUAGE_BYTES)


def adoption_timeline(repos: list[Repo], skip: frozenset[str] = frozenset()) -> list[tuple[str, date]]:
    """When each language first appeared in a repo (by repo creation date)."""
    first: dict[str, date] = {}
    for repo in _eligible(repos, skip):
        created = _parse_date(repo["created_at"])
        for lang, size in _repo_languages(repo).items():
            if size < MIN_LANGUAGE_BYTES:
                continue
            if lang not in first or created < first[lang]:
                first[lang] = created
    return sorted(first.items(), key=lambda kv: (kv[1], kv[0]))


def weekly_cadence(days: list[dict[str, Any]], today: date, weeks: int = 52) -> list[int]:
    """Contributions per ISO week (Mon-Sun); last element is the current week."""
    this_monday = today - timedelta(days=today.weekday())
    start = this_monday - timedelta(weeks=weeks - 1)
    buckets = [0] * weeks
    for day in days:
        d = _parse_date(day["date"])
        if d < start or d > today:
            continue
        buckets[(d - start).days // 7] += day["count"]
    return buckets


def weekly_streak(cadence: list[int]) -> int:
    """Consecutive active weeks ending now; an empty current week is not penalised."""
    weeks = list(cadence)
    if weeks and weeks[-1] == 0:
        weeks.pop()  # current week is still in progress
    streak = 0
    for count in reversed(weeks):
        if count == 0:
            break
        streak += 1
    return streak


def repos_shipped(repos: list[Repo], today: date, days: int = 90, skip: frozenset[str] = frozenset()) -> int:
    """Non-fork repos pushed to within the last `days` days."""
    cutoff = today - timedelta(days=days)
    return sum(1 for r in _eligible(repos, skip) if _parse_date(r["pushed_at"]) >= cutoff)


def summarize(
    repos: list[Repo],
    calendar: list[dict[str, Any]] | None,
    today: date,
    skip: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Aggregate-only summary. Never contains repository names."""
    summary: dict[str, Any] = {
        "generated": today.isoformat(),
        "repos": len(_eligible(repos, skip)),
        "languages": polyglot_count(repos, skip),
        "shipped_90d": repos_shipped(repos, today, 90, skip),
        "mix": [(n, round(p, 1)) for n, p in language_mix(repos, 6, skip)],
        "timeline": [(n, d.isoformat()) for n, d in adoption_timeline(repos, skip)],
        "cadence": None,
        "streak": None,
        "contributions_12m": None,
    }
    if calendar is not None:
        cadence = weekly_cadence(calendar, today)
        summary["cadence"] = cadence
        summary["streak"] = weekly_streak(cadence)
        summary["contributions_12m"] = sum(cadence)
    return summary
