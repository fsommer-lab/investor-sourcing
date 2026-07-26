# investor-sourcing

Screens employees of competitor funds and surfaces the **European and
Israeli companies they follow**. A company followed by several investors
across several competitor funds is a sourcing signal worth a look.

## How it works

```
config/funds.yaml            config/filters.yaml
      |                             |
      v                             v
  [collect] --provider--> SQLite cache --[screen]--> output/screened_companies.{csv,md}
```

1. **collect** — for each fund in `config/funds.yaml`, pull its employees
   (filtered to investing roles via `roles_include`), then each employee's
   followed companies. Everything lands in a local SQLite cache
   (`data/cache.db`), so runs are incremental.
2. **screen** — from the cache, keep companies headquartered in Europe or
   Israel, apply the filters in `config/filters.yaml`, and rank by how many
   tracked investors follow each company and across how many distinct funds.
3. **report** — CSV + Markdown in `output/`.

Because screening runs off the cache, you can iterate on filters without
re-collecting.

## Usage

```bash
pip install -e .

# End-to-end with the bundled sample data:
investor-sourcing run --provider csv --data-root data/samples

# Or stage by stage:
investor-sourcing collect --provider csv --data-root data/manual
investor-sourcing screen
```

## Data providers

LinkedIn has **no official API** for the companies a member follows, and
scraping that data with a logged-in session violates LinkedIn's user
agreement. Data acquisition is therefore an interface
(`src/investor_sourcing/providers/base.py`) with two halves:

- `fetch_employees(fund)` — the people at a tracked fund
- `fetch_followed_companies(employee)` — the companies each person follows

Bundled today:

- **csv** — reads `employees.csv` / `follows.csv` from a directory
  (manual research, analyst workflow, or a licensed vendor's export).

To add a vendor integration, implement the `Provider` protocol and register
it in `providers/__init__.py`. The rest of the pipeline is source-agnostic.

## Configuration

- `config/funds.yaml` — the competitor funds to track and which roles count.
- `config/filters.yaml` — screening filters: signal thresholds
  (`min_followers`, `min_funds`), employee count range, industry/keyword
  include/exclude, and noise suppression (`exclude_companies` for the
  Googles of the world, `exclude_portfolio` for a fund's own investments).
  Geography (Europe + Israel) is always enforced and lives in
  `src/investor_sourcing/screening/geography.py`.

## Layout

```
src/investor_sourcing/
├── cli.py            # collect / screen / run commands
├── config.py         # YAML loading + Filters dataclass
├── models.py         # Fund, Employee, Company, Follow, ScoredCompany
├── pipeline.py       # orchestration
├── storage.py        # SQLite cache
├── scoring.py        # aggregation + ranking
├── report.py         # CSV / Markdown output
├── providers/        # pluggable data sources
└── screening/        # geography + declarative filters
```
