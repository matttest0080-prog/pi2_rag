---
name: raspberry-pi-hardware-control
description: Use when testing or controlling Raspberry Pi-attached hardware over GPIO, I2C, PWM expanders, or CSI camera capture such as PCA9685 servos, sensors, Picamera2/OpenCV, and YOLOv4-tiny object detection tests. Emphasizes live discovery, safe motion ranges, wiring verification, and leaving hardware in a known state.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [raspberry-pi, gpio, i2c, pwm, pca9685, servo, hardware, gy9250, mpu9250, imu, vl53l0x, tof, csi-camera, opencv, picamera2, yolo]
    related_skills: []
---

# Raspberry Pi Hardware Control

## Overview

Use this skill for local Raspberry Pi hardware work: verifying buses, testing sensors and actuators, controlling PWM expanders, and debugging physical wiring. Hardware tasks need real tool output and conservative actuation: discover the live system first, move only within safe bounds, and report exactly what was exercised.

## When to Use

- The user asks to test or control a device connected to Raspberry Pi GPIO, I2C, SPI, UART, PWM, or CSI camera.
- The user gives physical pin wiring, GPIO numbers, I2C addresses, camera modules, or module names such as PCA9685, GY-9250, MPU-9250, GY-530, VL53L0X, OV5647, Picamera2, OpenCV, or YOLO.
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
See `references/gy9250-two-channel-servo-rag.md` for GY-9250 horizontal-vs-tilt two-channel servo notes and verification pattern.
See `references/vl53l0x-distance-servo-rag.md` for VL53L0X object-present and distance-change channel 0 trigger notes and verified one-minute outputs.
See `references/csi-camera-opencv-yolo-tiny.md` for CSI camera detection, OpenCV/Picamera2 setup, YOLOv4-tiny model download commands, image/video viewing instructions, and ad-hoc verification patterns.
Template: `templates/servokit_ch0_smoke_test.py` is a one-shot ServoKit channel-0 smoke test that leaves the servo centered.
Script: `scripts/servokit_ch0_ch1_2min.py` runs the confirmed 120-second CH0/CH1 ServoKit stress test and returns both servos to 90 degrees.
Script: `scripts/pca9685_ch0_ch1_wide.py` is the wider register-level CH0/CH1 test matching ServoKit's approximate 750/1500/2250us range.
Script: `scripts/vl53l0x_servo_ch0_object_1min.py` sweeps channel 0 while a VL53L0X object is within range and returns to center when no object is detected.
Script: `scripts/vl53l0x_servo_ch0_change_1min.py` moves channel 0 only when VL53L0X distance changes by a threshold, then recenters during stable readings.
Script: `scripts/yolo_tiny_csi_detect.py` captures one CSI camera frame, runs YOLOv4-tiny COCO through OpenCV DNN, and writes an annotated JPEG under `/tmp`.
Script: `scripts/yolo_tiny_csi_video.py` captures sampled CSI camera frames for a bounded duration, runs YOLOv4-tiny annotations, and encodes an MP4 under `/tmp` without storing video in the repo.


## GY-9250 / MPU-9250 Servo Trigger Pattern

Confirmed local GY-9250 context:

- Physical pin 3 / GPIO2 / SDA1 -> GY-9250 SDA.
- Physical pin 5 / GPIO3 / SCL1 -> GY-9250 SCL.
- Bus 1 address `0x68`; `WHO_AM_I=0x71`.
- Use `/home/pi2/pca9685-venv/bin/python`; that venv has ServoKit and `smbus2`.

For sensor-triggered servos, wake the MPU (`PWR_MGMT_1` register `0x6B = 0x01`), average a one-second still accelerometer baseline, then classify motion:

- Horizontal / XY movement: `sqrt((x-baseline_x)^2 + (y-baseline_y)^2)` in g; start at `0.08g`, lower to `0.03g` for sensitive tests. Map this to PCA9685 channel 0.
- Tilt / orientation: angle between current acceleration vector and baseline gravity vector; start at `12 deg`, lower to `8 deg` for sensitive tests. Map this to PCA9685 channel 1.

Use conservative angles 60/90/120 degrees, add per-channel cooldowns, and recenter all touched servos in `finally`.

Run the reusable script:

