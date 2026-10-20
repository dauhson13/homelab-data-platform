# homelab-data-platform

A dbt project and a Dagster project that model the workloads running in my homelab Kubernetes cluster: what runs in each namespace, how much memory and CPU it asks for, and which container images are used where.

The source data is a CSV built from the cluster's Kubernetes manifests (`scripts/build_inventory.py`). Only names, sizes and image repositories go in it, with no hostnames, addresses or secrets. Client namespaces are skipped.

## Layout

```
dbt/                  dbt project (seed, staging view, marts, tests)
homelab_dagster/      Dagster code location that runs the dbt project
scripts/              build_inventory.py regenerates the seed from manifests
tests/                pytest checks for the Dagster definitions and the script
deploy/               example values for the Dagster Helm chart
Dockerfile            image for the Dagster code location
```

Models:

| model | what it shows |
| --- | --- |
| `stg_workloads` | one row per Deployment, StatefulSet or DaemonSet, with totals per replica count |
| `namespace_summary` | workloads, replicas, memory and CPU requests per namespace |
| `image_inventory` | how many workloads and namespaces use each image |
| `largest_workloads` | the 15 running workloads that request the most memory |

## Run it locally

dbt runs on DuckDB by default, so nothing else is needed.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cd dbt
dbt build --profiles-dir .
```

## Run it in Dagster

```bash
dagster dev -m homelab_dagster.definitions
```

Every dbt model and seed shows up as an asset. A job called `daily_build` and a schedule that runs it at 06:00 are included.

## Refresh the data

```bash
python scripts/build_inventory.py /path/to/k8s-manifests
cd dbt && dbt build --profiles-dir .
```

## Use Trino instead of DuckDB

The `trino` target in `dbt/profiles.yml` reads its connection from environment variables:

```bash
export DBT_TARGET=trino
export LAKEHOUSE_HOST=trino.example.internal
export TRINO_USER=dbt
export LAKEHOUSE_PASSWORD=...
export TRINO_CATALOG=iceberg
export TRINO_SCHEMA=homelab
dbt build --profiles-dir .
```

The models under `dbt/models/lakehouse` only build on the Trino target. They read the Iceberg tables described below.

## Copy databases into the lakehouse

`homelab_dagster/lakehouse.py` reads every table from the databases that Trino can see (PostgreSQL, MySQL, SQL Server, MongoDB) plus the public content of a portfolio API, and rewrites them as Iceberg tables in `iceberg.raw_<catalog>`.

- It is a full refresh, except for tables listed in `INCREMENTAL`, which load only rows past a key.
- Tables whose names suggest logins, credentials or sessions are skipped.
- JSON columns are written as text, because Iceberg has no JSON type.
- Each run adds a row to `iceberg.ops.copy_runs` and the process exits non-zero if any table failed.

It runs as the `lakehouse_raw_copy` Dagster asset on a daily schedule, or directly with `python -m homelab_dagster.lakehouse`.

## Run it on the cluster

Build the image, push it to your registry and add `deploy/user-deployment.yaml` to the `dagster-user-deployments` section of the Dagster Helm values. The deployment file sets the Trino variables above for the code location.

## Tests

```bash
dbt build --profiles-dir dbt --project-dir dbt
pytest
```

