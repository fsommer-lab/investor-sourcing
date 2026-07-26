"""Pipeline orchestration: collect -> screen -> report.

collect() pulls employees and follow edges from the provider into the
SQLite cache; screen() re-runs filtering/scoring from the cache without
touching the provider, so filters can be iterated on cheaply.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .config import Filters
from .models import Fund, ScoredCompany
from .providers.base import Provider
from .scoring import screen_and_score
from .storage import Store

log = logging.getLogger(__name__)


def collect(store: Store, provider: Provider, funds: list[Fund]) -> None:
    for fund in funds:
        count = 0
        for employee in provider.fetch_employees(fund):
            if not fund.wants_role(employee.title):
                continue
            store.upsert_employee(employee)
            count += 1
            for company, follow in provider.fetch_followed_companies(employee):
                store.upsert_company(company)
                store.upsert_follow(follow)
        store.commit()
        log.info("%s: collected %d employees", fund.name, count)


def screen(store: Store, filters: Filters) -> list[ScoredCompany]:
    return screen_and_score(
        employees=store.employees(),
        companies=store.companies(),
        follows=store.follows(),
        filters=filters,
    )
