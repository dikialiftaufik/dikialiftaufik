"""GitHub data access (REST + GraphQL) using only the standard library."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

API = "https://api.github.com"
TIMEOUT = 20
RETRIES = 3


def _request(url: str, token: str | None, body: bytes | None = None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-metrics",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        headers["Content-Type"] = "application/json"
    last: Exception | None = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, data=body, headers=headers)  # noqa: S310
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403, 404):  # not retryable
                raise
            last = exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
        time.sleep(2**attempt)
    raise RuntimeError(f"request failed after {RETRIES} attempts: {url}") from last


def fetch_repos(user: str, token: str | None, include_private: bool) -> list[dict[str, Any]]:
    """List owned repos with their language byte counts."""
    raw: list[dict[str, Any]] = []
    page = 1
    while True:
        if include_private and token:
            url = f"{API}/user/repos?affiliation=owner&per_page=100&page={page}"
        else:
            url = f"{API}/users/{user}/repos?type=owner&per_page=100&page={page}"
        batch = _request(url, token)
        if not batch:
            break
        raw.extend(batch)
        page += 1
    repos = []
    for r in raw:
        if r["owner"]["login"].lower() != user.lower():
            continue
        languages = {} if r["fork"] else _request(r["languages_url"], token)
        repos.append(
            {
                "name": r["name"],
                "fork": r["fork"],
                "private": r["private"],
                "created_at": r["created_at"],
                "pushed_at": r["pushed_at"],
                "languages": languages,
            }
        )
    return repos


_CALENDAR_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_calendar(user: str, token: str | None) -> list[dict[str, Any]] | None:
    """Daily contribution counts for the last year; None without a token."""
    if not token:
        return None
    body = json.dumps({"query": _CALENDAR_QUERY, "variables": {"login": user}}).encode()
    data = _request(f"{API}/graphql", token, body)
    if "errors" in data:
        raise RuntimeError(f"GraphQL error: {data['errors']}")
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [{"date": d["date"], "count": d["contributionCount"]} for w in weeks for d in w["contributionDays"]]
