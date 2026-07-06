# GY-9250 horizontal vs tilt two-channel servo RAG notes

## Confirmed local hardware context

- Raspberry Pi physical pin 3 / GPIO2 / SDA1 is connected to GY-9250 SDA.
- Raspberry Pi physical pin 5 / GPIO3 / SCL1 is connected to GY-9250 SCL.
- I2C bus: `/dev/i2c-1` / bus `1`.
- PCA9685 observed at address `0x40`.
- GY-9250 / MPU-9250 observed at address `0x68`.
- `WHO_AM_I` register `0x75` returned `0x71` on this board.
- Existing working Python environment: `/home/pi2/pca9685-venv`.
- `smbus2` is installed in that venv for GY-9250 register access.
- `adafruit-circuitpython-servokit` is installed in that venv for PCA9685 servo control.

## Goal implemented

Map different GY-9250 movements to different PCA9685 servo channels:

- Horizontal / XY acceleration change -> servo channel 0.
- Tilt / orientation change -> servo channel 1.

The reusable script is:

```bash
skills/raspberry-pi-hardware-control/scripts/gy9250_two_channel_servo_trigger.py
```

Local development copy during the session was:

```bash
/home/pi2/test_gy9250_servo_trigger.py
```

## Motion classification heuristic

An accelerometer cannot perfectly separate linear horizontal translation from tilt, because both affect measured acceleration. The implemented practical split is:

- `horizontal_delta(accel, baseline)`: Euclidean delta of X/Y acceleration components in g.
- `tilt_degrees(accel, baseline)`: angle between current acceleration vector and baseline gravity vector.

Recommended starting thresholds:

- Horizontal hand motion: `--threshold 0.08`.
- More sensitive horizontal hand motion: `--threshold 0.03`.
- Tilt: `--tilt-threshold 12` degrees.
- More sensitive tilt: `--tilt-threshold 8` degrees.

Large tilts can also change X/Y acceleration enough to trigger the horizontal path. If strict separation is required later, add gating such as suppressing horizontal triggers whenever tilt exceeds the tilt threshold.

## Runtime flow

1. Center both servos at 90 degrees.
2. Read GY-9250 `WHO_AM_I` register `0x75` and expect `0x71` locally.
3. Wake the MPU by writing `PWR_MGMT_1` register `0x6B = 0x01`.
4. Calibrate baseline for about one second while the board is still.
5. Poll accelerometer values.
6. If horizontal delta exceeds threshold, alternate channel 0 between 60 and 120 degrees.
7. If tilt exceeds threshold, alternate channel 1 between 60 and 120 degrees.
8. In `finally`, recenter both channels at 90 degrees.

## Test command

Default first manual test:

```bash
/home/pi2/pca9685-venv/bin/python \
  skills/raspberry-pi-hardware-control/scripts/gy9250_two_channel_servo_trigger.py \
  --seconds 60 \
  --threshold 0.08 \
  --tilt-threshold 12 \
  --horizontal-channel 0 \
  --tilt-channel 1
```

More sensitive hand test:

```bash
/home/pi2/pca9685-venv/bin/python \
  skills/raspberry-pi-hardware-control/scripts/gy9250_two_channel_servo_trigger.py \
  --seconds 60 \
  --threshold 0.03 \
  --tilt-threshold 8
```

Operator instructions:

1. Start the command.
2. During `Calibrating baseline; keep GY-9250 still...`, keep the board still for about one second.
3. After `Run for ...`, move horizontally to test channel 0 and tilt to test channel 1.
4. Look for log lines like:
   - `HORIZONTAL 1: ... -> ch0 angle 60`
   - `TILT 1: ... -> ch1 angle 60`

## Observed verification evidence from session

I2C discovery showed:

```text
0x40: PCA9685
0x68: GY-9250 / MPU-9250
WHO_AM_I=0x71
```

A prior one-channel version with low threshold verified servo actuation path:

```text
TRIGGER 1: delta=0.016g -> ch0 angle 60
TRIGGER 2: delta=0.014g -> ch0 angle 120
Done: samples=150, triggers=9, max_delta=0.041g
Centering servo ch0 at 90 degrees
```

For the current two-channel script, use focused ad-hoc verification when no canonical test suite exists:

- Create a temporary `/tmp/hermes-verify-*` script using Python `tempfile`.
- Import `gy9250_two_channel_servo_trigger.py` or the local working copy.
- Verify `horizontal_delta()`, `tilt_degrees()`, `alternate()`, and simulated readings for horizontal -> channel 0 and tilt -> channel 1.
- Remove the temp script.
- Report it as ad-hoc verification, not formal suite green.

Fresh ad-hoc verification for this update passed with:

```text
ad-hoc verification passed: current file horizontal->ch0, tilt->ch1, helper math
```

## Safety and pitfalls

- Keep servo movement conservative at 60/90/120 degrees until the mechanism is known safe.
- Always recenter all touched servos in `finally`.
- Servo V+ usually needs external power; share GND with Raspberry Pi/PCA9685.
- Software I2C success does not prove physical servo motion if servo power, channel wiring, or plug orientation is wrong.
