"""Reproducible scale check using synthetic (not production player) events."""

from __future__ import annotations

import argparse
import json
import time
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

from .log_analyzer import LogRecord, extract_error_contexts


@dataclass(frozen=True)
class ScaleReport:
    synthetic_records: int
    injected_errors: int
    extracted_errors: int
    elapsed_seconds: float
    peak_memory_mb: float
    context_radius: int


def synthetic_records(total: int, error_every: int) -> Iterator[LogRecord]:
    if total <= 0 or error_every <= 0:
        raise ValueError("total and error_every must be positive")
    for index in range(total):
        is_error = (index + 1) % error_every == 0
        yield LogRecord(
            line_number=index + 1,
            timestamp=f"2026-10-30T10:{(index // 60) % 60:02d}:{index % 60:02d}Z",
            level="ERROR" if is_error else "INFO",
            event="simulated_timeout" if is_error else "heartbeat",
            payload={"sequence": index},
        )


def run_scale_check(total: int = 100_000, error_every: int = 10_000, radius: int = 2) -> ScaleReport:
    tracemalloc.start()
    started = time.perf_counter()
    contexts = extract_error_contexts(synthetic_records(total, error_every), radius)
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    injected = total // error_every
    return ScaleReport(total, injected, len(contexts), elapsed, peak / 1024 / 1024, radius)


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile synthetic log analysis")
    parser.add_argument("--records", type=int, default=100_000)
    parser.add_argument("--error-every", type=int, default=10_000)
    parser.add_argument("--radius", type=int, default=2)
    parser.add_argument("--output", type=Path, default=Path("reports/scale_report.json"))
    args = parser.parse_args()
    report = run_scale_check(args.records, args.error_every, args.radius)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    print(json.dumps(asdict(report), indent=2))


if __name__ == "__main__":
    main()

