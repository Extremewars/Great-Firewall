import asyncio
import platform
import re
import socket
import subprocess
import time
from typing import Any, Callable

from tqdm import tqdm

from config import (
    DNS_TRACE_TIMEOUT_SECONDS,
    ENABLE_FAILURE_DNS_TRACE,
    ENABLE_FAILURE_NETWORK_TRACE,
    FAILURE_TRACE_CONCURRENCY,
    MAX_FAILURE_TRACE_COUNT,
    TRACEROUTE_MAX_HOPS,
    TRACEROUTE_OUTPUT_LIMIT,
    TRACEROUTE_TIMEOUT_SECONDS,
)
from scanner.http import extract_domain

try:
    import dns.resolver

    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False


async def execute_traceroute_async(domain: str) -> dict[str, Any]:
    trace_data = {
        "network_trace_attempted": True,
        "network_trace_tool": None,
        "network_trace_hop_count": None,
        "network_trace_timeout_hops": None,
        "network_trace_summary": None,
        "network_trace_excerpt": None,
    }

    try:
        if platform.system() == "Windows":
            cmd = ["tracert", "-d", "-h", str(TRACEROUTE_MAX_HOPS), "-w", "1200", domain]
            trace_data["network_trace_tool"] = "tracert"
        else:
            cmd = ["traceroute", "-n", "-m", str(TRACEROUTE_MAX_HOPS), "-w", "2", domain]
            trace_data["network_trace_tool"] = "traceroute"

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=TRACEROUTE_TIMEOUT_SECONDS
            )
            raw_output = (stdout.decode(errors="ignore") or stderr.decode(errors="ignore") or "").strip()
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise asyncio.TimeoutError

        hop_lines = [
            line.strip()
            for line in raw_output.splitlines()
            if re.match(r"^\s*\d+\s+", line)
        ]

        timeout_hops = sum(1 for line in hop_lines if "*" in line)
        trace_data["network_trace_hop_count"] = len(hop_lines)
        trace_data["network_trace_timeout_hops"] = timeout_hops

        if len(hop_lines) == 0:
            summary = "No hop lines to analyze"
        elif timeout_hops > 5:
            summary = f"Significant delays: {timeout_hops} timeout hops"
        elif timeout_hops > 0:
            summary = f"Moderate delays: {timeout_hops} timeout hops"
        else:
            summary = "Trace without timeout hops"

        trace_data["network_trace_summary"] = summary
        trace_data["network_trace_excerpt"] = raw_output[:TRACEROUTE_OUTPUT_LIMIT]

    except FileNotFoundError:
        trace_data["network_trace_summary"] = "traceroute/tracert tool unavailable"
    except asyncio.TimeoutError:
        trace_data["network_trace_summary"] = f"Traceroute timeout after {TRACEROUTE_TIMEOUT_SECONDS}s"
    except Exception as error:
        trace_data["network_trace_summary"] = f"Traceroute error: {str(error)[:120]}"

    return trace_data


def resolve_dns_records(domain: str) -> dict[str, Any]:
    """Execute DNS diagnostics (A/AAAA/CNAME) for a domain."""
    start_time = time.time()
    dns_data = {
        "dns_trace_attempted": True,
        "dns_trace_provider": "dnspython" if HAS_DNSPYTHON else "socket",
        "dns_lookup_ms": None,
        "dns_a_records": None,
        "dns_aaaa_records": None,
        "dns_cname_records": None,
        "dns_error": None,
    }

    try:
        a_records = []
        aaaa_records = []
        cname_records = []

        if HAS_DNSPYTHON:
            resolver = dns.resolver.Resolver()
            resolver.lifetime = DNS_TRACE_TIMEOUT_SECONDS

            for rtype in ["A", "AAAA", "CNAME"]:
                try:
                    answers = resolver.resolve(domain, rtype)
                    records = sorted({str(answer).rstrip(".") for answer in answers})
                    if rtype == "A":
                        a_records = records
                    elif rtype == "AAAA":
                        aaaa_records = records
                    else:
                        cname_records = records
                except Exception:
                    pass
        else:
            addr_info = socket.getaddrinfo(domain, None)
            for info in addr_info:
                family = info[0]
                sockaddr = info[4]
                if family == socket.AF_INET:
                    a_records.append(sockaddr[0])
                elif family == socket.AF_INET6:
                    aaaa_records.append(sockaddr[0])

            a_records = sorted(set(a_records))
            aaaa_records = sorted(set(aaaa_records))

        dns_data["dns_a_records"] = ";".join(a_records) if a_records else None
        dns_data["dns_aaaa_records"] = ";".join(aaaa_records) if aaaa_records else None
        dns_data["dns_cname_records"] = ";".join(cname_records) if cname_records else None

        if not a_records and not aaaa_records and not cname_records:
            dns_data["dns_error"] = "No DNS records in response"

    except Exception as error:
        dns_data["dns_error"] = str(error)[:180]
    finally:
        dns_data["dns_lookup_ms"] = round((time.time() - start_time) * 1000, 2)

    return dns_data


