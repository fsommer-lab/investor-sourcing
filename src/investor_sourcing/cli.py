"""Command-line entry point.

    investor-sourcing add-employee   --fund <slug> --profile-id <id> --name <name> [--title <title>]
    investor-sourcing import-follows --profile-id <id> [--file paste.txt]   # or paste via stdin
    investor-sourcing collect --provider csv [--data-root data/manual]
    investor-sourcing enrich          # fill country/headcount/funding via Grata (GRATA_API_KEY)
    investor-sourcing screen  [--out output/]
    investor-sourcing run     # collect + screen in one go
    investor-sourcing query --keywords marketplace --funding bootstrapped --limit 10
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import config, intake, pipeline, report
from .models import Employee
from .providers import get_provider
from .screening.geography import normalize_country
from .storage import Store

DEFAULT_DB = Path("data/cache.db")
DEFAULT_OUT = Path("output")
DEFAULT_MANUAL_ROOT = Path("data/manual")


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

    unknown = [c for c in store.companies() if not normalize_country(c.hq_country)]
    if unknown:
        path = args.out / "needs_country.csv"
        report.write_needs_country(unknown, path)
        print(f"\nNote: {len(unknown)} cached companies have no recognizable HQ country "
              f"and were skipped by the geography screen -> {path}")
        print("Fill in hq_country in your follows.csv (or enrich via your data platform) "
              "and re-run collect + screen.")


def _do_enrich(args: argparse.Namespace, store: Store) -> None:
    from .grata import GrataClient, GrataError

    try:
        client = GrataClient()
    except GrataError as exc:
        print(exc)
        raise SystemExit(1)
    companies = store.companies()
    todo = [
        c for c in companies
        if args.all or not (c.hq_country and c.ownership_status)
    ]
    print(f"Enriching {len(todo)} of {len(companies)} cached companies via Grata...")
    hits = 0
    for company in todo:
        enriched = client.enrich(company)
        if enriched is None:
            print(f"  not found: {company.name}")
            continue
        store.upsert_company(enriched)
        hits += 1
        print(f"  {enriched.name:<35} {enriched.hq_country:<3} "
              f"funding={enriched.funding_status}")
    store.commit()
    print(f"Enriched {hits}/{len(todo)}.")


def _do_query(args: argparse.Namespace, store: Store) -> None:
    import dataclasses

    filters = config.load_filters(args.filters)
    overrides = {}
    if args.keywords:
        overrides["keywords_include"] = [k.strip() for k in args.keywords.split(",")]
    if args.industries:
        overrides["industries_include"] = [k.strip() for k in args.industries.split(",")]
    if args.funding:
        overrides["funding_profile"] = args.funding
    filters = dataclasses.replace(filters, **overrides)

    results = pipeline.screen(store, filters)
    unknown_funding = 0
    if args.funding:
        relaxed = dataclasses.replace(filters, funding_profile="")
        unknown_funding = sum(
            1 for r in pipeline.screen(store, relaxed)
            if r.company.funding_status == "unknown"
        )

    top = results[: args.limit]
    report.write_csv(top, args.out / "query_results.csv")
    print(f"Top {len(top)} matches (of {len(results)} passing) -> {args.out}/query_results.csv\n")
    for r in top:
        funding = r.company.funding_status
        print(f"  {r.company.name:<35} {r.company.hq_country:<3} "
              f"followers={r.follower_count} funds={r.fund_count} funding={funding}")
        if r.company.description:
            print(f"      {r.company.description[:100]}")
    if unknown_funding:
        print(f"\nNote: {unknown_funding} otherwise-matching companies have unknown "
              f"funding status — run `investor-sourcing enrich` to classify them.")


def _do_add_employee(args: argparse.Namespace) -> None:
    employee = Employee(
        profile_id=args.profile_id,
        name=args.name,
        title=args.title or "",
        fund_slug=args.fund,
    )
    intake.append_employee(args.data_root, employee)
    print(f"Added {employee.name} ({employee.fund_slug}) to {args.data_root / 'employees.csv'}")


def _do_import_follows(args: argparse.Namespace) -> None:
    if args.file:
        text = args.file.read_text(encoding="utf-8")
    else:
        print("Paste the copied 'Interests > Companies' text, then press Ctrl-D:")
        text = sys.stdin.read()
    names = intake.parse_followed_companies(text)
    if not names:
        print("No company names recognized in the pasted text — nothing written.")
        return
    written = intake.append_follows(args.data_root, args.profile_id, names)
    print(f"Wrote {written} follow rows for {args.profile_id} to "
          f"{args.data_root / 'follows.csv'}:")
    for name in names:
        print(f"  {name}")
    print("hq_country is blank on new rows — fill it in before screening.")


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

    p_enrich = sub.add_parser("enrich", help="fill country/headcount/funding data via Grata")
    _add_common(p_enrich)
    p_enrich.add_argument("--all", action="store_true",
                          help="re-enrich every company, not just those missing data")

    p_query = sub.add_parser(
        "query",
        help="ad-hoc thesis screen, e.g. --keywords marketplace --funding bootstrapped --limit 10",
    )
    _add_common(p_query)
    _add_screen_args(p_query)
    p_query.add_argument("--keywords", default="",
                         help="comma-separated, matched against name+description")
    p_query.add_argument("--industries", default="", help="comma-separated industry substrings")
    p_query.add_argument("--funding", default="", choices=["", "bootstrapped", "funded"],
                         help="require a Grata-derived funding status")
    p_query.add_argument("--limit", type=int, default=10)

    p_add = sub.add_parser("add-employee", help="record one tracked employee (manual workflow)")
    p_add.add_argument("--fund", required=True, help="fund linkedin_slug from funds.yaml")
    p_add.add_argument("--profile-id", required=True, help="profile slug (linkedin.com/in/<slug>)")
    p_add.add_argument("--name", required=True)
    p_add.add_argument("--title", default="")
    p_add.add_argument("--data-root", type=Path, default=DEFAULT_MANUAL_ROOT)

    p_imp = sub.add_parser(
        "import-follows",
        help="parse pasted 'Interests > Companies' text into follows.csv (manual workflow)",
    )
    p_imp.add_argument("--profile-id", required=True, help="employee the follows belong to")
    p_imp.add_argument("--file", type=Path, default=None, help="read pasted text from a file instead of stdin")
    p_imp.add_argument("--data-root", type=Path, default=DEFAULT_MANUAL_ROOT)

    args = parser.parse_args(argv)

    if args.command == "add-employee":
        _do_add_employee(args)
        return 0
    if args.command == "import-follows":
        _do_import_follows(args)
        return 0

    store = Store(args.db)
    try:
        if args.command in ("collect", "run"):
            _do_collect(args, store)
        if args.command in ("screen", "run"):
            _do_screen(args, store)
        if args.command == "enrich":
            _do_enrich(args, store)
        if args.command == "query":
            _do_query(args, store)
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
