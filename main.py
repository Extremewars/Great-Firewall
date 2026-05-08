import sys
import os
import time
import logging
from typing import Optional
import pandas as pd

from analysis import DataAnalyzer
from scanner.core import URLScanner
from utils.time_utils import format_elapsed_hhmmss
from config import (
    INPUT_CSV, OUTPUT_DIR, OUTPUT_LOG, OUTPUT_CSV, SCAN_START_ROW, 
    SCAN_END_ROW, TIMEOUT, DELAY_BETWEEN_REQUESTS, ASYNC_MAX_CONCURRENCY,
    RETRY_ATTEMPTS, ENABLE_HTTP_TRACE, ENABLE_FAILURE_NETWORK_TRACE,
    ENABLE_FAILURE_DNS_TRACE
)

def _resolve_output_paths(base_csv: str, base_log: str) -> tuple[str, str]:
    """Return a pair of paths with an optional suffix _2, _3... for subsequent runs on the same day"""
    csv_root, csv_ext = os.path.splitext(base_csv)
    log_root, log_ext = os.path.splitext(base_log)

    run_number = 1
    while True:
        suffix = "" if run_number == 1 else f"_{run_number}"
        candidate_csv = f"{csv_root}{suffix}{csv_ext}"
        candidate_log = f"{log_root}{suffix}{log_ext}"

        if not os.path.exists(candidate_csv) and not os.path.exists(candidate_log):
            return candidate_csv, candidate_log

        run_number += 1

def print_config() -> None:
    logging.info("\n" + "=" * 80)
    logging.info("SCANNING CONFIGURATION")
    logging.info("=" * 80)
    end_row_str = SCAN_END_ROW if SCAN_END_ROW is not None else "End of file"
    logging.info(f"   Row analysis range   : {SCAN_START_ROW} - {end_row_str}")
    logging.info(f"   URL Timeout          : {TIMEOUT}s")
    logging.info(f"   Retries              : {RETRY_ATTEMPTS}")
    logging.info(f"   Request delay        : {DELAY_BETWEEN_REQUESTS}s")
    logging.info(f"   Max concurrency      : {ASYNC_MAX_CONCURRENCY}")
    logging.info(f"   HTTP tracking (trace): {'Enabled' if ENABLE_HTTP_TRACE else 'Disabled'}")
    logging.info(f"   DNS Diagnostics      : {'Enabled' if ENABLE_FAILURE_DNS_TRACE else 'Disabled'}")
    logging.info(f"   Network Diagnostics  : {'Enabled' if ENABLE_FAILURE_NETWORK_TRACE else 'Disabled'}")

def main() -> Optional[pd.DataFrame]:
    script_started_at = time.perf_counter()

    # Ensure the output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    output_csv, output_log = _resolve_output_paths(OUTPUT_CSV, OUTPUT_LOG)

    # Configure native logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[
            logging.FileHandler(output_log, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )

    csv_file = INPUT_CSV
    if not os.path.exists(csv_file):
        logging.error(f"\nFile does not exist: {csv_file}")
        sys.exit(1)
    
    logging.info(f"\nFound file: {csv_file}")

    print_config()
    
    # ===== STAGE 1: DATA ANALYSIS AND FILTERING =====
    logging.info("\n" + "=" * 80)
    logging.info("STAGE 1: DATA ANALYSIS AND FILTERING")
    logging.info("=" * 80)
    
    analyzer = DataAnalyzer(csv_file)
    analyzer.filter_valid_data()

    # Getting URLs for testing
    urls_for_testing = analyzer.get_urls_for_testing()

    end_limit = SCAN_END_ROW if SCAN_END_ROW else len(urls_for_testing)
    urls_for_testing = urls_for_testing.iloc[SCAN_START_ROW:end_limit]

    if len(urls_for_testing) == 0:
        logging.error("\nNo URLs to test!")
        sys.exit(1)
    
    # ===== STAGE 2: RUNNING THE SCANNER =====
    logging.info("\n" + "=" * 80)
    logging.info("STAGE 2: RUNNING THE SCANNER")
    logging.info("=" * 80)
     
    scanner = URLScanner(urls_for_testing)
    scanner.test_all_urls(show_progress=True, started_at=script_started_at)
    
    # ===== STAGE 3: RESULTS SUMMARY =====
    logging.info("\n" + "=" * 80)
    logging.info("STAGE 3: RESULTS SUMMARY")
    logging.info("=" * 80)

    results_df = scanner.get_summary_statistics()

    logging.info(f"\nCreated files:")
    if results_df is None or len(results_df) == 0:
        logging.warning("No results to save")
        sys.exit(1)
    else:
        scanner.save_results(output_csv)
        logging.info(f"   {output_csv}  - CSV file with results")

    logging.info(f"   {output_log}  - Console logs")
    total_runtime = time.perf_counter() - script_started_at
    logging.info(f"\nTotal script run time: {format_elapsed_hhmmss(total_runtime)}")

    return results_df


if __name__ == "__main__":
    main()