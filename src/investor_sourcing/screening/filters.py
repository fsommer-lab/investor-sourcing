"""Declarative company filters driven by config/filters.yaml.

Geography is handled separately in geography.py and always applies;
these are the narrowing filters layered on top.
"""

from __future__ import annotations

from ..config import Filters
from ..models import Company


def _matches_any(haystack: str, needles: list[str]) -> bool:
    lowered = haystack.lower()
    return any(n.lower() in lowered for n in needles)


def passes_filters(company: Company, filters: Filters) -> bool:
    cid = company.company_id.lower()
    if cid in filters.exclude_companies or cid in filters.exclude_portfolio:
        return False

    if filters.employee_count_min is not None:
        if company.employee_count is None or company.employee_count < filters.employee_count_min:
            return False
    if filters.employee_count_max is not None:
        if company.employee_count is not None and company.employee_count > filters.employee_count_max:
            return False

    if filters.industries_include and not _matches_any(company.industry, filters.industries_include):
        return False
    if filters.industries_exclude and _matches_any(company.industry, filters.industries_exclude):
        return False

    text = f"{company.name} {company.description}"
    if filters.keywords_include and not _matches_any(text, filters.keywords_include):
        return False
    if filters.keywords_exclude and _matches_any(text, filters.keywords_exclude):
        return False

    return True
