import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, "..")

ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
SETTINGS_PATH = os.path.join(PROJECT_ROOT, "settings.json")
LABEL_PATH = os.path.join(PROJECT_ROOT, "labels.txt")
CACHE_DIR = os.path.join(PROJECT_ROOT, "filings_cache")

os.makedirs(CACHE_DIR, exist_ok=True)