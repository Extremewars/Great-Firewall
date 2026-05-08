import logging
import pandas as pd
from typing import List, Optional, Any, Dict, Tuple

ADMIN_LEVEL_LABELS: List[str] = [
    "National and ministerial organs",
    "Sub-ministerial departments",
    "Provincial-level governments and their departments",
    "Prefecture-level governments and their departments",
    "County/district-level governments",
]

class ConsoleTablePrinter:
    def __init__(self, column_spacing: int = 2, separator_char: str = "-") -> None:
        self.column_spacing = column_spacing
        self.separator_char = separator_char

    def print_table(self, headers: List[str], rows: List[List[Any]], title: Optional[str] = None) -> None:
        """
        Print a table with any number of columns.

        Args:
            headers: list of column headers
            rows: list of rows (each row is a list of values)
            title: optional table title
        """
        if not headers:
            return

        normalized_rows = [list(row) for row in rows]
        col_count = len(headers)

        col_widths = [len(str(headers[idx])) for idx in range(col_count)]
        for row in normalized_rows:
            for idx in range(col_count):
                value = ""
                if idx < len(row):
                    value = "" if row[idx] is None else str(row[idx])
                col_widths[idx] = max(col_widths[idx], len(value))

        gap = " " * self.column_spacing
        line_width = sum(col_widths) + (self.column_spacing * (col_count - 1))

        if title:
            logging.info("\n" + "=" * line_width)
            logging.info(title)
            logging.info("=" * line_width)

        header_line = gap.join(
            str(headers[idx]).ljust(col_widths[idx]) for idx in range(col_count)
        )
        logging.info(header_line)
        logging.info(self.separator_char * line_width)

        for row in normalized_rows:
            rendered: List[str] = []
            for idx in range(col_count):
                value = ""
                if idx < len(row):
                    value = "" if row[idx] is None else str(row[idx])

                # First column is usually descriptive, subsequent ones numerical/right-aligned.
                if idx == 0:
                    rendered.append(value.ljust(col_widths[idx]))
                else:
                    rendered.append(value.rjust(col_widths[idx]))

            logging.info(gap.join(rendered))


def map_admin_level_to_label(raw_value: Any) -> Optional[str]:
    """Map admin_level from input data to required table labels."""
    if raw_value is None:
        return None

    value = str(raw_value).strip().lower()
    if not value or value == "nan":
        return None

    numeric_map: Dict[int, str] = {
        0: ADMIN_LEVEL_LABELS[0],
        1: ADMIN_LEVEL_LABELS[1],
        2: ADMIN_LEVEL_LABELS[2],
        3: ADMIN_LEVEL_LABELS[3],
        4: ADMIN_LEVEL_LABELS[4],
    }

    try:
        numeric_value = int(float(value))
        if numeric_value in numeric_map:
            return numeric_map[numeric_value]
    except ValueError:
        pass


    if "national" in value or "ministerial" in value or "central" in value:
        return ADMIN_LEVEL_LABELS[0]
    if "sub-ministerial" in value or "sub ministerial" in value or value == "departmental":
        return ADMIN_LEVEL_LABELS[1]
    if "provincial" in value or value == "province":
        return ADMIN_LEVEL_LABELS[2]
    if "prefecture" in value:
        return ADMIN_LEVEL_LABELS[3]
    if "county" in value or "district" in value:
        return ADMIN_LEVEL_LABELS[4]

    return None


def build_admin_level_summary_rows(results_df: pd.DataFrame, admin_level_column: str = "admin_level") -> Tuple[List[List[Any]], Optional[Dict[str, int]]]:
    """Build summary table rows according to administrative level."""
    if admin_level_column not in results_df.columns:
        return [], None

    counts: Dict[str, int] = {label: 0 for label in ADMIN_LEVEL_LABELS}
    unknown_count = 0

    for raw_value in results_df[admin_level_column]:
        mapped_label = map_admin_level_to_label(raw_value)
        if mapped_label is None:
            unknown_count += 1
        else:
            counts[mapped_label] += 1

    rows: List[List[Any]] = [[label, counts[label]] for label in ADMIN_LEVEL_LABELS]
    if unknown_count > 0:
        rows.append(["Unmapped/other", unknown_count])

    return rows, counts


def print_admin_level_summary_table(results_df: pd.DataFrame, printer: Optional[ConsoleTablePrinter] = None) -> None:
    """Print a table with the number of tested websites by administrative levels."""
    rows, _ = build_admin_level_summary_rows(results_df)
    if not rows:
        logging.info("\nMissing 'admin_level' column in test results.")
        return

    headers: List[str] = [
        "Administrative level",
        "Total number of websites analysed",
    ]

    table_printer = printer or ConsoleTablePrinter()
    table_printer.print_table(headers=headers, rows=rows)


RESULT_CLASSIFICATION_LABELS: List[str] = [
    "Successful",
    "Time-out",
    "Blocked (Server-side)",
    "Blocked (DNS)",
    "Other error"
]


def map_status_to_classification(status_category: Any, status_message: Any = "") -> str:
    status = str(status_category).upper() if status_category else ""
    msg = str(status_message).lower() if status_message else ""

    if status in ("AVAILABLE", "SUCCESS", "200"):
        return "Successful"
    elif status == "TIMEOUT" or "timeout" in msg:
        return "Time-out"
    elif "dns" in msg or "resolve" in msg or "name or service not known" in msg:
        return "Blocked (DNS)"
    elif status == "BLOCKED" or "403" in msg or "forbidden" in msg or "refused" in msg or "reset" in msg:
        return "Blocked (Server-side)"
    else:
        return "Other error"


def build_result_classification_rows(results_df: pd.DataFrame, status_column: str = "status_category", message_column: str = "error_message") -> List[List[Any]]:
    if status_column not in results_df.columns:
        return []

    counts: Dict[str, int] = {label: 0 for label in RESULT_CLASSIFICATION_LABELS}

    # If the error message column is missing, substitute empty strings
    messages = results_df[message_column] if message_column in results_df.columns else [""] * len(results_df)
    statuses = results_df[status_column]

    for status_val, msg_val in zip(statuses, messages):
        mapped_label = map_status_to_classification(status_val, msg_val)
        counts[mapped_label] += 1

    rows: List[List[Any]] = [[label, counts[label]] for label in RESULT_CLASSIFICATION_LABELS]
    return rows


def print_result_classification_table(results_df: pd.DataFrame, printer: Optional[ConsoleTablePrinter] = None) -> None:
    rows = build_result_classification_rows(results_df)

    if not rows:
        logging.info("\nMissing status column in test results.")
        return

    headers: List[str] = [
        "Classification",
        "Total number of websites"
    ]

    table_printer = printer or ConsoleTablePrinter()
    table_printer.print_table(headers=headers, rows=rows, title="RESULTS CLASSIFICATION")
