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
    company_id     TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    hq_country     TEXT NOT NULL DEFAULT '',
    employee_count INTEGER,
    industry       TEXT NOT NULL DEFAULT '',
    description    TEXT NOT NULL DEFAULT '',
    website        TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS follows (
    profile_id TEXT NOT NULL REFERENCES employees(profile_id),
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    PRIMARY KEY (profile_id, company_id)
);
"""


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)

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
        self.conn.execute(
            "INSERT INTO companies (company_id, name, hq_country, employee_count, industry, description, website) "
            "VALUES (?,?,?,?,?,?,?) "
            "ON CONFLICT(company_id) DO UPDATE SET name=excluded.name, "
            "hq_country=excluded.hq_country, employee_count=excluded.employee_count, "
            "industry=excluded.industry, description=excluded.description, website=excluded.website",
            (c.company_id, c.name, c.hq_country, c.employee_count, c.industry, c.description, c.website),
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
            "SELECT company_id, name, hq_country, employee_count, industry, description, website "
            "FROM companies"
        ).fetchall()
        return [Company(*row) for row in rows]

    def follows(self) -> list[Follow]:
        rows = self.conn.execute("SELECT profile_id, company_id FROM follows").fetchall()
        return [Follow(*row) for row in rows]
