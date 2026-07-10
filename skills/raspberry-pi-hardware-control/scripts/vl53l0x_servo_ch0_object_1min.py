#!/usr/bin/env python3
"""Run VL53L0X-triggered PCA9685 channel 0 servo test for 60 seconds.

If an object is detected within DETECT_MM, sweep servo CH0 between SAFE_MIN/SAFE_MAX.
If no object is detected, leave CH0 still at CENTER.
Always returns CH0 to CENTER before exit.
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
CENTER = int(os.environ.get("CENTER", "90"))
SAFE_MIN = int(os.environ.get("SAFE_MIN", "60"))
SAFE_MAX = int(os.environ.get("SAFE_MAX", "120"))
STEP_INTERVAL_S = float(os.environ.get("STEP_INTERVAL_S", "0.35"))
READ_INTERVAL_S = float(os.environ.get("READ_INTERVAL_S", "0.10"))


def valid_detection(mm):
    # VL53L0X commonly reports very large values or raises errors when out of range.
    # Treat a finite near reading as an object detected.
    return mm is not None and 20 <= mm <= DETECT_MM


def main():
    i2c = busio.I2C(board.SCL, board.SDA)
    tof = adafruit_vl53l0x.VL53L0X(i2c)
    kit = ServoKit(channels=16)
    servo = kit.servo[0]
    servo.set_pulse_width_range(1000, 2000)

    servo.angle = CENTER
    print(f"START duration={DURATION_S:.1f}s detect_threshold<= {DETECT_MM}mm servo_ch=0 center={CENTER} sweep={SAFE_MIN}/{SAFE_MAX}", flush=True)

    t0 = time.monotonic()
    next_step = t0
    next_log = t0
    target = SAFE_MIN
    last_detected = None
    readings = 0
    detected_readings = 0
    min_mm = None
    max_mm = None

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
            if mm is not None:
                min_mm = mm if min_mm is None else min(min_mm, mm)
                max_mm = mm if max_mm is None else max(max_mm, mm)

            detected = valid_detection(mm)
            if detected:
                detected_readings += 1

            if detected != last_detected:
                state = "DETECTED -> servo sweeping" if detected else "NO_OBJECT -> servo stopped at center"
                print(f"{elapsed:5.1f}s distance={mm}mm {state}", flush=True)
                last_detected = detected
                if not detected:
                    servo.angle = CENTER

            if detected and now >= next_step:
                servo.angle = target
                target = SAFE_MAX if target == SAFE_MIN else SAFE_MIN
                next_step = now + STEP_INTERVAL_S

            if now >= next_log:
                print(f"{elapsed:5.1f}s distance={mm}mm detected={detected}", flush=True)
                next_log = now + 5.0

            time.sleep(READ_INTERVAL_S)

    finally:
        servo.angle = CENTER
        time.sleep(0.5)
        print(f"STOP servo_ch0_returned_to_center={CENTER}", flush=True)
        print(f"SUMMARY readings={readings} detected_readings={detected_readings} min_mm={min_mm} max_mm={max_mm}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("ERROR during VL53L0X/servo test:", flush=True)
        traceback.print_exc()
        raise
