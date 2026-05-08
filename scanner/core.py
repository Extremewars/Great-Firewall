import asyncio
import time
from typing import Any

import aiohttp
import pandas as pd
from tqdm import tqdm

from config import (
    TIMEOUT,
    DELAY_BETWEEN_REQUESTS,
    ENABLE_HTTP_TRACE,
    ENABLE_FAILURE_NETWORK_TRACE,
    ENABLE_FAILURE_DNS_TRACE,
    ASYNC_MAX_CONCURRENCY,
)
from scanner.diagnostics import run_batch_diagnostics_async
from scanner.http import (
    apply_http_exception,
    build_result_template,
    categorize_status,
    fetch_with_retries,
    normalize_url,
)
from report import build_summary_statistics, save_results
from utils.time_utils import format_elapsed_hhmmss


class URLScanner:
    def __init__(self, urls_df: pd.DataFrame) -> None:
        self.urls_df = urls_df.copy()
        self.results: list[dict[str, Any]] = []

    async def _test_single_url_async(
        self,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
        row: pd.Series,
        idx: int,
        show_progress: bool,
        progress_lock: asyncio.Lock,
        progress_bar: tqdm | None,
    ) -> dict[str, Any]:
        url = row.get('url')
        row_id = row.get('id', idx)
        name = row.get('name', 'N/A')
        metadata = {
            'unit': row.get('unit'),
            'province': row.get('province'),
            'prefecture': row.get('prefecture'),
            'county': row.get('county'),
            'admin_level': row.get('admin_level'),
        }

        if pd.isna(name):
            name = 'N/A'
        else:
            name = str(name)[:50]

        result = build_result_template(row_id=row_id, name=name, url=url, metadata=metadata)
        normalized_url = normalize_url(url)
        result['normalized_url'] = normalized_url

        async with semaphore:
            response, response_time, error = await fetch_with_retries(session, normalized_url)

        if error is None and response is not None:
            if ENABLE_HTTP_TRACE:
                redirect_urls = [str(resp.url) for resp in response.history]
                final_url = str(response.url)
                full_chain = redirect_urls + [final_url]
                result['final_url'] = final_url
                result['redirect_count'] = len(redirect_urls)
                result['redirect_chain'] = ' -> '.join(full_chain) if full_chain else None

            result['status_code'] = response.status
            result['response_time'] = round(response_time, 2)
            result['status_category'] = categorize_status(response.status)
        else:
            apply_http_exception(result, error)

        async with progress_lock:
            if show_progress and progress_bar is not None:
                progress_bar.update(1)

        return result

    async def _test_all_urls_async(self, show_progress: bool = True, started_at: float | None = None) -> list[dict[str, Any]]:
        total = len(self.urls_df)
        semaphore = asyncio.Semaphore(max(1, ASYNC_MAX_CONCURRENCY))
        progress_lock = asyncio.Lock()
        if started_at is None:
            started_at = time.perf_counter()
        progress_bar = None

        if show_progress:
            progress_bar = tqdm(
                total=total,
                desc='Progress',
                unit='url',
                dynamic_ncols=True,
                leave=True,
            )

        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        connector = aiohttp.TCPConnector(limit=max(1, ASYNC_MAX_CONCURRENCY), ssl=False)

        try:
            async with aiohttp.ClientSession(timeout=timeout, connector=connector, trust_env=True) as session:
                tasks = []
                for idx, (_, row) in enumerate(self.urls_df.iterrows(), 1):
                    tasks.append(
                        asyncio.create_task(
                            self._test_single_url_async(
                                session=session,
                                semaphore=semaphore,
                                row=row,
                                idx=idx,
                                show_progress=show_progress,
                                progress_lock=progress_lock,
                                progress_bar=progress_bar,
                            )
                        )
                    )
                    if DELAY_BETWEEN_REQUESTS > 0:
                        await asyncio.sleep(DELAY_BETWEEN_REQUESTS)

                results = await asyncio.gather(*tasks)
        finally:
            if progress_bar is not None:
                progress_bar.close()
        # Save results after HTTP stage to prevent data loss if further diagnostics are interrupted
        self.results = results

        failed_count = sum(1 for item in results if item.get('status_category') != 'AVAILABLE')
        if failed_count > 0 and (ENABLE_FAILURE_DNS_TRACE or ENABLE_FAILURE_NETWORK_TRACE):
            print(
                f"Starting diagnostics for failed connections: {failed_count} URLs"
            )

        try:
            await run_batch_diagnostics_async(results, normalize_url)
        except asyncio.CancelledError:
            print("\nTrace diagnostics interrupted. Returning URL scanning results")
            return results

        return results

    def test_all_urls(self, show_progress: bool = True, started_at: float | None = None) -> list[dict[str, Any]]:
        total = len(self.urls_df)
        internal_started_at = started_at if started_at is not None else time.perf_counter()

        try:
            self.results = asyncio.run(
                self._test_all_urls_async(show_progress=show_progress, started_at=internal_started_at)
            )
        except KeyboardInterrupt:
            print("\nOperation interrupted. Returning current results.")
            if not self.results:
                self.results = []

        elapsed = format_elapsed_hhmmss(time.perf_counter() - internal_started_at)
        print(f"\nTesting completed: {total} URLs")
        print(f"URL testing time: {elapsed}")
        return self.results

    def get_summary_statistics(self) -> pd.DataFrame:
        return build_summary_statistics(self.results)

    def save_results(self, output_file: str) -> Any:
        return save_results(self.results, output_file)
