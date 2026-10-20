-- One row per raw_* schema in the lakehouse with its table count.
select
    table_schema as source_schema,
    count(*) as tables
from iceberg.information_schema.tables
where table_schema like 'raw\_%' escape '\'
group by 1
