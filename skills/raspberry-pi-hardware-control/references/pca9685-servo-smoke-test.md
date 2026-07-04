# PCA9685 Channel-0 Servo Smoke Test

Session-derived recipe for testing a servo connected to PCA9685 channel 0 from a Raspberry Pi header I2C connection.

## Wiring context

- Raspberry Pi physical pin 3 / GPIO2 / SDA1 -> PCA9685 SDA.
- Raspberry Pi physical pin 5 / GPIO3 / SCL1 -> PCA9685 SCL.
- Raspberry Pi/PCA9685 GND must be common with the servo power supply GND.
- PCA9685 V+ should be powered by an external servo supply for real servos; do not rely on the Pi 5V rail for multiple or loaded servos.

## Discovery sequence

```sh
id
uname -a
test -e /dev/i2c-1 && echo /dev/i2c-1 exists || echo /dev/i2c-1 missing
command -v i2cdetect || true
raspi-config nonint get_i2c || true
i2cdetect -y 1
```

If I2C is disabled and the user wants the local machine configured:

```sh
sudo raspi-config nonint do_i2c 0
```

On a successful PCA9685 scan, expect `0x40` for the board and often `0x70` for the all-call address.

## Register-level Python smoke test

This script uses `smbus2` and leaves channel 0 centered at 1500us.

```python
import time, math
from smbus2 import SMBus

BUS = 1
ADDR = 0x40
CH = 0
MODE1 = 0x00
PRESCALE = 0xFE
LED0_ON_L = 0x06

bus = SMBus(BUS)

def write(reg, val):
    bus.write_byte_data(ADDR, reg, val & 0xFF)

def read(reg):
    return bus.read_byte_data(ADDR, reg)

def set_pwm_freq(freq_hz):
    prescaleval = 25000000.0 / 4096.0 / freq_hz - 1.0
    prescale = int(math.floor(prescaleval + 0.5))
    oldmode = read(MODE1)
    sleepmode = (oldmode & 0x7F) | 0x10
    write(MODE1, sleepmode)
    write(PRESCALE, prescale)
    write(MODE1, oldmode)
    time.sleep(0.005)
    write(MODE1, oldmode | 0xA1)  # restart + auto-increment + all-call
    return prescale

def set_channel(ch, off_count):
    base = LED0_ON_L + 4 * ch
    vals = [0, 0, off_count & 0xFF, (off_count >> 8) & 0x0F]
    bus.write_i2c_block_data(ADDR, base, vals)

def us_to_count(us, freq=50):
    period_us = 1000000.0 / freq
    return int(round(us * 4096 / period_us))

print('PCA9685 MODE1 before:', hex(read(MODE1)))
prescale = set_pwm_freq(50)
print('Set PWM freq 50Hz, prescale', prescale)

sequence = [
    ('center 1500us', 1500, 1.0),
    ('one side 1200us', 1200, 0.8),
    ('center 1500us', 1500, 0.8),
    ('other side 1800us', 1800, 0.8),
    ('center 1500us', 1500, 1.0),
]

for label, us, delay in sequence:
    count = us_to_count(us)
    print(f'CH{CH}: {label} -> count {count}')
    set_channel(CH, count)
    time.sleep(delay)

print('Done: channel 0 left at center pulse 1500us.')
bus.close()
```

Representative successful output:

```text
PCA9685 MODE1 before: 0x11
Set PWM freq 50Hz, prescale 121
CH0: center 1500us -> count 307
CH0: one side 1200us -> count 246
CH0: center 1500us -> count 307
CH0: other side 1800us -> count 369
CH0: center 1500us -> count 307
Done: channel 0 left at center pulse 1500us.
```

## Notes

- 50Hz gives a 20ms period. 1500us maps to about 307 counts, 1200us to about 246 counts, and 1800us to about 369 counts.
- For unknown mechanical linkages, widen the sweep only after this smoke test succeeds.
