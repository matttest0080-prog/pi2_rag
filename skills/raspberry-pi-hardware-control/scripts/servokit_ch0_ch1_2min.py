import time
from adafruit_servokit import ServoKit

kit = ServoKit(channels=16)

DURATION_SEC = 120
STEP_DELAY_SEC = 2
SEQUENCE = [
    (0, 180),
    (90, 90),
    (180, 0),
    (90, 90),
]

start = time.monotonic()
end = start + DURATION_SEC
cycle = 0

try:
    while time.monotonic() < end:
        for ch0_angle, ch1_angle in SEQUENCE:
            remaining = end - time.monotonic()
            if remaining <= 0:
                break
            cycle += 1
            print(f"{cycle}: CH0={ch0_angle}度, CH1={ch1_angle}度, remaining={remaining:.1f}s")
            kit.servo[0].angle = ch0_angle
            kit.servo[1].angle = ch1_angle
            time.sleep(min(STEP_DELAY_SEC, max(0, remaining)))
finally:
    kit.servo[0].angle = 90
    kit.servo[1].angle = 90
    print("完成：2分鐘測試結束，CH0/CH1 停在 90度")
