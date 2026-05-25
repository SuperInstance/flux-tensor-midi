"""
flux_check.presets — Industry constraint bounds for 10 domains.

Each preset is a list of dicts: {name, lo, hi, severity}
Severity: 1=caution, 2=warning, 3=critical.
"""

from __future__ import annotations
from typing import Dict, List

PresetDef = List[Dict]


PRESETS: Dict[str, PresetDef] = {
    "automotive_can": [
        {"name": "engine_rpm",             "lo": 0,    "hi": 8000,  "severity": 3},
        {"name": "vehicle_speed_kmh",      "lo": 0,    "hi": 300,   "severity": 2},
        {"name": "coolant_temp_c",         "lo": -40,  "hi": 150,   "severity": 3},
        {"name": "throttle_pct",           "lo": 0,    "hi": 100,   "severity": 1},
        {"name": "brake_pressure_bar",     "lo": 0,    "hi": 200,   "severity": 3},
        {"name": "steering_angle_deg",     "lo": -720, "hi": 720,   "severity": 2},
        {"name": "battery_voltage_v",      "lo": 9,    "hi": 16,    "severity": 2},
        {"name": "fuel_level_pct",         "lo": 0,    "hi": 100,   "severity": 1},
    ],

    "aviation_adsb": [
        {"name": "altitude_ft",        "lo": -1000, "hi": 45000, "severity": 3},
        {"name": "ground_speed_kt",    "lo": 0,     "hi": 600,   "severity": 2},
        {"name": "heading_deg",        "lo": -180,  "hi": 180,   "severity": 1},
        {"name": "cabin_temp_c",       "lo": -55,   "hi": 70,    "severity": 2},
        {"name": "cabin_pressure_kpa", "lo": 75,    "hi": 101,   "severity": 3},
        {"name": "fuel_flow_pct",      "lo": 0,     "hi": 100,   "severity": 2},
        {"name": "hydraulic_pct",      "lo": 60,    "hi": 100,   "severity": 3},
        {"name": "pitch_deg",          "lo": -90,   "hi": 90,    "severity": 2},
    ],

    "medical_fhir": [
        {"name": "body_temp_c",          "lo": 36.1, "hi": 37.8,  "severity": 2},
        {"name": "heart_rate_bpm",       "lo": 60,   "hi": 100,   "severity": 3},
        {"name": "spo2_pct",             "lo": 95,   "hi": 100,   "severity": 3},
        {"name": "bp_systolic_mmhg",     "lo": 80,   "hi": 120,   "severity": 2},
        {"name": "bp_diastolic_mmhg",    "lo": 60,   "hi": 100,   "severity": 2},
        {"name": "respiratory_rate",     "lo": 12,   "hi": 20,    "severity": 2},
        {"name": "ph",                   "lo": 7.35, "hi": 7.45,  "severity": 3},
        {"name": "glucose_mg_dl",        "lo": 0,    "hi": 300,   "severity": 1},
    ],

    "financial_fix": [
        {"name": "price",            "lo": 0.0001, "hi": 100000, "severity": 3},
        {"name": "volume",           "lo": 1,      "hi": 10000000,"severity": 2},
        {"name": "pct_change",       "lo": -100,   "hi": 100,    "severity": 2},
        {"name": "volatility",       "lo": 0.001,  "hi": 1000,   "severity": 1},
        {"name": "correlation",      "lo": 0,      "hi": 1,      "severity": 1},
        {"name": "spread_bps",       "lo": -100000,"hi": 100000, "severity": 2},
        {"name": "time_offset_s",    "lo": 0,      "hi": 86400,  "severity": 1},
        {"name": "duration_years",   "lo": 0.01,   "hi": 100,    "severity": 1},
    ],

    "energy_scada": [
        {"name": "grid_freq_hz",         "lo": 49.0, "hi": 51.0, "severity": 3},
        {"name": "voltage_pu",           "lo": 0.9,  "hi": 1.1,  "severity": 3},
        {"name": "transformer_temp_c",   "lo": 0,    "hi": 80,   "severity": 2},
        {"name": "line_load_pct",        "lo": 0,    "hi": 100,  "severity": 2},
        {"name": "current_a",            "lo": 0,    "hi": 500,  "severity": 2},
        {"name": "power_factor_pct_off", "lo": -100, "hi": 100,  "severity": 1},
        {"name": "phase_angle_deg",      "lo": 0,    "hi": 360,  "severity": 1},
        {"name": "thd_pct",              "lo": 0,    "hi": 50,   "severity": 2},
    ],

    "iot_mqtt": [
        {"name": "ambient_temp_c", "lo": -40,  "hi": 85,    "severity": 1},
        {"name": "humidity_pct",    "lo": 0,    "hi": 100,   "severity": 1},
        {"name": "pressure_hpa",   "lo": 300,  "hi": 1100,  "severity": 1},
        {"name": "co2_ppm",        "lo": 0,    "hi": 1000,  "severity": 2},
        {"name": "pm25_ug_m3",     "lo": 0,    "hi": 500,   "severity": 2},
        {"name": "light_lux",      "lo": 0,    "hi": 5000,  "severity": 1},
        {"name": "battery_pct",    "lo": 0,    "hi": 100,   "severity": 2},
        {"name": "wifi_rssi_dbm",  "lo": -120, "hi": -20,   "severity": 1},
    ],

    "maritime_nmea": [
        {"name": "heading_deg",      "lo": 0,    "hi": 360,   "severity": 2},
        {"name": "speed_knots",      "lo": 0,    "hi": 50,    "severity": 1},
        {"name": "depth_m",          "lo": 0,    "hi": 11000, "severity": 3},
        {"name": "water_temp_c",     "lo": -2,   "hi": 40,    "severity": 1},
        {"name": "wind_speed_kt",    "lo": 0,    "hi": 150,   "severity": 2},
        {"name": "wind_dir_deg",     "lo": 0,    "hi": 360,   "severity": 1},
        {"name": "lat_deg",          "lo": -90,  "hi": 90,    "severity": 3},
        {"name": "lon_deg",          "lo": -180, "hi": 180,   "severity": 3},
    ],

    "nuclear_reactor": [
        {"name": "core_temp_c",        "lo": 200,  "hi": 3000,  "severity": 3},
        {"name": "pressure_psi",       "lo": 500,  "hi": 2500,  "severity": 3},
        {"name": "coolant_flow_pct",   "lo": 50,   "hi": 100,   "severity": 3},
        {"name": "neutron_flux_pct",   "lo": 0,    "hi": 120,   "severity": 3},
        {"name": "radiation_mrem_hr",  "lo": 0,    "hi": 100,   "severity": 3},
        {"name": "containment_psi",    "lo": 14.0, "hi": 16.0,  "severity": 3},
        {"name": "boron_ppm",          "lo": 0,    "hi": 4000,  "severity": 2},
        {"name": "feedwater_flow_pct", "lo": 20,   "hi": 100,   "severity": 2},
    ],

    "railway_ertms": [
        {"name": "speed_kmh",        "lo": 0,   "hi": 350,   "severity": 3},
        {"name": "acceleration_ms2", "lo": -3,  "hi": 3,     "severity": 2},
        {"name": "track_gauge_mm",   "lo": 1430,"hi": 1470,  "severity": 3},
        {"name": "axle_load_ton",    "lo": 0,   "hi": 25,    "severity": 2},
        {"name": "brake_pressure_bar","lo": 3,  "hi": 10,    "severity": 3},
        {"name": "signal_delay_ms",  "lo": 0,   "hi": 500,   "severity": 2},
        {"name": "voltage_v",        "lo": 20,  "hi": 30,    "severity": 2},
        {"name": "temp_c",           "lo": -40, "hi": 80,    "severity": 1},
    ],

    "robotics": [
        {"name": "joint_angle_rad",  "lo": -3.14, "hi": 3.14,  "severity": 2},
        {"name": "joint_velocity_rps","lo": -10,  "hi": 10,    "severity": 2},
        {"name": "torque_nm",        "lo": -100,  "hi": 100,   "severity": 2},
        {"name": "battery_pct",      "lo": 0,     "hi": 100,   "severity": 1},
        {"name": "cpu_temp_c",       "lo": -20,   "hi": 95,    "severity": 2},
        {"name": "motor_current_a",  "lo": 0,     "hi": 50,    "severity": 3},
        {"name": "proximity_m",      "lo": 0.01,  "hi": 10,    "severity": 1},
        {"name": "load_pct",         "lo": 0,     "hi": 100,   "severity": 2},
    ],
}


def available_presets() -> list[str]:
    return sorted(PRESETS.keys())


def get_preset(name: str) -> PresetDef:
    if name not in PRESETS:
        raise KeyError(f"Unknown preset '{name}'. Available: {', '.join(available_presets())}")
    return PRESETS[name]
