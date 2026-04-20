import logging
from typing import Optional

from models import Company
from tools.claude_cli import call_claude_mcp, parse_json

logger = logging.getLogger(__name__)

_PORTFOLIO_PROMPT = """\
You are scanning the portfolio of a VC investor on PitchBook. Follow these steps exactly:

Step 1: Find the investor
- Call pitchbook_search with name="{investor_name}" and entity_types=["business_entity"]
- From the results, identify the VC/venture capital firm matching "{investor_name}"
- Record their PBID

Step 2: Get their active portfolio companies
- Call pitchbook_get_investor_investments with:
  - investor_pbid = the PBID from step 1
  - filter_by = {{"investor_status": "Active"}}
  - limit = 40
  - sort_by = "investor_since_desc"

Step 3: Get a profile for each portfolio company
- For each company returned in step 2, call pitchbook_get_profile using the company's PBID
- Collect: description, sector/industry, HQ country, total funding raised,
  last round type and size, headcount, website

Step 4: Return ONLY a JSON array — no markdown, no preamble, no explanation:
[{{
  "name": "company name",
  "country": "full country name or null",
  "sector": "primary sector or null",
  "description": "2-3 sentences on what they do or null",
  "total_funding_eur": number or null,
  "last_round_type": "Pre-Seed|Seed|Series A|Series B|etc. or null",
  "last_round_amount_eur": number or null,
  "last_round_date": "YYYY-MM-DD or null",
  "headcount": number or null,
  "founded_year": number or null,
  "website": "URL or null",
  "pitchbook_url": "URL or null"
}}]

If the investor is not found, return: []
"""


def scan_investor_portfolio(investor_name: str) -> list[Company]:
    """
    Use the PitchBook MCP (via claude CLI) to scan a VC's active portfolio.
    Returns a list of Company objects, unscored.
    """
    logger.info("PitchBook: scanning portfolio of '%s' via claude CLI…", investor_name)
    prompt = _PORTFOLIO_PROMPT.format(investor_name=investor_name)
    output = call_claude_mcp(prompt, timeout=600)
    if not output:
        return []

    data = parse_json(output)
    if not isinstance(data, list):
        logger.warning("Portfolio scan: unexpected response format")
        return []

    companies: list[Company] = []
    for item in data:
        try:
            companies.append(Company(
                name=item.get("name") or "Unknown",
                country=item.get("country") or "Unknown",
                sector=item.get("sector") or "Unknown",
                description=item.get("description") or "",
                total_funding_eur=_f(item.get("total_funding_eur")),
                last_round_type=item.get("last_round_type"),
                last_round_amount_eur=_f(item.get("last_round_amount_eur")),
                last_round_date=item.get("last_round_date"),
                headcount=item.get("headcount"),
                founded_year=item.get("founded_year"),
                website=item.get("website"),
                pitchbook_url=item.get("pitchbook_url"),
                source="pitchbook",
                source_url=item.get("pitchbook_url"),
            ))
        except Exception as e:
            logger.warning("Failed to parse portfolio item: %s", e)

    logger.info(
        "PitchBook: %d active portfolio companies found for '%s'",
        len(companies), investor_name,
    )
    return companies


def _f(value) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