async def diagnose_failed_connection_async(result: dict[str, Any], normalized_url: str) -> dict[str, Any]:
    """Add tracing for failed connections."""
    domain = extract_domain(normalized_url)

    if ENABLE_FAILURE_DNS_TRACE and domain:
        dns_result = await asyncio.to_thread(resolve_dns_records, domain)
        result.update(dns_result)

    if (
        ENABLE_FAILURE_NETWORK_TRACE
        and domain
        and result.get("status_category") in {"TIMEOUT", "CONNECTION_ERROR", "ERROR"}
    ):
        result.update(await execute_traceroute_async(domain))

    return result


async def run_batch_diagnostics_async(results: list[dict[str, Any]], normalize_url_func: Callable[[str], str]) -> None:
    """Asynchronously enrich trace for failed connections with a concurrency limit."""
    if not (ENABLE_FAILURE_DNS_TRACE or ENABLE_FAILURE_NETWORK_TRACE):
        return

    failed_indexes = [
        index
        for index, item in enumerate(results)
        if item.get("status_category") != "AVAILABLE"
    ]

    if not failed_indexes:
        return

    selected_indexes = failed_indexes
    if MAX_FAILURE_TRACE_COUNT and MAX_FAILURE_TRACE_COUNT > 0:
        selected_indexes = failed_indexes[:MAX_FAILURE_TRACE_COUNT]

    skipped = len(failed_indexes) - len(selected_indexes)
    if skipped > 0:
        print(
            f"\nTrace only for {len(selected_indexes)} out of {len(failed_indexes)} failed URLs "
            f"(skipped {skipped} for speed)."
        )

    semaphore = asyncio.Semaphore(max(1, FAILURE_TRACE_CONCURRENCY))
    per_item_timeout_seconds = max(
        10,
        TRACEROUTE_TIMEOUT_SECONDS + DNS_TRACE_TIMEOUT_SECONDS + 5,
    )

    network_trace_indexes = [
        index
        for index in selected_indexes
        if results[index].get("status_category") in {"TIMEOUT", "CONNECTION_ERROR", "ERROR"}
    ]
    network_trace_index_set = set(network_trace_indexes)

    progress_bar = None
    if ENABLE_FAILURE_NETWORK_TRACE and network_trace_indexes:
        estimated_upper_bound_seconds = int(
            (len(network_trace_indexes) * max(1, per_item_timeout_seconds))
            / max(1, FAILURE_TRACE_CONCURRENCY)
        )
        print(
            f"Traceroutes to perform: {len(network_trace_indexes)} hosts "
            f"(estimated upper bound timeout <= {estimated_upper_bound_seconds}s)."
        )
        progress_bar = tqdm(
            total=len(network_trace_indexes),
            desc="Traceroute",
            unit="host",
            dynamic_ncols=True,
            leave=True,
        )

    async def enrich_one(index):
        async with semaphore:
            item = results[index]
            normalized = item.get("normalized_url") or normalize_url_func(item.get("url"))
            try:
                await asyncio.wait_for(
                    diagnose_failed_connection_async(item, normalized),
                    timeout=per_item_timeout_seconds,
                )
            except asyncio.TimeoutError:
                item["network_trace_attempted"] = True
                item["network_trace_summary"] = (
                    f"Diagnostics timeout after {per_item_timeout_seconds}s"
                )

            if progress_bar is not None and index in network_trace_index_set:
                progress_bar.update(1)

    try:
        await asyncio.gather(*(enrich_one(index) for index in selected_indexes))
    finally:
        if progress_bar is not None:
            progress_bar.close()
