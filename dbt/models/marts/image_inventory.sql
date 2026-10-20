select
    image,
    count(*) as workloads,
    count(distinct namespace) as namespaces,
    count(distinct image_tag) as tags_in_use
from {{ ref('stg_workloads') }}
group by image
