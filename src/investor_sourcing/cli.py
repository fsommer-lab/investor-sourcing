"""Command-line entry point.

    investor-sourcing collect --provider csv [--data-root data/manual]
    investor-sourcing screen  [--out output/]
    investor-sourcing run     # collect + screen in one go
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import config, pipeline, report
from .providers import get_provider
from .storage import Store

DEFAULT_DB = Path("data/cache.db")
DEFAULT_OUT = Path("output")


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite cache path")
    parser.add_argument("--funds", type=Path, default=None, help="funds.yaml path")


def _add_collect_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", default="csv", help="data provider (default: csv)")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="root directory for the csv provider (default: data/manual)",
    )


def _add_screen_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--filters", type=Path, default=None, help="filters.yaml path")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory")


def _build_provider(args: argparse.Namespace):
    kwargs = {}
    if args.provider == "csv" and args.data_root is not None:
        kwargs["root"] = args.data_root
    return get_provider(args.provider, **kwargs)


def _do_collect(args: argparse.Namespace, store: Store) -> None:
    funds = config.load_funds(args.funds)
    provider = _build_provider(args)
    pipeline.collect(store, provider, funds)
    print(f"Collected: {len(store.employees())} employees, "
          f"{len(store.companies())} companies, {len(store.follows())} follow edges.")


def _do_screen(args: argparse.Namespace, store: Store) -> None:
    filters = config.load_filters(args.filters)
    results = pipeline.screen(store, filters)
    report.write_csv(results, args.out / "screened_companies.csv")
    report.write_markdown(results, args.out / "screened_companies.md")
    print(f"{len(results)} companies passed the screen -> {args.out}/screened_companies.csv")
    for r in results[:15]:
        print(f"  {r.company.name:<35} {r.company.hq_country:<3} "
              f"followers={r.follower_count} funds={r.fund_count}")


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="investor-sourcing")
    sub = parser.add_subparsers(dest="command", required=True)

    p_collect = sub.add_parser("collect", help="pull employees + follows into the cache")
    _add_common(p_collect)
    _add_collect_args(p_collect)

    p_screen = sub.add_parser("screen", help="filter + score cached data, write reports")
    _add_common(p_screen)
    _add_screen_args(p_screen)

    p_run = sub.add_parser("run", help="collect then screen")
    _add_common(p_run)
    _add_collect_args(p_run)
    _add_screen_args(p_run)

    args = parser.parse_args(argv)
    store = Store(args.db)
    try:
        if args.command in ("collect", "run"):
            _do_collect(args, store)
        if args.command in ("screen", "run"):
            _do_screen(args, store)
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
