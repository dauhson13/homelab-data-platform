-- the namespace rollup must add up to the staging table
select s.total as staged, m.total as rolled_up
from (select sum(memory_total_mb) as total from {{ ref('stg_workloads') }}) s
cross join (select sum(memory_total_mb) as total from {{ ref('namespace_summary') }}) m
where s.total <> m.total
