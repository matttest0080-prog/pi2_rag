# pi2_rag

RAG notes and Hermes skill assets for the local Raspberry Pi 2 PCA9685 servo setup.

## Hardware context

- Raspberry Pi physical pin 3 / GPIO2 / SDA1 -> PCA9685 SDA
- Raspberry Pi physical pin 5 / GPIO3 / SCL1 -> PCA9685 SCL
- Raspberry Pi physical pin 3 / GPIO2 / SDA1 -> GY-9250 SDA
- Raspberry Pi physical pin 5 / GPIO3 / SCL1 -> GY-9250 SCL
- I2C bus used: `/dev/i2c-1`
- PCA9685 observed address: `0x40`
- GY-9250 / MPU-9250 observed address: `0x68`, `WHO_AM_I=0x71`
- PCA9685 all-call address: `0x70`

Servos require proper V+ servo power and common GND with the Raspberry Pi/PCA9685.

## Contents

```text
skills/raspberry-pi-hardware-control/
  SKILL.md
  references/
    adafruit-servokit-pca9685.md
    pca9685-servo-smoke-test.md
    pca9685-servokit-session-rag.md
    gy9250-two-channel-servo-rag.md
  scripts/
    pca9685_ch0_ch1_wide.py
    servokit_ch0_ch1_2min.py
    gy9250_two_channel_servo_trigger.py
  templates/
    servokit_ch0_smoke_test.py
```

## Confirmed working ServoKit environment

```bash
python3 -m venv /home/pi2/pca9685-venv
/home/pi2/pca9685-venv/bin/pip install --upgrade pip setuptools wheel
/home/pi2/pca9685-venv/bin/pip install adafruit-circuitpython-servokit smbus2
```

Run scripts with:

```bash
/home/pi2/pca9685-venv/bin/python <script.py>
```

## Confirmed working tests

Channel 0 smoke test:

```bash
/home/pi2/pca9685-venv/bin/python skills/raspberry-pi-hardware-control/templates/servokit_ch0_smoke_test.py
```

Channel 0 + channel 1 two-minute sustained test:

```bash
/home/pi2/pca9685-venv/bin/python skills/raspberry-pi-hardware-control/scripts/servokit_ch0_ch1_2min.py
```

Manual PCA9685 register-level wide range test:

```bash
python3 skills/raspberry-pi-hardware-control/scripts/pca9685_ch0_ch1_wide.py
```

GY-9250 horizontal/tilt two-channel servo trigger:

```bash
/home/pi2/pca9685-venv/bin/python skills/raspberry-pi-hardware-control/scripts/gy9250_two_channel_servo_trigger.py --seconds 60 --threshold 0.08 --tilt-threshold 12
```

Behavior: horizontal / XY movement triggers PCA9685 channel 0; tilt / orientation change triggers channel 1. Both channels alternate 60/120 degrees and return to 90 degrees on exit.

## Notes

ServoKit default mapping observed on this setup:

```text
0度   ≈ 747us
90度  ≈ 1499us
180度 ≈ 2251us
```

The earlier narrow manual range, `1200us -> 1500us -> 1800us`, may look like it is not moving. The wider range, `750us -> 1500us -> 2250us`, better matches ServoKit's visible 0/90/180 degree test.
