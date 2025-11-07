# pipeline_local.py
import subprocess
import os
import time
from datetime import datetime
from local_config import logging, CSV_DIR

def log_step(message, level="INFO"):
    """Print and log a message with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    symbol = {
        "INFO": "[INFO]",
        "SUCCESS": "[OK]  ",
        "ERROR": "[ERR] ",
        "WARN": "[WARN]",
        "START": "[>>>] ",
        "PROCESS": "[FILE]"
    }.get(level, "      ")
    
    formatted = f"[{timestamp}] {symbol} {message}"
    print(formatted)
    
    if level == "ERROR":
        logging.error(message)
    elif level == "WARN":
        logging.warning(message)
    else:
        logging.info(message)

def run(cmd, desc):
    print(f"\n{'='*60}")
    print(f" {desc}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f" FAILED: {result.stderr}")
        logging.error(f"{desc} failed: {result.stderr}")
        raise RuntimeError(f"{desc} failed")
    output = result.stdout.strip()
    if output:
        print(output)
    logging.info(f"SUCCESS: {desc}")
    return output

if __name__ == "__main__":
    start_time = time.time()
    processed_count = 0
    error_count = 0
    skipped_rows_total = 0
    
    # Clear banner for each workflow run
    print("\n" + "=" * 70)
    print("  *** ARGO CRON WORKFLOW STARTED ***")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")
    
    log_step("CSV TO DORIS PIPELINE STARTED", "START")
    
    try:
        # 1. Ingest - discover all CSVs
        log_step("Step 1: Discovering CSV files...", "INFO")
        run("python3 0_ingest.py", "Ingest discovery")
        
        # Count total files
        import glob
        all_files = sorted([os.path.basename(f) for f in glob.glob(os.path.join(CSV_DIR, "*.csv"))])
        log_step(f"Found {len(all_files)} CSV files: {', '.join(all_files)}", "INFO")
        
        # Check how many already processed
        checkpoint_file = os.path.join(os.path.dirname(CSV_DIR), "checkpoint.txt")
        processed_already = set()
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file) as f:
                processed_already = {line.strip() for line in f if line.strip()}
        
        remaining = len(all_files) - len(processed_already)
        log_step(f"Already processed: {len(processed_already)} files", "INFO")
        log_step(f"Remaining to process: {remaining} files", "INFO")
        
        # 2. Process ALL unprocessed files
        file_number = 1
        while True:
            # Discover next unprocessed file
            next_file = run("python3 discover_next_1.py", "Discover next file")
            if not next_file:
                log_step("All files processed!", "SUCCESS")
                break
            
            log_step("=" * 60, "PROCESS")
            log_step(f"Processing file {file_number}/{remaining}: {next_file}", "PROCESS")
            log_step("=" * 60, "PROCESS")
            
            try:
                # 3. Validate
                log_step(f"Validating {next_file}...", "INFO")
                run(f"python3 2_validate.py \"{next_file}\"", f"Validate {next_file}")
                log_step(f"Validation passed", "SUCCESS")
                
                # 4. Transform & Stage
                log_step(f"Transforming and staging {next_file}...", "INFO")
                transform_output = run("python3 3_transform.py", "Transform & Stage")
                staged = transform_output.strip().splitlines()[-1].strip()
                log_step(f"Staged file created: {os.path.basename(staged)}", "SUCCESS")
                
                # 5. Load to Doris (with schema validation and row-level error handling)
                log_step(f"Loading to Doris database...", "INFO")
                env = os.environ.copy()
                env["DORIS_HOST"] = os.getenv("DORIS_HOST", "host.docker.internal")
                env["DORIS_FE_HTTP_PORT"] = os.getenv("DORIS_FE_HTTP_PORT", "8030")
                
                result = subprocess.run(
                    ["python3", "4_load_to_doris.py", staged, next_file], 
                    check=True, 
                    env=env,
                    capture_output=True,
                    text=True
                )
                print(result.stdout)
                
                # Check if there were skipped rows
                if "bad rows" in result.stdout.lower() or "skipped" in result.stdout.lower():
                    import re
                    match = re.search(r'(\d+)\s+bad rows', result.stdout, re.IGNORECASE)
                    if match:
                        bad_count = int(match.group(1))
                        skipped_rows_total += bad_count
                        log_step(f"Skipped {bad_count} bad rows - saved to error file", "WARN")
                
                log_step(f"Data loaded successfully", "SUCCESS")
                
                # 6. Checkpoint - mark as processed
                run(f"python3 6_checkpoint.py \"{next_file}\"", "Update checkpoint")
                
                processed_count += 1
                file_number += 1
                log_step(f"COMPLETED: {next_file}", "SUCCESS")
                
            except subprocess.CalledProcessError as e:
                # Check if it's a schema mismatch error
                if "SCHEMA_MISMATCH" in e.stderr or "SCHEMA_MISMATCH" in e.stdout:
                    log_step(f"Schema mismatch detected in {next_file}", "WARN")
                    log_step(f"File saved to error_files/error_{next_file}", "WARN")
                    log_step(f"Expected schema doesn't match - file skipped", "WARN")
                    error_count += 1
                    # Still checkpoint it so we don't retry
                    run(f"python3 6_checkpoint.py \"{next_file}\"", "Checkpoint (error)")
                    file_number += 1
                else:
                    # Other errors - don't checkpoint, allow retry
                    log_step(f"Processing failed: {next_file}", "ERROR")
                    log_step(f"Error: {e.stderr}", "ERROR")
                    raise
        
        # Summary
        elapsed_time = time.time() - start_time
        print("\n" + "=" * 70)
        print("  *** PIPELINE COMPLETED SUCCESSFULLY ***")
        print("=" * 70)
        log_step(f"Total runtime: {elapsed_time:.2f} seconds", "INFO")
        log_step(f"Files processed: {processed_count}", "SUCCESS")
        if error_count > 0:
            log_step(f"Schema mismatch errors: {error_count} files", "WARN")
        if skipped_rows_total > 0:
            log_step(f"Bad rows skipped: {skipped_rows_total} rows", "WARN")
        print("=" * 70 + "\n")
        
    except Exception as e:
        log_step(f"Pipeline failed: {e}", "ERROR")
        logging.error(f"Pipeline failed: {e}")