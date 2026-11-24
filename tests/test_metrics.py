from datetime import date

from metrics import compute, render

TODAY = date(2026, 11, 24)  # a Tuesday


def repo(name, langs, created="2025-01-10T00:00:00Z", pushed="2026-11-01T00:00:00Z", fork=False):
    return {"name": name, "fork": fork, "created_at": created, "pushed_at": pushed, "languages": langs}


REPOS = [
    repo("a", {"TypeScript": 6000, "HTML": 90000}),
    repo("b", {"Dart": 3000, "TypeScript": 1000}, created="2024-11-01T00:00:00Z"),
    repo("c", {"Python": 500}),  # below the trivial-usage threshold
    repo("d", {"Java": 99999}, fork=True),
    repo("e", {"PHP": 2000}, pushed="2026-01-01T00:00:00Z"),
]


def test_language_mix_excludes_markup_forks_and_skips():
    mix = dict(compute.language_mix(REPOS, top_n=2, skip=frozenset({"e"})))
    assert "HTML" not in mix and "Java" not in mix and "PHP" not in mix
    assert abs(mix["TypeScript"] - 66.67) < 0.01
    assert abs(sum(mix.values()) - 100) < 1e-9


def test_language_mix_folds_remainder_into_other():
    mix = compute.language_mix(REPOS, top_n=1)
    assert [n for n, _ in mix] == ["TypeScript", "Other"]


def test_language_mix_empty():
    assert compute.language_mix([]) == []


def test_polyglot_ignores_trivial_languages():
    assert compute.polyglot_count(REPOS) == 3  # TypeScript, Dart, PHP


def test_adoption_timeline_uses_earliest_repo():
    timeline = dict(compute.adoption_timeline(REPOS))
    assert timeline["TypeScript"] == date(2024, 11, 1)
    assert "Python" not in timeline and "Java" not in timeline


def test_repos_shipped_window():
    assert compute.repos_shipped(REPOS, TODAY, 90) == 3  # a, b, c; e is stale, d is a fork


def test_weekly_cadence_buckets_by_week():
    days = [
        {"date": "2026-11-24", "count": 3},  # current week
        {"date": "2026-11-23", "count": 2},  # Monday, current week
        {"date": "2026-11-22", "count": 4},  # Sunday, previous week
        {"date": "2025-01-01", "count": 99},  # outside the window
    ]
    cadence = compute.weekly_cadence(days, TODAY, weeks=4)
    assert cadence == [0, 0, 4, 5]


def test_weekly_streak_ignores_empty_current_week():
    assert compute.weekly_streak([0, 2, 3, 0]) == 2
    assert compute.weekly_streak([2, 0, 3, 1]) == 2
    assert compute.weekly_streak([0, 0]) == 0


def test_summary_never_leaks_repo_names():
    secret = [repo("very-private-project", {"Go": 5000})]
    summary = compute.summarize(secret, [{"date": "2026-11-24", "count": 1}], TODAY)
    assert "very-private-project" not in str(summary)


def test_summary_without_calendar_degrades():
    summary = compute.summarize(REPOS, None, TODAY)
    assert summary["cadence"] is None and summary["streak"] is None


def test_render_outputs_valid_svg_for_both_themes():
    summary = compute.summarize(REPOS, [{"date": "2026-11-24", "count": 5}], TODAY)
    for theme in ("light", "dark"):
        svg = render.render_svg(summary, theme)
        assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
        assert "TypeScript" in svg


def test_render_escapes_text_and_handles_missing_sections():
    summary = compute.summarize([], None, TODAY)
    summary["mix"] = [("C<script>", 100.0)]
    svg = render.render_svg(summary, "light")
    assert "<script>" not in svg and "&lt;script&gt;" in svg


def test_flutter_scaffolding_is_ignored_in_dart_repos():
    flutter = repo("app", {"Dart": 5000, "C++": 90000, "Swift": 4000})
    native = repo("firmware", {"C++": 2000})
    totals = compute.language_totals([flutter, native])
    assert totals == {"Dart": 5000, "C++": 2000}
