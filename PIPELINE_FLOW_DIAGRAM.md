# CSV to Doris Pipeline - Complete Flow Documentation

## 📋 Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Detailed Flow Diagram](#detailed-flow-diagram)
3. [Component Breakdown](#component-breakdown)
4. [Step-by-Step Execution](#step-by-step-execution)
5. [Data Flow & Transformations](#data-flow--transformations)
6. [Error Handling Flow](#error-handling-flow)
7. [Kubernetes & Argo Integration](#kubernetes--argo-integration)

---

## 🏗️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     WINDOWS HOST MACHINE                             │
│  C:\Users\singh\Desktop\Minikube-Doris\                             │
│                                                                       │
│  ├── data/               (Source CSV files)                          │
│  ├── scripts/            (Python pipeline scripts)                   │
│  ├── stage_test/         (Staged/transformed CSV files)              │
│  ├── error_files/        (Failed rows & schema mismatches)           │
│  ├── checkpoint.txt      (Tracks processed files)                    │
│  └── table_map.json      (Maps schemas to table names)               │
└───────────────────┬─────────────────────────────────────────────────┘
                    │
                    │ Volume Mount (hostPath)
                    │ /Minikube-Doris ↔ C:\Users\singh\Desktop\Minikube-Doris
                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     MINIKUBE KUBERNETES                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │         ARGO WORKFLOWS NAMESPACE (argo)                      │   │
│  │                                                               │   │
│  │  ┌─────────────────────────────────────────────────┐         │   │
│  │  │  CronWorkflow: csv-doris-cron                   │         │   │
│  │  │  Schedule: */5 * * * * (Every 5 minutes)        │         │   │
│  │  │  Timezone: America/New_York                     │         │   │
│  │  └──────────────────┬──────────────────────────────┘         │   │
│  │                     │ Creates workflow every 5 min            │   │
│  │                     ↓                                         │   │
│  │  ┌─────────────────────────────────────────────────┐         │   │
│  │  │  Workflow Instance: csv-doris-cron-XXXXXXXXXX   │         │   │
│  │  │  (Ephemeral - deleted after success/failure)     │         │   │
│  │  └──────────────────┬──────────────────────────────┘         │   │
│  │                     │ Spawns Pod                              │   │
│  │                     ↓                                         │   │
│  │  ┌─────────────────────────────────────────────────┐         │   │
│  │  │  Pod: csv-doris-cron-XXXXXXXXXX                 │         │   │
│  │  │  Image: python:3.11-slim                        │         │   │
│  │  │  ┌───────────────────────────────────────────┐  │         │   │
│  │  │  │  Init: Install dependencies               │  │         │   │
│  │  │  │  - pip install pandas pymysql requests    │  │         │   │
│  │  │  └───────────────────────────────────────────┘  │         │   │
│  │  │  ┌───────────────────────────────────────────┐  │         │   │
│  │  │  │  Main: Run pipeline_local.py              │  │         │   │
│  │  │  │  - Orchestrates all pipeline steps        │  │         │   │
│  │  │  └───────────────────────────────────────────┘  │         │   │
│  │  │  Volumes:                                        │         │   │
│  │  │  - /app → mounted from host                     │         │   │
│  │  │  Environment:                                    │         │   │
│  │  │  - DORIS_HOST=host.docker.internal              │         │   │
│  │  │  - DORIS_PORT=9030                               │         │   │
│  │  │  - DORIS_DB=updated_test2                        │         │   │
│  │  └─────────────────────────────────────────────────┘         │   │
│  └─────────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            │ MySQL Protocol (Port 9030)
                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     APACHE DORIS DATABASE                            │
│  IP: 192.168.29.181                                                  │
│  Ports: 9030 (MySQL), 8030 (HTTP/FE)                                │
│  Database: updated_test2                                             │
│  Table: main_data_table                                              │
│  Model: DUPLICATE KEY                                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Detailed Flow Diagram

```
START (Every 5 minutes - Cron: */5 * * * *)
  │
  │ Argo CronWorkflow Controller triggers
  ↓
┌────────────────────────────────────────────────────────────────┐
│ PHASE 1: POD INITIALIZATION                                     │
└────────────────────────────────────────────────────────────────┘
  │
  ├─→ Create Pod: csv-doris-cron-XXXXXXXXXX
  │   └─→ Pull Image: python:3.11-slim
  │
  ├─→ Mount Volume: /app ← C:\Users\singh\Desktop\Minikube-Doris
  │
  ├─→ Set Environment Variables:
  │   ├─ DORIS_HOST=host.docker.internal
  │   ├─ DORIS_PORT=9030
  │   ├─ DORIS_USER=root
  │   ├─ DORIS_PASS=(empty)
  │   ├─ DORIS_DB=updated_test2
  │   └─ DORIS_FE_HTTP_PORT=8030
  │
  └─→ Install Dependencies:
      └─→ pip install pandas pymysql requests numpy
  │
  ↓
┌────────────────────────────────────────────────────────────────┐
│ PHASE 2: PIPELINE ORCHESTRATION (pipeline_local.py)            │
└────────────────────────────────────────────────────────────────┘
  │
  ├─→ Print Banner:
  │   ======================================================================
  │     *** ARGO CRON WORKFLOW STARTED ***
  │     Timestamp: 2025-11-06 06:45:46
  │   ======================================================================
  │
  ├─→ [STEP 1] DISCOVER ALL CSV FILES (0_ingest.py)
  │   │
  │   ├─→ Scan directory: /app/data/*.csv
  │   ├─→ Found: ['a.csv', 'b.csv', 'c.csv', 'd.csv', 'e.csv', 
  │   │            'emp.csv', 'meal_metadata.csv', 'people.csv']
  │   └─→ Return: 8 files discovered
  │
  ├─→ [STEP 2] CHECK PROCESSED FILES
  │   │
  │   ├─→ Read: /app/checkpoint.txt
  │   ├─→ Already processed: 0 files
  │   └─→ Remaining to process: 8 files
  │
  ├─→ [LOOP] FOR EACH UNPROCESSED FILE:
  │   │
  │   └─→ ┌──────────────────────────────────────────────────────┐
  │       │  FILE PROCESSING WORKFLOW                             │
  │       └──────────────────────────────────────────────────────┘
  │       │
  │       ├─→ [STEP 2.1] DISCOVER NEXT FILE (discover_next_1.py)
  │       │   │
  │       │   ├─→ Read: /app/checkpoint.txt
  │       │   ├─→ Find first unprocessed file
  │       │   └─→ Return: "a.csv" (for example)
  │       │
  │       ├─→ [STEP 2.2] VALIDATE (2_validate.py)
  │       │   │
  │       │   ├─→ Read: /app/data/a.csv
  │       │   ├─→ Check: File exists? ✓
  │       │   ├─→ Check: Valid CSV format? ✓
  │       │   ├─→ Check: Has data? ✓
  │       │   └─→ Return: VALID
  │       │
  │       ├─→ [STEP 2.3] TRANSFORM & STAGE (3_transform.py)
  │       │   │
  │       │   ├─→ Read: /app/data/a.csv
  │       │   │   Input: 6 rows, 2 columns ['name', 'age']
  │       │   │
  │       │   ├─→ Clean column names:
  │       │   │   'name' → 'name'
  │       │   │   'age' → 'age'
  │       │   │
  │       │   ├─→ Remove duplicates: 0 duplicates found
  │       │   │
  │       │   ├─→ Handle nulls: 0 nulls found
  │       │   │
  │       │   ├─→ Save staged file:
  │       │   │   Output: /app/stage_test/staged_a.csv
  │       │   │   Final: 6 rows, 2 columns
  │       │   │
  │       │   └─→ Return: /app/stage_test/staged_a.csv
  │       │
  │       ├─→ [STEP 2.4] LOAD TO DORIS (4_load_to_doris.py)
  │       │   │
  │       │   ├─→ Read: /app/stage_test/staged_a.csv
  │       │   │
  │       │   ├─→ CHECK: Is this the FIRST file?
  │       │   │   │
  │       │   │   ├─→ YES (table_map.json doesn't exist)
  │       │   │   │   │
  │       │   │   │   ├─→ [SCHEMA DETECTION]
  │       │   │   │   │   │
  │       │   │   │   │   ├─→ Analyze 'name' column:
  │       │   │   │   │   │   Values: ['Kara', 'Ishuu', 'Sharma', ...]
  │       │   │   │   │   │   Type: VARCHAR(100)
  │       │   │   │   │   │
  │       │   │   │   │   ├─→ Analyze 'age' column:
  │       │   │   │   │   │   Values: [77, 91, 55, 22, 19, 66]
  │       │   │   │   │   │   All numeric? YES (100%)
  │       │   │   │   │   │   Range: 19-91
  │       │   │   │   │   │   Type: TINYINT (-128 to 127)
  │       │   │   │   │   │
  │       │   │   │   │   └─→ Schema: age|name (sorted column keys)
  │       │   │   │   │
  │       │   │   │   ├─→ [CREATE TABLE]
  │       │   │   │   │   CREATE TABLE main_data_table (
  │       │   │   │   │     `id` BIGINT NOT NULL,
  │       │   │   │   │     `name` VARCHAR(100),
  │       │   │   │   │     `age` TINYINT
  │       │   │   │   │   )
  │       │   │   │   │   DUPLICATE KEY(`id`)
  │       │   │   │   │   DISTRIBUTED BY HASH(`id`) BUCKETS 3
  │       │   │   │   │   PROPERTIES ("replication_num" = "1");
  │       │   │   │   │
  │       │   │   │   ├─→ Save table_map.json:
  │       │   │   │   │   {
  │       │   │   │   │     "main_table": "main_data_table",
  │       │   │   │   │     "main_schema": "age|name"
  │       │   │   │   │   }
  │       │   │   │   │
  │       │   │   │   └─→ Set last_id = 0
  │       │   │   │
  │       │   │   └─→ NO (table_map.json exists)
  │       │   │       │
  │       │   │       ├─→ Read table_map.json
  │       │   │       ├─→ Expected schema: "age|name"
  │       │   │       ├─→ Current schema: "age|name" (from staged file)
  │       │   │       │
  │       │   │       ├─→ Schema match? 
  │       │   │       │   │
  │       │   │       │   ├─→ YES: Continue
  │       │   │       │   │   └─→ Get max(id) from main_data_table
  │       │   │       │   │       last_id = 6 (for example)
  │       │   │       │   │
  │       │   │       │   └─→ NO: SCHEMA MISMATCH!
  │       │   │       │       ├─→ Save to: /app/error_files/error_b.csv
  │       │   │       │       ├─→ Log: Schema mismatch detected
  │       │   │       │       ├─→ Checkpoint file anyway
  │       │   │       │       └─→ Skip to next file
  │       │   │       │
  │       │   │       └─→ Continue loading...
  │       │   │
  │       │   ├─→ [ADD AUTO-INCREMENT IDs]
  │       │   │   │
  │       │   │   ├─→ Insert 'id' column at position 0
  │       │   │   └─→ IDs: range(last_id+1, last_id+1+len(df))
  │       │   │       Example: [1, 2, 3, 4, 5, 6] for first file
  │       │   │                [7, 8, 9, 10, 11] for second file
  │       │   │
  │       │   ├─→ [ROW-LEVEL VALIDATION]
  │       │   │   │
  │       │   │   ├─→ Connect to Doris
  │       │   │   ├─→ Get table schema (DESC main_data_table):
  │       │   │   │   id: BIGINT
  │       │   │   │   name: VARCHAR(100)
  │       │   │   │   age: TINYINT
  │       │   │   │
  │       │   │   ├─→ FOR EACH ROW in dataframe:
  │       │   │   │   │
  │       │   │   │   ├─→ FOR EACH COLUMN:
  │       │   │   │   │   │
  │       │   │   │   │   ├─→ Is NULL/NaN? → Store as NULL
  │       │   │   │   │   │
  │       │   │   │   │   ├─→ Expected type INT/BIGINT/TINYINT?
  │       │   │   │   │   │   ├─→ Try: int(float(str(value)))
  │       │   │   │   │   │   ├─→ Success? → Store as integer
  │       │   │   │   │   │   └─→ Fail? → Mark row as BAD
  │       │   │   │   │   │       Example: "twenty" cannot convert to int
  │       │   │   │   │   │
  │       │   │   │   │   ├─→ Expected type FLOAT/DOUBLE?
  │       │   │   │   │   │   ├─→ Try: float(str(value))
  │       │   │   │   │   │   ├─→ Success? → Store as float
  │       │   │   │   │   │   └─→ Fail? → Mark row as BAD
  │       │   │   │   │   │
  │       │   │   │   │   ├─→ Expected type DATE/DATETIME?
  │       │   │   │   │   │   ├─→ Try: pd.to_datetime(value)
  │       │   │   │   │   │   ├─→ Success? → Store as date
  │       │   │   │   │   │   └─→ Fail? → Mark row as BAD
  │       │   │   │   │   │
  │       │   │   │   │   └─→ Expected type VARCHAR?
  │       │   │   │   │       └─→ Accept anything
  │       │   │   │   │
  │       │   │   │   ├─→ Row valid? 
  │       │   │   │   │   ├─→ YES: Add to good_rows[]
  │       │   │   │   │   └─→ NO: Add to bad_rows[]
  │       │   │   │   │       Log: [WARN] Row 3 invalid: Column 'age' expects INT, got 'twenty'
  │       │   │   │
  │       │   │   ├─→ Any bad rows?
  │       │   │   │   ├─→ YES:
  │       │   │   │   │   ├─→ Save to: /app/error_files/error_e.csv
  │       │   │   │   │   │   (Contains only the bad rows)
  │       │   │   │   │   ├─→ Log: Found 2 bad rows - saved to error_e.csv
  │       │   │   │   │   └─→ Continue with good rows only
  │       │   │   │   │
  │       │   │   │   └─→ NO: All rows valid!
  │       │   │   │
  │       │   │   └─→ Result:
  │       │   │       good_rows: [(1, 'lara', 77), (2, 'Aara', 21)]
  │       │   │       bad_rows: [(3, 'aysuh', 'twenty'), (4, 'rahul', 'fifty')]
  │       │   │
  │       │   ├─→ [INSERT TO DORIS]
  │       │   │   │
  │       │   │   ├─→ Build SQL:
  │       │   │   │   INSERT INTO `main_data_table` 
  │       │   │   │   (`id`, `name`, `age`) 
  │       │   │   │   VALUES (%s, %s, %s)
  │       │   │   │
  │       │   │   ├─→ Execute batch insert (only good rows):
  │       │   │   │   executemany(sql, good_rows)
  │       │   │   │
  │       │   │   ├─→ Commit transaction
  │       │   │   │
  │       │   │   └─→ Log: Successfully loaded 2 rows
  │       │   │       (Skipped 2 bad rows)
  │       │   │
  │       │   └─→ Return: SUCCESS
  │       │
  │       └─→ [STEP 2.5] CHECKPOINT (6_checkpoint.py)
  │           │
  │           ├─→ Read: /app/checkpoint.txt
  │           ├─→ Append: "a.csv\n"
  │           └─→ Save: /app/checkpoint.txt
  │               Now contains: a.csv
  │
  ├─→ LOOP continues for next unprocessed file...
  │
  └─→ [END LOOP] All files processed!
  │
  ↓
┌────────────────────────────────────────────────────────────────┐
│ PHASE 3: SUMMARY & CLEANUP                                     │
└────────────────────────────────────────────────────────────────┘
  │
  ├─→ Print Summary:
  │   ======================================================================
  │     *** PIPELINE COMPLETED SUCCESSFULLY ***
  │   ======================================================================
  │   Total runtime: 60.45 seconds
  │   Files processed: 6
  │   Schema mismatch errors: 2 files
  │   Bad rows skipped: 2 rows
  │   ======================================================================
  │
  ├─→ Exit Code: 0 (Success)
  │
  ↓
┌────────────────────────────────────────────────────────────────┐
│ PHASE 4: ARGO WORKFLOW CLEANUP                                 │
└────────────────────────────────────────────────────────────────┘
  │
  ├─→ Workflow Status: Succeeded ✓
  ├─→ Pod Status: Completed
  ├─→ Keep workflow history: 3 successful, 3 failed
  └─→ Delete pod after completion
  │
  ↓
WAIT FOR NEXT CRON TRIGGER (5 minutes)
  │
  └─→ Loop back to START...
```

---

## 🧩 Component Breakdown

### **1. Argo CronWorkflow (argo-cron-pipeline.yaml)**

**Location**: `C:\Users\singh\Desktop\Minikube-Doris\argo-cron-pipeline.yaml`

**Purpose**: Kubernetes CronWorkflow that triggers the pipeline every 5 minutes.

**Key Configuration**:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: CronWorkflow
metadata:
  name: csv-doris-cron
  namespace: argo
spec:
  schedule: "*/5 * * * *"    # Every 5 minutes
  timezone: "America/New_York"
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
```

**Cron Schedule Breakdown**:
```
*/5  *  *  *  *
 │   │  │  │  │
 │   │  │  │  └─── Day of week (0-6, Sunday=0)
 │   │  │  └────── Month (1-12)
 │   │  └───────── Day of month (1-31)
 │   └──────────── Hour (0-23)
 └──────────────── Minute (0-59, */5 = every 5 minutes)
```

**What happens**:
- Argo Workflows controller watches CronWorkflows
- Every 5 minutes (at :00, :05, :10, :15, etc.), it creates a new Workflow
- Workflow creates a Pod to run the pipeline
- Pod mounts volume, installs dependencies, runs pipeline
- After completion, pod is deleted (logs preserved in Argo)

---

### **2. Pipeline Scripts**

#### **pipeline_local.py** - Master Orchestrator
**Role**: Main entry point, coordinates all pipeline steps

**Key Functions**:
- `log_step(message, level)`: Timestamps all log messages
- `run(cmd, desc)`: Executes subprocess commands with error handling
- Main loop: Discovers files, validates, transforms, loads, checkpoints

**Flow**:
1. Print workflow start banner
2. Discover all CSV files
3. Check checkpoint for processed files
4. FOR EACH unprocessed file:
   - Discover next file
   - Validate
   - Transform
   - Load to Doris (with error handling)
   - Checkpoint
5. Print summary statistics

---

#### **0_ingest.py** - File Discovery
**Role**: Scans data directory for all CSV files

**Input**: None (reads from `/app/data/`)

**Output**: Prints list of CSV files found

**Logic**:
```python
csv_files = glob.glob(os.path.join(CSV_DIR, "*.csv"))
print(f"Found: {[os.path.basename(f) for f in csv_files]}")
```

---

#### **discover_next_1.py** - Next File Selector
**Role**: Finds the next unprocessed CSV file

**Input**: 
- Reads `/app/checkpoint.txt` (processed files)
- Reads `/app/data/*.csv` (all files)

**Output**: Filename of next unprocessed file (or empty if all done)

**Logic**:
```python
all_files = set(['a.csv', 'b.csv', 'c.csv', ...])
processed = set(['a.csv', 'c.csv'])  # from checkpoint.txt
remaining = all_files - processed  # {'b.csv', ...}
return sorted(remaining)[0] if remaining else None
```

---

#### **2_validate.py** - File Validation
**Role**: Ensures CSV file is valid before processing

**Input**: Filename (e.g., "a.csv")

**Checks**:
- ✓ File exists
- ✓ File is readable
- ✓ Valid CSV format
- ✓ Has at least 1 row of data
- ✓ Has at least 1 column

**Output**: Prints "Validated: <filename>" or raises error

---

#### **3_transform.py** - Data Cleaning & Staging
**Role**: Clean and standardize data before loading

**Input**: Filename (e.g., "a.csv")

**Transformations**:
1. **Column name cleaning**:
   - `strip()` - remove whitespace
   - `lower()` - convert to lowercase
   - `replace(' ', '_')` - spaces to underscores
   - `replace('(', '').replace(')', '')` - remove parentheses

2. **Remove duplicate rows**:
   - `df.drop_duplicates()`

3. **Handle missing values**:
   - Fill NULL values with string "NULL"
   - Log which columns had nulls

**Output**: 
- Creates `/app/stage_test/staged_<filename>.csv`
- Prints transformation statistics
- Returns path to staged file

**Example**:
```
Input:  data/a.csv          → 6 rows, ['name', 'age']
Output: stage_test/staged_a.csv → 6 rows, ['name', 'age']
```

---

#### **4_load_to_doris.py** - Database Loading (MOST COMPLEX)
**Role**: Intelligent schema detection, row validation, data loading

**Input**: 
- Staged file path: `/app/stage_test/staged_a.csv`
- Original filename: `a.csv`

**Key Functions**:

##### **infer_doris_type(series)** - Intelligent Type Detection
**Purpose**: Determine the best Doris data type for a column

**Algorithm**:
```
1. Remove NULL/NaN values from series

2. If column is object/string type:
   - Count how many values are numeric (can convert to float)
   - If > 50% are numeric → treat as NUMERIC
   - Else → treat as VARCHAR
   
3. If column is numeric:
   - Check if all floats are actually integers (22.0 → 22)
   - Determine range:
     • -128 to 127 → TINYINT
     • -32768 to 32767 → SMALLINT
     • -2147483648 to 2147483647 → INT
     • Larger → BIGINT
   - If has decimals → DOUBLE
   
4. If column is boolean → BOOLEAN

5. If column is datetime → DATETIME

6. If column is string:
   - Calculate max length
   - Assign VARCHAR with appropriate size:
     • ≤50 chars → VARCHAR(100)
     • ≤100 chars → VARCHAR(200)
     • ≤255 chars → VARCHAR(500)
     • ≤1000 chars → VARCHAR(2000)
     • Larger → VARCHAR(65533)
```

**Example**:
```python
# Column 'age' with values: [77, 91, 55, 22, 19, 66]
infer_doris_type(df['age'])
→ All numeric, range 19-91
→ Returns: "TINYINT"

# Column 'name' with values: ['Kara', 'Ishuu', 'Sharma']
infer_doris_type(df['name'])
→ Max length: 6 characters
→ Returns: "VARCHAR(100)"

# Column with mixed: [77, 91, "twenty", 55]
infer_doris_type(df['mixed'])
→ 75% numeric (3/4), but > 50%
→ Converts to numeric, coerces "twenty" to NaN
→ After dropping NaN: [77, 91, 55]
→ Returns: "TINYINT"
```

---

##### **First File Processing** - Table Creation
**When**: table_map.json doesn't exist (first file ever)

**Steps**:
1. Create table name: `main_data_table`
2. Detect schema using `infer_doris_type()` for each column
3. Create table in Doris:
   ```sql
   CREATE TABLE main_data_table (
     `id` BIGINT NOT NULL,
     `name` VARCHAR(100),
     `age` TINYINT
   )
   DUPLICATE KEY(`id`)
   DISTRIBUTED BY HASH(`id`) BUCKETS 3
   PROPERTIES ("replication_num" = "1");
   ```
4. Save table_map.json:
   ```json
   {
     "main_table": "main_data_table",
     "main_schema": "age|name"
   }
   ```

---

##### **Subsequent File Processing** - Schema Validation
**When**: table_map.json exists

**Steps**:
1. Read expected schema from table_map.json: `"age|name"`
2. Calculate current schema from file: `"age|name"`
3. Compare:
   - **Match**: Continue loading
   - **Mismatch**: 
     - Save entire file to `/app/error_files/error_<filename>.csv`
     - Log schema mismatch
     - Checkpoint the file (don't retry)
     - Skip to next file

**Example Mismatch**:
```
Expected: "age|name"
Got:      "name|salary"
→ Different columns!
→ Save to error_files/error_b.csv
→ Skip file
```

---

##### **Row-Level Validation** - Type Checking
**Purpose**: Filter out rows with invalid data types

**Algorithm**:
```python
FOR EACH ROW in dataframe:
    good_row = True
    validated_values = []
    
    FOR EACH COLUMN:
        expected_type = schema[column]  # From DESC table
        value = row[column]
        
        IF value is NULL:
            validated_values.append(NULL)
            
        ELSE IF expected_type is INT/BIGINT/TINYINT:
            TRY:
                int_value = int(float(str(value)))
                validated_values.append(int_value)
            EXCEPT:
                good_row = False
                Log: "Row X invalid: Column 'age' expects INT, got 'twenty'"
                BREAK
                
        ELSE IF expected_type is FLOAT/DOUBLE:
            TRY:
                float_value = float(str(value))
                validated_values.append(float_value)
            EXCEPT:
                good_row = False
                BREAK
                
        ELSE IF expected_type is DATE/DATETIME:
            TRY:
                date_value = pd.to_datetime(value)
                validated_values.append(value)
            EXCEPT:
                good_row = False
                BREAK
                
        ELSE:  # VARCHAR
            validated_values.append(value)  # Accept anything
    
    IF good_row:
        good_rows.append(tuple(validated_values))
    ELSE:
        bad_rows.append(row)
```

**Example**:
```
Row 1: (1, 'lara', 77)    → age=77 converts to int ✓ → GOOD
Row 2: (2, 'Aara', 21)    → age=21 converts to int ✓ → GOOD
Row 3: (3, 'aysuh', 'twenty') → age='twenty' FAILS int conversion ✗ → BAD
Row 4: (4, 'rahul', 'fifty')  → age='fifty' FAILS int conversion ✗ → BAD

Result:
  good_rows = [(1, 'lara', 77), (2, 'Aara', 21)]
  bad_rows = [(3, 'aysuh', 'twenty'), (4, 'rahul', 'fifty')]
  
  Save bad_rows to: error_files/error_e.csv
  Load only good_rows to database
```

---

##### **Database Insert** - Batch Loading
**Purpose**: Insert validated rows into Doris

**Steps**:
1. Get max(id) from table to continue auto-increment
2. Add id column to dataframe: `range(last_id+1, last_id+1+len(df))`
3. Build SQL:
   ```sql
   INSERT INTO `main_data_table` (`id`, `name`, `age`) 
   VALUES (%s, %s, %s)
   ```
4. Execute batch insert:
   ```python
   cursor.executemany(sql, good_rows)
   conn.commit()
   ```
5. Log success with row counts

---

#### **6_checkpoint.py** - Progress Tracking
**Role**: Mark file as processed to prevent reprocessing

**Input**: Filename (e.g., "a.csv")

**Logic**:
```python
with open('/app/checkpoint.txt', 'a') as f:
    f.write(f"{filename}\n")
```

**Output**: 
- Appends filename to checkpoint.txt
- File contents after processing 3 files:
  ```
  a.csv
  c.csv
  d.csv
  ```

---

## 📊 Data Flow & Transformations

### **Example: Processing e.csv**

```
┌─────────────────────────────────────────────────────────────┐
│ ORIGINAL FILE: data/e.csv                                    │
├─────────────────────────────────────────────────────────────┤
│ name     | age                                               │
│──────────┼─────                                              │
│ lara     | 77                                                │
│ Aara     | 21                                                │
│ aysuh    | twenty  ← Invalid (string in age column)         │
│ rahul    | fifty   ← Invalid (string in age column)         │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ [VALIDATE] ✓ File valid
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ TRANSFORM: 3_transform.py                                    │
├─────────────────────────────────────────────────────────────┤
│ - Clean column names: 'age ' → 'age' (trim space)           │
│ - Remove duplicates: 0 found                                 │
│ - Fill NULLs: 0 found                                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STAGED FILE: stage_test/staged_e.csv                         │
├─────────────────────────────────────────────────────────────┤
│ name     | age                                               │
│──────────┼─────                                              │
│ lara     | 77                                                │
│ Aara     | 21                                                │
│ aysuh    | twenty                                            │
│ rahul    | fifty                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ [LOAD TO DORIS]
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ SCHEMA CHECK                                                 │
├─────────────────────────────────────────────────────────────┤
│ Expected schema: "age|name" (from table_map.json)           │
│ Current schema:  "age|name"                                  │
│ Match? ✓ YES → Continue                                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ ADD AUTO-INCREMENT IDs                                       │
├─────────────────────────────────────────────────────────────┤
│ last_id from DB = 22 (from previous files)                  │
│                                                               │
│ id  | name     | age                                         │
│─────┼──────────┼─────                                        │
│ 23  | lara     | 77                                          │
│ 24  | Aara     | 21                                          │
│ 25  | aysuh    | twenty                                      │
│ 26  | rahul    | fifty                                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ ROW-LEVEL VALIDATION (Against Table Schema)                 │
├─────────────────────────────────────────────────────────────┤
│ Table schema from Doris:                                     │
│   id: BIGINT                                                 │
│   name: VARCHAR(100)                                         │
│   age: TINYINT                                               │
│                                                               │
│ Row 1: (23, 'lara', 77)                                      │
│   ✓ id=23 → int ✓                                           │
│   ✓ name='lara' → varchar ✓                                 │
│   ✓ age=77 → int(float('77')) = 77 ✓                        │
│   → GOOD ROW                                                 │
│                                                               │
│ Row 2: (24, 'Aara', 21)                                      │
│   ✓ id=24 → int ✓                                           │
│   ✓ name='Aara' → varchar ✓                                 │
│   ✓ age=21 → int(float('21')) = 21 ✓                        │
│   → GOOD ROW                                                 │
│                                                               │
│ Row 3: (25, 'aysuh', 'twenty')                               │
│   ✓ id=25 → int ✓                                           │
│   ✓ name='aysuh' → varchar ✓                                │
│   ✗ age='twenty' → int(float('twenty')) → ValueError!       │
│   → BAD ROW                                                  │
│   [WARN] Row 3 invalid: Column 'age' expects INT, got 'twenty'│
│                                                               │
│ Row 4: (26, 'rahul', 'fifty')                                │
│   ✓ id=26 → int ✓                                           │
│   ✓ name='rahul' → varchar ✓                                │
│   ✗ age='fifty' → int(float('fifty')) → ValueError!         │
│   → BAD ROW                                                  │
│   [WARN] Row 4 invalid: Column 'age' expects INT, got 'fifty'│
│                                                               │
│ RESULT:                                                       │
│   Good rows: 2                                               │
│   Bad rows: 2                                                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ├─────────────────────┐
                            │                     │
                    Good Rows                Bad Rows
                            │                     │
                            ↓                     ↓
┌──────────────────────────────┐  ┌──────────────────────────────┐
│ INSERT TO DORIS DATABASE     │  │ ERROR FILE:                   │
├──────────────────────────────┤  │ error_files/error_e.csv       │
│ INSERT INTO main_data_table  │  ├──────────────────────────────┤
│ VALUES                        │  │ name     | age               │
│   (23, 'lara', 77),          │  │──────────┼─────              │
│   (24, 'Aara', 21);          │  │ aysuh    | twenty            │
│                               │  │ rahul    | fifty             │
│ Rows inserted: 2              │  └──────────────────────────────┘
└──────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ CHECKPOINT: 6_checkpoint.py                                  │
├─────────────────────────────────────────────────────────────┤
│ Append "e.csv" to checkpoint.txt                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
                      FILE COMPLETE!
```

---

## 🚨 Error Handling Flow

```
                         ERROR DECISION TREE
                                │
                ┌───────────────┴───────────────┐
                │                               │
         File Level Errors              Row Level Errors
                │                               │
                ↓                               ↓
    ┌───────────────────────┐      ┌───────────────────────┐
    │ VALIDATION FAILURE    │      │ TYPE MISMATCH         │
    │ (2_validate.py)       │      │ (4_load_to_doris.py)  │
    ├───────────────────────┤      ├───────────────────────┤
    │ - File not found      │      │ - String in INT col   │
    │ - Not a valid CSV     │      │ - Invalid number      │
    │ - Empty file          │      │ - Invalid date format │
    │ - No columns          │      │ - Type conversion err │
    └───────┬───────────────┘      └───────┬───────────────┘
            │                              │
            └──────────┬───────────────────┘
                       │
                       ↓
            ┌──────────────────────┐
            │ CHECKPOINT FILE?     │
            ├──────────────────────┤
            │ YES - Don't retry    │
            │ NO  - Will retry     │
            └──────────┬───────────┘
                       │
                       ↓
        ┌──────────────────────────────┐
        │ SAVE TO error_files/         │
        ├──────────────────────────────┤
        │ Filename format:              │
        │   error_<original_name>.csv  │
        │                               │
        │ Examples:                     │
        │   error_e.csv                │
        │   error_b.csv                │
        └──────────────┬───────────────┘
                       │
                       ↓
                ┌─────────────┐
                │ LOG ERROR   │
                │ CONTINUE    │
                └─────────────┘


                SCHEMA MISMATCH FLOW
                        │
                        ↓
        ┌───────────────────────────────────┐
        │ First file (table doesn't exist)  │
        │ → Create table with detected types│
        │ → Save schema to table_map.json   │
        └───────────────┬───────────────────┘
                        │
                        ↓
        ┌───────────────────────────────────┐
        │ Subsequent file                    │
        │ → Read expected schema             │
        │ → Compare with current file schema │
        └───────────────┬───────────────────┘
                        │
            ┌───────────┴───────────┐
            │                       │
        Match                   Mismatch
            │                       │
            ↓                       ↓
    ┌──────────────┐    ┌────────────────────────┐
    │ CONTINUE     │    │ SAVE ENTIRE FILE       │
    │ Loading      │    │ to error_files/        │
    └──────────────┘    ├────────────────────────┤
                        │ - Log schema mismatch  │
                        │ - Checkpoint file      │
                        │ - Skip to next file    │
                        └────────────────────────┘
```

### **Error File Examples**

**error_e.csv** (Bad rows):
```csv
name,age
aysuh,twenty
rahul,fifty
```

**error_b.csv** (Schema mismatch - entire file):
```csv
name,salary
John,50000
Jane,60000
Bob,55000
```

**error_meal_metadata.csv** (Schema mismatch - different number of columns):
```csv
age,gender,weight_kg,...(54 columns total)
25,Male,75,...
```

---

## ⚙️ Kubernetes & Argo Integration

### **How Cron Scheduling Works**

```
┌─────────────────────────────────────────────────────────────┐
│ ARGO WORKFLOWS ARCHITECTURE                                  │
└─────────────────────────────────────────────────────────────┘

Minikube Cluster
├── Namespace: argo
│   ├── Argo Workflow Controller (Deployment)
│   │   └── Pod: workflow-controller-xxxxx
│   │       ├── Watches CronWorkflows
│   │       ├── Creates Workflows on schedule
│   │       └── Manages workflow lifecycle
│   │
│   ├── CronWorkflow: csv-doris-cron (Custom Resource)
│   │   └── spec:
│   │       ├── schedule: "*/5 * * * *"
│   │       ├── timezone: "America/New_York"
│   │       └── workflowSpec: {...}
│   │
│   └── Workflows (Created dynamically every 5 minutes)
│       ├── csv-doris-cron-1762411500 (Completed)
│       ├── csv-doris-cron-1762411800 (Completed)
│       └── csv-doris-cron-1762412100 (Running)
│           └── Pod: csv-doris-cron-1762412100
│               ├── Init Container: Install dependencies
│               └── Main Container: Run pipeline
│
└── Namespace: default (not used in this project)
```

### **Timeline of a Single Cron Execution**

```
Time: 06:45:00 (New York Time)
  │
  │ Argo Controller: "Time to create new workflow!"
  ↓
06:45:00 - CREATE Workflow: csv-doris-cron-1762411500
  │         └─ Generate unique ID from timestamp
  │
06:45:01 - CREATE Pod: csv-doris-cron-1762411500
  │         └─ Kubernetes Scheduler assigns to node
  │
06:45:02 - PULL Image: python:3.11-slim
  │         └─ (If not cached, download from Docker Hub)
  │
06:45:05 - START Init Container
  │         └─ pip install pandas pymysql requests numpy
  │
06:45:20 - Init Complete (dependencies installed)
  │
06:45:21 - START Main Container
  │         └─ python3 /app/scripts/pipeline_local.py
  │
06:45:21 - Pipeline Running...
  │         ├─ Discover files
  │         ├─ Process a.csv
  │         ├─ Process b.csv (schema mismatch → error)
  │         ├─ Process c.csv
  │         ├─ Process d.csv
  │         ├─ Process e.csv (2 bad rows → error file)
  │         ├─ Process emp.csv
  │         ├─ Process meal_metadata.csv (schema mismatch → error)
  │         └─ Process people.csv
  │
06:46:46 - Pipeline Complete (exit code 0)
  │
06:46:47 - Workflow Status: Succeeded ✓
  │
06:46:50 - DELETE Pod (logs saved in Argo)
  │
06:46:51 - Workflow archived (kept for history)
  │
  ↓
Wait until 06:50:00...
  │
06:50:00 - Next execution begins!
```

### **Volume Mounting Explained**

```
┌──────────────────────────────────────────────────────────────┐
│ WINDOWS HOST                                                  │
│ C:\Users\singh\Desktop\Minikube-Doris\                       │
│                                                                │
│ ├── data/                                                     │
│ │   ├── a.csv                                                │
│ │   ├── b.csv                                                │
│ │   └── ...                                                  │
│ ├── scripts/                                                  │
│ │   ├── pipeline_local.py                                    │
│ │   ├── 4_load_to_doris.py                                   │
│ │   └── ...                                                  │
│ ├── checkpoint.txt                                            │
│ └── table_map.json                                            │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 │ Minikube hostPath mount
                 │ (Configured in YAML)
                 ↓
┌──────────────────────────────────────────────────────────────┐
│ MINIKUBE VM                                                   │
│ /Minikube-Doris/  (Same files, shared)                       │
│                                                                │
│ ├── data/                                                     │
│ ├── scripts/                                                  │
│ ├── checkpoint.txt                                            │
│ └── table_map.json                                            │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 │ Pod volumeMount
                 │ (Mounted into container)
                 ↓
┌──────────────────────────────────────────────────────────────┐
│ POD CONTAINER                                                 │
│ /app/  (Read/write access to Windows files!)                 │
│                                                                │
│ ├── data/                                                     │
│ │   └── Python reads: pd.read_csv('/app/data/a.csv')        │
│ ├── scripts/                                                  │
│ │   └── Executes: python3 /app/scripts/pipeline_local.py    │
│ ├── checkpoint.txt                                            │
│ │   └── Updates persist to Windows!                          │
│ └── table_map.json                                            │
│     └── Changes visible on Windows!                           │
└──────────────────────────────────────────────────────────────┘

KEY BENEFIT: No need to rebuild Docker image when you edit scripts!
            Changes on Windows are immediately visible in pods.
```

### **Environment Variables Flow**

```yaml
# In argo-cron-pipeline.yaml
env:
  - name: DORIS_HOST
    value: "host.docker.internal"  # Special DNS from pod to host
  - name: DORIS_PORT
    value: "9030"
  - name: DORIS_DB
    value: "updated_test2"
```

```python
# In scripts (e.g., 4_load_to_doris.py)
import os

doris_host = os.getenv("DORIS_HOST", "localhost")
# Returns: "host.docker.internal"

doris_port = int(os.getenv("DORIS_PORT", "9030"))
# Returns: 9030

doris_db = os.getenv("DORIS_DB", "test")
# Returns: "updated_test2"

# Connect to Doris
conn = pymysql.connect(
    host=doris_host,  # host.docker.internal
    port=doris_port,  # 9030
    database=doris_db  # updated_test2
)
```

**host.docker.internal** resolves to:
- From pod: `192.168.29.181` (your Windows machine's IP on network)
- This allows pod to connect to Doris running outside Kubernetes

---

## 🎯 Key Design Decisions

### **1. Why DUPLICATE KEY Model?**
```sql
DUPLICATE KEY(`id`)
```
- Allows duplicate rows (Doris doesn't enforce uniqueness)
- Fast inserts (no primary key lookups)
- Suitable for append-only data pipelines
- Auto-increment handled by application (not database)

### **2. Why Majority Voting for Type Detection?**
```python
if numeric_count / total_count > 0.5:
    # Treat as numeric
```
- Handles data quality issues (occasional bad values)
- Example: Column with [22, 33, "N/A", 44] → 75% numeric → Treat as INT
- Bad values get filtered to error file during row validation

### **3. Why Checkpoint After Error?**
```python
# Even if file fails, checkpoint it
run(f"python3 6_checkpoint.py \"{next_file}\"", "Checkpoint (error)")
```
- Prevents infinite retry loops
- User can inspect error file and decide to reprocess manually
- Keeps pipeline moving forward

### **4. Why Separate Staged Files?**
```python
staged_path = os.path.join(STAGE_DIR, f"staged_{filename}")
```
- Original files remain untouched
- Can debug by comparing original vs staged
- Staged files can be deleted after successful load

### **5. Why Volume Mount Instead of Docker Image?**
- **Fast iteration**: Edit Python script → Immediately available in next pod
- **No rebuild**: No need to rebuild/push Docker image for code changes
- **Live data**: CSV files added to folder are immediately processable
- **Debugging**: Can view checkpoint.txt, error files in real-time

---

## 📈 Performance Characteristics

**Pipeline Metrics** (from logs):
- Total runtime: ~60 seconds for 8 files
- Files processed: 6 successful
- Schema mismatches: 2 files
- Bad rows filtered: 2 rows
- Total rows loaded: 30 rows

**Breakdown by Stage**:
```
Stage                  | Time per File | % of Total
-----------------------|---------------|------------
Discover & Validate    | ~2-3 sec     | 10%
Transform              | ~2-3 sec     | 10%
Load to Doris          | ~3-5 sec     | 60%
Checkpoint             | ~1 sec       | 5%
Overhead (subprocess)  | ~1-2 sec     | 15%
```

**Bottlenecks**:
1. **Doris Connection**: Each file creates new connection (could use connection pooling)
2. **Subprocess Overhead**: Running 5+ Python scripts per file (could consolidate)
3. **Row-by-row Validation**: O(n) for each row (acceptable for small datasets)

**Scalability**:
- Current: 8 files, ~200 total rows → 60 seconds
- Estimated: 100 files, ~10,000 rows → 10-15 minutes
- Limit: Single-threaded, sequential processing

---

## 🔍 Monitoring & Debugging

### **View Live Logs**
```powershell
# Follow logs from all workflow pods
kubectl logs -n argo -l workflows.argoproj.io/workflow --tail=200 -f

# View specific workflow
argo logs -n argo csv-doris-cron-1762411500 -f

# List recent workflows
argo list -n argo

# Get workflow details
argo get -n argo csv-doris-cron-1762411500
```

### **Check Files**
```powershell
# View checkpoint
Get-Content C:\Users\singh\Desktop\Minikube-Doris\checkpoint.txt

# View error files
Get-ChildItem C:\Users\singh\Desktop\Minikube-Doris\error_files

# View staged files
Get-ChildItem C:\Users\singh\Desktop\Minikube-Doris\stage_test

# View table map
Get-Content C:\Users\singh\Desktop\Minikube-Doris\table_map.json
```

### **Check Database**
```sql
-- Connect to Doris
mysql -h 192.168.29.181 -P 9030 -u root

-- View table schema
DESC updated_test2.main_data_table;

-- Count rows
SELECT COUNT(*) FROM updated_test2.main_data_table;

-- View sample data
SELECT * FROM updated_test2.main_data_table LIMIT 10;

-- Check data types are correct
SELECT 
  name,
  age,
  TYPEOF(age) as age_type  -- Should show TINYINT
FROM updated_test2.main_data_table
LIMIT 5;
```

---

## 🎓 Summary

**This pipeline demonstrates**:
1. ✅ Kubernetes-native workflow orchestration (Argo Workflows)
2. ✅ Cron-based scheduling (every 5 minutes)
3. ✅ Intelligent schema detection (majority voting algorithm)
4. ✅ Row-level data validation (type checking)
5. ✅ Error handling (schema mismatches, bad rows)
6. ✅ Incremental processing (checkpoint-based)
7. ✅ Clean separation of concerns (6 specialized scripts)
8. ✅ Production-ready logging (timestamps, progress, summaries)
9. ✅ Volume mounting for live code/data updates
10. ✅ MySQL protocol for database loading

**Perfect for**:
- ETL pipelines with varying CSV schemas
- Data quality enforcement
- Automated data ingestion
- Multi-tenant data loading (one table for compatible schemas)

---

*End of Documentation*