```bash
/home/pi2/pca9685-venv/bin/python skills/raspberry-pi-hardware-control/scripts/gy9250_two_channel_servo_trigger.py --seconds 60 --threshold 0.08 --tilt-threshold 12
```

See `references/gy9250-two-channel-servo-rag.md` for RAG notes and verification pattern.
Script: `scripts/gy9250_two_channel_servo_trigger.py` maps horizontal motion to channel 0 and tilt to channel 1.

## VL53L0X / GY-530 Distance Servo Trigger Pattern

Confirmed local VL53L0X context:

- Physical pin 3 / GPIO2 / SDA1 -> VL53L0X SDA.
- Physical pin 5 / GPIO3 / SCL1 -> VL53L0X SCL.
- Bus 1 address `0x29`; PCA9685 is on the same bus at `0x40`.
- Use `/home/pi2/pca9685-venv/bin/python`; that venv has ServoKit and Adafruit VL53L0X libraries.

For object-present triggering, treat finite readings from 20 mm through `DETECT_MM` as an object and sweep channel 0 between 60/120 degrees while present. For change-only triggering, compare each valid reading with the previous valid reading and move channel 0 only when `abs(delta) >= CHANGE_MM`; use 50 mm as the known-good default to avoid jitter-triggered motion.

Run the reusable scripts:

```bash
/home/pi2/pca9685-venv/bin/python skills/raspberry-pi-hardware-control/scripts/vl53l0x_servo_ch0_object_1min.py
/home/pi2/pca9685-venv/bin/python skills/raspberry-pi-hardware-control/scripts/vl53l0x_servo_ch0_change_1min.py
```

Both scripts run for 60 seconds by default, keep motion conservative at 60/90/120 degrees, expose tuning through environment variables, and return channel 0 to 90 degrees in `finally`.

For full integration, run `scripts/all_integration_vl53_gy9250_pca9685.py`. It performs a conservative CH0/CH1 smoke motion, reads VL53L0X and GY-9250 together for 60 seconds, maps VL53L0X distance changes plus GY-9250 horizontal motion to channel 0, maps GY-9250 tilt to channel 1, and recenters both servos on exit.

See `references/vl53l0x-distance-servo-rag.md` for RAG notes, verified outputs, and tuning knobs.

## CSI Camera OpenCV / YOLOv4-tiny Pattern

Confirmed local CSI camera context:

- Raspberry Pi 2 Model B Rev 1.1 with OV5647 CSI camera detected by `rpicam-hello --list-cameras`.
- `python3-opencv` is installed from apt and verified as OpenCV 4.10.0.
- `python3-picamera2` is installed and is the preferred capture path; direct `cv2.VideoCapture('/dev/video0')` can open but fail to read frames.
- YOLO model files live outside this repo under `/home/pi2/object_detection/models` by default, or can be provided with `YOLO_TINY_MODEL_DIR`.

Download model assets before running object detection:

```bash
mkdir -p /home/pi2/object_detection/models
cd /home/pi2/object_detection/models
curl -L --fail -o coco.names https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names
curl -L --fail -o yolov4-tiny.cfg https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4-tiny.cfg
curl -L --fail -o yolov4-tiny.weights https://github.com/AlexeyAB/darknet/releases/download/yolov4/yolov4-tiny.weights
```

Run one-frame detection:

```bash
python3 skills/raspberry-pi-hardware-control/scripts/yolo_tiny_csi_detect.py --input-size 320 --conf 0.20 --out /tmp/yolo_tiny_csi_detect.jpg
```

Run a one-minute sampled annotated video:

```bash
python3 skills/raspberry-pi-hardware-control/scripts/yolo_tiny_csi_video.py --duration 60 --input-size 224 --conf 0.15 --out /tmp/yolo_tiny_csi_1min.mp4
```

On Raspberry Pi 2, expect sampled/non-realtime detection: local YOLOv4-tiny inference took about 5.2 seconds per sampled frame at `--input-size 224`. Serve outputs from `/tmp` with `python3 -m http.server 8000 --bind 0.0.0.0 --directory /tmp` and view `http://<pi-ip>:8000/yolo_tiny_csi_detect.jpg` or `http://<pi-ip>:8000/yolo_tiny_csi_1min.mp4`.

See `references/csi-camera-opencv-yolo-tiny.md` for confirmed outputs, model limitations, and ad-hoc verification steps.

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
