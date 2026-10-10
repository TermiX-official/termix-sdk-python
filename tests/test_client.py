from termix_platform_sdk import TermixClient


def test_compat_match_no_warning():
    warned = []
    c = TermixClient(chain="bsc", on_warning=lambda m: warned.append(m))
    c._check_compat({"chainId": 56})
    assert warned == []


def test_compat_mismatch_warns():
    warned = []
    c = TermixClient(chain="bsc", on_warning=lambda m: warned.append(m))
    c._check_compat({"chainId": 97})  # bsc expects 56
    assert len(warned) == 1


def test_compat_skipped_for_base_url_override():
    warned = []
    c = TermixClient(base_url="https://x.example/api/v1", on_warning=lambda m: warned.append(m))
    c._check_compat({"chainId": 97})
    assert warned == []
