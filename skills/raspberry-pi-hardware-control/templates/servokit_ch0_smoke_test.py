from adafruit_servokit import ServoKit
from time import sleep

kit = ServoKit(channels=16)

# One-shot PCA9685 channel 0 smoke test.
# Leaves the servo centered at 90 degrees.
for angle in [0, 90, 180, 90]:
    print(f"{angle}度")
    kit.servo[0].angle = angle
    sleep(2)

print("完成：channel 0 停在 90度")
