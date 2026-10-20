-- n8n executions per workflow and status, with the average run time in seconds.
select
    w.name as workflow,
    e.status,
    count(*) as executions,
    avg(date_diff('millisecond', e.startedat, e.stoppedat)) / 1000.0 as avg_seconds
from {{ source('raw_postgres_n8n', 'public__execution_entity') }} e
join {{ source('raw_postgres_n8n', 'public__workflow_entity') }} w on w.id = e.workflowid
group by 1, 2
