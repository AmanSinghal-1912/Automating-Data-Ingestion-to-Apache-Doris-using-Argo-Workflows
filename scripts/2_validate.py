# 2_validate.py
import os
import pandas as pd
import sys
from local_config import CSV_DIR, logging

def validate(filename):
    path = os.path.join(CSV_DIR, filename)
    if not os.path.exists(path):
        print(f"Missing: {path}")
        return False
    
    try:
        # Just read a few rows to validate
        pd.read_csv(path, nrows=3)
        print(f"Validated: {filename}")
        logging.info(f"Validated: {filename}")
        return True
    except Exception as e:
        print(f"Invalid: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    
    sys.exit(0 if validate(sys.argv[1]) else 1)