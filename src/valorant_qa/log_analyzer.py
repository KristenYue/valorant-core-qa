"""Streaming JSONL error-context extractor with CSV output."""

from __future__ import annotations

import argparse
import csv
import json
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, TextIO


@dataclass(frozen=True)
class LogRecord:
    line_number: int
    timestamp: str
    level: str
    event: str
    payload: dict


@dataclass(frozen=True)
class ErrorContext:
    error: LogRecord
    before: tuple[LogRecord, ...]
    after: tuple[LogRecord, ...]


def parse_jsonl(stream: TextIO) -> Iterator[LogRecord]:
    for line_number, raw in enumerate(stream, start=1):
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on line {line_number}") from exc
        for required in ("timestamp", "level", "event"):
            if required not in data:
                raise ValueError(f"missing {required} on line {line_number}")
        try:
            datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid timestamp on line {line_number}") from exc
        yield LogRecord(
            line_number=line_number,
            timestamp=data["timestamp"],
            level=str(data["level"]).upper(),
            event=str(data["event"]),
            payload={k: v for k, v in data.items() if k not in {"timestamp", "level", "event"}},
        )


def extract_error_contexts(records: Iterable[LogRecord], radius: int = 2) -> list[ErrorContext]:
    """Extract ERROR records and bounded neighbor context in one pass."""
    if radius < 0:
        raise ValueError("radius must be non-negative")
    previous: deque[LogRecord] = deque(maxlen=radius)
    pending: list[tuple[LogRecord, tuple[LogRecord, ...], list[LogRecord]]] = []
    completed: list[ErrorContext] = []

    for record in records:
        still_pending = []
        for error, before, after in pending:
            if len(after) < radius:
                after.append(record)
            if len(after) == radius:
                completed.append(ErrorContext(error, before, tuple(after)))
            else:
                still_pending.append((error, before, after))
        pending = still_pending

        if record.level == "ERROR":
            if radius == 0:
                completed.append(ErrorContext(record, (), ()))
            else:
                pending.append((record, tuple(previous), []))
        previous.append(record)

    completed.extend(ErrorContext(error, before, tuple(after)) for error, before, after in pending)
    return sorted(completed, key=lambda item: item.error.timestamp)


def write_csv(contexts: Iterable[ErrorContext], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["timestamp", "event", "line_number", "before", "after", "payload"],
        )
        writer.writeheader()
        for context in contexts:
            writer.writerow(
                {
                    "timestamp": context.error.timestamp,
                    "event": context.error.event,
                    "line_number": context.error.line_number,
                    "before": " | ".join(item.event for item in context.before),
                    "after": " | ".join(item.event for item in context.after),
                    "payload": json.dumps(context.error.payload, ensure_ascii=False),
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract ERROR context from JSONL logs")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--radius", type=int, default=2)
    args = parser.parse_args()
    with args.input.open(encoding="utf-8") as stream:
        contexts = extract_error_contexts(parse_jsonl(stream), args.radius)
    write_csv(contexts, args.output)
    print(f"wrote {len(contexts)} error contexts to {args.output}")


if __name__ == "__main__":
    main()

