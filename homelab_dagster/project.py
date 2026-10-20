from pathlib import Path

from dagster_dbt import DbtProject

dbt_project = DbtProject(
    project_dir=Path(__file__).resolve().parent.parent / "dbt",
    profiles_dir=Path(__file__).resolve().parent.parent / "dbt",
)
dbt_project.prepare_if_dev()
