from dagster import AssetSelection, Definitions, ScheduleDefinition, define_asset_job
from dagster_dbt import DbtCliResource

from .assets import homelab_dbt_assets
from .project import dbt_project

daily_build = define_asset_job("daily_build", selection=AssetSelection.all())

defs = Definitions(
    assets=[homelab_dbt_assets],
    jobs=[daily_build],
    schedules=[ScheduleDefinition(job=daily_build, cron_schedule="0 6 * * *")],
    resources={"dbt": DbtCliResource(project_dir=dbt_project)},
)
