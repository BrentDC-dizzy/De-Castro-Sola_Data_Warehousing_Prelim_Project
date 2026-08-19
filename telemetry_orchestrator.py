import sqlite3
import pandas as pd
import hashlib
import logging
import os
import shutil
import pyarrow as pa
import pyarrow.parquet as pq

# Configure paths (dynamic, relative to this script's location)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, "shop_oltp_p1.db")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
QUARANTINE_DIR = os.path.join(PROJECT_ROOT, "quarantine")
QUARANTINE_FILE = os.path.join(QUARANTINE_DIR, "failed_vitals.csv")
LAKEHOUSE_DIR = os.path.join(PROJECT_ROOT, "data", "lakehouse")
LOG_FILE = os.path.join(LOG_DIR, "hospital_ops.log")

# Setup Logging
os.makedirs(LOG_DIR, exist_ok=True)
logger = logging.getLogger("TelemetryOrchestrator")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_FILE, mode='w')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def initialize_directories():
    """Ensure idempotency by clearing existing outputs before run."""
    try:
        logger.info("Initializing run. Clearing previous artifacts for idempotency.")
        if os.path.exists(LAKEHOUSE_DIR):
            shutil.rmtree(LAKEHOUSE_DIR)
        os.makedirs(LAKEHOUSE_DIR, exist_ok=True)
        
        if os.path.exists(QUARANTINE_FILE):
            os.remove(QUARANTINE_FILE)
        os.makedirs(QUARANTINE_DIR, exist_ok=True)
        logger.info("Directories prepared successfully.")
    except Exception as e:
        logger.error(f"Failed to prepare directories: {e}")
        raise

def hash_pii(text):
    if pd.isna(text):
        return text
    return hashlib.sha256(str(text).encode('utf-8')).hexdigest()

def execute_pipeline():
    logger.info("Starting pipeline extraction.")
    try:
        # Extract
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM orders", conn)
        conn.close()
        logger.info(f"Extracted {len(df)} rows from {DB_PATH}.")
        
        # Identify anomalies
        logger.info("Validating and quarantining anomalous records.")
        # Null patient_id or negative vital sign or null vital sign
        anomaly_mask = df['patient_id'].isna() | (df['vital_sign_reading'] < 0) | df['vital_sign_reading'].isna()
        
        # Quarantine
        failed_records = df[anomaly_mask].copy()
        clean_records = df[~anomaly_mask].copy()
        
        # Hash PII in quarantined records before writing (regulatory compliance)
        if not failed_records.empty:
            failed_records['patient_name'] = failed_records['patient_name'].apply(hash_pii)
            failed_records['patient_id'] = failed_records['patient_id'].apply(hash_pii)
            failed_records.to_csv(QUARANTINE_FILE, index=False)
            logger.info(f"Archived {len(failed_records)} corrupted rows to {QUARANTINE_FILE}.")
        else:
            logger.info("No anomalies found in the source data.")
            
        # Clean text
        logger.info("Standardizing text fields and hashing PII.")
        clean_records['department'] = clean_records['department'].str.strip().str.lower()
        
        # Hash PII
        clean_records['patient_name'] = clean_records['patient_name'].apply(hash_pii)
        clean_records['patient_id'] = clean_records['patient_id'].apply(hash_pii)
        
        # Feature Engineering for Partitioning
        logger.info("Extracting year partition key from order_date.")
        clean_records['year'] = pd.to_datetime(clean_records['order_date']).dt.year.astype(str)
        # Rename department to dept to match output partition specs (dept=cardiology/...)
        clean_records = clean_records.rename(columns={'department': 'dept'})
        
        # Serialize to Parquet via PyArrow (pandas uses pyarrow under the hood)
        logger.info("Serializing to Hive-style partitioned Apache Parquet.")
        clean_records.to_parquet(
            path=LAKEHOUSE_DIR,
            engine='pyarrow',
            partition_cols=['dept', 'year'],
            compression='snappy',
            index=False
        )
        logger.info(f"Successfully wrote {len(clean_records)} clean records to {LAKEHOUSE_DIR}.")
        
    except Exception as e:
        logger.exception(f"Pipeline execution halted due to an unexpected error: {e}")

if __name__ == "__main__":
    initialize_directories()
    execute_pipeline()
