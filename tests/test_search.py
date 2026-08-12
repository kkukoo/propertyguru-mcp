"""Basic smoke tests for the URL builder and search-payload parsing."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from propertyguru_mcp import build_search_url, search_propertyguru


class TestBuildSearchUrl:
    def test_minimal_sg_sale(self):
        u = build_search_url("sg", "sale", None, None, None, None, None, None)
        assert "propertyguru.com.sg" in u
        assert "/property-for-sale?" in u
        assert "isCommercial=false" in u
        assert "listingType=sale" in u

    def test_my_rent_with_freetext_and_price(self):
        u = build_search_url(
            "my", "rent", "Mont Kiara", None, [2], 2000, 4000, "price_asc"
        )
        assert "propertyguru.com.my" in u
        assert "/property-for-rent?" in u
        assert "freetext=Mont%20Kiara" in u or "freetext=Mont+Kiara" in u
        assert "minPrice=2000" in u
        assert "maxPrice=4000" in u
        assert "bedrooms%5B%5D=2" in u
        assert "sort=price_asc" in u

    def test_invalid_region_raises(self):
        with pytest.raises(ValueError, match="unsupported region"):
            build_search_url("hk", "sale", None, None, None, None, None, None)

    def test_invalid_listing_type_raises(self):
        with pytest.raises(ValueError, match="unsupported listing_type"):
            build_search_url("sg", "buy", None, None, None, None, None, None)

    def test_bedrooms_list_serializes_each_value(self):
        u = build_search_url("sg", "sale", None, None, [2, 3], None, None, None)
        assert u.count("bedrooms%5B%5D=") == 2


# Minimal synthetic listingData fixture (only the keys `search_propertyguru` reads).
_FAKE_NEXT_DATA = {
    "props": {
        "pageProps": {
            "pageData": {
                "data": {
                    "listingsData": [
                        {"listingData": {"id": 1, "price": {"value": 1000}}},
                        {"listingData": {"id": 2, "price": {"value": 2000}}},
                        {"listingData": {"id": 3, "price": {"value": 3000}}},
                    ]
                }
            }
        }
    }
}


class TestSearchPropertyguru:
    def test_parses_listings_data_from_next_data(self):
        with patch("propertyguru_mcp.server.fetch_next_data") as mock_fetch:
            mock_fetch.return_value = _FAKE_NEXT_DATA
            result = search_propertyguru(
                region="sg", listing_type="sale", freetext="Orchard",
                property_type=None, bedrooms_min=3, bedrooms_max=3,
                price_min=3_000_000, price_max=5_000_000,
                sort="price_asc", limit=25,
            )
        assert result["count"] == 3
        assert result["region"] == "sg"
        assert result["listing_type"] == "sale"
        assert "propertyguru.com.sg" in result["url"]
        assert result["listings"][0]["id"] == 1

    def test_limit_truncates_listings(self):
        with patch("propertyguru_mcp.server.fetch_next_data") as mock_fetch:
            mock_fetch.return_value = _FAKE_NEXT_DATA
            result = search_propertyguru(
                region="sg", listing_type="sale", freetext=None,
                property_type=None, bedrooms_min=None, bedrooms_max=None,
                price_min=None, price_max=None, sort=None, limit=2,
            )
        assert result["count"] == 2

    def test_bedrooms_equal_min_max_becomes_single_exact(self):
        with patch("propertyguru_mcp.server.fetch_next_data") as mock_fetch:
            mock_fetch.return_value = _FAKE_NEXT_DATA
            search_propertyguru(
                region="sg", listing_type="sale", freetext=None,
                property_type=None, bedrooms_min=3, bedrooms_max=3,
                price_min=None, price_max=None, sort=None, limit=25,
            )
        called_url = mock_fetch.call_args[0][0]
        assert called_url.count("bedrooms%5B%5D=") == 1
        assert "bedrooms%5B%5D=3" in called_url


def test_full_smoke_with_fixture(tmp_path):
    """End-to-end: write fake HTML with __NEXT_DATA__, run fetch via mocked urlopen."""
    fake_html = (
        '<html><body><script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(_FAKE_NEXT_DATA)
        + "</script></body></html>"
    )

    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return fake_html.encode()

    with patch("urllib.request.urlopen", return_value=FakeResp()):
        from propertyguru_mcp import fetch_next_data
        result = fetch_next_data("https://example.invalid/x")
    assert result == _FAKE_NEXT_DATA
