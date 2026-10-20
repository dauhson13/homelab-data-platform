with ranked as (
    select
        namespace,
        name,
        kind,
        memory_total_mb,
        cpu_total_m,
        row_number() over (order by memory_total_mb desc, namespace, name) as memory_rank
    from {{ ref('stg_workloads') }}
    where is_running
)
select * from ranked where memory_rank <= 15
