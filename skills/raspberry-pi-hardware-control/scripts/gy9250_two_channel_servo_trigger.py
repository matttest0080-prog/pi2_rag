#!/usr/bin/env python3
"""Move PCA9685 servos from GY-9250/MPU-9250 motion.

Wiring assumed on Raspberry Pi I2C bus 1:
  GY-9250 SDA -> physical pin 3 (GPIO2/SDA1)
  GY-9250 SCL -> physical pin 5 (GPIO3/SCL1)
  PCA9685 address 0x40, GY-9250/MPU-9250 address 0x68

Default behavior:
  * horizontal/side motion changes servo channel 0
  * tilt/orientation changes servo channel 1
  * both servos alternate between 60 and 120 degrees, then recenter at exit

Note: an accelerometer cannot perfectly separate translation from tilt. This uses
a practical heuristic: XY acceleration delta is treated as horizontal motion;
gravity-vector angle change is treated as tilt.
"""
import argparse
import math
import time
from smbus2 import SMBus
from adafruit_servokit import ServoKit

BUS = 1
MPU_ADDR = 0x68
PWR_MGMT_1 = 0x6B
WHO_AM_I = 0x75
ACCEL_XOUT_H = 0x3B
ACCEL_SCALE = 16384.0  # +/-2g


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


def vec_delta(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def horizontal_delta(accel, baseline):
    """XY-plane acceleration difference in g."""
    dx = accel[0] - baseline[0]
    dy = accel[1] - baseline[1]
    return math.sqrt(dx * dx + dy * dy)


def tilt_degrees(accel, baseline):
    """Angle between current and baseline acceleration vectors."""
    mag_a = math.sqrt(sum(x * x for x in accel))
    mag_b = math.sqrt(sum(x * x for x in baseline))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(accel, baseline)) / (mag_a * mag_b)
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.acos(dot))


def average_accel(bus, samples=30, delay=0.02):
    vals = []
    for _ in range(samples):
        vals.append(read_accel_g(bus))
        time.sleep(delay)
    return tuple(sum(v[i] for v in vals) / len(vals) for i in range(3))


def fmt_vec(v):
    return f"({v[0]:+.3f}, {v[1]:+.3f}, {v[2]:+.3f})g"


def alternate(pos, left, right):
    return right if pos == left else left


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=30.0, help="test duration")
    parser.add_argument("--threshold", type=float, default=0.08, help="horizontal XY delta in g that triggers channel 0")
    parser.add_argument("--tilt-threshold", type=float, default=12.0, help="tilt angle in degrees that triggers channel 1")
    parser.add_argument("--channel", type=int, default=None, help="backward-compatible alias for --horizontal-channel")
    parser.add_argument("--horizontal-channel", type=int, default=0, help="PCA9685 channel for horizontal motion")
    parser.add_argument("--tilt-channel", type=int, default=1, help="PCA9685 channel for tilt motion")
    parser.add_argument("--left", type=int, default=60, help="first trigger angle")
    parser.add_argument("--right", type=int, default=120, help="second trigger angle")
    parser.add_argument("--center", type=int, default=90, help="center/final angle")
    parser.add_argument("--cooldown", type=float, default=0.45, help="minimum seconds between servo moves per channel")
    parser.add_argument("--poll", type=float, default=0.05, help="sensor poll interval")
    args = parser.parse_args()

    h_ch = args.channel if args.channel is not None else args.horizontal_channel
    t_ch = args.tilt_channel
    if h_ch == t_ch:
        raise SystemExit("horizontal channel and tilt channel must be different")

    print(
        f"Opening I2C bus {BUS}; MPU/GY-9250 addr=0x{MPU_ADDR:02x}; "
        f"horizontal ch={h_ch}; tilt ch={t_ch}"
    )
    kit = ServoKit(channels=16)
    h_servo = kit.servo[h_ch]
    t_servo = kit.servo[t_ch]

    h_pos = args.left
    t_pos = args.left
    h_triggers = 0
    t_triggers = 0
    samples = 0
    max_h_delta = 0.0
    max_tilt = 0.0

    try:
        h_servo.angle = args.center
        t_servo.angle = args.center
        with SMBus(BUS) as bus:
            who = bus.read_byte_data(MPU_ADDR, WHO_AM_I)
            print(f"WHO_AM_I=0x{who:02x} (MPU-9250 commonly 0x71/0x73)")
            # Wake device and select the X gyro PLL clock source.
            bus.write_byte_data(MPU_ADDR, PWR_MGMT_1, 0x01)
            time.sleep(0.1)

            print("Calibrating baseline; keep GY-9250 still for about 1 second...")
            baseline = average_accel(bus, samples=40, delay=0.025)
            print(f"Baseline accel={fmt_vec(baseline)}")
            print(
                f"Run for {args.seconds:.1f}s. Horizontal XY delta >= {args.threshold:.3f}g "
                f"moves ch{h_ch}; tilt >= {args.tilt_threshold:.1f} deg moves ch{t_ch}."
            )

            end = time.monotonic() + args.seconds
            last_h_move = 0.0
            last_t_move = 0.0
            last_log = 0.0
            while time.monotonic() < end:
                now = time.monotonic()
                accel = read_accel_g(bus)
                h_delta = horizontal_delta(accel, baseline)
                tilt = tilt_degrees(accel, baseline)
                samples += 1
                max_h_delta = max(max_h_delta, h_delta)
                max_tilt = max(max_tilt, tilt)

                if now - last_log >= 1.0:
                    print(
                        f"sample={samples:04d} accel={fmt_vec(accel)} "
                        f"horizontal={h_delta:.3f}g max_h={max_h_delta:.3f}g "
                        f"tilt={tilt:.1f}deg max_tilt={max_tilt:.1f}deg"
                    )
                    last_log = now

                if h_delta >= args.threshold and now - last_h_move >= args.cooldown:
                    angle = h_pos
                    print(f"HORIZONTAL {h_triggers + 1}: {h_delta:.3f}g -> ch{h_ch} angle {angle}")
                    h_servo.angle = angle
                    h_pos = alternate(h_pos, args.left, args.right)
                    h_triggers += 1
                    last_h_move = now

                if tilt >= args.tilt_threshold and now - last_t_move >= args.cooldown:
                    angle = t_pos
                    print(f"TILT {t_triggers + 1}: {tilt:.1f}deg -> ch{t_ch} angle {angle}")
                    t_servo.angle = angle
                    t_pos = alternate(t_pos, args.left, args.right)
                    t_triggers += 1
                    last_t_move = now

                time.sleep(args.poll)

            print(
                f"Done: samples={samples}, horizontal_triggers={h_triggers}, "
                f"tilt_triggers={t_triggers}, max_h_delta={max_h_delta:.3f}g, "
                f"max_tilt={max_tilt:.1f}deg"
            )
    finally:
        print(f"Centering servo ch{h_ch} and ch{t_ch} at {args.center} degrees")
        for ch, servo in ((h_ch, h_servo), (t_ch, t_servo)):
            try:
                servo.angle = args.center
            except Exception as exc:
                print(f"Could not center servo ch{ch}: {exc}")
        time.sleep(0.4)


if __name__ == "__main__":
    main()

