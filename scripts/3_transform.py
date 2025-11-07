# 3_transform.py
import os
import pandas as pd
from local_config import CSV_DIR, STAGE_DIR, logging

def transform(filename):
    src = os.path.join(CSV_DIR, filename)
    dst = os.path.join(STAGE_DIR, f"staged_{filename}")

    print(f"\n[TRANSFORM] {filename}")
    
    # Read CSV
    df = pd.read_csv(src)
    original_rows = len(df)
    original_cols = list(df.columns)
    print(f"  Input: {original_rows} rows, {len(original_cols)} columns")
    print(f"  Original columns: {original_cols}")

    # Clean column names
    df.columns = [c.strip().lower().replace(' ', '_').replace('.', '_').replace('(', '').replace(')', '') for c in df.columns]
    cleaned_cols = list(df.columns)
    if cleaned_cols != original_cols:
        print(f"  Cleaned columns: {cleaned_cols}")

    # Drop duplicates
    before = len(df)
    df = df.drop_duplicates()
    duplicates_removed = before - len(df)
    if duplicates_removed > 0:
        print(f"  Removed {duplicates_removed} duplicate rows")

    # Fill missing values
    null_counts = df.isnull().sum()
    total_nulls = null_counts.sum()
    if total_nulls > 0:
        print(f"  Found {total_nulls} null values across columns")
        for col, count in null_counts[null_counts > 0].items():
            print(f"    - {col}: {count} nulls")
        df = df.fillna("NULL")
        print(f"  Filled nulls with 'NULL'")

    # Save staged file
    df.to_csv(dst, index=False)
    final_rows = len(df)
    print(f"  Output: {final_rows} rows")
    print(f"  Saved to: {os.path.basename(dst)}")
    
    # This is what gets returned to pipeline
    print(dst)
    
    logging.info(f"Transformed {filename} -> {final_rows} rows (removed {duplicates_removed} dupes, filled {total_nulls} nulls)")
    return dst

if __name__ == "__main__":
    from discover_next_1 import discover_next
    f = discover_next()
    if f:
        transform(f)
    else:
        print("All done.")