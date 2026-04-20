#!/usr/bin/env python3
"""
VC Portfolio Scanner
Usage: python run.py "Accel"
       python run.py "Index Ventures" --min-score 0
"""
import argparse
import logging
import sys

from config import THESIS, SLACK_WEBHOOK_URL
from models import Company
from tools.pitchbook import scan_investor_portfolio
from tools.slack import send_portfolio_scan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("portfolio_scanner")


def _score(company: Company) -> Company:
    score = 0
    breakdown: dict[str, int] = {}

    geo_values = set(THESIS["geographies"].values())
    if company.country in geo_values:
        score += 20
        breakdown["geography"] = 20

    sector_kws = [s.lower() for s in THESIS["sectors"]]
    combined = f"{company.sector} {company.description}".lower()
    if any(kw in combined for kw in sector_kws):
        score += 20
        breakdown["sector"] = 20

    total = company.total_funding_eur or 0
    pts = 25 if total == 0 else 20 if total <= 10_000_000 else 10 if total <= THESIS["max_total_funding_eur"] else 0
    score += pts
    breakdown["funding"] = pts

    if company.last_round_type in THESIS["deal_types_include"]:
        score += 10
        breakdown["round_type"] = 10

    hc = company.headcount or 0
    if THESIS["min_headcount"] <= hc <= 80:
        score += 25
        breakdown["headcount"] = 25
    elif 80 < hc <= THESIS["max_headcount"]:
        score += 15
        breakdown["headcount"] = 15

    company.score = min(score, 100)
    company.score_breakdown = breakdown
    return company


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan a VC's portfolio on PitchBook and post matching companies to Slack"
    )
    parser.add_argument("investor", help="Name of the VC/investor firm to scan")
    parser.add_argument(
        "--min-score",
        type=int,
        default=THESIS["min_score_threshold"],
        help=f"Minimum thesis score to include (default: {THESIS['min_score_threshold']})",
    )
    args = parser.parse_args()

    logger.info("\u2550\u2550\u2550 VC Portfolio Scanner: %s \u2550\u2550\u2550", args.investor)

    companies = scan_investor_portfolio(args.investor)
    if not companies:
        logger.error("No portfolio data returned \u2014 check the investor name or PitchBook MCP access")
        sys.exit(1)

    scored = [_score(c) for c in companies]

    relevant = [c for c in scored if (c.score or 0) >= args.min_score]
    relevant.sort(key=lambda c: c.score or 0, reverse=True)

    logger.info(
        "Total portfolio: %d  |  Matching thesis (\u2265%d): %d",
        len(companies), args.min_score, len(relevant),
    )
    for c in relevant:
        print(f"  {c.score:.0f}/100  {c.name}  ({c.country}, {c.sector})")

    send_portfolio_scan(
        investor_name=args.investor,
        companies=relevant,
        total_scanned=len(companies),
        min_score=args.min_score,
    )

    logger.info("\u2550\u2550\u2550 Done \u2550\u2550\u2550")


if __name__ == "__main__":
    main()
