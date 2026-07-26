"""Load and validate the YAML configuration files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .models import Fund

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


@dataclass
class Filters:
    min_followers: int = 1
    min_funds: int = 1
    employee_count_min: int | None = None
    employee_count_max: int | None = None
    industries_include: list[str] = field(default_factory=list)
    industries_exclude: list[str] = field(default_factory=list)
    keywords_include: list[str] = field(default_factory=list)
    keywords_exclude: list[str] = field(default_factory=list)
    exclude_companies: list[str] = field(default_factory=list)
    exclude_portfolio: list[str] = field(default_factory=list)
    # '' = any; 'bootstrapped' or 'funded' filter on Grata-derived status.
    funding_profile: str = ""


def load_funds(path: Path | None = None) -> list[Fund]:
    path = path or CONFIG_DIR / "funds.yaml"
    raw = yaml.safe_load(path.read_text()) or {}
    funds = []
    for entry in raw.get("funds", []):
        funds.append(
            Fund(
                name=entry["name"],
                linkedin_slug=entry["linkedin_slug"],
                roles_include=tuple(entry.get("roles_include") or ()),
            )
        )
    if not funds:
        raise ValueError(f"No funds configured in {path}")
    return funds


def load_filters(path: Path | None = None) -> Filters:
    path = path or CONFIG_DIR / "filters.yaml"
    if not path.exists():
        return Filters()
    raw = yaml.safe_load(path.read_text()) or {}
    employee_count = raw.get("employee_count") or {}
    return Filters(
        min_followers=int(raw.get("min_followers", 1)),
        min_funds=int(raw.get("min_funds", 1)),
        employee_count_min=employee_count.get("min"),
        employee_count_max=employee_count.get("max"),
        industries_include=list(raw.get("industries_include") or []),
        industries_exclude=list(raw.get("industries_exclude") or []),
        keywords_include=list(raw.get("keywords_include") or []),
        keywords_exclude=list(raw.get("keywords_exclude") or []),
        exclude_companies=[s.lower() for s in raw.get("exclude_companies") or []],
        exclude_portfolio=[s.lower() for s in raw.get("exclude_portfolio") or []],
        funding_profile=str(raw.get("funding_profile") or "").lower(),
    )
