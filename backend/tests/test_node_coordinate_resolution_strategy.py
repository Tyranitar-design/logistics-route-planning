import os
import sys
from types import SimpleNamespace

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.services.node_coordinate_service import (
    build_resolution_candidates,
    resolve_node_coordinates,
)


def test_resolution_candidates_strip_noise_and_include_macau_alias():
    node = SimpleNamespace(
        id=7,
        name="澳门特别行政区物流节点",
        province=None,
        city="澳门特别行政区",
        district=None,
        address="澳门特别行政区（由真实运单网络自动生成）",
    )

    candidates = build_resolution_candidates(node)

    assert "澳门特别行政区" in candidates
    assert "澳门" in candidates
    assert all("自动生成" not in candidate for candidate in candidates)
    assert all("物流节点" not in candidate for candidate in candidates)


def test_resolution_candidates_add_structured_alias_for_county_like_city():
    node = SimpleNamespace(
        id=5,
        name="成县物流节点",
        province=None,
        city="成县",
        district=None,
        address="成县（由真实运单网络自动生成）",
    )

    candidates = build_resolution_candidates(node)

    assert "成县" in candidates
    assert "陇南成县" in candidates
    assert "甘肃省陇南市成县" in candidates


def test_resolve_node_coordinates_tries_multiple_queries_until_success():
    node = SimpleNamespace(
        id=7,
        name="澳门特别行政区物流节点",
        province=None,
        city="澳门特别行政区",
        district=None,
        address="澳门特别行政区（由真实运单网络自动生成）",
    )

    class FakeResult:
        def __init__(self, success, longitude=None, latitude=None, query=None):
            self.success = success
            self.longitude = longitude
            self.latitude = latitude
            self.formatted_address = query
            self.province = "澳门特别行政区"
            self.city = "澳门特别行政区"
            self.district = "澳门半岛"
            self.provider = "amap"
            self.provider_status = "ok" if success else "degraded"
            self.degraded = not success
            self.fallback_reason = None if success else "ENGINE_RESPONSE_DATA_ERROR"
            self.authenticity = {"message": "地理编码来自高德官方地理编码服务。"}
            self.error = None if success else "ENGINE_RESPONSE_DATA_ERROR"

    class FakeAmapService:
        def __init__(self):
            self.calls = []

        def geocode(self, address, city=None):
            self.calls.append((address, city))
            if address == "澳门特别行政区":
                return FakeResult(False)
            if address == "澳门":
                return FakeResult(True, longitude=113.5439, latitude=22.1987, query=address)
            return FakeResult(False)

    service = FakeAmapService()
    result = resolve_node_coordinates(node, service)

    assert result["success"] is True
    assert result["longitude"] == 113.5439
    assert result["latitude"] == 22.1987
    assert result["resolution_query_used"] == "澳门"
    assert len(result["resolution_attempts"]) >= 2
