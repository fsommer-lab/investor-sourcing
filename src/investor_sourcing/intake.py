"""Manual-research intake: turn pasted LinkedIn page text into pipeline CSVs.

This exists so the account-safe workflow (a human browsing LinkedIn
normally in their own browser) is fast: you copy the "Interests ->
Companies" section of a profile, paste it here, and the tedious data
entry is done for you. Nothing in this module talks to LinkedIn.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from .models import Employee

# Lines that are UI chrome rather than company names when copying the
# Interests -> Companies section of a profile.
_NOISE_PATTERNS = [
    re.compile(r"^\s*$"),
    re.compile(r"^(follow|following|unfollow)$", re.I),
    re.compile(r"^[\d,.\s]+(followers?|members?)$", re.I),
    re.compile(r"^(interests|companies|groups|newsletters|schools)$", re.I),
    re.compile(r"^show all.*$", re.I),
    re.compile(r"^·.*$"),
    re.compile(r"^\d+$"),
]


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "unknown"


def parse_followed_companies(text: str) -> list[str]:
    """Extract an ordered, deduplicated list of company names from pasted text."""
    names: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if any(p.match(line) for p in _NOISE_PATTERNS):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(line)
    return names


def _append_rows(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if new_file:
            writer.writerow(header)
        writer.writerows(rows)


def append_employee(root: Path, employee: Employee) -> None:
    _append_rows(
        root / "employees.csv",
        ["fund_slug", "profile_id", "name", "title"],
        [[employee.fund_slug, employee.profile_id, employee.name, employee.title]],
    )


def append_follows(root: Path, profile_id: str, company_names: list[str]) -> int:
    """Append follow rows for one employee; hq_country is left blank for
    later enrichment. Returns the number of rows written."""
    rows = [
        [profile_id, slugify(name), name, "", "", "", "", ""]
        for name in company_names
    ]
    _append_rows(
        root / "follows.csv",
        [
            "profile_id", "company_id", "company_name", "hq_country",
            "employee_count", "industry", "description", "website",
        ],
        rows,
    )
    return len(rows)
