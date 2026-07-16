"""Tests for Home Assistant Bluetooth proxy routing helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.bluetooth import BluetoothScanningMode

from custom_components.tuya_ble_mesh.ha_bluetooth import (
    create_ha_ble_callbacks,
    register_ha_active_scan,
)


@pytest.mark.requires_ha
def test_register_active_scan_targets_address_with_active_mode() -> None:
    """Address callbacks must request ACTIVE mode from HA's scheduler."""
    hass = MagicMock()
    callback = MagicMock()
    cancel = MagicMock()

    with patch(
        "homeassistant.components.bluetooth.async_register_callback",
        return_value=cancel,
    ) as register:
        result = register_ha_active_scan(hass, "02:00:00:00:00:42", callback)

    assert result is cancel
    assert register.call_args.args[0] is hass
    assert register.call_args.args[1] is callback
    assert register.call_args.args[2]["address"] == "02:00:00:00:00:42"
    assert register.call_args.args[3] is BluetoothScanningMode.ACTIVE


@pytest.mark.requires_ha
@pytest.mark.asyncio
async def test_callbacks_resolve_and_connect_through_ha() -> None:
    """The helper should resolve via HA and connect via retry-connector."""
    hass = MagicMock()
    ble_device = MagicMock(address="02:00:00:00:00:42")
    client = MagicMock()

    with (
        patch(
            "homeassistant.components.bluetooth.async_ble_device_from_address",
            return_value=ble_device,
        ) as resolve,
        patch(
            "bleak_retry_connector.close_stale_connections_by_address",
            new=AsyncMock(),
        ) as close_stale,
        patch(
            "bleak_retry_connector.establish_connection",
            new=AsyncMock(return_value=client),
        ) as establish,
    ):
        resolve_callback, connect_callback = create_ha_ble_callbacks(
            hass, "Synthetic SIG Light"
        )
        assert resolve_callback("02:00:00:00:00:42") is ble_device
        result = await connect_callback(ble_device)

    assert result is client
    resolve.assert_called_once_with(
        hass, "02:00:00:00:00:42", connectable=True
    )
    close_stale.assert_awaited_once_with("02:00:00:00:00:42")
    assert establish.await_args.args[1] is ble_device
    assert establish.await_args.kwargs["max_attempts"] == 5
    assert establish.await_args.kwargs["use_services_cache"] is True
