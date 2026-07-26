"""Provider interfaces — the only place that knows where the data comes from.

LinkedIn exposes no official API for a member's followed companies, and
scraping it with a logged-in session breaches LinkedIn's user agreement.
The pipeline therefore treats data acquisition as pluggable:

* a licensed people/company data vendor -> implement a new Provider
* a manual export / research workflow   -> CsvProvider (bundled)

A Provider implements both halves (employees of a fund, follows of an
employee); split implementations can mix in the two protocols separately.
"""

from __future__ import annotations

from typing import Iterable, Protocol, runtime_checkable

from ..models import Company, Employee, Follow, Fund


@runtime_checkable
class EmployeeProvider(Protocol):
    def fetch_employees(self, fund: Fund) -> Iterable[Employee]:
        """Yield current employees of the fund (pre role-filtering)."""
        ...


@runtime_checkable
class FollowProvider(Protocol):
    def fetch_followed_companies(
        self, employee: Employee
    ) -> Iterable[tuple[Company, Follow]]:
        """Yield (company, follow-edge) pairs for one employee."""
        ...


class Provider(EmployeeProvider, FollowProvider, Protocol):
    """Full provider: both employee discovery and follow extraction."""
