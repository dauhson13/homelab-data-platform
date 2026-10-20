import sys
from pathlib import Path

from homelab_dagster.definitions import defs

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_inventory  # noqa: E402


def test_dbt_models_become_assets():
    keys = {k.to_user_string() for k in defs.resolve_asset_graph().get_all_asset_keys()}
    assert {"namespace_summary", "image_inventory", "largest_workloads", "stg_workloads", "workloads"} <= keys


def test_schedules_cover_the_dbt_build_and_the_lakehouse_copy():
    assert sorted(s.name for s in defs.schedules) == ["daily_build_schedule", "lakehouse_copy_schedule"]


def test_memory_and_cpu_units():
    assert build_inventory.to_mb("512Mi") == 512
    assert build_inventory.to_mb("1Gi") == 1024
    assert build_inventory.to_millicores("250m") == 250
    assert build_inventory.to_millicores("2") == 2000


def test_registry_host_is_dropped_from_images():
    assert build_inventory.split_image("registry.example.com/team/app:1.2") == ("team/app", "1.2")
    assert build_inventory.split_image("redis:7-alpine") == ("redis", "7-alpine")
    assert build_inventory.split_image("postgres") == ("postgres", "latest")


def test_lakehouse_copy_is_not_part_of_the_dbt_build():
    keys = {k.to_user_string() for k in defs.resolve_job_def("daily_build").asset_layer.executable_asset_keys}
    assert "lakehouse_raw_copy" not in keys
    assert "stg_workloads" in keys


def test_json_columns_are_cast_for_iceberg():
    from homelab_dagster import lakehouse

    class Cur:
        def execute(self, sql):
            pass

        def fetchall(self):
            return [("id", "integer"), ("data", "json")]

    assert lakehouse.select_list(Cur(), "src", "public", "t") == '"id", CAST("data" AS VARCHAR) AS "data"'
