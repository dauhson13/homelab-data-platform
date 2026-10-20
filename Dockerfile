FROM python:3.12-slim

WORKDIR /opt/dagster/app
COPY pyproject.toml ./
COPY homelab_dagster ./homelab_dagster
COPY dbt ./dbt
RUN pip install --no-cache-dir . \
 && DBT_TARGET=trino LAKEHOUSE_HOST=build dagster-dbt project prepare-and-package --file homelab_dagster/project.py

EXPOSE 3030
CMD ["dagster", "code-server", "start", "-h", "0.0.0.0", "-p", "3030", "-m", "homelab_dagster.definitions"]
