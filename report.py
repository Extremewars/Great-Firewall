import logging
from typing import List, Dict, Any, Optional
import pandas as pd

from utils.table_printer import print_admin_level_summary_table, print_result_classification_table

def build_summary_statistics(results: List[Dict[str, Any]]) -> Optional[pd.DataFrame]:
    if not results:
        return None

    results_df = pd.DataFrame(results)

    logging.info("\n" + "=" * 80)
    logging.info("RESULTS SUMMARY")
    logging.info("=" * 80)

    category_counts = results_df["status_category"].value_counts()

    logging.info("\nSTATUS CATEGORIES:")
    for category, count in category_counts.items():
        percentage = (count / len(results_df)) * 100
        bar = "█" * int(percentage / 5)
        logging.info(f"{category:20} │ {bar:20} │ {count:4} ({percentage:5.1f}%)")

    logging.info("\nRESPONSE TIME STATISTICS:")
    valid_responses = results_df[results_df["response_time"].notna()]["response_time"]
    if len(valid_responses) > 0:
        logging.info(f"Average time:    {valid_responses.mean():.2f}s")
        logging.info(f"Min:             {valid_responses.min():.2f}s")
        logging.info(f"Max:             {valid_responses.max():.2f}s")
        logging.info(f"Median:          {valid_responses.median():.2f}s")

    logging.info("\nHTTP CODES:")
    status_codes = results_df[results_df["status_code"].notna()]["status_code"].value_counts().sort_index()
    for code, count in status_codes.items():
        logging.info(f"HTTP {int(code):3}:  {count:4} pages")

    logging.info("\nTABLES:")
    print_admin_level_summary_table(results_df)
    print_result_classification_table(results_df)

    logging.info("\n" + "=" * 80)
    return results_df


def save_results(results: List[Dict[str, Any]], output_file: str) -> pd.DataFrame:
    results_df = pd.DataFrame(results)
    results_df.to_csv(output_file, index=False, encoding='utf-8')
    logging.info(f"\nResults saved: {output_file}")
    return results_df
