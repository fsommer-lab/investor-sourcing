"""SQLite cache so collection runs are incremental and re-screenable offline."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import Company, Employee, Follow

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    profile_id TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    title      TEXT NOT NULL DEFAULT '',
    fund_slug  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS companies (
    company_id        TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    hq_country        TEXT NOT NULL DEFAULT '',
    employee_count    INTEGER,
    industry          TEXT NOT NULL DEFAULT '',
    description       TEXT NOT NULL DEFAULT '',
    website           TEXT NOT NULL DEFAULT '',
    ownership_status  TEXT NOT NULL DEFAULT '',
    total_funding_usd INTEGER,
    latest_round      TEXT NOT NULL DEFAULT '',
    grata_uid         TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS follows (
    profile_id TEXT NOT NULL REFERENCES employees(profile_id),
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    PRIMARY KEY (profile_id, company_id)
);
"""

# Columns added after the first release; older caches get them via ALTER.
_COMPANY_MIGRATIONS = {
    "ownership_status": "TEXT NOT NULL DEFAULT ''",
    "total_funding_usd": "INTEGER",
    "latest_round": "TEXT NOT NULL DEFAULT ''",
    "grata_uid": "TEXT NOT NULL DEFAULT ''",
}

_COMPANY_COLUMNS = (
    "company_id", "name", "hq_country", "employee_count", "industry",
    "description", "website", "ownership_status", "total_funding_usd",
    "latest_round", "grata_uid",
)


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)
        self._migrate()

    def _migrate(self) -> None:
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(companies)")}
        for column, decl in _COMPANY_MIGRATIONS.items():
            if column not in existing:
                self.conn.execute(f"ALTER TABLE companies ADD COLUMN {column} {decl}")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def upsert_employee(self, e: Employee) -> None:
        self.conn.execute(
            "INSERT INTO employees (profile_id, name, title, fund_slug) VALUES (?,?,?,?) "
            "ON CONFLICT(profile_id) DO UPDATE SET name=excluded.name, "
            "title=excluded.title, fund_slug=excluded.fund_slug",
            (e.profile_id, e.name, e.title, e.fund_slug),
        )

    def upsert_company(self, c: Company) -> None:
        # Blank/NULL incoming values never overwrite existing data, so a
        # re-collect from sparse CSVs cannot wipe out Grata enrichment.
        self.conn.execute(
            "INSERT INTO companies (company_id, name, hq_country, employee_count, "
            "industry, description, website, ownership_status, total_funding_usd, "
            "latest_round, grata_uid) VALUES (?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(company_id) DO UPDATE SET "
            "name=COALESCE(NULLIF(excluded.name,''), companies.name), "
            "hq_country=COALESCE(NULLIF(excluded.hq_country,''), companies.hq_country), "
            "employee_count=COALESCE(excluded.employee_count, companies.employee_count), "
            "industry=COALESCE(NULLIF(excluded.industry,''), companies.industry), "
            "description=COALESCE(NULLIF(excluded.description,''), companies.description), "
            "website=COALESCE(NULLIF(excluded.website,''), companies.website), "
            "ownership_status=COALESCE(NULLIF(excluded.ownership_status,''), companies.ownership_status), "
            "total_funding_usd=COALESCE(excluded.total_funding_usd, companies.total_funding_usd), "
            "latest_round=COALESCE(NULLIF(excluded.latest_round,''), companies.latest_round), "
            "grata_uid=COALESCE(NULLIF(excluded.grata_uid,''), companies.grata_uid)",
            (c.company_id, c.name, c.hq_country, c.employee_count, c.industry,
             c.description, c.website, c.ownership_status, c.total_funding_usd,
             c.latest_round, c.grata_uid),
        )

    def upsert_follow(self, f: Follow) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO follows (profile_id, company_id) VALUES (?,?)",
            (f.profile_id, f.company_id),
        )

    def commit(self) -> None:
        self.conn.commit()

    def employees(self) -> list[Employee]:
        rows = self.conn.execute(
            "SELECT profile_id, name, title, fund_slug FROM employees"
        ).fetchall()
        return [Employee(*row) for row in rows]

    def companies(self) -> list[Company]:
        rows = self.conn.execute(
            f"SELECT {', '.join(_COMPANY_COLUMNS)} FROM companies"
        ).fetchall()
        return [Company(*row) for row in rows]

    def follows(self) -> list[Follow]:
        rows = self.conn.execute("SELECT profile_id, company_id FROM follows").fetchall()
        return [Follow(*row) for row in rows]
