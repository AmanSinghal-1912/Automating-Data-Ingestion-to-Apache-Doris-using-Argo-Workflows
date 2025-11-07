# 4_load_to_doris.py
import pandas as pd
import numpy as np
import os
import json
import sys
from datetime import datetime
from local_config import (
    logging, get_doris_host, get_doris_port, get_doris_user, get_doris_pass, 
    get_doris_db, TABLE_MAP_FILE, BASE_DIR
)

ERROR_DIR = os.path.join(BASE_DIR, "error_files")

def infer_doris_type(series):
    """
    Intelligently infer Doris data type from pandas Series using majority voting
    """
    # Remove nulls for type detection
    series_clean = series.dropna()
    
    if len(series_clean) == 0:
        return "VARCHAR(255)"  # Default for empty columns
    
    # For object dtype, check if MAJORITY of values are numeric
    if series.dtype == 'object':
        numeric_count = 0
        total_count = len(series_clean)
        
        for val in series_clean:
            try:
                # Try to convert to number
                float(str(val).strip())
                numeric_count += 1
            except (ValueError, TypeError):
                pass
        
        # If majority (>50%) are numeric, treat as numeric
        if numeric_count / total_count > 0.5:
            # Convert to numeric, coerce non-numeric to NaN
            series_clean = pd.to_numeric(series_clean.astype(str).str.strip(), errors='coerce')
            # Remove the NaN values created from non-numeric strings
            series_clean = series_clean.dropna()
            
            if len(series_clean) == 0:
                return "VARCHAR(255)"
    
    # Integer types
    if pd.api.types.is_integer_dtype(series_clean):
        max_val = series_clean.max()
        min_val = series_clean.min()
        
        # Check for values exceeding BIGINT range - use DOUBLE instead
        BIGINT_MAX = 9223372036854775807
        BIGINT_MIN = -9223372036854775808
        
        if max_val > BIGINT_MAX or min_val < BIGINT_MIN:
            return "DOUBLE"
        
        # TINYINT: -128 to 127
        if min_val >= -128 and max_val <= 127:
            return "TINYINT"
        # SMALLINT: -32768 to 32767
        elif min_val >= -32768 and max_val <= 32767:
            return "SMALLINT"
        # INT: -2147483648 to 2147483647
        elif min_val >= -2147483648 and max_val <= 2147483647:
            return "INT"
        # BIGINT
        else:
            return "BIGINT"
    
    # Float/Decimal types
    if pd.api.types.is_float_dtype(series_clean):
        max_val = series_clean.max()
        min_val = series_clean.min()
        
        # Check for values exceeding BIGINT range
        BIGINT_MAX = 9223372036854775807
        BIGINT_MIN = -9223372036854775808
        
        # Check if all floats are actually integers (like 22.0, 23.0)
        if (series_clean % 1 == 0).all():
            # Check if values are within safe integer range
            if max_val > BIGINT_MAX or min_val < BIGINT_MIN:
                return "DOUBLE"  # Too large for BIGINT, use DOUBLE
            
            max_val_int = int(max_val)
            min_val_int = int(min_val)
            
            if min_val_int >= -128 and max_val_int <= 127:
                return "TINYINT"
            elif min_val_int >= -32768 and max_val_int <= 32767:
                return "SMALLINT"
            elif min_val_int >= -2147483648 and max_val_int <= 2147483647:
                return "INT"
            else:
                return "BIGINT"
        return "DOUBLE"
    
    # Boolean
    if pd.api.types.is_bool_dtype(series_clean):
        return "BOOLEAN"
    
    # Datetime
    if pd.api.types.is_datetime64_any_dtype(series_clean):
        return "DATETIME"
    
    # Date
    try:
        if series_clean.astype(str).str.match(r'^\d{4}-\d{2}-\d{2}$').all():
            return "DATE"
    except:
        pass
    
    # String/VARCHAR - determine length
    if series.dtype == 'object' or pd.api.types.is_string_dtype(series):
        max_length = series_clean.astype(str).str.len().max()
        
        if max_length <= 50:
            return "VARCHAR(100)"
        elif max_length <= 100:
            return "VARCHAR(200)"
        elif max_length <= 255:
            return "VARCHAR(500)"
        elif max_length <= 1000:
            return "VARCHAR(2000)"
        else:
            return "VARCHAR(65533)"
    
    # Default fallback
    return "VARCHAR(255)"

