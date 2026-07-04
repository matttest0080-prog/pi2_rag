---
name: raspberry-pi-hardware-control
description: Use when testing or controlling Raspberry Pi-attached hardware over GPIO, I2C, or PWM expanders such as PCA9685. Emphasizes live discovery, safe motion ranges, wiring verification, and leaving hardware in a known state.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [raspberry-pi, gpio, i2c, pwm, pca9685, servo, hardware]
    related_skills: []
---

# Raspberry Pi Hardware Control

## Overview

Use this skill for local Raspberry Pi hardware work: verifying buses, testing sensors and actuators, controlling PWM expanders, and debugging physical wiring. Hardware tasks need real tool output and conservative actuation: discover the live system first, move only within safe bounds, and report exactly what was exercised.

## When to Use

- The user asks to test or control a device connected to Raspberry Pi GPIO, I2C, SPI, UART, or PWM.
- The user gives physical pin wiring, GPIO numbers, I2C addresses, or module names such as PCA9685.
- The task involves servos, LEDs, relays, sensors, motor drivers, or other attached hardware.
- You need to enable an interface, probe a bus, or run a short hardware smoke test.

Don't use for purely software GPIO library design with no attached hardware verification; use a software-development/testing skill instead.

## Operating Principles

1. **Inspect before actuating.** Check identity, groups, kernel, required device nodes, and interface status before sending signals. Completion: you know whether `/dev/i2c-*`, GPIO permissions, or equivalent access paths exist.
2. **Probe the bus.** For I2C devices, run an address scan on the expected bus and identify likely addresses before writing. Completion: scan output shows the target address or the absence is reported as a blocker.
3. **Use conservative motion.** For servos, start at center and test a narrow pulse range before wider sweeps. Completion: the actuator returns to a known safe state.
4. **Prefer direct deterministic scripts.** Small Python scripts using `smbus`/`smbus2` or the relevant local library are better than hand-typing many register writes. Completion: script output records the registers/frequencies/pulses used.
5. **Report physical caveats.** If software succeeds but motion is absent, list likely wiring and power causes without claiming the hardware moved unless the user confirms or a sensor verifies it.

## Raspberry Pi I2C Checklist

Use live commands rather than assumptions:

- `id` confirms membership in groups such as `i2c`, `gpio`, or `spi`.
- `test -e /dev/i2c-1` checks whether the common Raspberry Pi I2C1 bus is present.
- `i2cdetect -y 1` scans the common header bus for devices.
- `raspi-config nonint get_i2c` reports Raspberry Pi I2C enablement; `0` means enabled, `1` means disabled.
- `sudo raspi-config nonint do_i2c 0` enables I2C when the user wants the local machine configured.

Pin reminder for the standard 40-pin Raspberry Pi header:

- Physical pin 3 = GPIO2 = SDA1.
- Physical pin 5 = GPIO3 = SCL1.
- A shared GND is required for reliable signaling.

## PCA9685 Servo Smoke Test

Default PCA9685 addresses commonly observed:

- `0x40`: default PCA9685 device address.
- `0x70`: all-call address; seeing both `0x40` and `0x70` is normal on many boards.

Safe register-level sequence for channel 0:

1. Scan I2C bus 1 and confirm `0x40` appears. Completion: `i2cdetect -y 1` shows `40`.
2. Set PWM frequency to 50Hz. Completion: PCA9685 prescale is written and script prints the chosen prescale.
3. Move the channel through a conservative sequence: 1500us center, 1200us, 1500us, 1800us, 1500us. Completion: script exits successfully and leaves the servo centered.
4. If no motion occurs despite successful I2C writes, check external servo power on V+, common ground, channel number, plug orientation, and servo health.

For two-channel testing, center both channels first, then test CH0 alone, CH1 alone, and both together with opposite directions before returning both to center. This separates channel wiring mistakes from shared power problems.

When the user wants Adafruit's `ServoKit`, install `adafruit-circuitpython-servokit` in a venv on PEP 668 Raspberry Pi OS, run scripts through that venv's Python, and use properly indented loops with a sleep after every commanded angle. Prefer a one-shot `[0, 90, 180, 90]` smoke test before offering an infinite loop.

See `references/pca9685-servo-smoke-test.md` for the exact register-level Python recipe and observed output pattern.
See `references/adafruit-servokit-pca9685.md` for ServoKit setup, corrected loop examples, and multi-channel testing notes.
See `references/pca9685-servokit-session-rag.md` for the RAG-style retrieval notes from the verified local session: wiring, observed I2C scan, ServoKit install path, pulse mapping, and the confirmed 2-minute CH0/CH1 sequence.
Template: `templates/servokit_ch0_smoke_test.py` is a one-shot ServoKit channel-0 smoke test that leaves the servo centered.
Script: `scripts/servokit_ch0_ch1_2min.py` runs the confirmed 120-second CH0/CH1 ServoKit stress test and returns both servos to 90 degrees.
Script: `scripts/pca9685_ch0_ch1_wide.py` is the wider register-level CH0/CH1 test matching ServoKit's approximate 750/1500/2250us range.

## Power and Safety Pitfalls

1. **Powering servos from the Pi.** PCA9685 logic power is not the same as servo power. Multiple or loaded servos usually need an external V+ supply sized for stall current.
2. **No common ground.** External servo supply GND must connect to Raspberry Pi/PCA9685 GND or PWM signals may be meaningless.
3. **Overwide first sweep.** Avoid jumping immediately to 500-2500us or 0-180 degrees. Mechanical linkages can bind.
4. **Assuming software success means physical motion.** I2C writes can succeed even if the servo has no V+ power or the signal wire is on the wrong channel.
5. **Wrong bus after enabling I2C.** Some systems expose unusual buses; always scan the bus connected to the physical header. On standard Raspberry Pi header pins 3/5, this is normally `/dev/i2c-1`.

## Verification Checklist

- [ ] Interface device node exists or enablement action was completed.
- [ ] Target I2C address or GPIO line was discovered live.
- [ ] Test used conservative values and returned hardware to a known state.
- [ ] Script or command output was captured in the final response.
- [ ] Physical power/wiring caveats were stated when software succeeded but motion could not be independently verified.
