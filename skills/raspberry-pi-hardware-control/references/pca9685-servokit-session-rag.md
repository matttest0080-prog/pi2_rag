# PCA9685 Servo Test RAG Notes

This reference captures the verified local Raspberry Pi + PCA9685 servo test workflow from the hardware session. Treat it as retrieval context for future servo tests on this machine.

## Local wiring

- Raspberry Pi physical pin 3 / GPIO2 / SDA1 -> PCA9685 SDA.
- Raspberry Pi physical pin 5 / GPIO3 / SCL1 -> PCA9685 SCL.
- I2C header bus used successfully: `/dev/i2c-1`.
- PCA9685 default address observed: `0x40`.
- PCA9685 all-call address observed: `0x70`.
- Servo power still requires V+ power sized for the servos and common GND with the Pi/PCA9685.

## Live discovery commands and observed state

Useful preflight commands:

```bash
id
uname -a
test -e /dev/i2c-1 && echo /dev/i2c-1 exists || echo /dev/i2c-1 missing
command -v i2cdetect || true
raspi-config nonint get_i2c || true
i2cdetect -y 1
```

Observed after enabling I2C:

```text
/dev/i2c-1
/dev/i2c-2
```

Observed PCA9685 scan pattern:

```text
40: 40 -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: 70 -- -- -- -- -- -- --
```

I2C was enabled with:

```bash
sudo raspi-config nonint do_i2c 0
```

This wrote/activated:

```text
dtparam=i2c_arm=on
```

## Confirmed working ServoKit setup

The `adafruit_servokit` module was not initially installed in system Python. On this PEP 668 Raspberry Pi OS host, the working setup is a virtualenv:

```bash
python3 -m venv /home/pi2/pca9685-venv
/home/pi2/pca9685-venv/bin/pip install --upgrade pip setuptools wheel
/home/pi2/pca9685-venv/bin/pip install adafruit-circuitpython-servokit
```

Run ServoKit scripts with:

```bash
/home/pi2/pca9685-venv/bin/python SCRIPT.py
```

## Confirmed working channel 0 ServoKit test

File created during session:

```text
/home/pi2/test_servokit_ch0.py
```

Program behavior:

- CH0 -> 0 degrees, sleep 2s.
- CH0 -> 90 degrees, sleep 2s.
- CH0 -> 180 degrees, sleep 2s.
- CH0 -> 90 degrees, sleep 2s.
- Leaves CH0 centered at 90 degrees.

Observed output:

```text
0度
90度
180度
90度
完成：channel 0 停在 90度
```

## ServoKit pulse range vs manual register pulse range

ServoKit default mapping observed by writing angles then reading PCA9685 registers:

```text
0度   -> off_count 153 -> about 747us
90度  -> off_count 307 -> about 1499us
180度 -> off_count 461 -> about 2251us
```

The initial manual register script used only:

```text
1200us -> 1500us -> 1800us
```

This was too narrow to visibly move the user's servo in the same way as ServoKit. For tests intended to match ServoKit, use approximately:

```text
750us -> 1500us -> 2250us
```

## Confirmed working 2-minute dual-servo test

File created during session:

```text
/tmp/test_pca9685_ch0_ch1_2min.py
```

Use ServoKit, because ServoKit was confirmed working on this setup. Duration: 120 seconds. Step delay: 2 seconds.

Sequence:

```text
CH0=0度,   CH1=180度
CH0=90度,  CH1=90度
CH0=180度, CH1=0度
CH0=90度,  CH1=90度
```

This repeats until the 120-second timer ends, then leaves both channels centered:

```text
完成：2分鐘測試結束，CH0/CH1 停在 90度
```

Observed final output included:

```text
60: CH0=90度, CH1=90度, remaining=1.9s
完成：2分鐘測試結束，CH0/CH1 停在 90度
```

## Preferred future behavior

When asked to test this PCA9685 setup:

1. Use `i2cdetect -y 1` first and confirm `0x40`.
2. If the user asks for a known-good test, prefer ServoKit via `/home/pi2/pca9685-venv/bin/python`.
3. For CH0-only smoke test, use `/home/pi2/test_servokit_ch0.py` or the skill template.
4. For CH0+CH1 sustained test, use the 2-minute ServoKit script template.
5. If using register-level scripts, match ServoKit's wider range only after safe motion is confirmed.
6. Always end by returning active servos to 90 degrees / 1500us center.
