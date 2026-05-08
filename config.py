import os
from datetime import datetime

# ===== DISABLE SSL WARNINGS =====
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# HTTP Parameters
HTTP_VERSION = "HTTP/1.1"
TIMEOUT = 15  # seconds
RETRY_ATTEMPTS = 1

# ===== Connection Tracking =====
ENABLE_HTTP_TRACE = True
ENABLE_FAILURE_NETWORK_TRACE = True
ENABLE_FAILURE_DNS_TRACE = True

# ===== Asynchronous Mode (asyncio + aiohttp + Semaphore) =====
ASYNC_MAX_CONCURRENCY = 20
FAILURE_TRACE_CONCURRENCY = 4
MAX_FAILURE_TRACE_COUNT = 0

TRACEROUTE_MAX_HOPS = 15
TRACEROUTE_TIMEOUT_SECONDS = 30
TRACEROUTE_OUTPUT_LIMIT = 1200

DNS_TRACE_TIMEOUT_SECONDS = 4

# User-Agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
]

# Delay parameters
DELAY_BETWEEN_REQUESTS = 0.1  # seconds

# Status to exclude
EXCLUDE_STATUS = ['例外']  # anomalies/exceptions

# URL processing order
PROCESS_URLS_FROM_BOTTOM = False # False (default)

# Row scanning range
SCAN_START_ROW = 0
SCAN_END_ROW = 500     # default 'None', to scan until the end of the file

# Input file
INPUT_CSV = "Chinese government websites.csv"

# Output files
DATE_STAMP = datetime.today().strftime("%Y-%m-%d")
OUTPUT_DIR = "results"
CSV_NAME = f"results_{DATE_STAMP}.csv"
LOG_NAME = f"console_log_{DATE_STAMP}.txt"
OUTPUT_CSV = os.path.join(OUTPUT_DIR, CSV_NAME)
OUTPUT_LOG = os.path.join(OUTPUT_DIR, LOG_NAME)