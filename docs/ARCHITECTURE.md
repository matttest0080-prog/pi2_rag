# Architecture

## Purpose

`pi2_rag` is a Raspberry Pi 2 hardware knowledge repository. It keeps verified hardware notes, executable experiments, and agent-facing skill material together so a retrieval-capable agent can ground hardware actions in project-specific evidence.

It is intentionally lightweight: the Raspberry Pi 2 should not be expected to host a large local embedding model or heavyweight vector database unless hardware constraints are explicitly revisited.

## Logical layers

```text
[Physical hardware]
 Raspberry Pi 2
  ├─ I2C sensors
  ├─ PCA9685 servo controller
  └─ CSI camera
        │
        ▼
[Experiment scripts]
 skills/.../scripts + templates
        │
        ▼
[Verified knowledge]
 skills/.../references + README
        │
        ▼
[Agent skill]
 skills/.../SKILL.md
        │
        ▼
[Hermes Agent / Hermes Agent IoT]
 retrieval + planning + controlled execution
```

## Hardware layer

Current documented I2C devices share `/dev/i2c-1`:

- PCA9685: `0x40`
- GY-9250 / MPU-9250: `0x68`
- GY-530 / VL53L0X: `0x29`
- PCA9685 all-call: `0x70`

The addresses are observations from one tested setup and should be verified on every deployment.

## Experiment layer

Scripts are direct hardware experiments, not yet a stable public Python API. They validate individual devices and combined behavior before abstractions are introduced.

Current categories include:

- PCA9685 servo motion
- GY-9250 motion/tilt triggers
- VL53L0X distance/object triggers
- combined sensor-to-servo behavior
- CSI camera + OpenCV DNN / YOLOv4-tiny experiments

## Knowledge / RAG layer

The repository name uses "RAG" because the references are designed to be retrievable context for an agent. At present, the repository does not require a specific vector database implementation.

A low-resource deployment should prefer one of these patterns:

1. **File/keyword retrieval on Pi2** — simplest and lowest memory cost.
2. **Remote embedding/vector retrieval** — Pi2 sends text/query metadata to a stronger host.
3. **Hermes-managed retrieval** — Hermes Agent IoT indexes or selects the relevant skill/reference material according to its supported retrieval path.

The project should avoid implying that a local heavyweight embedding stack is required on Raspberry Pi 2.

## Agent integration

The `SKILL.md` file is the agent-facing entry point. It should reference detailed material in `references/` and choose scripts/templates only when hardware state and safety conditions are known.

Recommended decision flow:

```text
user/agent request
      │
      ▼
identify hardware target
      │
      ▼
retrieve matching reference
      │
      ▼
verify I2C/device state
      │
      ▼
select conservative script/template
      │
      ▼
execute and observe
      │
      ▼
record validated result
```

## Safety boundaries

Hardware automation must treat actuator commands as physical side effects. Agent workflows should:

- verify the target device before execution;
- keep default servo motion conservative;
- avoid repeated uncontrolled motion loops;
- require external servo power and common ground;
- return actuators to a neutral state on normal exit when practical;
- surface sensor failures instead of silently substituting fabricated readings.

## Future normalization

A future API layer could separate hardware drivers from behavior logic:

```text
pi2_hw/
  bus.py
  pca9685.py
  mpu9250.py
  vl53l0x.py
  camera.py

behaviors/
  motion_to_servo.py
  distance_to_servo.py
  perception_trigger.py
```

That structure is a roadmap direction only; the current tested scripts remain the source of truth until an abstraction has equivalent hardware validation.