def get_columns_key(df):
    return "|".join(sorted(df.columns))

def get_main_table_name():
    """Get or create the main table name for the first schema"""
    if not os.path.exists(TABLE_MAP_FILE):
        return None
    with open(TABLE_MAP_FILE) as f:
        table_map = json.load(f)
    return table_map.get("main_table", None)

def get_main_schema():
    """Get the schema of the main table"""
    if not os.path.exists(TABLE_MAP_FILE):
        return None
    with open(TABLE_MAP_FILE) as f:
        table_map = json.load(f)
    return table_map.get("main_schema", None)

def save_error_csv(df, original_filename, reason):
    """Save mismatched data to error CSV with simple naming"""
    os.makedirs(ERROR_DIR, exist_ok=True)
    
    # Simple naming: error_<filename>.csv
    base_name = os.path.splitext(original_filename)[0]
    error_file = os.path.join(ERROR_DIR, f"error_{base_name}.csv")
    
    df.to_csv(error_file, index=False)
    
    # Log the error
    error_msg = f"SCHEMA_MISMATCH: {original_filename} - {reason}\n  Saved to: {error_file}"
    print(f"\n[WARN] {error_msg}")
    logging.error(error_msg)
    
    return error_file

def save_bad_rows_csv(bad_rows_df, original_filename, reason):
    """Save rows that failed validation/conversion to error CSV"""
    os.makedirs(ERROR_DIR, exist_ok=True)
    
    # Simple naming: error_<filename>.csv
    base_name = os.path.splitext(original_filename)[0]
    error_file = os.path.join(ERROR_DIR, f"error_{base_name}.csv")
    
    bad_rows_df.to_csv(error_file, index=False)
    
    # Log the error
    error_msg = f"BAD_ROWS: {original_filename} - {reason}\n  Saved {len(bad_rows_df)} bad rows to: {error_file}"
    print(f"\n[WARN] {error_msg}")
    logging.warning(error_msg)
    
    return error_file

def get_or_create_table(df, col_key):
    import pymysql
    conn = pymysql.connect(host=get_doris_host(), port=get_doris_port(),
                           user=get_doris_user(), password=get_doris_pass(),
                           database=get_doris_db())
    cur = conn.cursor()

    table_map = {}
    if os.path.exists(TABLE_MAP_FILE):
        with open(TABLE_MAP_FILE) as f:
            table_map = json.load(f)

    if col_key in table_map:
        table_name = table_map[col_key]
        cur.execute(f"SELECT MAX(id) FROM `{table_name}`")
        max_id = cur.fetchone()[0] or 0
        cur.close(); conn.close()
        return table_name, max_id

    table_name = f"tbl_{len(table_map)+1}"
    df = df.copy()
    df.insert(0, 'id', range(1, len(df) + 1))

    # NO PRIMARY KEY — DUPLICATE KEY MODEL
    cols = [f"`id` BIGINT NOT NULL"] + \
           [f"`{c}` VARCHAR(65533)" for c in df.columns[1:]]
    col_defs = ",\n    ".join(cols)

    sql = f"""
    CREATE TABLE IF NOT EXISTS `{table_name}` (
        {col_defs}
    )
    DUPLICATE KEY(`id`)
    DISTRIBUTED BY HASH(`id`) BUCKETS 3
    PROPERTIES ("replication_num" = "1");
    """
    print(f"Creating table `{table_name}`...")
    cur.execute(sql)
    conn.commit()

    table_map[col_key] = table_name
    with open(TABLE_MAP_FILE, "w") as f:
        json.dump(table_map, f)

    cur.close(); conn.close()
    return table_name, 0

