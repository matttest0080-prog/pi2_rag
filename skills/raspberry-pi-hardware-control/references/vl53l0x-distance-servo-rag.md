# VL53L0X Distance-Triggered Servo RAG Notes

## Confirmed local hardware

- Raspberry Pi header I2C bus: `/dev/i2c-1`.
- GY-530 / VL53L0X Time-of-Flight sensor wiring uses the shared I2C lines:
  - physical pin 3 / GPIO2 / SDA1 -> VL53L0X SDA.
  - physical pin 5 / GPIO3 / SCL1 -> VL53L0X SCL.
- PCA9685 servo controller is on the same I2C bus.
- Observed I2C scan during verification:
  - VL53L0X: `0x29`.
  - PCA9685: `0x40`.
  - GY-9250 also present: `0x68`.
- Use `/home/pi2/pca9685-venv/bin/python`; the venv has `adafruit-circuitpython-vl53l0x`, `adafruit-circuitpython-servokit`, `board`, and `busio` installed.

## Prerequisite checks

Run these before actuating hardware:

```bash
id
test -e /dev/i2c-1 && echo /dev/i2c-1 exists
raspi-config nonint get_i2c
i2cdetect -y 1
/home/pi2/pca9685-venv/bin/python - <<'PY'
for m in ['adafruit_servokit','adafruit_vl53l0x','board','busio']:
    __import__(m)
    print(m, 'OK')
PY
```

Expected local pattern:

```text
/dev/i2c-1 exists
0
... 29 ...
... 40 ...
... 68 ...
adafruit_servokit OK
adafruit_vl53l0x OK
board OK
busio OK
```

`raspi-config nonint get_i2c` returning `0` means I2C is enabled.

## Test 1: object-present trigger for channel 0

Script:

```bash
/home/pi2/pca9685-venv/bin/python skills/raspberry-pi-hardware-control/scripts/vl53l0x_servo_ch0_object_1min.py
```

Default behavior:

- Duration: 60 seconds.
- Distance threshold: `DETECT_MM=1000`.
- Any valid distance from 20 mm through 1000 mm is treated as an object.
- When an object is present, PCA9685 channel 0 sweeps between 60 and 120 degrees.
- When no object is present, channel 0 stays centered at 90 degrees.
- `finally` returns channel 0 to 90 degrees.

Verified local run:

```text
START duration=60.0s detect_threshold<= 1000mm servo_ch=0 center=90 sweep=60/120
  0.0s distance=77mm DETECTED -> servo sweeping
  5.0s distance=78mm detected=True
 10.0s distance=77mm detected=True
 15.0s distance=78mm detected=True
 20.1s distance=94mm detected=True
 25.1s distance=319mm detected=True
 30.1s distance=143mm detected=True
 35.1s distance=102mm detected=True
 40.1s distance=102mm detected=True
 45.2s distance=297mm detected=True
 50.2s distance=84mm detected=True
 55.2s distance=106mm detected=True
STOP servo_ch0_returned_to_center=90
SUMMARY readings=431 detected_readings=431 min_mm=61 max_mm=413
```

Interpretation: the object was present for the whole one-minute test, so channel 0 remained in the sweeping state and returned to center at exit.

## Test 2: distance-change trigger for channel 0

Script:

```bash
/home/pi2/pca9685-venv/bin/python skills/raspberry-pi-hardware-control/scripts/vl53l0x_servo_ch0_change_1min.py
```

Default behavior:

- Duration: 60 seconds.
- Valid distance range: 20 mm through `DETECT_MM=1000`.
- Change threshold: `CHANGE_MM=50`.
- Compare each valid reading with the previous valid reading.
- When absolute distance delta is at least 50 mm, channel 0 moves once, alternating between 60 and 120 degrees.
- When distance is stable, channel 0 returns to and holds 90 degrees.
- `finally` returns channel 0 to 90 degrees.

Verified local run:

```text
START duration=60.0s detect<= 1000mm change_threshold>= 50mm servo_ch=0 center=90 move=60/120
  0.0s distance=106mm valid=True delta=None changed=False
  5.0s distance=105mm valid=True delta=0 changed=False
 10.0s distance=105mm valid=True delta=2 changed=False
 12.4s distance=176mm delta=67mm CHANGE -> servo angle 60
 12.8s distance=128mm delta=51mm CHANGE -> servo angle 120
 13.6s stable -> servo stopped at center 90
 14.2s distance=110mm delta=62mm CHANGE -> servo angle 60
 15.0s stable -> servo stopped at center 90
 16.6s distance=189mm delta=68mm CHANGE -> servo angle 120
 17.1s distance=113mm delta=66mm CHANGE -> servo angle 60
 17.9s stable -> servo stopped at center 90
 19.8s distance=175mm delta=53mm CHANGE -> servo angle 120
 20.3s distance=105mm delta=69mm CHANGE -> servo angle 60
 21.1s stable -> servo stopped at center 90
STOP servo_ch0_returned_to_center=90
SUMMARY readings=432 valid_readings=432 change_events=7 min_mm=100 max_mm=189
```

Interpretation: 7 distance-change events were detected in one minute; each event commanded channel 0 once, and stable periods recentered the servo.

## Tuning knobs

Both scripts read environment variables, so tests can be adjusted without editing files:

```bash
DETECT_MM=700 CHANGE_MM=30 DURATION_S=30 /home/pi2/pca9685-venv/bin/python skills/raspberry-pi-hardware-control/scripts/vl53l0x_servo_ch0_change_1min.py
```

Useful variables:

- `DURATION_S`: test duration, default `60`.
- `DETECT_MM`: maximum valid/object distance in millimeters, default `1000`.
- `CHANGE_MM`: change threshold for the change-trigger script, default `50`.
- `CENTER`: resting servo angle, default `90`.
- `SAFE_MIN`: low movement angle, default `60`.
- `SAFE_MAX`: high movement angle, default `120`.
- `READ_INTERVAL_S`: sensor polling interval, default `0.10` seconds.
- `ACTIVE_HOLD_S`: change-trigger script hold time before recentering, default `0.80` seconds.

## Pitfalls

1. Treating constant nearby readings as motion. Use the change-trigger script when the servo should move only when distance changes.
2. Too-low `CHANGE_MM`. VL53L0X readings can jitter by a few millimeters; keep a threshold such as 30-50 mm unless high sensitivity is required.
3. Not recentering after stable periods. The change-trigger script explicitly recenters when `ACTIVE_HOLD_S` expires.
4. Overwide first motion. Keep 60/90/120 degrees until the mechanical mount is known safe.
5. Assuming I2C success proves physical servo motion. PCA9685 logic can work while servo V+ or common ground is missing.
