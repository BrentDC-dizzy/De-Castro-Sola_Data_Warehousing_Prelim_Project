# Healthcare Operations & Patient Telemetry DataWarehousing Pipeline

## Overview
This repository contains a full Data Engineering pipeline for a simulated regional hospital network. The project safely ingests mock telemetry rows from a transactional database (SQLite), standardizes strings, securely hashes sensitive Patient IDs and Names (PII), isolates anomalous values (e.g., negative vital readings), and serializes validated data into a Hive-partitioned Data Lake (Apache Parquet format).

## Project Structure
```
DeCastro-Sola_prelim_project/
├── data/
│   └── lakehouse/              <-- Hive-partitioned Apache Parquet (dept=.../year=...)
├── logs/
│   └── hospital_ops.log        <-- Trace execution logs of the orchestrator
├── quarantine/
│   └── failed_vitals.csv       <-- Isolated corrupted telemetry records (PII-hashed)
├── requirements.txt            <-- Python environment dependencies lock 
├── generate_mock_db.py         <-- Simulator script to build the source SQLite data
├── telemetry_orchestrator.py   <-- Main execution ETL pipeline
├── DataOps_Report.md           <-- Architectural decisions for Data Operations
└── README.md                   <-- Project execution documentation
```

## Setup Instructions

### 1. Requirements
- Python 3.10+
- Git

### 2. Initialization 
Navigate into the working directory and create your virtual environment. Ensure you activate your virtual environment before proceeding.

**Windows PowerShell:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**MacOS/Linux bash:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Dependency Installation
Install the core data libraries within the active environment:
```bash
pip install -r requirements.txt
```

## System Execution
Proceed with the data transformation workflow. 

### Step 1: Initialize Mock Source System
Run the simulation generation script. This creates a `shop_oltp_p1.db` SQLite database possessing exactly 4,000 synthetic patient telemetry rows. Note that roughly ~10% of the dataset is systematically corrupted to simulate real-world ETL issues.
```bash
python generate_mock_db.py
```

### Step 2: Execute Telemetry Orchestrator
Execute the core pipeline.
```bash
python telemetry_orchestrator.py
```

### Step 3: Analyze Architecture Outputs
1. Track pipeline step-by-step progress metrics and anomaly discovery counts inside `logs/hospital_ops.log`.
2. Inspect `quarantine/failed_vitals.csv` to witness safely sequestered corrupted values (with PII fields cryptographically hashed).
3. Open `data/lakehouse/` where you will see the generated Parquet databases correctly partitioned into `dept=*/year=*` Hive folders containing secure, production-grade output schemas for downstream analysis.