def check_fe_api(timeout=3):
    """Quick GET to FE root or /api to verify connectivity."""
    health_url = f"{get_doris_fe()}/api"
    try:
        r = requests.get(health_url, auth=(get_doris_user(), get_doris_pass()), timeout=timeout)
        return r.status_code < 500
    except Exception:
        return False

def stream_load_to_doris(file_path, table_name, timeout=300):
    doris_host = get_doris_host()
    doris_http_port = get_doris_fe_http_port()
    doris_db = get_doris_db()
    url = f"http://{doris_host}:{doris_http_port}/api/{doris_db}/{table_name}/_stream_load"
    auth = (get_doris_user(), get_doris_pass())
    headers = {
        "Expect": "100-continue",
        "column_separator": ",",
        "columns": ",".join([f"`{c}`" for c in pd.read_csv(file_path, nrows=0).columns]),
        "format": "csv",
        "strip_outer_array": "true"
    }

    print(f"Stream loading → `{table_name}` … to URL: {url}")
    with open(file_path, 'rb') as f:
        response = requests.put(url, data=f, auth=auth, headers=headers, timeout=timeout)

    if response.status_code != 200:
        print(f"Stream Load FAILED: {response.status_code} {response.text}")
        raise RuntimeError(f"Stream Load failed: {response.text}")

    result = response.json()
    if result.get("Status") != "Success":
        print(f"Stream Load FAILED: {result}")
        raise RuntimeError(f"Stream Load failed: {result}")

    return result

