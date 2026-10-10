import pytest

from termix_platform_sdk import from_base_units, to_base_units


def test_round_trip():
    for v in ["0", "1", "1.5", "24.28", "1000000", "0.000001"]:
        assert from_base_units(to_base_units(v, 18), 18) == v.rstrip("0").rstrip(".") if "." in v else v


def test_exact_base_units():
    assert to_base_units("24.28", 18) == 24_280000000000000000
    assert to_base_units("0.1", 6) == 100000


def test_over_precision_rejected():
    with pytest.raises(ValueError):
        to_base_units("1.1234567", 6)


def test_negative():
    assert from_base_units(to_base_units("-1.5", 18), 18) == "-1.5"
