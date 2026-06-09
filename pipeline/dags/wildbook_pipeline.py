"""
Airflow DAG — runs the Wildbook identification pipeline daily.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import dag, task


@dag(
    dag_id="wildbook_pipeline",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "wildbook",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(hours=2),
    },
    tags=["wildbook", "ml", "identification"],
)
def wildbook_pipeline_dag():
    @task.bash
    def run_kedro_identify():
        return "cd /opt/airflow/wildbook-pipeline && kedro run --pipeline identify"

    run_kedro_identify()


dag = wildbook_pipeline_dag()
