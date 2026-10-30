import pytest

from valorant_qa.scale_analysis import run_scale_check, synthetic_records


def test_one_hundred_thousand_synthetic_records():
    report = run_scale_check(total=100_000, error_every=10_000, radius=2)
    assert report.synthetic_records == 100_000
    assert report.injected_errors == 10
    assert report.extracted_errors == 10
    assert report.peak_memory_mb > 0


@pytest.mark.parametrize("total,error_every", [(0, 1), (1, 0), (-1, 1)])
def test_invalid_scale_parameters(total, error_every):
    with pytest.raises(ValueError):
        list(synthetic_records(total, error_every))

