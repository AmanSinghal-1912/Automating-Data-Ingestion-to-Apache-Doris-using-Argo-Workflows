# 0_ingest.py
import os
from local_config import CSV_DIR, logging

def ingest():
    files = [f for f in os.listdir(CSV_DIR) if f.lower().endswith(".csv")]
    if not files:
        print("No CSVs found.")
        return
    print(f"Found: {files}")
    logging.info(f"Found CSVs: {files}")

if __name__ == "__main__":
    ingest()