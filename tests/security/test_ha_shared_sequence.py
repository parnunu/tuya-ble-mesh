"""Tests for shared Home Assistant SIG Mesh sequence storage."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tuya_ble_mesh.sig_mesh_device import SIGMeshDevice

from custom_components.tuya_ble_mesh.ha_sequence import (
    SEQ_SAFETY_MARGIN,
    HASequenceStore,
    get_ha_sequence_store,
)

_TEST_NET_KEY = "00112233445566778899aabbccddeeff"  # pragma: allowlist secret


def _data(*, initial: int = 0, source: str = "0001") -> dict[str, object]:
    return {
        "net_key": _TEST_NET_KEY,
        "iv_index": 0,
        "unicast_our": source,
        "initial_sequence": initial,
    }


@pytest.mark.requires_ha
def test_same_network_and_source_share_monotonic_store() -> None:
    """Entries on one network/source must use the same counter object."""
    hass = MagicMock()
    hass.data = {}

    with patch("homeassistant.helpers.storage.Store", return_value=MagicMock()):
        first = get_ha_sequence_store(hass, _data(initial=20))
        second = get_ha_sequence_store(hass, _data(initial=40))

    assert first is not None
    assert second is first
    assert first.get_seq() == 40
    first.set_seq(10)
    assert first.get_seq() == 40


@pytest.mark.requires_ha
def test_different_source_uses_different_store() -> None:
    """Different controller source addresses have independent replay windows."""
    hass = MagicMock()
    hass.data = {}

    with patch("homeassistant.helpers.storage.Store", return_value=MagicMock()):
        first = get_ha_sequence_store(hass, _data(source="0001"))
        second = get_ha_sequence_store(hass, _data(source="0002"))

    assert first is not second


@pytest.mark.requires_ha
@pytest.mark.asyncio
async def test_load_merges_network_and_legacy_entry_with_margin() -> None:
    """Migration must advance beyond both network and legacy persisted values."""
    hass = MagicMock()
    network_store = MagicMock()
    network_store.async_load = AsyncMock(return_value={"seq": 100})
    network_store.async_save = AsyncMock()
    legacy_store = MagicMock()
    legacy_store.async_load = AsyncMock(return_value={"seq": 250})

    with patch(
        "homeassistant.helpers.storage.Store",
        side_effect=[network_store, legacy_store],
    ):
        store = HASequenceStore(hass, "tuya_ble_mesh.seq.network.test", 20)
        restored = await store.async_load("legacy_entry")
        await store.async_save()

    assert restored == 250 + SEQ_SAFETY_MARGIN
    network_store.async_save.assert_awaited_once_with({"seq": restored})


@pytest.mark.requires_ha
@pytest.mark.asyncio
async def test_two_devices_allocate_unique_shared_sequences() -> None:
    """Two proxy connections on one Mesh network must never reuse a sequence."""
    hass = MagicMock()
    hass.data = {}
    backing_store = MagicMock()

    with patch("homeassistant.helpers.storage.Store", return_value=backing_store):
        store = get_ha_sequence_store(hass, _data(initial=500))

    assert store is not None
    first = SIGMeshDevice("02:00:00:00:00:01", 0x00B0, 0x0001, MagicMock(), seq_store=store)
    second = SIGMeshDevice("02:00:00:00:00:02", 0x00C0, 0x0001, MagicMock(), seq_store=store)

    allocated = await asyncio.gather(first._next_seq(), second._next_seq())

    assert sorted(allocated) == [500, 501]
    assert store.get_seq() == 502
