select
    namespace,
    count(*) as workloads,
    sum(case when is_running then 1 else 0 end) as running_workloads,
    sum(replicas) as replicas,
    sum(memory_total_mb) as memory_total_mb,
    sum(cpu_total_m) as cpu_total_m,
    sum(case when is_exposed then 1 else 0 end) as exposed_workloads
from {{ ref('stg_workloads') }}
group by namespace
