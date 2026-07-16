"""Home Assistant Bluetooth routing helpers.

These helpers keep address discovery and connections inside Home Assistant's
Bluetooth manager so AUTO-mode ESPHome proxies can be activated on demand.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from bleak import BleakClient
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def create_ha_ble_callbacks(
    hass: HomeAssistant, connection_name: str
) -> tuple[Callable[[str], Any], Callable[[Any], Awaitable[BleakClient]]]:
    """Create HA-routed BLE lookup and connection callbacks."""
    from bleak_retry_connector import (
        BleakClientWithServiceCache,
        close_stale_connections_by_address,
        establish_connection,
    )
    from homeassistant.components.bluetooth import async_ble_device_from_address

    def _ble_device_from_ha(address: str) -> Any:
        device = async_ble_device_from_address(hass, address.upper(), connectable=True)
        if device is None:
            _LOGGER.debug("BLE device %s is not yet in HA's connectable cache", address)
        return device

    async def _ble_connect_via_ha(ble_device: Any) -> BleakClient:
        await close_stale_connections_by_address(ble_device.address)
        return await establish_connection(
            BleakClientWithServiceCache,
            ble_device,
            f"{connection_name} {ble_device.address}",
            max_attempts=5,
            use_services_cache=True,
        )

    return _ble_device_from_ha, _ble_connect_via_ha


def register_ha_active_scan(
    hass: HomeAssistant,
    address: str,
    callback: Callable[[Any, Any], None],
) -> Callable[[], None]:
    """Register a target-specific active-scan request with HA Bluetooth."""
    from homeassistant.components.bluetooth import (
        BluetoothCallbackMatcher,
        BluetoothScanningMode,
        async_register_callback,
    )

    return async_register_callback(
        hass,
        callback,
        BluetoothCallbackMatcher(address=address.upper()),
        BluetoothScanningMode.ACTIVE,
    )
