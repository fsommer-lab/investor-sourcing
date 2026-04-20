import json
import logging
from typing import Optional

import requests

from config import SLACK_WEBHOOK_URL
from models import Company

logger = logging.getLogger(__name__)


def _eur(amount: float) -> str:
    if amount >= 1_000_000:
        return f"\u20ac{amount / 1_000_000:.1f}M"
    return f"\u20ac{amount / 1_000:.0f}K"


def _score_bar(score: float) -> str:
    filled = round(score / 10)
    return "\u2588" * filled + "\u2591" * (10 - filled) + f"  {score:.0f}/100"


def _funding_line(company: Company) -> str:
    if company.last_round_amount_eur and company.last_round_type:
        line = f"{company.last_round_type}: {_eur(company.last_round_amount_eur)}"
        if company.total_funding_eur and company.total_funding_eur != company.last_round_amount_eur:
            line += f" \u00b7 total {_eur(company.total_funding_eur)}"
        return line
    if company.total_funding_eur:
        return f"Total raised: {_eur(company.total_funding_eur)}"
    return "Funding not disclosed"


def _company_block(company: Company, rank: int) -> list[dict]:
    hc = f"{company.headcount} employees" if company.headcount else "headcount unknown"
    desc = company.description or ""
    if len(desc) > 220:
        desc = desc[:220] + "\u2026"

    lines = [
        f"*{rank}. {company.name}*  \u00b7  {company.country}",
        f"_{company.sector}_  \u00b7  {hc}  \u00b7  {_funding_line(company)}",
        f"`{_score_bar(company.score or 0)}`",
    ]
    if desc:
        lines.append(desc)

    accessory: Optional[dict] = None
    if company.pitchbook_url:
        accessory = {
            "type": "button",
            "text": {"type": "plain_text", "text": "PitchBook \u2192"},
            "url": company.pitchbook_url,
        }

    block: dict = {
        "type": "section",
        "text": {"type": "mrkdwn", "text": "\n".join(lines)},
    }
    if accessory:
        block["accessory"] = accessory

    return [block, {"type": "divider"}]


def send_portfolio_scan(
    investor_name: str,
    companies: list[Company],
    total_scanned: int = 0,
    min_score: int = 40,
) -> bool:
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL not set \u2014 skipping Slack notification")
        return False

    matching = len(companies)

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"\U0001f3e6 Portfolio Scan: {investor_name}",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Active portfolio scanned:* {total_scanned}"},
                {"type": "mrkdwn", "text": f"*Matching thesis (\u2265{min_score}/100):* {matching}"},
                {
                    "type": "mrkdwn",
                    "text": (
                        f"*Top score:* {max(c.score or 0 for c in companies):.0f}/100"
                        if companies
                        else "*Top score:* \u2014"
                    ),
                },
            ],
        },
        {"type": "divider"},
    ]

    if not companies:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"No portfolio companies match the thesis (min score {min_score}/100).",
            },
        })
    else:
        for rank, company in enumerate(companies, start=1):
            blocks.extend(_company_block(company, rank))
            if len(blocks) >= 48:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"_\u2026 and {matching - rank} more. Run with `--min-score 0` to see all._",
                    },
                })
                break

    try:
        resp = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps({"blocks": blocks}),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Slack message sent: %d matching companies for '%s'", matching, investor_name)
        return True
    except Exception as e:
        logger.error("Failed to send Slack message: %s", e)
        return False
