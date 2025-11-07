# discover_next_1.py
import os
from local_config import CSV_DIR, CHECKPOINT_FILE, logging

def discover_next():
    files = sorted([f for f in os.listdir(CSV_DIR) if f.lower().endswith(".csv")])
    processed = set()
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            processed = {line.strip() for line in f if line.strip()}
    for f in files:
        if f not in processed:
            logging.info(f"Next: {f}")
            return f
    return None

if __name__ == "__main__":
    print(discover_next() or "")