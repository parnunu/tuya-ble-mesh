"""Shared replay-safe SIG Mesh sequence storage for Home Assistant."""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from custom_components.tuya_ble_mesh.const import (
    CONF_INITIAL_SEQUENCE,
    CONF_IV_INDEX,
    CONF_NET_KEY,
    CONF_UNICAST_OUR,
    DEFAULT_IV_INDEX,
    DOMAIN,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.storage import Store

SEQ_SAFETY_MARGIN = 100
_SEQ_STORE_VERSION = 1
_DATA_SEQUENCE_STORES = f"{DOMAIN}_sequence_stores"


class HASequenceStore:
    """Monotonic sequence store shared by entries on one Mesh network/source."""

    def __init__(
        self, hass: HomeAssistant, storage_key: str, initial_sequence: int = 0
    ) -> None:
        from homeassistant.helpers.storage import Store

        self._hass = hass
        self._store: Store[dict[str, int]] = Store(
            hass, _SEQ_STORE_VERSION, storage_key
        )
        self._seq = initial_sequence
        self._load_lock = asyncio.Lock()
        self._network_loaded = False
        self._loaded_legacy_entries: set[str] = set()

    def get_seq(self) -> int:
        """Return the next sequence number."""
        return self._seq

    def set_seq(self, seq: int) -> None:
        """Advance, but never decrease, the shared sequence number."""
        self._seq = max(self._seq, seq)

    async def async_load(self, legacy_entry_id: str | None = None) -> int:
        """Load the network store and merge an entry's legacy sequence store."""
        from homeassistant.helpers.storage import Store

        async with self._load_lock:
            if not self._network_loaded:
                data = await self._store.async_load()
                if data is not None and "seq" in data:
                    self.set_seq(data["seq"] + SEQ_SAFETY_MARGIN)
                self._network_loaded = True

            if (
                legacy_entry_id is not None
                and legacy_entry_id not in self._loaded_legacy_entries
            ):
                legacy_store: Store[dict[str, int]] = Store(
                    self._hass,
                    _SEQ_STORE_VERSION,
                    f"tuya_ble_mesh.seq.{legacy_entry_id}",
                )
                legacy = await legacy_store.async_load()
                if legacy is not None and "seq" in legacy:
                    self.set_seq(legacy["seq"] + SEQ_SAFETY_MARGIN)
                self._loaded_legacy_entries.add(legacy_entry_id)

            return self._seq

    async def async_save(self) -> None:
        """Persist the shared network sequence number."""
        await self._store.async_save({"seq": self._seq})


def get_ha_sequence_store(
    hass: HomeAssistant, data: Mapping[str, Any]
) -> HASequenceStore | None:
    """Return a shared store keyed by NetKey fingerprint, IV Index, and source."""
    net_key = data.get(CONF_NET_KEY)
    if not net_key:
        return None

    try:
        net_key_bytes = bytes.fromhex(str(net_key))
        iv_index = int(data.get(CONF_IV_INDEX, DEFAULT_IV_INDEX))
        our_address = int(str(data.get(CONF_UNICAST_OUR, "0001")), 16)
        initial_sequence = int(data.get(CONF_INITIAL_SEQUENCE, 0))
    except (TypeError, ValueError):
        return None

    fingerprint = hashlib.sha256(net_key_bytes).hexdigest()[:16]
    network_id = f"{fingerprint}.{iv_index:08x}.{our_address:04x}"
    stores: dict[str, HASequenceStore] = hass.data.setdefault(
        _DATA_SEQUENCE_STORES, {}
    )
    if network_id not in stores:
        stores[network_id] = HASequenceStore(
            hass,
            f"tuya_ble_mesh.seq.network.{network_id}",
            initial_sequence,
        )
    else:
        stores[network_id].set_seq(initial_sequence)
    return stores[network_id]
