import os
from dotenv import load_dotenv

load_dotenv()

THESIS = {
    "geographies": {
        "DE": "Germany",
        "AT": "Austria",
        "CH": "Switzerland",
        "GB": "United Kingdom",
        "SE": "Sweden",
        "NO": "Norway",
        "DK": "Denmark",
        "FI": "Finland",
        "NL": "Netherlands",
        "BE": "Belgium",
        "FR": "France",
        "IT": "Italy",
        "ES": "Spain",
        "IL": "Israel",
    },
    "sectors": [
        "Software", "SaaS", "B2B Software", "Enterprise Software",
        "AI", "Artificial Intelligence", "Machine Learning", "Deep Learning",
        "Data", "Data Analytics", "Business Intelligence", "Analytics",
        "Information Services", "Information Technology",
        "Developer Tools", "Infrastructure Software",
        "Fintech", "HR Tech", "Legal Tech", "Proptech",
    ],
    "max_total_funding_eur": 20_000_000,
    "deal_types_include": ["Pre-Seed", "Seed", "Series A"],
    "deal_types_exclude": ["Series B", "Series C", "Series D", "Growth Equity", "Late Stage", "PE Buyout", "IPO"],
    "min_headcount": 25,
    "max_headcount": 300,
    "min_score_threshold": 40,
}

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
