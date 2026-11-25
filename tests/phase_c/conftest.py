"""Phase C fixtures — dummy ticket/KB data only. No live API keys or ES."""

from __future__ import annotations

import pytest

DUMMY_TICKET = {
    "number": "INC9999999",
    "short_description": "VPN disconnects on wifi",
    "description": "Dummy laptop loses VPN when roaming",
    "category": "Network",
    "subcategory": "VPN",
    "cmdb_ci": "DUMMY-LAPTOP-1",
}

DUMMY_INDEXED_HIT = {
    "type": "article",
    "sys_id": "dummy-sys-001",
    "article_number": "KB0999999",
    "title": "Dummy VPN Troubleshooting",
    "chunk": "Restart the dummy VPN client and reconnect.",
    "chunk_semantic": "Restart the dummy VPN client and reconnect.",
    "chunk_no": "1_Dummy_VPN_Troubleshooting_1_0",
    "tags": ["vpn", "wifi", "disconnects"],
}


@pytest.fixture
def dummy_ticket():
    return dict(DUMMY_TICKET)


@pytest.fixture
def dummy_indexed_hit():
    return dict(DUMMY_INDEXED_HIT)


@pytest.fixture
def dummy_indexed_hits(dummy_indexed_hit):
    second = dict(dummy_indexed_hit)
    second["sys_id"] = "dummy-sys-002"
    second["title"] = "Dummy WiFi Guide"
    second["chunk"] = "Check dummy SSID and password."
    second["chunk_semantic"] = second["chunk"]
    second["tags"] = ["wifi"]
    second["chunk_no"] = "1_Dummy_WiFi_Guide_1_0"
    return [dummy_indexed_hit, second]
