# Batch Processing System

This project is the complete start-to-end implementation for **Problem Statement 114: Batch Processing System**. It uses Python, FastAPI, Pandas, SQLite, and Apache Airflow as requested.

## Components:
1. **`database.py`**: Initializes the SQLite database and generates random dummy data to act as "raw data" for the batch jobs.
2. **`processor.py`**: The core data engine. It extracts data using Pandas, aggregates it (sum of amounts, transaction counts), and loads the final report back into the database. It handles data chunking for scalability.
3. **`api.py`**: A FastAPI application to view the generated reports or trigger batch jobs manually.
4. **`dags/batch_dag.py`**: An Apache Airflow Directed Acyclic Graph that orchestrates and schedules the batch job to run nightly.

## How to Run Locally

### 1. Initialize the Database
```bash
python database.py
```
*This creates `batch_data.db` and populates it with transactions from the past 3 days.*

### 2. Test the Batch Processing Manually
```bash
python processor.py
```
*This simulates a manual run of the batch script for yesterday's data.*

### 3. Run the API (FastAPI)
```bash
pip install -r requirements.txt
python api.py
```
You can access the documentation at [http://localhost:8000/docs](http://localhost:8000/docs).
* Endpoints:
  - `GET /reports`: View all processed reports.
  - `GET /reports/{date}`: View a report for a specific date.
  - `POST /trigger_job/{date}`: Trigger a job manually in the background.

### 4. (Optional) Run with Docker (Includes Airflow and Redis)
```bash
docker-compose up -d
```
* Access Airflow UI: [http://localhost:8080](http://localhost:8080)
* Access FastAPI: [http://localhost:8000/docs](http://localhost:8000/docs)
