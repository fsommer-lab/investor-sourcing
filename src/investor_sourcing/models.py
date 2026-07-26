"""Core domain objects shared across the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Fund:
    """A competitor fund whose employees we track."""

    name: str
    linkedin_slug: str
    roles_include: tuple[str, ...] = ()

    def wants_role(self, title: str) -> bool:
        if not self.roles_include:
            return True
        lowered = title.lower()
        return any(role.lower() in lowered for role in self.roles_include)


@dataclass(frozen=True)
class Employee:
    """An investor at a tracked fund.

    profile_id is the stable identifier from the data provider — for
    LinkedIn-shaped data this is the public profile slug
    (linkedin.com/in/<slug>).
    """

    profile_id: str
    name: str
    title: str
    fund_slug: str


@dataclass(frozen=True)
class Company:
    """A company that at least one tracked employee follows.

    company_id is the provider's stable identifier (LinkedIn company slug
    where available). hq_country should be an ISO 3166-1 alpha-2 code;
    the geography screen normalizes common country names as a fallback.

    Funding fields are filled by Grata enrichment, not by follow data.
    """

    company_id: str
    name: str
    hq_country: str = ""
    employee_count: int | None = None
    industry: str = ""
    description: str = ""
    website: str = ""
    ownership_status: str = ""
    total_funding_usd: int | None = None
    latest_round: str = ""
    grata_uid: str = ""

    @property
    def funding_status(self) -> str:
        """'bootstrapped' | 'funded' | 'unknown', derived from Grata data."""
        status = self.ownership_status.lower()
        if "bootstrap" in status:
            return "bootstrapped"
        if status in {"investor_backed", "investor backed", "private_equity",
                      "private equity", "public", "venture_capital"}:
            return "funded"
        if self.total_funding_usd:
            return "funded"
        return "unknown"


@dataclass(frozen=True)
class Follow:
    """Edge: employee follows company."""

    profile_id: str
    company_id: str


@dataclass
class ScoredCompany:
    """A screened company with its aggregated follow signal."""

    company: Company
    followers: list[Employee] = field(default_factory=list)

    @property
    def follower_count(self) -> int:
        return len(self.followers)

    @property
    def fund_slugs(self) -> list[str]:
        return sorted({e.fund_slug for e in self.followers})

    @property
    def fund_count(self) -> int:
        return len(self.fund_slugs)