def load_file(staged_path, original_filename=None):
    df = pd.read_csv(staged_path)
    
    # Get the main table and schema
    main_table = get_main_table_name()
    main_schema = get_main_schema()
    current_schema = get_columns_key(df)
    
    # First file - create main table
    if main_table is None:
        print("[NEW] First file - creating main table...")
        table_name = "main_data_table"
        last_id = 0
        
        # Save to table map
        table_map = {
            "main_table": table_name,
            "main_schema": current_schema
        }
        with open(TABLE_MAP_FILE, "w") as f:
            json.dump(table_map, f, indent=2)
        
        # Create table
        import pymysql
        conn = pymysql.connect(
            host=get_doris_host(), port=get_doris_port(),
            user=get_doris_user(), password=get_doris_pass(),
            database=get_doris_db()
        )
        cur = conn.cursor()
        
        df_temp = df.copy()
        df_temp.insert(0, 'id', range(1, len(df_temp) + 1))
        
        # Intelligently detect column types with detailed logging
        print(f"\n[SCHEMA] Schema Detection for: {original_filename or 'unknown.csv'}")
        print(f"  Total rows: {len(df)}")
        print(f"  Columns: {len(df.columns)}")
        print(f"\n  Column Type Analysis:")
        cols = [f"`id` BIGINT NOT NULL"]
        for col in df_temp.columns[1:]:
            col_type = infer_doris_type(df_temp[col])
            cols.append(f"`{col}` {col_type}")
            
            # Show sample values and detection logic
            sample_vals = df_temp[col].head(3).tolist()
            print(f"    - {col:20s} -> {col_type:15s} (samples: {sample_vals})")
        
        col_defs = ",\n    ".join(cols)
        
        sql = f"""
        CREATE TABLE IF NOT EXISTS `{table_name}` (
            {col_defs}
        )
        DUPLICATE KEY(`id`)
        DISTRIBUTED BY HASH(`id`) BUCKETS 3
        PROPERTIES ("replication_num" = "1");
        """
        print(f"Creating table `{table_name}`...")
        cur.execute(sql)
        conn.commit()
        cur.close()
        conn.close()
        
    # Subsequent files - check schema
    else:
        table_name = main_table
        
        # Schema mismatch - save to error CSV
        if current_schema != main_schema:
            error_file = save_error_csv(
                df, 
                original_filename or "unknown.csv",
                f"Schema mismatch. Expected: {main_schema}, Got: {current_schema}"
            )
            print(f"\n[ERR] SCHEMA_MISMATCH")
            sys.exit(1)  # Exit with error code
        
        # Get last ID - check if table exists first
        import pymysql
        conn = pymysql.connect(
            host=get_doris_host(), port=get_doris_port(),
            user=get_doris_user(), password=get_doris_pass(),
            database=get_doris_db()
        )
        cur = conn.cursor()
        
        # Check if table exists
        cur.execute("SHOW TABLES")
        existing_tables = [row[0] for row in cur.fetchall()]
        
        if table_name not in existing_tables:
            # Table in map but doesn't exist in DB - recreate it
            print(f"[WARN] Table '{table_name}' not found in database, recreating...")
            last_id = 0
            
            # Create table with schema detection
            df_temp = df.copy()
            df_temp.insert(0, 'id', range(1, len(df_temp) + 1))
            
            print(f"\n[SCHEMA] Schema Detection for: {original_filename or 'unknown.csv'}")
            print(f"  Total rows: {len(df)}")
            print(f"  Columns: {len(df.columns)}")
            print(f"\n  Column Type Analysis:")
            cols = [f"`id` BIGINT NOT NULL"]
            for col in df_temp.columns[1:]:
                col_type = infer_doris_type(df_temp[col])
                cols.append(f"`{col}` {col_type}")
                sample_vals = df_temp[col].head(3).tolist()
                print(f"    - {col:20s} -> {col_type:15s} (samples: {sample_vals})")
            
            col_defs = ",\n    ".join(cols)
            
            sql = f"""
            CREATE TABLE IF NOT EXISTS `{table_name}` (
                {col_defs}
            )
            DUPLICATE KEY(`id`)
            DISTRIBUTED BY HASH(`id`) BUCKETS 3
            PROPERTIES ("replication_num" = "1");
            """
            print(f"Creating table `{table_name}`...")
            cur.execute(sql)
            conn.commit()
        else:
            # Table exists - get last ID
            cur.execute(f"SELECT MAX(id) FROM `{table_name}`")
            last_id = cur.fetchone()[0] or 0
        
        cur.close()
        conn.close()
    
    # ALWAYS add IDs (starting from last_id + 1)
    df.insert(0, 'id', range(last_id + 1, last_id + 1 + len(df)))
    
    # Use MySQL INSERT with row-level error handling
    print(f"\n[LOAD] Loading Data to Doris:")
    print(f"  Table: {table_name}")
    print(f"  Total rows: {len(df)}")
    
    import pymysql
    import math
    
    conn = pymysql.connect(
        host=get_doris_host(), 
        port=get_doris_port(),
        user=get_doris_user(), 
        password=get_doris_pass(),
        database=get_doris_db()
    )
    cursor = conn.cursor()
    
    try:
        # Get column types from table schema
        cursor.execute(f"DESC `{table_name}`")
        schema_info = cursor.fetchall()
        column_types = {}
        for row in schema_info:
            col_name = row[0]
            col_type = row[1].upper()
            column_types[col_name] = col_type
        
        print(f"  Table schema loaded: {len(column_types)} columns")
        
        # Build INSERT statement
        columns = list(df.columns)
        placeholders = ", ".join(["%s"] * len(columns))
        column_names = ", ".join([f"`{c}`" for c in columns])
        insert_sql = f"INSERT INTO `{table_name}` ({column_names}) VALUES ({placeholders})"
        
        print(f"  Validating rows against schema...")
        
        # Convert dataframe to list of tuples with TYPE validation
        data = []
        bad_rows_indices = []
        bad_row_details = []
        
        for idx, row in enumerate(df.itertuples(index=False)):
            try:
                cleaned_row = []
                is_valid_row = True
                error_msg = ""
                
                for col_idx, (col_name, value) in enumerate(zip(columns, row)):
                    # Handle NULL/NaN
                    if pd.isna(value) or (isinstance(value, float) and math.isnan(value)):
                        cleaned_row.append(None)
                        continue
                    
                    # Get expected type for this column
                    expected_type = column_types.get(col_name, "VARCHAR")
                    
                    # Validate based on column type
                    if "TINYINT" in expected_type or "SMALLINT" in expected_type or "INT" in expected_type or "BIGINT" in expected_type:
                        # Must be a valid integer
                        try:
                            int_val = int(float(str(value).strip()))
                            cleaned_row.append(int_val)
                        except (ValueError, TypeError):
                            is_valid_row = False
                            error_msg = f"Column '{col_name}' expects INT, got '{value}'"
                            break
                    
                    elif "DOUBLE" in expected_type or "FLOAT" in expected_type or "DECIMAL" in expected_type:
                        # Must be a valid number
                        try:
                            float_val = float(str(value).strip())
                            cleaned_row.append(float_val)
                        except (ValueError, TypeError):
                            is_valid_row = False
                            error_msg = f"Column '{col_name}' expects FLOAT, got '{value}'"
                            break
                    
                    elif "DATETIME" in expected_type or "DATE" in expected_type:
                        # Must be a valid date/datetime
                        try:
                            pd.to_datetime(value)
                            cleaned_row.append(value)
                        except:
                            is_valid_row = False
                            error_msg = f"Column '{col_name}' expects DATE, got '{value}'"
                            break
                    
                    else:
                        # VARCHAR/STRING - accept anything
                        cleaned_row.append(value)
                
                # Add row if valid, otherwise track as bad
                if is_valid_row:
                    data.append(tuple(cleaned_row))
                else:
                    bad_rows_indices.append(idx)
                    bad_row_details.append(f"Row {idx+2}: {error_msg}")
                    if len(bad_row_details) <= 5:  # Show first 5 errors
                        print(f"    [WARN] Row {idx+2} invalid: {error_msg}")
                        
            except Exception as e:
                # Track rows that failed conversion
                bad_rows_indices.append(idx)
                bad_row_details.append(f"Row {idx+2}: {str(e)[:50]}")
                if len(bad_row_details) <= 5:  # Show first 5 errors
                    print(f"    [WARN] Row {idx+2} failed: {e}")
        
        # If there are bad rows, save them to error file
        if bad_rows_indices:
            print(f"\n  [ERR] Found {len(bad_rows_indices)} bad rows!")
            bad_rows_df = df.iloc[bad_rows_indices].copy()
            bad_rows_df.drop('id', axis=1, inplace=True, errors='ignore')  # Remove auto-generated ID
            error_file = save_bad_rows_csv(
                bad_rows_df, 
                original_filename or "unknown.csv",
                f"{len(bad_rows_indices)} rows failed data type validation"
            )
            print(f"  [INFO] Bad rows saved to: {os.path.basename(error_file)}")
            print(f"  [OK]   Proceeding with {len(data)} valid rows")
        else:
            print(f"  [OK]   All {len(data)} rows valid")
        
        # Execute batch insert only for good rows
        if data:
            print(f"  Inserting {len(data)} rows to database...")
            cursor.executemany(insert_sql, data)
            conn.commit()
            
            print(f"\n[OK]   Successfully loaded {len(data)} rows into `{table_name}`")
            if bad_rows_indices:
                print(f"[WARN] Skipped {len(bad_rows_indices)} bad rows (saved to error file)")
            logging.info(f"MySQL INSERT loaded {staged_path} → {table_name}, {len(data)} rows ({len(bad_rows_indices)} rows skipped)")
        else:
            print(f"\n[ERR]  No valid rows to load!")
            logging.error(f"All rows failed validation in {staged_path}")
        
    except Exception as e:
        print(f"\n[ERR] MySQL INSERT failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 4_load_to_doris.py <staged_file> [original_filename]")
        sys.exit(1)
    
    staged_path = sys.argv[1]
    original_filename = sys.argv[2] if len(sys.argv) > 2 else None
    
    load_file(staged_path, original_filename)
