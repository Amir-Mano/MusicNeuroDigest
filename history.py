"""Append-only, human-readable record of every article ever sent in the
digest -- grouped the same way the email is (new / classic / preprints) --
so there's a browsable archive independent of the seen_*.json dedup state
(which only tracks PMIDs, not titles, and is never meant to be read by eye).
"""

from datetime import date

import config


def _section(label: str, articles: list) -> list:
    if not articles:
        return []
    lines = [f"### {label}"]
    lines.extend(f"- {a['title']}" for a in articles)
    lines.append("")
    return lines


def record_sent(
    this_week: list, must_read: dict | None, classic: dict | None, preprints: list
) -> None:
    """Append one dated section for this run. No-op if nothing was sent."""
    if not this_week and not classic and not preprints:
        return

    new_articles = [
        {**a, "title": f"{a['title']} (MUST-READ)"}
        if must_read and a["pmid"] == must_read["pmid"]
        else a
        for a in this_week
    ]

    lines = [f"## {date.today().isoformat()}", ""]
    lines.extend(_section("New this week", new_articles))
    lines.extend(_section("Classic worth revisiting", [classic] if classic else []))
    lines.extend(_section("Preprints", preprints))

    with config.HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
