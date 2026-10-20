-- How many portfolio projects use each technology (the tech column is a comma-separated list).
select
    trim(tech_item) as technology,
    count(*) as projects
from {{ source('raw_portfolio', 'projects') }}
cross join unnest(split(tech, ',')) as t(tech_item)
where is_public = 'True' and tech is not null and trim(tech_item) <> ''
group by 1
