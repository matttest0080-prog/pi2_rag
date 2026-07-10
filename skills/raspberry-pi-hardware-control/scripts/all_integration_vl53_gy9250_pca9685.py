#!/usr/bin/env python3
"""Integrated hardware test: VL53L0X + GY-9250 + PCA9685 servos.

Checks:
- I2C devices: VL53L0X 0x29, PCA9685 0x40, GY-9250 0x68
- Python libs: Adafruit VL53L0X, ServoKit, smbus2
- Servo channels: CH0 and CH1 conservative center/60/120/center smoke motion
- 60s live integration loop:
  * VL53L0X distance change >= CHANGE_MM triggers CH0 once
  * GY-9250 horizontal XY acceleration >= H_THRESHOLD_G triggers CH0 once
  * GY-9250 tilt angle >= TILT_THRESHOLD_DEG triggers CH1 once
  * stable/no-trigger periods recenter channels
Always returns CH0 and CH1 to CENTER on exit.
"""
import math
import os
import time
import traceback

import board
import busio
import adafruit_vl53l0x
from adafruit_servokit import ServoKit
from smbus2 import SMBus

BUS = 1
MPU_ADDR = 0x68
WHO_AM_I = 0x75
PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B
ACCEL_SCALE = 16384.0

DURATION_S = float(os.environ.get("DURATION_S", "60"))
DETECT_MM = int(os.environ.get("DETECT_MM", "1000"))
CHANGE_MM = int(os.environ.get("CHANGE_MM", "50"))
H_THRESHOLD_G = float(os.environ.get("H_THRESHOLD_G", "0.08"))
TILT_THRESHOLD_DEG = float(os.environ.get("TILT_THRESHOLD_DEG", "12"))
CENTER = int(os.environ.get("CENTER", "90"))
SAFE_MIN = int(os.environ.get("SAFE_MIN", "60"))
SAFE_MAX = int(os.environ.get("SAFE_MAX", "120"))
POLL_S = float(os.environ.get("POLL_S", "0.10"))
COOLDOWN_S = float(os.environ.get("COOLDOWN_S", "0.60"))
ACTIVE_HOLD_S = float(os.environ.get("ACTIVE_HOLD_S", "0.80"))


def read_i16(bus, addr, reg):
    hi = bus.read_byte_data(addr, reg)
    lo = bus.read_byte_data(addr, reg + 1)
    val = (hi << 8) | lo
    return val - 65536 if val & 0x8000 else val


def read_accel_g(bus):
    return (
        read_i16(bus, MPU_ADDR, ACCEL_XOUT_H) / ACCEL_SCALE,
        read_i16(bus, MPU_ADDR, ACCEL_XOUT_H + 2) / ACCEL_SCALE,
        read_i16(bus, MPU_ADDR, ACCEL_XOUT_H + 4) / ACCEL_SCALE,
    )


def avg_accel(bus, samples=30, delay=0.025):
    vals = []
    for _ in range(samples):
        vals.append(read_accel_g(bus))
        time.sleep(delay)
    return tuple(sum(v[i] for v in vals) / len(vals) for i in range(3))


def horizontal_delta(accel, baseline):
    dx = accel[0] - baseline[0]
    dy = accel[1] - baseline[1]
    return math.sqrt(dx * dx + dy * dy)


def tilt_degrees(accel, baseline):
    mag_a = math.sqrt(sum(x * x for x in accel))
    mag_b = math.sqrt(sum(x * x for x in baseline))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(accel, baseline)) / (mag_a * mag_b)
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.acos(dot))


def valid_distance(mm):
    return mm is not None and 20 <= mm <= DETECT_MM


def alternate(current):
    return SAFE_MAX if current == SAFE_MIN else SAFE_MIN


def fmt_vec(v):
    return f"({v[0]:+.3f},{v[1]:+.3f},{v[2]:+.3f})g"


