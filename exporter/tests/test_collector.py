import pytest
from prometheus_client import CollectorRegistry, generate_latest

from gcups_exporter.client import GcupsApiError
from gcups_exporter.collector import GcupsCollector

# Real responses from a Green Cell PowerProof (UPS03) on gcups 1.1.10.
CONNECTED_PARAMETERS = {
    "inputVoltage": 232.8, "inputVoltageFault": 232.8, "outputVoltage": 232.8, "load": 9,
    "inputFrequency": 50, "batteryVoltage": 27.5, "temperature": -1, "utilityFail": False,
    "batteryLow": False, "bypassBoost": False, "failed": False, "offline": True,
    "testInProgress": False, "shutdownActive": False, "beeperOn": True, "batteryLevel": 100,
    "active": True, "connected": True, "status": 0, "register": [], "issues": [], "errno": 0,
    "inputVoltageNominal": 230, "inputFrequencyNominal": 50, "batteryVoltageNominal": 24,
    "inputCurrentNominal": 4, "batteryNumberNominal": 2,
    "batteryVoltageHighNominal": 25.2, "batteryVoltageLowNominal": 21.96, "reg": 9,
}
DATA = {
    "manufacturer": "Fry's Electronics", "vendor": "GreenCell S.A.",
    "protocol": "MEC", "protocol_version": "MEC0003", "info": "#  .\r",
}
SPECIFICATION = {
    "id": "0001:0000", "name": "PowerProof", "codes": ["UPS03"], "online": False,
    "power": 600, "capacity": 1000, "batteryNumber": 2, "batteryVoltage": 24, "current": 4,
}


class FakeClient:
    def __init__(self, responses=None, error=None):
        self.responses = responses or {}
        self.error = error

    def get(self, path):
        if self.error:
            raise self.error
        return self.responses[path]


def scrape(client):
    """Return {sample line without value: value} for the gcups_* samples."""
    registry = CollectorRegistry()
    registry.register(GcupsCollector(client))
    samples = {}
    for line in generate_latest(registry).decode().splitlines():
        if line.startswith("gcups_"):
            name, value = line.rsplit(" ", 1)
            samples[name] = float(value)
    return samples


def connected_client(**parameter_overrides):
    return FakeClient({
        "/current_parameters": {**CONNECTED_PARAMETERS, **parameter_overrides},
        "/data": DATA,
        "/device/specification": SPECIFICATION,
    })


def test_connected_ups_exports_readings():
    samples = scrape(connected_client())

    assert samples["gcups_up"] == 1
    assert samples["gcups_connected"] == 1
    assert samples["gcups_utility_fail"] == 0
    assert samples["gcups_input_voltage_volts"] == 232.8
    assert samples["gcups_battery_voltage_volts"] == 27.5
    assert samples["gcups_nominal_battery_count"] == 2
    assert samples["gcups_rated_power_va"] == 600


def test_percentages_are_exported_as_ratios():
    samples = scrape(connected_client())

    assert samples["gcups_load_ratio"] == pytest.approx(0.09)
    assert samples["gcups_battery_level_ratio"] == 1.0


def test_info_metric_has_identification_labels():
    samples = scrape(connected_client())

    info = next(name for name in samples if name.startswith("gcups_ups_info{"))
    for label in ('model="PowerProof"', 'codes="UPS03"', 'usb_id="0001:0000"',
                  'protocol_version="MEC0003"', 'vendor="GreenCell S.A."'):
        assert label in info


def test_missing_temperature_sensor_is_omitted():
    assert "gcups_temperature_celsius" not in scrape(connected_client(temperature=-1))
    assert scrape(connected_client(temperature=31))["gcups_temperature_celsius"] == 31


def test_disconnected_ups_exports_only_health_and_flags():
    samples = scrape(connected_client(connected=False))

    assert samples["gcups_up"] == 1
    assert samples["gcups_connected"] == 0
    assert "gcups_input_voltage_volts" not in samples
    assert not any(name.startswith("gcups_ups_info") for name in samples)


def test_api_error_reports_down_instead_of_failing():
    samples = scrape(FakeClient(error=GcupsApiError("connection refused")))

    assert samples["gcups_up"] == 0
    assert set(samples) == {"gcups_up", "gcups_scrape_duration_seconds"}


def test_non_object_response_reports_down():
    client = connected_client()
    client.responses["/data"] = ["not", "an", "object"]

    assert scrape(client)["gcups_up"] == 0


def test_no_ups_attached_reports_disconnected():
    # Without a UPS the app answers these endpoints with 200 and an empty body.
    client = FakeClient({
        "/current_parameters": None,
        "/data": {"manufacturer": None, "vendor": None, "protocol": None,
                  "protocol_version": None, "info": None},
        "/device/specification": None,
    })

    samples = scrape(client)

    assert samples["gcups_up"] == 1
    assert samples["gcups_connected"] == 0
    assert "gcups_input_voltage_volts" not in samples
