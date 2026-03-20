# Data Hub - Audit Log Dashboard

A Streamlit app for visualizing audit_log metrics from the Data Hub PostgreSQL database.

## Setup

1. Create a virtual environment:
```bash
cd streamlit_app
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set the database URL (optional, defaults to local):
```bash
export DATABASE_URL="postgresql://datahub:datahub@localhost:5432/datahub"
```

## Run

```bash
streamlit run app.py
```

The dashboard will open at http://localhost:8501

## Features

- **Key Metrics**: Total records, added count, duplicate count, duplicate rate
- **Filters**: Filter by model, connection ID, and status
- **Charts**:
  - Records by model
  - Records by status
  - Records over time (daily)
  - Records by connection ID
- **Model x Status breakdown table**
- **Recent entries table** (last 100 records)
