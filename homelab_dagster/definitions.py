from dagster import AssetSelection, Definitions, ScheduleDefinition, define_asset_job
from dagster_dbt import DbtCliResource

from .assets import homelab_dbt_assets
from .lakehouse import lakehouse_raw_copy
from .project import dbt_project

daily_build = define_asset_job("daily_build", selection=AssetSelection.all() - AssetSelection.assets(lakehouse_raw_copy))
lakehouse_copy = define_asset_job("lakehouse_copy", selection=AssetSelection.assets(lakehouse_raw_copy))

defs = Definitions(
    assets=[homelab_dbt_assets, lakehouse_raw_copy],
    jobs=[daily_build, lakehouse_copy],
    schedules=[
        ScheduleDefinition(job=lakehouse_copy, cron_schedule="0 5 * * *"),
        ScheduleDefinition(job=daily_build, cron_schedule="0 6 * * *"),
    ],
    resources={"dbt": DbtCliResource(project_dir=dbt_project)},
)
