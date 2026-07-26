"""Aggregate follow edges into a ranked signal per company.

The core signal: how many tracked competitor investors follow a company,
and across how many distinct funds. A company followed by several people
at several funds is a far stronger sourcing signal than a single follow.
"""

from __future__ import annotations

from .config import Filters
from .models import Company, Employee, Follow, ScoredCompany
from .screening import is_europe_or_israel, passes_filters


def screen_and_score(
    employees: list[Employee],
    companies: list[Company],
    follows: list[Follow],
    filters: Filters,
) -> list[ScoredCompany]:
    employees_by_id = {e.profile_id: e for e in employees}
    companies_by_id = {c.company_id: c for c in companies}

    followers: dict[str, list[Employee]] = {}
    for edge in follows:
        employee = employees_by_id.get(edge.profile_id)
        if employee is None:
            continue
        followers.setdefault(edge.company_id, []).append(employee)

    scored: list[ScoredCompany] = []
    for company_id, follower_list in followers.items():
        company = companies_by_id.get(company_id)
        if company is None:
            continue
        if not is_europe_or_israel(company.hq_country):
            continue
        if not passes_filters(company, filters):
            continue
        sc = ScoredCompany(company=company, followers=follower_list)
        if sc.follower_count < filters.min_followers:
            continue
        if sc.fund_count < filters.min_funds:
            continue
        scored.append(sc)

    scored.sort(key=lambda s: (s.fund_count, s.follower_count, s.company.name), reverse=True)
    return scored
