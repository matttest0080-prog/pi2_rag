#!/usr/bin/env python3
"""Run VL53L0X change-triggered PCA9685 channel 0 servo test for 60 seconds.

Logic:
- Read VL53L0X distance continuously.
- If the distance changes by CHANGE_MM or more compared with the previous valid
  reading, treat it as a detected change and move servo channel 0 once.
- If distance is stable/no valid object reading, hold the servo still at CENTER.
- Always return channel 0 to CENTER on exit.
"""
import os
import time
import traceback

import board
import busio
import adafruit_vl53l0x
from adafruit_servokit import ServoKit

DURATION_S = float(os.environ.get("DURATION_S", "60"))
DETECT_MM = int(os.environ.get("DETECT_MM", "1000"))
CHANGE_MM = int(os.environ.get("CHANGE_MM", "50"))
CENTER = int(os.environ.get("CENTER", "90"))
SAFE_MIN = int(os.environ.get("SAFE_MIN", "60"))
SAFE_MAX = int(os.environ.get("SAFE_MAX", "120"))
READ_INTERVAL_S = float(os.environ.get("READ_INTERVAL_S", "0.10"))
ACTIVE_HOLD_S = float(os.environ.get("ACTIVE_HOLD_S", "0.80"))


def valid_distance(mm):
    return mm is not None and 20 <= mm <= DETECT_MM


def main():
    i2c = busio.I2C(board.SCL, board.SDA)
    tof = adafruit_vl53l0x.VL53L0X(i2c)
    kit = ServoKit(channels=16)
    servo = kit.servo[0]
    servo.set_pulse_width_range(1000, 2000)
    servo.angle = CENTER

    print(
        f"START duration={DURATION_S:.1f}s detect<= {DETECT_MM}mm "
        f"change_threshold>= {CHANGE_MM}mm servo_ch=0 center={CENTER} move={SAFE_MIN}/{SAFE_MAX}",
        flush=True,
    )

    t0 = time.monotonic()
    next_log = t0
    last_valid_mm = None
    last_change_time = 0.0
    target = SAFE_MIN
    readings = 0
    valid_readings = 0
    change_events = 0
    min_mm = None
    max_mm = None
    was_active = False

    try:
        while True:
            now = time.monotonic()
            elapsed = now - t0
            if elapsed >= DURATION_S:
                break

            try:
                mm = int(tof.range)
            except Exception:
                mm = None

            readings += 1
            is_valid = valid_distance(mm)
            delta = None
            changed = False

            if is_valid:
                valid_readings += 1
                min_mm = mm if min_mm is None else min(min_mm, mm)
                max_mm = mm if max_mm is None else max(max_mm, mm)
                if last_valid_mm is not None:
                    delta = abs(mm - last_valid_mm)
                    changed = delta >= CHANGE_MM
                last_valid_mm = mm

            if changed:
                change_events += 1
                last_change_time = now
                servo.angle = target
                print(
                    f"{elapsed:5.1f}s distance={mm}mm delta={delta}mm CHANGE -> servo angle {target}",
                    flush=True,
                )
                target = SAFE_MAX if target == SAFE_MIN else SAFE_MIN

            active = (now - last_change_time) <= ACTIVE_HOLD_S
            if was_active and not active:
                servo.angle = CENTER
                print(f"{elapsed:5.1f}s stable -> servo stopped at center {CENTER}", flush=True)
            was_active = active

            if now >= next_log:
                print(
                    f"{elapsed:5.1f}s distance={mm}mm valid={is_valid} delta={delta} changed={changed}",
                    flush=True,
                )
                next_log = now + 5.0

            time.sleep(READ_INTERVAL_S)
    finally:
        servo.angle = CENTER
        time.sleep(0.5)
        print(f"STOP servo_ch0_returned_to_center={CENTER}", flush=True)
        print(
            f"SUMMARY readings={readings} valid_readings={valid_readings} "
            f"change_events={change_events} min_mm={min_mm} max_mm={max_mm}",
            flush=True,
        )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("ERROR during VL53L0X change/servo test:", flush=True)
        traceback.print_exc()
        raise
