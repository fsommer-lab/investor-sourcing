"""Geography screen: Europe + Israel.

Accepts ISO 3166-1 alpha-2 codes and normalizes common country-name
spellings that show up in provider data.
"""

from __future__ import annotations

EUROPE_AND_ISRAEL: frozenset[str] = frozenset(
    {
        # EU
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE",
        "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT",
        "RO", "SK", "SI", "ES", "SE",
        # Rest of Europe
        "GB", "CH", "NO", "IS", "LI", "MC", "AD", "SM", "VA", "UA", "MD",
        "RS", "BA", "ME", "MK", "AL", "XK", "TR", "GE", "AM", "AZ", "BY",
        # Israel
        "IL",
    }
)

_NAME_TO_CODE: dict[str, str] = {
    "united kingdom": "GB",
    "uk": "GB",
    "great britain": "GB",
    "england": "GB",
    "scotland": "GB",
    "germany": "DE",
    "france": "FR",
    "israel": "IL",
    "netherlands": "NL",
    "the netherlands": "NL",
    "spain": "ES",
    "italy": "IT",
    "sweden": "SE",
    "switzerland": "CH",
    "norway": "NO",
    "denmark": "DK",
    "finland": "FI",
    "ireland": "IE",
    "belgium": "BE",
    "austria": "AT",
    "poland": "PL",
    "portugal": "PT",
    "czech republic": "CZ",
    "czechia": "CZ",
    "romania": "RO",
    "greece": "GR",
    "hungary": "HU",
    "estonia": "EE",
    "latvia": "LV",
    "lithuania": "LT",
    "croatia": "HR",
    "slovenia": "SI",
    "slovakia": "SK",
    "bulgaria": "BG",
    "luxembourg": "LU",
    "iceland": "IS",
    "ukraine": "UA",
    "serbia": "RS",
    "turkey": "TR",
    "türkiye": "TR",
    "cyprus": "CY",
    "malta": "MT",
}


def normalize_country(value: str) -> str:
    """Return an ISO alpha-2 code for a code or common country name, else ''."""
    v = value.strip()
    if not v:
        return ""
    if len(v) == 2 and v.isalpha():
        return v.upper()
    return _NAME_TO_CODE.get(v.lower(), "")


def is_europe_or_israel(country: str) -> bool:
    return normalize_country(country) in EUROPE_AND_ISRAEL
