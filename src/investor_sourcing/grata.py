"""Grata API client for company enrichment and funding cross-checks.

Fills in HQ country, headcount, industry, description, and — the key
signal for bootstrapped screens — ownership status and funding totals.

Auth: set GRATA_API_KEY in the environment (get a key from your Grata
workspace's API settings). The endpoint/field mapping below follows the
Grata Enrichment API (v1.4); if Grata revs its schema, only this module
needs updating.
"""

from __future__ import annotations

import dataclasses
import logging
import os
import time
from typing import Any

import requests

from .models import Company

log = logging.getLogger(__name__)

API_BASE = os.environ.get("GRATA_API_BASE", "https://search.grata.com/api/v1.4")
# Courtesy delay between calls; Grata enforces its own rate limits too.
REQUEST_DELAY_SECONDS = 0.5


class GrataError(RuntimeError):
    pass


class GrataClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GRATA_API_KEY", "")
        if not self.api_key:
            raise GrataError(
                "GRATA_API_KEY is not set. Export it before running enrichment:\n"
                "  export GRATA_API_KEY=..."
            )
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Token {self.api_key}", "Content-Type": "application/json"}
        )

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        url = f"{API_BASE}{path}"
        try:
            resp = self.session.post(url, json=payload, timeout=30)
        except requests.RequestException as exc:
            log.warning("Grata request failed (%s): %s", url, exc)
            return None
        if resp.status_code == 401:
            raise GrataError("Grata rejected the API key (401). Check GRATA_API_KEY.")
        if resp.status_code == 404:
            return None
        if resp.status_code == 429:
            log.warning("Grata rate limit hit; backing off 30s")
            time.sleep(30)
            return self._post(path, payload)
        if not resp.ok:
            log.warning("Grata %s returned %d: %s", path, resp.status_code, resp.text[:200])
            return None
        return resp.json()

    def enrich(self, company: Company) -> Company | None:
        """Return the company enriched with Grata data, or None if not found.

        Lookup preference: existing grata_uid, then website domain, then a
        name search as last resort (log-flagged, since name matches can be
        wrong — verify low-confidence rows in the output).
        """
        data: dict[str, Any] | None = None
        if company.grata_uid:
            data = self._post("/enrich/", {"company_uid": company.grata_uid})
        if data is None and company.website:
            domain = _domain_of(company.website)
            if domain:
                data = self._post("/enrich/", {"domain": domain})
        if data is None and company.name:
            data = self._search_by_name(company.name)
            if data is not None:
                log.info("Grata: matched '%s' by name search — verify the match", company.name)
        if data is None:
            return None
        time.sleep(REQUEST_DELAY_SECONDS)
        return _merge(company, data)

    def _search_by_name(self, name: str) -> dict[str, Any] | None:
        result = self._post("/search/", {"terms": [name], "page_size": 1})
        if not result:
            return None
        companies = result.get("companies") or result.get("results") or []
        return companies[0] if companies else None


def _domain_of(url: str) -> str:
    d = url.strip().lower()
    for prefix in ("https://", "http://", "www."):
        d = d.removeprefix(prefix)
    return d.split("/")[0]


def _merge(company: Company, data: dict[str, Any]) -> Company:
    """Map a Grata company payload onto our model. Grata wins only where
    we have nothing, except funding/ownership where Grata is authoritative."""
    hq = data.get("headquarters") or {}
    if isinstance(hq, list):
        hq = hq[0] if hq else {}
    country = (
        hq.get("country_iso") or hq.get("country_code") or hq.get("country") or ""
    )
    industry = ""
    classifications = data.get("industry_classifications") or []
    if classifications and isinstance(classifications, list):
        first = classifications[0]
        industry = first.get("industry_name", "") if isinstance(first, dict) else str(first)

    funding = data.get("funding") or {}
    total_funding = (
        funding.get("total_funding_usd")
        or funding.get("total_funding")
        or data.get("total_funding_usd")
        or data.get("total_funding")
    )
    latest = funding.get("latest_round") or data.get("latest_funding_round") or {}
    if isinstance(latest, dict):
        latest_round = " ".join(
            str(v) for v in (latest.get("round_type"), latest.get("date")) if v
        )
    else:
        latest_round = str(latest or "")

    return dataclasses.replace(
        company,
        name=company.name or data.get("name", ""),
        hq_country=company.hq_country or str(country),
        employee_count=company.employee_count
        or data.get("employees_on_professional_networks")
        or data.get("employee_count"),
        industry=company.industry or industry,
        description=company.description or data.get("description", ""),
        website=company.website or data.get("domain", ""),
        ownership_status=str(data.get("ownership_status") or data.get("ownership") or ""),
        total_funding_usd=int(total_funding) if total_funding else None,
        latest_round=latest_round,
        grata_uid=str(data.get("company_uid") or data.get("uid") or company.grata_uid),
    )
