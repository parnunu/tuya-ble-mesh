"""Regression tests for Home Assistant device factory wiring."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from custom_components.tuya_ble_mesh.const import (
    CONF_ADAPTER,
    CONF_APP_KEY,
    CONF_DEV_KEY,
    CONF_DEVICE_TYPE,
    CONF_IV_INDEX,
    CONF_NET_KEY,
    CONF_UNICAST_OUR,
    CONF_UNICAST_TARGET,
    DEVICE_TYPE_SIG_LIGHT,
)
from custom_components.tuya_ble_mesh.device_factory import create_device


def test_sig_light_legacy_adapter_uses_ha_bluetooth_callbacks() -> None:
    """Legacy adapter data must not bypass Home Assistant Bluetooth routing."""
    data = {
        CONF_DEVICE_TYPE: DEVICE_TYPE_SIG_LIGHT,
        CONF_ADAPTER: "hci0",
        CONF_NET_KEY: "00112233445566778899aabbccddeeff",  # pragma: allowlist secret
        CONF_DEV_KEY: "ffeeddccbbaa99887766554433221100",  # pragma: allowlist secret
        CONF_APP_KEY: "aabbccddeeff00112233445566778899",  # pragma: allowlist secret
        CONF_UNICAST_TARGET: "00B0",
        CONF_UNICAST_OUR: "0001",
        CONF_IV_INDEX: 0,
    }
    ha_device_callback = MagicMock()
    ha_connect_callback = MagicMock()

    with patch("tuya_ble_mesh.sig_mesh_device.SIGMeshDevice") as device_cls:
        create_device(
            DEVICE_TYPE_SIG_LIGHT,
            "02:00:00:00:00:01",
            data,
            ha_device_callback,
            ha_connect_callback,
        )

    kwargs = device_cls.call_args.kwargs
    assert "adapter" not in kwargs
    assert kwargs["ble_device_callback"] is ha_device_callback
    assert kwargs["ble_connect_callback"] is ha_connect_callback


def test_sig_light_legacy_adapter_constructs_ha_managed_device() -> None:
    """Legacy adapter data must not select the direct BlueZ backend."""
    data = {
        CONF_DEVICE_TYPE: DEVICE_TYPE_SIG_LIGHT,
        CONF_ADAPTER: "hci0",
        CONF_NET_KEY: "00112233445566778899aabbccddeeff",  # pragma: allowlist secret
        CONF_DEV_KEY: "ffeeddccbbaa99887766554433221100",  # pragma: allowlist secret
        CONF_APP_KEY: "aabbccddeeff00112233445566778899",  # pragma: allowlist secret
        CONF_UNICAST_TARGET: "00B0",
        CONF_UNICAST_OUR: "0001",
        CONF_IV_INDEX: 0,
        "initial_sequence": 41,
    }

    device = create_device(
        DEVICE_TYPE_SIG_LIGHT,
        "02:00:00:00:00:01",
        data,
        MagicMock(),
        MagicMock(),
    )

    assert device.address == "02:00:00:00:00:01"
    assert device.get_seq() == 41
    assert device._adapter is None
