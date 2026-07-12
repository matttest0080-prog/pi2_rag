# CSI Camera OpenCV YOLOv4-tiny Test Notes

## Confirmed local context

- Host: Raspberry Pi 2 Model B Rev 1.1.
- CSI camera detected by `rpicam-hello --list-cameras` as `ov5647 [2592x1944 10-bit GBRG]`.
- Legacy `vcgencmd get_camera` can report `detected=0`; use `rpicam`/libcamera for this setup.
- System OpenCV was installed with `sudo apt-get install -y python3-opencv` and verified as `cv2 4.10.0`.
- `python3-picamera2` is installed and works for CSI capture.
- Direct `cv2.VideoCapture('/dev/video0')` opened but did not read frames; use Picamera2 arrays, then convert RGB to OpenCV BGR.

## Model assets

The repository intentionally does not include the large YOLO weights or generated videos. Download model assets on the Raspberry Pi before running the scripts:

```bash
mkdir -p /home/pi2/object_detection/models
cd /home/pi2/object_detection/models
curl -L --fail -o coco.names https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names
curl -L --fail -o yolov4-tiny.cfg https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4-tiny.cfg
curl -L --fail -o yolov4-tiny.weights https://github.com/AlexeyAB/darknet/releases/download/yolov4/yolov4-tiny.weights
```

The committed scripts also accept a custom model directory:

```bash
export YOLO_TINY_MODEL_DIR=/path/to/models
```

Required files in that directory:

- `coco.names`
- `yolov4-tiny.cfg`
- `yolov4-tiny.weights`

## One-frame object detection test

Run from the repository root:

```bash
python3 skills/raspberry-pi-hardware-control/scripts/yolo_tiny_csi_detect.py   --input-size 320   --conf 0.20   --out /tmp/yolo_tiny_csi_detect.jpg
```

Confirmed local output pattern:

```text
captured: 640x480
model: YOLOv4-tiny COCO, input=320, conf=0.2
inference_seconds: 10.54
detections: 0
saved: /tmp/yolo_tiny_csi_detect.jpg ok=True
```

Use a lower confidence threshold for weak detections:

```bash
python3 skills/raspberry-pi-hardware-control/scripts/yolo_tiny_csi_detect.py --conf 0.15
```

View the image over the temporary HTTP server:

```bash
python3 -m http.server 8000 --bind 0.0.0.0 --directory /tmp
# Browser: http://<pi-ip>:8000/yolo_tiny_csi_detect.jpg
```

## One-minute annotated video test

Run from the repository root:

```bash
python3 skills/raspberry-pi-hardware-control/scripts/yolo_tiny_csi_video.py   --duration 60   --input-size 224   --conf 0.15   --out /tmp/yolo_tiny_csi_1min.mp4
```

Confirmed local output pattern:

```text
captured_frames: 12
target_duration_seconds: 60.0
average_inference_seconds: 5.21
total_detections_across_frames: 1
saved: /tmp/yolo_tiny_csi_1min.mp4
```

Verified video properties:

```text
codec_name=h264
width=640
height=480
avg_frame_rate=5/1
duration=60.400000
```

View the video over the temporary HTTP server:

```bash
python3 -m http.server 8000 --bind 0.0.0.0 --directory /tmp
# Browser: http://<pi-ip>:8000/yolo_tiny_csi_1min.mp4
```

## Performance expectations on Raspberry Pi 2

- YOLOv4-tiny runs, but not in real time.
- At 640x480 capture and `--input-size 224`, one inference takes about 5.2 seconds.
- The video script samples frames, annotates them, and holds each annotated frame in the final MP4; it is not true 30 FPS live detection.
- For speed, lower `--input-size` to `160` or `224`; for accuracy, try `320` or `416` and expect slower runs.

## COCO object classes and limitations

YOLOv4-tiny COCO recognizes common objects such as `person`, `cup`, `cell phone`, `book`, `chair`, `bottle`, and `scissors`.

It does not reliably recognize electronics-specific objects such as breadboards, PCA9685 boards, GY-9250 modules, VL53L0X boards, jumper wires, resistors, or IC part numbers. For those, use either custom training or OpenCV color/shape rules.

## Verification pattern for script edits

When editing these scripts outside a formal test suite, create a temporary `/tmp/hermes-verify-*.py` script that:

1. Imports the changed script.
2. Confirms model assets exist and COCO labels load.
3. Runs the OpenCV DNN path on a blank synthetic frame with high confidence.
4. Confirms `draw()` changes a synthetic frame.
5. For the video script, monkeypatches `subprocess.run` and checks concat duration math without encoding a real video.
6. Deletes the temporary verification script and any temporary output paths.

Label this as ad-hoc verification, not suite green.
