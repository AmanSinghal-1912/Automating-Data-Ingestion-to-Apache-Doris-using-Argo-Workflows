# 6_checkpoint.py
from local_config import CHECKPOINT_FILE, logging

def mark_done(filename):
    with open(CHECKPOINT_FILE, "a") as f:
        f.write(filename + "\n")
    print(f"Checkpoint: {filename}")
    logging.info(f"Checkpoint: {filename}")

if __name__ == "__main__":
    import sys
    mark_done(sys.argv[1])