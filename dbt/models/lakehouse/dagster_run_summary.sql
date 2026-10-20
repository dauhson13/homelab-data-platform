-- Dagster runs per day and status, from the copy of its run storage.
select
    date(create_timestamp) as run_date,
    status,
    count(*) as runs
from {{ source('raw_postgres_dagster', 'public__runs') }}
group by 1, 2
