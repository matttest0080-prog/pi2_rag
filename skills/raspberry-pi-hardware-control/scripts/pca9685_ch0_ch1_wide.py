import time
from smbus2 import SMBus

BUS = 1
ADDR = 0x40
CHANNELS = [0, 1]
MODE1 = 0x00
MODE2 = 0x01
PRESCALE = 0xFE
LED0_ON_L = 0x06
FREQ = 50

bus = SMBus(BUS)

def write(reg, val):
    bus.write_byte_data(ADDR, reg, val & 0xFF)

def read(reg):
    return bus.read_byte_data(ADDR, reg)

def set_pwm_freq(freq_hz):
    prescale = int(round(25000000.0 / (4096 * freq_hz)) - 1)
    oldmode = read(MODE1)
    write(MODE1, (oldmode & 0x7F) | 0x10)
    write(PRESCALE, prescale)
    write(MODE1, oldmode)
    time.sleep(0.005)
    write(MODE1, oldmode | 0xA0)
    return prescale

def set_channel_count(ch, count):
    base = LED0_ON_L + 4 * ch
    bus.write_i2c_block_data(ADDR, base, [0, 0, count & 0xFF, (count >> 8) & 0x0F])

def us_to_count(us):
    return int(round(us * 4096 * FREQ / 1000000.0))

def set_channel_us(ch, us):
    count = us_to_count(us)
    print(f'CH{ch}: {us}us -> count {count}')
    set_channel_count(ch, count)

print('MODE1 before:', hex(read(MODE1)), 'MODE2 before:', hex(read(MODE2)))
write(MODE2, 0x04)
prescale = set_pwm_freq(FREQ)
print(f'Set PWM freq {FREQ}Hz, prescale {prescale}')

print('Center both channels')
for ch in CHANNELS:
    set_channel_us(ch, 1500)
time.sleep(1)

print('Test CH0 wide range')
for us in [750, 1500, 2250, 1500]:
    set_channel_us(0, us)
    time.sleep(1)

print('Test CH1 wide range')
for us in [750, 1500, 2250, 1500]:
    set_channel_us(1, us)
    time.sleep(1)

print('Done: CH0 and CH1 left at 1500us / about 90度')
bus.close()
