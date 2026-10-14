"""Mapping from GC UPS API fields to Prometheus metrics.

To export a new value, add a line to MEASUREMENTS or STATUS_FLAGS.
"""
from __future__ import annotations

from typing import NamedTuple

PREFIX = "gcups"
PERCENT = 0.01  # API percentages -> Prometheus 0-1 ratios


class Measurement(NamedTuple):
    """A numeric field of /api/current_parameters."""
    field: str
    name: str
    help: str
    scale: float = 1.0


class StatusFlag(NamedTuple):
    """A boolean field of /api/current_parameters, exported as 0/1."""
    field: str
    name: str
    help: str


MEASUREMENTS = [
    Measurement("inputVoltage", "input_voltage_volts", "Input voltage."),
    Measurement("inputVoltageFault", "input_fault_voltage_volts", "Input fault voltage."),
    Measurement("outputVoltage", "output_voltage_volts", "Output voltage."),
    Measurement("inputFrequency", "input_frequency_hertz", "Input frequency."),
    Measurement("load", "load_ratio", "Output load (0-1).", PERCENT),
    Measurement("batteryVoltage", "battery_voltage_volts", "Battery voltage."),
    Measurement("batteryLevel", "battery_level_ratio", "Battery charge level (0-1).", PERCENT),
    Measurement("inputVoltageNominal", "nominal_input_voltage_volts", "Nominal input voltage."),
    Measurement("inputFrequencyNominal", "nominal_input_frequency_hertz", "Nominal input frequency."),
    Measurement("inputCurrentNominal", "nominal_input_current_amperes", "Nominal input current."),
    Measurement("batteryVoltageNominal", "nominal_battery_voltage_volts", "Nominal battery voltage."),
    Measurement("batteryVoltageHighNominal", "nominal_battery_voltage_high_volts", "Nominal battery high voltage."),
    Measurement("batteryVoltageLowNominal", "nominal_battery_voltage_low_volts", "Nominal battery low voltage."),
    Measurement("batteryNumberNominal", "nominal_battery_count", "Number of batteries."),
]

STATUS_FLAGS = [
    StatusFlag("utilityFail", "utility_fail", "1 if utility power has failed (running on battery)."),
    StatusFlag("batteryLow", "battery_low", "1 if the battery is low."),
    StatusFlag("bypassBoost", "bypass_boost", "1 if the UPS is in bypass/boost (AVR) mode."),
    StatusFlag("failed", "failed", "1 if the UPS reports a fault."),
    StatusFlag("offline", "offline", "Offline flag as reported by the UPS status register."),
    StatusFlag("testInProgress", "test_in_progress", "1 if a battery test is running."),
    StatusFlag("shutdownActive", "shutdown_active", "1 if a shutdown is pending."),
    StatusFlag("beeperOn", "beeper_on", "1 if the beeper is enabled."),
]


def metric_name(name: str) -> str:
    return f"{PREFIX}_{name}"
