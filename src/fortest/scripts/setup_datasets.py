
import os
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REPO_URL = "https://github.com/forecastingresearch/forecastbench-datasets"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA_DIR = os.path.join(BASE_DIR, "data")
TARGET_DIR = os.path.join(DATA_DIR, "forecastbench")

def ensure_forecastbench_data():
    """
    Checks if the forecastbench-datasets repo is cloned in data/forecastbench.
    If not, clones it.
    """
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    if os.path.exists(TARGET_DIR):
        logger.info(f"ForecastBench data found at {TARGET_DIR}")
        return

    logger.info(f"Cloning ForecastBench datasets from {REPO_URL} to {TARGET_DIR}...")
    try:
        subprocess.run(["git", "clone", REPO_URL, TARGET_DIR], check=True)
        logger.info("Clone successful.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to clone repository: {e}")
        raise

if __name__ == "__main__":
    ensure_forecastbench_data()