def main():
    print("START integrated test: VL53L0X + GY-9250 + PCA9685 CH0/CH1", flush=True)
    print(
        f"duration={DURATION_S:.1f}s detect<= {DETECT_MM}mm change>= {CHANGE_MM}mm "
        f"horizontal>= {H_THRESHOLD_G:.3f}g tilt>= {TILT_THRESHOLD_DEG:.1f}deg",
        flush=True,
    )

    kit = ServoKit(channels=16)
    ch0 = kit.servo[0]
    ch1 = kit.servo[1]
    ch0.set_pulse_width_range(1000, 2000)
    ch1.set_pulse_width_range(1000, 2000)

    try:
        # Known initial state + conservative smoke motion for both channels.
        for s in (ch0, ch1):
            s.angle = CENTER
        time.sleep(0.4)
        print("SERVO_SMOKE ch0/ch1 center -> 60 -> 120 -> center", flush=True)
        for angle in (SAFE_MIN, SAFE_MAX, CENTER):
            ch0.angle = angle
            ch1.angle = angle
            print(f"SERVO_SMOKE ch0={angle} ch1={angle}", flush=True)
            time.sleep(0.45)

        i2c = busio.I2C(board.SCL, board.SDA)
        tof = adafruit_vl53l0x.VL53L0X(i2c)

        with SMBus(BUS) as bus:
            who = bus.read_byte_data(MPU_ADDR, WHO_AM_I)
            print(f"GY9250 WHO_AM_I=0x{who:02x}", flush=True)
            bus.write_byte_data(MPU_ADDR, PWR_MGMT_1, 0x01)
            time.sleep(0.1)
            print("Calibrating GY-9250 baseline; keep sensor still...", flush=True)
            baseline = avg_accel(bus)
            print(f"GY9250 baseline={fmt_vec(baseline)}", flush=True)

            last_valid_mm = None
            ch0_target = SAFE_MIN
            ch1_target = SAFE_MIN
            last_ch0_move = 0.0
            last_ch1_move = 0.0
            last_trigger_time = 0.0
            readings = valid_readings = vl53_changes = h_events = tilt_events = 0
            min_mm = max_mm = None
            max_delta_mm = 0
            max_h = 0.0
            max_tilt = 0.0
            next_log = time.monotonic()
            t0 = time.monotonic()

            while time.monotonic() - t0 < DURATION_S:
                now = time.monotonic()
                elapsed = now - t0
                try:
                    mm = int(tof.range)
                except Exception:
                    mm = None
                readings += 1

                is_valid = valid_distance(mm)
                delta_mm = None
                if is_valid:
                    valid_readings += 1
                    min_mm = mm if min_mm is None else min(min_mm, mm)
                    max_mm = mm if max_mm is None else max(max_mm, mm)
                    if last_valid_mm is not None:
                        delta_mm = abs(mm - last_valid_mm)
                        max_delta_mm = max(max_delta_mm, delta_mm)
                    last_valid_mm = mm

                accel = read_accel_g(bus)
                h = horizontal_delta(accel, baseline)
                tilt = tilt_degrees(accel, baseline)
                max_h = max(max_h, h)
                max_tilt = max(max_tilt, tilt)

                ch0_reason = None
                if delta_mm is not None and delta_mm >= CHANGE_MM:
                    ch0_reason = f"VL53_CHANGE delta={delta_mm}mm distance={mm}mm"
                    vl53_changes += 1
                elif h >= H_THRESHOLD_G:
                    ch0_reason = f"GY_HORIZONTAL h={h:.3f}g"
                    h_events += 1

                if ch0_reason and now - last_ch0_move >= COOLDOWN_S:
                    ch0.angle = ch0_target
                    print(f"{elapsed:5.1f}s CH0 {ch0_reason} -> angle {ch0_target}", flush=True)
                    ch0_target = alternate(ch0_target)
                    last_ch0_move = now
                    last_trigger_time = now

                if tilt >= TILT_THRESHOLD_DEG and now - last_ch1_move >= COOLDOWN_S:
                    ch1.angle = ch1_target
                    tilt_events += 1
                    print(f"{elapsed:5.1f}s CH1 GY_TILT tilt={tilt:.1f}deg -> angle {ch1_target}", flush=True)
                    ch1_target = alternate(ch1_target)
                    last_ch1_move = now
                    last_trigger_time = now

                if now - last_trigger_time > ACTIVE_HOLD_S:
                    ch0.angle = CENTER
                    ch1.angle = CENTER

                if now >= next_log:
                    print(
                        f"{elapsed:5.1f}s distance={mm}mm delta={delta_mm} valid={is_valid} "
                        f"h={h:.3f}g tilt={tilt:.1f}deg",
                        flush=True,
                    )
                    next_log = now + 5.0

                time.sleep(POLL_S)

            print(
                "SUMMARY "
                f"readings={readings} valid_readings={valid_readings} min_mm={min_mm} max_mm={max_mm} "
                f"max_delta_mm={max_delta_mm} vl53_changes={vl53_changes} "
                f"h_events={h_events} tilt_events={tilt_events} max_h={max_h:.3f}g max_tilt={max_tilt:.1f}deg",
                flush=True,
            )
    finally:
        try:
            ch0.angle = CENTER
            ch1.angle = CENTER
            time.sleep(0.5)
        finally:
            print(f"STOP ch0_center={CENTER} ch1_center={CENTER}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("ERROR integrated test failed:", flush=True)
        traceback.print_exc()
        raise
