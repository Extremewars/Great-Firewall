import logging
import pandas as pd
from typing import Optional
from config import EXCLUDE_STATUS, PROCESS_URLS_FROM_BOTTOM


class DataAnalyzer:
    def __init__(self, csv_file: str) -> None:
        self.csv_file: str = csv_file
        self.df: Optional[pd.DataFrame] = None
        self.load_data()
    
    def load_data(self) -> None:
        try:
            self.df = pd.read_csv(self.csv_file, encoding='utf-8')
            logging.info(f"Loaded {len(self.df)} records")
            logging.info(f"Columns: {list(self.df.columns)}")
        except UnicodeDecodeError:
            logging.warning("UTF-8 failed, trying GB2312...")
            self.df = pd.read_csv(self.csv_file, encoding='gb2312')
            logging.info(f"Loaded {len(self.df)} records (GB2312)")
    
    def filter_valid_data(self) -> pd.DataFrame:
        if self.df is None:
            return pd.DataFrame()
            
        initial_count = len(self.df)
        self.df = self.df[~self.df['status'].isin(EXCLUDE_STATUS)]
        removed = initial_count - len(self.df)
        logging.info(f"\nFiltering: Removed {removed} anomalies (status=例外)")
        logging.info(f"Remaining: {len(self.df)} records to test")
        return self.df
    
    
    def get_urls_for_testing(self) -> pd.DataFrame:
        if self.df is None:
            return pd.DataFrame()
            
        # Delete empty or NaN URLs
        urls = self.df[self.df['url'].notna() & (self.df['url'] != '')].copy()

        if PROCESS_URLS_FROM_BOTTOM:
            urls = urls.iloc[::-1].reset_index(drop=True)
            logging.info("Testing order: bottom to top")
        else:
            logging.info("Testing order: top to bottom")

        return urls
    