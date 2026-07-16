"""Minimal stub for homeassistant.components.bluetooth."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from unittest.mock import MagicMock


class BluetoothScanningMode(Enum):
    """Scanning mode supported by HA's Bluetooth manager."""

    PASSIVE = "passive"
    ACTIVE = "active"
    AUTO = "auto"


class BluetoothCallbackMatcher(dict[str, Any]):
    """Minimal dict-like matcher used by Bluetooth callbacks."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)


def async_register_callback(
    hass: Any,
    callback: Any,
    match_dict: BluetoothCallbackMatcher,
    mode: BluetoothScanningMode,
    *,
    scan_interval: float | None = None,
    scan_duration: float | None = None,
) -> Any:
    """Return a cancellation callback for a registered Bluetooth matcher."""
    return MagicMock()


@dataclass
class BluetoothServiceInfoBleak:
    name: str = ""
    address: str = ""
    rssi: int = -65
    manufacturer_data: dict[int, bytes] = field(default_factory=dict)
    service_uuids: list[str] = field(default_factory=list)
    service_data: dict[str, bytes] = field(default_factory=dict)
    source: str = "local"
    advertisement: Any = None
    device: Any = None
    connectable: bool = True
    time: float = 0.0


def async_ble_device_from_address(hass: Any, address: str, connectable: bool = True) -> Any:
    return MagicMock()
