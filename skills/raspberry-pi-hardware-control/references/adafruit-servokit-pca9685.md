# Adafruit ServoKit with PCA9685 on Raspberry Pi

Session-derived notes for PCA9685 servo testing using `adafruit_servokit`.

## Setup pattern

On Raspberry Pi OS with PEP 668 system Python, install Adafruit libraries in a project venv rather than system pip:

```bash
python3 -m venv ~/pca9685-venv
~/pca9685-venv/bin/pip install --upgrade pip setuptools wheel
~/pca9685-venv/bin/pip install adafruit-circuitpython-servokit
```

Run scripts with:

```bash
~/pca9685-venv/bin/python script.py
```

## Minimal corrected ServoKit example

The user's original loop needed Python indentation, and each angle in an infinite loop should sleep before the next jump:

```python
from adafruit_servokit import ServoKit
from time import sleep

kit = ServoKit(channels=16)

while True:
    print("0度")
    kit.servo[0].angle = 0
    sleep(2)

    print("90度")
    kit.servo[0].angle = 90
    sleep(2)

    print("180度")
    kit.servo[0].angle = 180
    sleep(2)
```

For a one-shot smoke test, prefer `[0, 90, 180, 90]` so the servo ends centered.

## Multi-channel PCA9685 test pattern

For channel 0 and 1, first center both channels, then test each alone, then test both together. This helps distinguish wiring/channel mistakes from power issues.

Observed good execution pattern:

```text
PCA9685 detected at 0x40; all-call 0x70 may also appear.
CH0: 1500us / 90 degrees center
CH1: 1500us / 90 degrees center
CH0 alone: low -> center -> high -> center
CH1 alone: low -> center -> high -> center
CH0 and CH1 together: opposite directions -> center -> opposite directions -> center
```

## Reporting

Do not claim the servo physically moved unless the user confirms it or another sensor verifies motion. Report that the code ran successfully and list the commanded angles/pulses.