import asyncio
import random
import socket
import time
import unicodedata
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import aiohttp

from config import HTTP_VERSION, RETRY_ATTEMPTS, TIMEOUT, USER_AGENTS


def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)


def prepare_headers() -> dict[str, str]:
    return {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def normalize_url(url: Any) -> str:
    # NFKC replaces full-width characters (e.g. '：') with ASCII, which prevents ValueError in urlparse.
    normalized = unicodedata.normalize("NFKC", str(url)).strip()
    if not normalized.lower().startswith(("http://", "https://")):
        normalized = "http://" + normalized
    return normalized


def extract_domain(normalized_url: str) -> str:
    try:
        parsed = urlparse(str(normalized_url))
    except ValueError:
        return ""
    return parsed.netloc or parsed.path.split("/")[0]


def categorize_status(status_code: int) -> str:
    if 200 <= status_code < 300:
        return "AVAILABLE"
    if status_code == 403:
        return "BLOCKED_403"
    if status_code == 404:
        return "NOT_FOUND"
    if 400 <= status_code < 500:
        return "CLIENT_ERROR"
    if status_code >= 500:
        return "SERVER_ERROR"
    return "OTHER"


def build_result_template(row_id: int | str, name: str, url: str, metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row_id,
        "name": name,
        "url": url,
        "unit": metadata.get("unit"),
        "province": metadata.get("province"),
        "prefecture": metadata.get("prefecture"),
        "county": metadata.get("county"),
        "admin_level": metadata.get("admin_level"),
        "timestamp": datetime.now().isoformat(),
        "status_code": None,
        "status_category": "UNKNOWN",
        "response_time": None,
        "error_message": None,
        "http_version": HTTP_VERSION,
        # Http details
        "normalized_url": None,
        "final_url": None,
        "redirect_count": 0,
        "redirect_chain": None,
        # Network trace
        "network_trace_attempted": False,
        "network_trace_tool": None,
        "network_trace_hop_count": None,
        "network_trace_timeout_hops": None,
        "network_trace_summary": None,
        "network_trace_excerpt": None,
        # DNS trace
        "dns_trace_attempted": False,
        "dns_trace_provider": None,
        "dns_lookup_ms": None,
        "dns_a_records": None,
        "dns_aaaa_records": None,
        "dns_cname_records": None,
        "dns_error": None,
    }


def apply_http_exception(result: dict[str, Any], error: Exception) -> None:
    """Mapping of aiohttp/asyncio exceptions to error categories."""
    if isinstance(error, asyncio.TimeoutError):
        result["status_category"] = "TIMEOUT"
        result["error_message"] = f"Timeout after {TIMEOUT}s"
        result["response_time"] = TIMEOUT
        return

    if isinstance(error, aiohttp.ClientConnectorError):
        os_error = getattr(error, "os_error", None)
        if isinstance(os_error, socket.gaierror):
            result["status_category"] = "DNS_ERROR"
            result["error_message"] = "DNS Error - domain not resolved"
        else:
            error_str = str(error).lower()
            if "name or service not known" in error_str or "getaddrinfo failed" in error_str:
                result["status_category"] = "DNS_ERROR"
                result["error_message"] = "DNS Error - domain not resolved"
            else:
                result["status_category"] = "CONNECTION_ERROR"
                result["error_message"] = str(error)[:120]
        return

    if isinstance(error, aiohttp.ClientError):
        result["status_category"] = "ERROR"
        result["error_message"] = str(error)[:120]
        return

    result["status_category"] = "ERROR"
    result["error_message"] = str(error)[:120]


async def fetch_with_retries(session: aiohttp.ClientSession, normalized_url: str) -> tuple[aiohttp.ClientResponse | None, float | None, Exception | None]:
    """Fetch URL asynchronously with retry control."""
    attempts = max(1, RETRY_ATTEMPTS + 1)
    last_error = None

    for attempt in range(attempts):
        try:
            start_time = time.perf_counter()
            async with session.get(
                normalized_url,
                headers=prepare_headers(),
                allow_redirects=True,
                ssl=False,
            ) as response:
                await response.read()
                response_time = time.perf_counter() - start_time
                return response, response_time, None
        except (asyncio.TimeoutError, aiohttp.ClientError, ValueError) as exc:
            last_error = exc
            if attempt < attempts - 1:
                continue

    return None, None, last_error
