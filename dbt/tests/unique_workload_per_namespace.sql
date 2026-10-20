-- a workload name should appear once per namespace
select namespace, name, count(*) as copies
from {{ ref('stg_workloads') }}
group by namespace, name
having count(*) > 1
