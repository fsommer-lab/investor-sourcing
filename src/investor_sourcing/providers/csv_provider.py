"""File-based provider: reads employees and follows from CSVs.

Lets the pipeline run end-to-end today from manual research or a vendor
export, and doubles as the fixture provider for tests.

Expected layout (default root: data/manual/):

employees.csv
    fund_slug,profile_id,name,title

follows.csv
    profile_id,company_id,company_name,hq_country,employee_count,industry,description,website
    (optional extra columns: ownership_status,total_funding_usd,latest_round)

Only fund_slug/profile_id/name and profile_id/company_id/company_name are
required; the remaining company columns are optional enrichment — they can
also be filled later via `investor-sourcing enrich` (Grata).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from ..models import Company, Employee, Follow, Fund

DEFAULT_ROOT = Path("data/manual")


class CsvProvider:
    def __init__(self, root: Path | str = DEFAULT_ROOT):
        self.root = Path(root)

    def fetch_employees(self, fund: Fund) -> Iterable[Employee]:
        path = self.root / "employees.csv"
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row["fund_slug"].strip() != fund.linkedin_slug:
                    continue
                yield Employee(
                    profile_id=row["profile_id"].strip(),
                    name=row["name"].strip(),
                    title=(row.get("title") or "").strip(),
                    fund_slug=fund.linkedin_slug,
                )

    def fetch_followed_companies(
        self, employee: Employee
    ) -> Iterable[tuple[Company, Follow]]:
        path = self.root / "follows.csv"
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row["profile_id"].strip() != employee.profile_id:
                    continue
                raw_count = (row.get("employee_count") or "").strip()
                raw_funding = (row.get("total_funding_usd") or "").strip()
                company = Company(
                    company_id=row["company_id"].strip(),
                    name=row["company_name"].strip(),
                    hq_country=(row.get("hq_country") or "").strip(),
                    employee_count=int(raw_count) if raw_count else None,
                    industry=(row.get("industry") or "").strip(),
                    description=(row.get("description") or "").strip(),
                    website=(row.get("website") or "").strip(),
                    ownership_status=(row.get("ownership_status") or "").strip(),
                    total_funding_usd=int(raw_funding) if raw_funding else None,
                    latest_round=(row.get("latest_round") or "").strip(),
                )
                yield company, Follow(
                    profile_id=employee.profile_id, company_id=company.company_id
                )
