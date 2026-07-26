"""Write the screened results as CSV and a readable Markdown summary."""

from __future__ import annotations

import csv
from pathlib import Path

from .models import ScoredCompany


def write_csv(results: list[ScoredCompany], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "company",
                "company_id",
                "hq_country",
                "employee_count",
                "industry",
                "website",
                "follower_count",
                "fund_count",
                "funds",
                "followers",
            ]
        )
        for r in results:
            writer.writerow(
                [
                    r.company.name,
                    r.company.company_id,
                    r.company.hq_country,
                    r.company.employee_count or "",
                    r.company.industry,
                    r.company.website,
                    r.follower_count,
                    r.fund_count,
                    "; ".join(r.fund_slugs),
                    "; ".join(f"{e.name} ({e.fund_slug})" for e in r.followers),
                ]
            )


def write_markdown(results: list[ScoredCompany], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Competitor follow signal — Europe & Israel",
        "",
        f"{len(results)} companies passed the screen.",
        "",
        "| Company | HQ | Followers | Funds | Followed by |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        followers = ", ".join(e.name for e in r.followers)
        lines.append(
            f"| {r.company.name} | {r.company.hq_country} "
            f"| {r.follower_count} | {r.fund_count} | {followers} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
