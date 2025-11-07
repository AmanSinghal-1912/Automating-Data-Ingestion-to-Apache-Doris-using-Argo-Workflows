# local_config.py
import os
import logging

BASE_DIR = "/app"
CSV_DIR       = os.path.join(BASE_DIR, "data")
STAGE_DIR     = os.path.join(BASE_DIR, "stage_test")
LOG_DIR       = os.path.join(BASE_DIR, "pipeline_logs")
CHECKPOINT_FILE = os.path.join(BASE_DIR, "checkpoint.txt")
TABLE_MAP_FILE  = os.path.join(BASE_DIR, "table_map.json")

# DORIS Configuration - Use functions to read at runtime, not at import time
def get_doris_host():
    return os.getenv("DORIS_HOST", "host.minikube.internal")

def get_doris_port():
    return int(os.getenv("DORIS_PORT", "9030"))

def get_doris_user():
    return os.getenv("DORIS_USER", "root")

def get_doris_pass():
    return os.getenv("DORIS_PASS", "")

def get_doris_db():
    return os.getenv("DORIS_DB", "test2")

def get_doris_fe_http_port():
    return int(os.getenv("DORIS_FE_HTTP_PORT", "8030"))

def get_doris_fe():
    return f"http://{get_doris_host()}:{get_doris_fe_http_port()}"

# Legacy compatibility - these read at import time but can be overridden by env
DORIS_HOST = get_doris_host()
DORIS_PORT = get_doris_port()
DORIS_USER = get_doris_user()
DORIS_PASS = get_doris_pass()
DORIS_DB = get_doris_db()
DORIS_FE_HTTP_PORT = get_doris_fe_http_port()
DORIS_FE = get_doris_fe()
DORIS_MYSQL_PORT = DORIS_PORT


for d in [CSV_DIR, STAGE_DIR, LOG_DIR]:
    os.makedirs(d, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "pipeline.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filemode='a'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)