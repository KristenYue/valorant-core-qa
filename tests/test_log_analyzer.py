from io import StringIO

import pytest

from valorant_qa.log_analyzer import extract_error_contexts, parse_jsonl, write_csv


LOGS = """\
{"timestamp":"2026-10-30T10:00:00Z","level":"INFO","event":"queue_joined","player":"p1"}
{"timestamp":"2026-10-30T10:00:01Z","level":"INFO","event":"match_found","match":"m1"}
{"timestamp":"2026-10-30T10:00:03Z","level":"ERROR","event":"load_timeout","match":"m1"}
{"timestamp":"2026-10-30T10:00:04Z","level":"INFO","event":"retry_started","attempt":2}
{"timestamp":"2026-10-30T10:00:05Z","level":"INFO","event":"load_recovered","match":"m1"}
"""


def test_extract_error_with_neighbor_context():
    contexts = extract_error_contexts(parse_jsonl(StringIO(LOGS)), radius=2)
    assert len(contexts) == 1
    assert contexts[0].error.event == "load_timeout"
    assert [record.event for record in contexts[0].before] == ["queue_joined", "match_found"]
    assert [record.event for record in contexts[0].after] == ["retry_started", "load_recovered"]


def test_write_csv(tmp_path):
    contexts = extract_error_contexts(parse_jsonl(StringIO(LOGS)), radius=1)
    output = tmp_path / "errors.csv"
    write_csv(contexts, output)
    content = output.read_text(encoding="utf-8-sig")
    assert "load_timeout" in content
    assert "retry_started" in content


@pytest.mark.parametrize(
    "bad_line",
    [
        "not-json",
        '{"timestamp":"2026-10-30T10:00:00Z","level":"INFO"}',
        '{"timestamp":"yesterday","level":"INFO","event":"bad"}',
    ],
)
def test_invalid_logs_fail_with_clear_error(bad_line):
    with pytest.raises(ValueError):
        list(parse_jsonl(StringIO(bad_line)))

