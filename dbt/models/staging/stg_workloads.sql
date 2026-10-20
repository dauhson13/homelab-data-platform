select
    namespace,
    name,
    kind,
    replicas,
    image,
    image_tag,
    containers,
    memory_request_mb,
    cpu_request_m,
    replicas * memory_request_mb as memory_total_mb,
    replicas * cpu_request_m as cpu_total_m,
    case when replicas > 0 then true else false end as is_running,
    case when exposed = 1 then true else false end as is_exposed
from {{ ref('workloads') }}
