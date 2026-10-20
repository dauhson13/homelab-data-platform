"""Copy every table from the databases Trino federates into Iceberg tables.

Each source catalog (postgres, sandbox_mysql, ...) becomes an Iceberg schema
named raw_<catalog>, and each table is a full refresh of the source table.
"""
import os
import warnings

import trino

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

SOURCES = [
    "postgresql", "postgres_metabase", "postgres_n8n", "postgres_dagster",
    "sandbox_postgres", "sandbox_mysql", "sandbox_sqlserver", "sandbox_mongodb",
]
SKIP_SCHEMAS = {"information_schema", "pg_catalog", "sys", "INFORMATION_SCHEMA", "performance_schema", "mysql"}
TARGET = "iceberg"
# Login, credential and session tables stay out of the analytics copy.
SENSITIVE = ("user", "credential", "secret", "session", "token", "password", "auth", "api_key", "setting", "login")


def is_sensitive(table):
    name = table.lower()
    return any(word in name for word in SENSITIVE)


def connect():
    host = os.environ.get("LAKEHOUSE_HOST", "trino.data.svc.cluster.local")
    return trino.dbapi.connect(
        host=host,
        port=int(os.environ.get("LAKEHOUSE_PORT", "8443")),
        user=os.environ["TRINO_USER"],
        http_scheme="https",
        auth=trino.auth.BasicAuthentication(os.environ["TRINO_USER"], os.environ["TRINO_PASSWORD"]),
        verify=os.environ.get("TRINO_VERIFY", "false").lower() == "true",
    )


def _rows(cur, sql):
    cur.execute(sql)
    return cur.fetchall()


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def select_list(cur, src, schema, table):
    """Column list for the copy; Iceberg has no json type, so json columns are written as text."""
    cols = _rows(cur, f"SELECT column_name, data_type FROM {src}.information_schema.columns "
                      f"WHERE table_schema = '{schema}' AND table_name = '{table}' ORDER BY ordinal_position")
    return ", ".join(f"json_format({quote(c)}) AS {quote(c)}" if t == "json" else quote(c) for c, t in cols)


def sync(log=print):
    """Full refresh of every source table. Returns (copied, failed) lists."""
    conn = connect()
    cur = conn.cursor()
    copied, failed = [], []
    for src in SOURCES:
        dest_schema = f"raw_{src}"
        try:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {TARGET}.{dest_schema}")
            cur.fetchall()
            tables = _rows(cur, f"SELECT table_schema, table_name FROM {src}.information_schema.tables "
                                f"WHERE table_type = 'BASE TABLE'")
        except Exception as exc:
            failed.append((src, str(exc)[:200]))
            log(f"{src}: cannot list tables: {exc}")
            continue
        for schema, table in tables:
            if schema in SKIP_SCHEMAS or is_sensitive(table):
                continue
            dest = f"{TARGET}.{dest_schema}.{quote(schema + '__' + table)}"
            try:
                cur.execute(f"CREATE OR REPLACE TABLE {dest} AS "
                            f"SELECT {select_list(cur, src, schema, table)} FROM {src}.{quote(schema)}.{quote(table)}")
                cur.fetchall()
                copied.append(f"{src}.{schema}.{table}")
                log(f"copied {src}.{schema}.{table}")
            except Exception as exc:
                failed.append((f"{src}.{schema}.{table}", str(exc)[:200]))
                log(f"{src}.{schema}.{table}: {exc}")
    return copied, failed


def _asset():
    from dagster import AssetExecutionContext, asset

    @asset(name="lakehouse_raw_copy", group_name="lakehouse")
    def lakehouse_raw_copy(context: AssetExecutionContext):
        copied, failed = sync(context.log.info)
        context.log.info(f"copied {len(copied)} tables, {len(failed)} failed")
        return {"copied": len(copied), "failed": len(failed)}

    return lakehouse_raw_copy


try:
    lakehouse_raw_copy = _asset()
except ImportError:  # plain-script run without dagster installed
    lakehouse_raw_copy = None


if __name__ == "__main__":
    ok, bad = sync()
    print(f"copied {len(ok)} tables, {len(bad)} failed")
    raise SystemExit(1 if bad and not ok else 0)
