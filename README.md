# investor-sourcing

Screens employees of competitor funds and surfaces the **European and
Israeli companies they follow**. A company followed by several investors
across several competitor funds is a sourcing signal worth a look.

The target workflow — *"tell me 10 bootstrapped vertical marketplaces"*:

```bash
investor-sourcing query --keywords "marketplace" --funding bootstrapped --limit 10
```

...which screens the follow data of tracked competitor-fund employees for
European/Israeli companies matching the category, cross-checked against
**Grata** funding data to confirm they are actually bootstrapped.

## How it works

```
config/funds.yaml                        config/filters.yaml + query flags
      |                                            |
      v                                            v
  [collect] --provider--> SQLite cache --[screen/query]--> output/*.csv
                              ^
                              |
                          [enrich]  <-- Grata API (country, headcount,
                                        industry, ownership, funding)
```

1. **collect** — for each fund in `config/funds.yaml`, pull its employees
   (filtered to investing roles via `roles_include`), then each employee's
   followed companies. Everything lands in a local SQLite cache
   (`data/cache.db`), so runs are incremental.
2. **enrich** — fill in HQ country, headcount, industry, description, and
   ownership/funding for cached companies via the Grata API
   (`export GRATA_API_KEY=...`). Blank fields never overwrite existing
   data, so enrichment and manual research compose safely.
3. **screen / query** — from the cache, keep companies headquartered in
   Europe or Israel, apply the filters in `config/filters.yaml` (plus any
   per-query flags), and rank by how many tracked investors follow each
   company and across how many distinct funds.
4. **report** — CSV + Markdown in `output/`.

Because screening runs off the cache, you can iterate on filters without
re-collecting.

## Usage

```bash
pip install -e .

# End-to-end with the bundled sample data:
investor-sourcing run --provider csv --data-root data/samples

# Or stage by stage:
investor-sourcing collect --provider csv --data-root data/manual
export GRATA_API_KEY=...       # from your Grata workspace settings
investor-sourcing enrich       # funding + firmographics cross-check
investor-sourcing screen

# Thesis queries against the enriched cache:
investor-sourcing query --keywords "marketplace" --funding bootstrapped --limit 10
investor-sourcing query --industries "cybersecurity" --funding funded --limit 20
```

### Manual research workflow (account-safe)

```bash
# 1. Record an employee you found while browsing a fund's people page:
investor-sourcing add-employee --fund example-growth-partners \
    --profile-id jane-doe-123 --name "Jane Doe" --title Principal

# 2. On their profile, open Interests > Companies, select-all, copy,
#    then paste into:
investor-sourcing import-follows --profile-id jane-doe-123
# (UI chrome like "Following" / "12,345 followers" is stripped automatically)

# 3. Fill in hq_country on the new follows.csv rows, then:
investor-sourcing run --provider csv --data-root data/manual
# Companies still missing a country land in output/needs_country.csv.
```

## Keeping your LinkedIn account safe

The only approach with zero ban risk is: **no automation ever touches your
logged-in account.** This repo is built around that rule.

Safe (what this tool supports):

- **Browse normally, paste, import.** You open profiles yourself in your
  own browser at human pace — ordinary LinkedIn usage. Copy the
  "Interests → Companies" section and run `import-follows`; the parsing
  and data entry happen locally, offline.
- **Licensed vendor data.** A vendor's export goes through the same CSV
  format (or a new Provider). Your account is never involved.

Not safe (never wire these into this tool):

- Headless browsers, bots, or scripts driving your logged-in session —
  LinkedIn detects request patterns, not just volume.
- Browser extensions that auto-visit or auto-scrape profiles. Many
  "sales automation" extensions get accounts restricted.
- Sharing your session cookie with any third-party service.
- Even "slow" automation: one detection is enough, and restrictions often
  hit the account, not the tool.

Practical habits for the manual workflow: keep daily profile views in the
range you'd browse anyway (LinkedIn also caps commercial-use search on
free accounts), spread research over days rather than marathon sessions,
and prefer Sales Navigator if you're doing heavy people-search — it's the
product LinkedIn sells for exactly this usage.

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
