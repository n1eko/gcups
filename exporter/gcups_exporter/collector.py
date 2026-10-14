"""Prometheus collector that reads the UPS state on every scrape."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Iterator, Protocol

from prometheus_client.core import GaugeMetricFamily, InfoMetricFamily, Metric
from prometheus_client.registry import Collector

from .client import GcupsApiError
from .metrics import MEASUREMENTS, STATUS_FLAGS, metric_name

log = logging.getLogger(__name__)


class ApiClient(Protocol):
    def get(self, path: str) -> Any: ...


@dataclass(frozen=True)
class UpsSnapshot:
    """The API responses one scrape is built from."""
    parameters: dict
    data: dict
    specification: dict

    @classmethod
    def fetch(cls, client: ApiClient) -> UpsSnapshot:
        # Empty responses (None) mean no UPS is attached; treat them as {}.
        return cls(
            parameters=_as_dict(client.get("/current_parameters")),
            data=_as_dict(client.get("/data")),
            specification=_as_dict(client.get("/device/specification")),
        )

    @property
    def connected(self) -> bool:
        return self.parameters.get("connected") is True


class GcupsCollector(Collector):
    def __init__(self, client: ApiClient) -> None:
        self._client = client

    def collect(self) -> Iterator[Metric]:
        started = time.monotonic()
        try:
            snapshot = UpsSnapshot.fetch(self._client)
        except GcupsApiError as e:
            log.warning("scrape failed: %s", e)
            snapshot = None

        yield from _health_metrics(up=snapshot is not None, duration=time.monotonic() - started)
        if snapshot is None:
            return

        yield from _status_metrics(snapshot)
        # Without a UPS the app reports zeros, which would look like real readings.
        if snapshot.connected:
            yield from _measurement_metrics(snapshot)
            yield _info_metric(snapshot)


def _health_metrics(up: bool, duration: float) -> Iterator[Metric]:
    yield _gauge("up", "1 if the GC UPS app API could be read.", int(up))
    yield _gauge("scrape_duration_seconds", "Time spent reading the GC UPS app API.", duration)


def _status_metrics(snapshot: UpsSnapshot) -> Iterator[Metric]:
    yield _gauge("connected", "1 if the app is connected to the UPS.", int(snapshot.connected))
    for flag in STATUS_FLAGS:
        value = snapshot.parameters.get(flag.field)
        if isinstance(value, bool):
            yield _gauge(flag.name, flag.help, int(value))


def _measurement_metrics(snapshot: UpsSnapshot) -> Iterator[Metric]:
    for measurement in MEASUREMENTS:
        value = snapshot.parameters.get(measurement.field)
        if _is_number(value):
            yield _gauge(measurement.name, measurement.help, value * measurement.scale)

    # -1 means the model has no temperature sensor.
    temperature = snapshot.parameters.get("temperature")
    if _is_number(temperature) and temperature >= 0:
        yield _gauge("temperature_celsius", "UPS temperature.", temperature)

    power = snapshot.specification.get("power")
    if _is_number(power):
        yield _gauge("rated_power_va", "Rated power from the device specification.", power)


def _info_metric(snapshot: UpsSnapshot) -> Metric:
    data, spec = snapshot.data, snapshot.specification
    labels = {
        "manufacturer": data.get("manufacturer", ""),
        "vendor": data.get("vendor", ""),
        "protocol": data.get("protocol", ""),
        "protocol_version": data.get("protocol_version", ""),
        "model": spec.get("name", ""),
        "usb_id": spec.get("id", ""),
        "codes": ",".join(spec.get("codes") or []),
    }
    info = InfoMetricFamily(metric_name("ups"), "UPS identification.")
    info.add_metric([], {key: str(value) for key, value in labels.items()})
    return info


def _gauge(name: str, help_text: str, value: float) -> GaugeMetricFamily:
    return GaugeMetricFamily(metric_name(name), help_text, value=value)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _as_dict(value: Any) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise GcupsApiError(f"expected a JSON object, got {type(value).__name__}")
    return value
