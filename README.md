# Pi2 RAG — Raspberry Pi 2 Hardware Control Knowledge Base

> Practical Raspberry Pi 2 hardware-control notes, scripts, and Hermes skill assets for PCA9685 servos, GY-9250 / MPU-9250, VL53L0X distance sensing, and CSI-camera experiments.

This repository is a small, hardware-focused companion project for Raspberry Pi 2 development. It stores verified wiring notes, reusable scripts, and RAG/skill reference material so an AI agent can retrieve concrete setup knowledge instead of relying on generic hardware assumptions.

## What this project is

`pi2_rag` is primarily a **knowledge and experiment repository**, not a standalone vector database or full RAG server. Its current value is the structured hardware knowledge under `skills/raspberry-pi-hardware-control/`, plus scripts that were used to validate the hardware setup.

The intended integration path is:

```text
Raspberry Pi 2 hardware
        │
        ├── PCA9685 servos
        ├── GY-9250 / MPU-9250
        ├── GY-530 / VL53L0X
        └── CSI camera
                │
                ▼
pi2_rag knowledge + scripts
                │
                ▼
Hermes Agent / Hermes Agent IoT
                │
                ▼
retrieval-guided hardware actions
```

For the agent runtime and low-resource IoT packaging, see [`matttest0080-prog/hermes-agent-iot`](https://github.com/matttest0080-prog/hermes-agent-iot).

## Hardware status

| Hardware / interface | Observed status | Notes |
| --- | --- | --- |
| Raspberry Pi 2 I2C bus | ✅ Verified | `/dev/i2c-1` |
| PCA9685 | ✅ Verified | `0x40` |
| GY-9250 / MPU-9250 | ✅ Verified | `0x68`, `WHO_AM_I=0x71` |
| GY-530 / VL53L0X | ✅ Verified | `0x29` |
| PCA9685 all-call | ℹ️ Present | `0x70` |
| PCA9685 servo channel 0/1 | ✅ Tested | ServoKit + register-level scripts |
| GY-9250 → servo trigger | ✅ Tested | horizontal/tilt mapping |
| VL53L0X → servo trigger | ✅ Tested | distance/object-change mapping |
| Combined VL53L0X + GY-9250 + PCA9685 | ✅ Tested | integration script included |
| CSI camera + YOLOv4-tiny | 🧪 Experimental | OpenCV DNN scripts included |

## Wiring reference

All listed I2C devices share the Raspberry Pi 2 I2C bus:

| Raspberry Pi 2 | Function | Connected devices |
| --- | --- | --- |
| Physical pin 3 / GPIO2 | SDA1 | PCA9685, GY-9250, VL53L0X |
| Physical pin 5 / GPIO3 | SCL1 | PCA9685, GY-9250, VL53L0X |
| GND | Common ground | Pi, sensors, PCA9685 logic and servo supply ground |

**Servo power must come from a suitable external V+ supply.** Do not power multiple servos from the Raspberry Pi 5 V rail. The Raspberry Pi, PCA9685 logic, and servo supply must share a common ground.

## Repository layout

```text
pi2_rag/
├── README.md
├── requirements-pi2.txt
├── docs/
│   └── ARCHITECTURE.md
└── skills/
    └── raspberry-pi-hardware-control/
        ├── SKILL.md
        ├── references/
        ├── scripts/
        └── templates/
```

The skill directory contains the agent-facing instructions, detailed reference notes, executable experiments, and reusable templates.

## Minimal Raspberry Pi 2 environment

Create a dedicated virtual environment:

```bash
python3 -m venv ~/pca9685-venv
source ~/pca9685-venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-pi2.txt
```

The minimal dependency file covers the current ServoKit/I2C baseline. CSI-camera and YOLO experiments may require additional system packages such as Picamera2 and OpenCV that are normally installed through Raspberry Pi OS packages rather than forcing them into the small Pi2 Python environment.

## Quick hardware tests

### PCA9685 channel 0 smoke test

```bash
~/pca9685-venv/bin/python \
  skills/raspberry-pi-hardware-control/templates/servokit_ch0_smoke_test.py
```

### PCA9685 channel 0 + 1 sustained test

```bash
~/pca9685-venv/bin/python \
  skills/raspberry-pi-hardware-control/scripts/servokit_ch0_ch1_2min.py
```

### GY-9250 motion / tilt → servo

```bash
~/pca9685-venv/bin/python \
  skills/raspberry-pi-hardware-control/scripts/gy9250_two_channel_servo_trigger.py \
  --seconds 60 --threshold 0.08 --tilt-threshold 12
```

### VL53L0X object detection → servo

```bash
~/pca9685-venv/bin/python \
  skills/raspberry-pi-hardware-control/scripts/vl53l0x_servo_ch0_object_1min.py
```

### VL53L0X distance change → servo

```bash
~/pca9685-venv/bin/python \
  skills/raspberry-pi-hardware-control/scripts/vl53l0x_servo_ch0_change_1min.py
```

### Combined sensor + servo integration

```bash
~/pca9685-venv/bin/python \
  skills/raspberry-pi-hardware-control/scripts/all_integration_vl53_gy9250_pca9685.py
```

The integration script performs conservative servo motion, reads VL53L0X and GY-9250 data together, maps distance/horizontal movement to channel 0 and tilt to channel 1, then returns the servos to 90° when exiting.

## CSI camera experiments

Single-frame YOLOv4-tiny test:

```bash
python3 skills/raspberry-pi-hardware-control/scripts/yolo_tiny_csi_detect.py \
  --input-size 320 --conf 0.20 --out /tmp/yolo_tiny_csi_detect.jpg
```

One-minute annotated-video test:

```bash
python3 skills/raspberry-pi-hardware-control/scripts/yolo_tiny_csi_video.py \
  --duration 60 --input-size 224 --conf 0.15 \
  --out /tmp/yolo_tiny_csi_1min.mp4
```

Model weights and generated images/videos should stay outside the repository. See `skills/raspberry-pi-hardware-control/references/csi-camera-opencv-yolo-tiny.md` for the experiment notes.

## Servo calibration note

Observed ServoKit pulse mapping on this setup:

```text
0°   ≈ 747 µs
90°  ≈ 1499 µs
180° ≈ 2251 µs
```

A narrow manual range such as `1200 → 1500 → 1800 µs` can appear to produce little movement. The wider `750 → 1500 → 2250 µs` range better matches the visible ServoKit 0/90/180° test on this hardware.

## Safety and operating limits

- Test one actuator at a time before running combined scripts.
- Use an external servo power supply sized for stall current.
- Always share ground between the Pi, PCA9685, sensors, and actuator supply.
- Keep servo travel conservative until mechanical limits are known.
- Stop a script immediately if a servo stalls, chatters continuously, overheats, or drives into a hard stop.
- Verify I2C addresses with `i2cdetect -y 1` before assuming the documented address matches another board revision.

## Project direction

- [x] PCA9685 servo smoke tests
- [x] Two-channel servo tests
- [x] GY-9250 motion/tilt trigger
- [x] VL53L0X distance trigger
- [x] Combined VL53L0X + GY-9250 + PCA9685 experiment
- [x] CSI camera + YOLOv4-tiny experiment notes
- [ ] Normalize sensor/actuator APIs
- [ ] Add machine-readable hardware inventory
- [ ] Add repeatable test fixtures
- [ ] Add Hermes Agent IoT retrieval examples
- [ ] Add multi-VL53L0X address/XSHUT workflow
- [ ] Add ADS1115 and additional I2C device references

## Related project

- [Hermes Agent IoT](https://github.com/matttest0080-prog/hermes-agent-iot) — low-resource Hermes Agent fork for Raspberry Pi 2 / ARMv7, MQTT, Home Assistant, robotics and edge-agent deployment.

## License

No explicit open-source license is currently declared for this repository. Until a license is added, GitHub users can view and fork the public repository under GitHub's platform terms, but reuse/redistribution rights are not being granted here by an explicit software license.
