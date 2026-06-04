# Datasets

## Synthetic Demo Data

The project ships with a synthetic demo dataset starter pack so local
profiling, pattern detection, and vulnerability detection all have
representative data immediately after `decision-system seed-demo-data`.

These files are safe to commit; no real company information is included.

## Real / Private Company Data

Do **not** commit real company data to this repository. Keep private CSV
files under `company_data/<category>/` and rely on `.gitignore` to
exclude everything except `demo_*.csv` files.

If you need to source private data, place it in `company_data/` alongside
the demo files; the profiler and graph extractors will see it locally
without ever checking it in.

## Public Datasets

Public datasets are useful for larger and more realistic profiling and
detection scenarios. They should live in the ignored `datasets/` folder
and never be committed directly.

### Recommended public datasets

| Dataset | Source | Fits in | Notes |
|---------|--------|----------|-------|
| **UCI Online Retail** | UCI Machine Learning Repository | `sales` | Contains invoice-level transactions with product descriptions and quantities. Good for channel-concentration and billing-pattern detection. |
| **Tableau Sample Superstore** | Tableau Public / data.world | `sales` / `customers` | Classic retail dataset with orders, customers, regions, and profit. Rich enough to build early claim-ledger contradictions (e.g., profit vs. discount analysis). |
| **Microsoft AdventureWorks** | docs.microsoft.com | `sales` / `products` / `operations` | Sample OLTP data with product catalogue, sales orders, and vendor data. Good for entity-relationship extraction demos once `.bak` files are restored to SQL Server. |
| **Google Analytics Demo Account** | analytics.google.com | `analytics` | Demographics, sessions, traffic sources, and conversion data. Good for testing `analytics` and `marketing` profiling. |

## Dataset Lifecycle

```text
downloaded public dataset
        |
        v
  datasets/ (ignored local folder)
        |
  decision-system import-datasets --source-dir datasets --max-rows 5000
        |
        v
  company_data/<category>/demo_*.csv  (safe to commit)
  company_data/<category>/imported_*.csv  (ignored by git)
  company_data/<category>/private_*.csv  (ignored by git)
        |
  decision-system profile-data
        |
        v
  .decision_system/data_profiles/profiles.json  (generated local state)
```

## Adding a New Public Dataset

1. Place the extracted CSV (or Excel) file into `datasets/`.
2. Run `decision-system import-datasets --source-dir datasets --max-rows 5000`.
3. Inspect the result with `decision-system inspect-imports`.
4. Profile it with `decision-system profile-data`.

SQL Server `.bak` files are not yet supported. Restore them in SQL Server
and export the relevant tables to CSV first.
