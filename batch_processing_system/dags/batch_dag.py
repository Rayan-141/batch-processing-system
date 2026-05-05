from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

# Ensure the processor module can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processor import process_daily_data

# Default arguments for the DAG
default_args = {
    'owner': 'rayan_rawat',
    'depends_on_past': False,
    'start_date': datetime(2023, 10, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    'nightly_data_processing',
    default_args=default_args,
    description='A batch processing DAG to aggregate daily transactions.',
    schedule_interval='@daily', # Runs at midnight every day
    catchup=False
)

def run_processing(**kwargs):
    """
    Wrapper function to extract execution date from Airflow context
    and pass it to our Pandas processing script.
    """
    # kwargs['ds'] gives the execution date as YYYY-MM-DD
    execution_date = kwargs['ds'] 
    process_daily_data(execution_date)

# Define the processing task
process_task = PythonOperator(
    task_id='process_data_pandas',
    python_callable=run_processing,
    provide_context=True,
    dag=dag,
)

process_task
