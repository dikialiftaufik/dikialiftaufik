"""Render the metrics summary as a self-contained SVG (light and dark)."""

from __future__ import annotations

from datetime import date
from typing import Any
from xml.sax.saxutils import escape

WIDTH = 800
PAD = 24
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

THEMES = {
    "light": {"bg": "#ffffff", "fg": "#1f2328", "muted": "#59636e", "tile": "#f6f8fa", "line": "#d1d9e0"},
    "dark": {"bg": "#0d1117", "fg": "#e6edf3", "muted": "#9198a1", "tile": "#151b23", "line": "#3d444d"},
}
# Okabe-Ito palette: distinguishable for common colour-vision deficiencies.
PALETTE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#7f8790"]


def _text(x: float, y: float, content: str, *, size: int, fill: str, weight: int = 400, anchor: str = "start") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}">{escape(content)}</text>'
    )


def _tiles(summary: dict[str, Any], t: dict[str, str], y: int) -> tuple[list[str], int]:
    tiles = [
        (str(summary["repos"]), "public repositories"),
        (str(summary["languages"]), "programming languages"),
        (str(summary["shipped_90d"]), "repos updated, last 90 days"),
    ]
    if summary["streak"] is not None:
        tiles.append((str(summary["streak"]), "consecutive active weeks"))
    gap = 12
    w = (WIDTH - 2 * PAD - gap * (len(tiles) - 1)) / len(tiles)
    out = []
    for i, (value, label) in enumerate(tiles):
        x = PAD + i * (w + gap)
        out.append(
            f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="64" rx="8" fill="{t["tile"]}" stroke="{t["line"]}"/>'
        )
        out.append(_text(x + 14, y + 30, value, size=24, fill=t["fg"], weight=600))
        out.append(_text(x + 14, y + 50, label, size=12, fill=t["muted"]))
    return out, y + 64


def _languages(summary: dict[str, Any], t: dict[str, str], y: int) -> tuple[list[str], int]:
    mix = summary["mix"]
    if not mix:
        return [], y
    out = [
        _text(PAD, y + 14, "Most-used languages (share of code, excluding markup)", size=14, fill=t["fg"], weight=600)
    ]
    bar_y = y + 28
    inner = WIDTH - 2 * PAD
    x = float(PAD)
    for i, (name, pct) in enumerate(mix):
        w = inner * pct / 100
        out.append(
            f'<rect x="{x:.2f}" y="{bar_y}" width="{max(w, 1):.2f}" height="12" fill="{PALETTE[i % len(PALETTE)]}"><title>{escape(name)} {pct}%</title></rect>'
        )
        x += w
    for i, (name, pct) in enumerate(mix):
        lx = PAD + (i % 4) * 188
        ly = bar_y + 36 + (i // 4) * 22
        out.append(f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{PALETTE[i % len(PALETTE)]}"/>')
        out.append(_text(lx + 16, ly, f"{name} {pct}%", size=12, fill=t["fg"]))
    rows = (len(mix) + 3) // 4
    return out, bar_y + 36 + (rows - 1) * 22 + 6


def _cadence(summary: dict[str, Any], t: dict[str, str], y: int) -> tuple[list[str], int]:
    cadence = summary["cadence"]
    if cadence is None:
        return [], y
    out = [_text(PAD, y + 14, "Contributions per week, last 52 weeks", size=14, fill=t["fg"], weight=600)]
    top, height = y + 28, 56
    inner = WIDTH - 2 * PAD
    step = inner / len(cadence)
    peak = max(cadence) or 1
    for i, count in enumerate(cadence):
        h = max(2, round(height * count / peak)) if count else 2
        color = "#0072B2" if count else t["line"]
        out.append(
            f'<rect x="{PAD + i * step:.2f}" y="{top + height - h}" width="{step - 3:.2f}" height="{h}" rx="1" fill="{color}"><title>{count}</title></rect>'
        )
    out.append(
        _text(
            PAD,
            top + height + 18,
            f"{summary['contributions_12m']} contributions in total · peak week: {peak}",
            size=12,
            fill=t["muted"],
        )
    )
    return out, top + height + 24


def _timeline(summary: dict[str, Any], t: dict[str, str], y: int, today: date) -> tuple[list[str], int]:
    timeline = summary["timeline"]
    if not timeline:
        return [], y
    out = [_text(PAD, y + 14, "When each language first appeared in a repository", size=14, fill=t["fg"], weight=600)]
    start = date.fromisoformat(timeline[0][1])
    span = max((today - start).days, 1)
    x0, x1 = PAD + 110, WIDTH - PAD - 70
    row_y = y + 40
    for i, (lang, iso) in enumerate(timeline):
        cy = row_y + i * 22
        d = date.fromisoformat(iso)
        cx = x0 + (x1 - x0) * (d - start).days / span
        out.append(_text(PAD, cy + 4, lang, size=12, fill=t["fg"]))
        out.append(f'<line x1="{x0}" y1="{cy}" x2="{x1}" y2="{cy}" stroke="{t["line"]}"/>')
        out.append(f'<circle cx="{cx:.1f}" cy="{cy}" r="5" fill="{PALETTE[i % len(PALETTE)]}"/>')
        out.append(_text(x1 + 12, cy + 4, d.strftime("%b %Y"), size=12, fill=t["muted"]))
    return out, row_y + (len(timeline) - 1) * 22 + 12


def render_svg(summary: dict[str, Any], theme: str) -> str:
    """Return the complete SVG document for one theme."""
    t = THEMES[theme]
    today = date.fromisoformat(summary["generated"])
    body: list[str] = [
        _text(PAD, 36, "GitHub activity", size=18, fill=t["fg"], weight=600),
        _text(WIDTH - PAD, 36, f"Updated {summary['generated']} · public data", size=12, fill=t["muted"], anchor="end"),
    ]
    y = 56
    for section in (
        lambda y: _tiles(summary, t, y),
        lambda y: _languages(summary, t, y),
        lambda y: _cadence(summary, t, y),
        lambda y: _timeline(summary, t, y, today),
    ):
        part, end = section(y)
        if part:
            body.extend(part)
            y = end + 24
    height = y
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" aria-label="GitHub activity summary" '
        f'font-family="{FONT}">'
        f'<rect width="{WIDTH}" height="{height}" rx="10" fill="{t["bg"]}" stroke="{t["line"]}"/>'
        + "".join(body)
        + "</svg>\n"
    )
