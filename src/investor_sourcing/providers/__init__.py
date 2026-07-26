from .base import EmployeeProvider, FollowProvider, Provider
from .csv_provider import CsvProvider

PROVIDERS: dict[str, type[Provider]] = {
    "csv": CsvProvider,
}


def get_provider(name: str, **kwargs) -> Provider:
    try:
        cls = PROVIDERS[name]
    except KeyError:
        raise ValueError(f"Unknown provider '{name}'. Available: {', '.join(PROVIDERS)}") from None
    return cls(**kwargs)


__all__ = ["EmployeeProvider", "FollowProvider", "Provider", "CsvProvider", "get_provider"]
