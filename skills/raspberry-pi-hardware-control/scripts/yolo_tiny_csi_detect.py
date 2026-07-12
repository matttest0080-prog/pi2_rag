#!/usr/bin/env python3
"""Capture one frame from Raspberry Pi CSI camera and run YOLOv4-tiny via OpenCV DNN."""
from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import cv2
import numpy as np
from picamera2 import Picamera2

ROOT = Path(__file__).resolve().parent
MODEL_DIR = Path(os.environ.get("YOLO_TINY_MODEL_DIR", ROOT / "models"))
if not MODEL_DIR.exists() and Path("/home/pi2/object_detection/models").exists():
    MODEL_DIR = Path("/home/pi2/object_detection/models")

DEFAULT_CFG = MODEL_DIR / "yolov4-tiny.cfg"
DEFAULT_WEIGHTS = MODEL_DIR / "yolov4-tiny.weights"
DEFAULT_NAMES = MODEL_DIR / "coco.names"


def load_names(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def capture_frame(width: int, height: int, warmup: float) -> np.ndarray:
    picam2 = Picamera2()
    config = picam2.create_still_configuration(main={"size": (width, height), "format": "RGB888"})
    picam2.configure(config)
    picam2.start()
    try:
        time.sleep(warmup)
        rgb = picam2.capture_array()
    finally:
        picam2.stop()
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def detect(frame: np.ndarray, conf_threshold: float, nms_threshold: float, input_size: int):
    names = load_names(DEFAULT_NAMES)
    net = cv2.dnn.readNetFromDarknet(str(DEFAULT_CFG), str(DEFAULT_WEIGHTS))
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

    h, w = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (input_size, input_size), swapRB=True, crop=False)
    net.setInput(blob)
    output_names = net.getUnconnectedOutLayersNames()
    start = time.time()
    outputs = net.forward(output_names)
    elapsed = time.time() - start

    boxes = []
    confidences = []
    class_ids = []
    for output in outputs:
        for det in output:
            scores = det[5:]
            class_id = int(np.argmax(scores))
            confidence = float(scores[class_id])
            if confidence >= conf_threshold:
                cx, cy, bw, bh = det[:4] * np.array([w, h, w, h])
                x = int(cx - bw / 2)
                y = int(cy - bh / 2)
                boxes.append([x, y, int(bw), int(bh)])
                confidences.append(confidence)
                class_ids.append(class_id)

    idxs = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)
    results = []
    if len(idxs) > 0:
        for i in np.array(idxs).flatten():
            x, y, bw, bh = boxes[i]
            label = names[class_ids[i]] if class_ids[i] < len(names) else str(class_ids[i])
            results.append((label, confidences[i], x, y, bw, bh))
    return results, elapsed


def draw(frame: np.ndarray, results) -> np.ndarray:
    out = frame.copy()
    for label, conf, x, y, w, h in results:
        cv2.rectangle(out, (x, y), (x + w, y + h), (0, 255, 0), 2)
        text = f"{label} {conf:.2f}"
        cv2.putText(out, text, (max(0, x), max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--warmup", type=float, default=1.0)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--nms", type=float, default=0.40)
    parser.add_argument("--input-size", type=int, default=320, help="Use 320 for speed, 416 for accuracy")
    parser.add_argument("--out", default="/tmp/yolo_tiny_csi_detect.jpg")
    args = parser.parse_args()

    for p in (DEFAULT_CFG, DEFAULT_WEIGHTS, DEFAULT_NAMES):
        if not p.exists():
            raise FileNotFoundError(p)

    frame = capture_frame(args.width, args.height, args.warmup)
    results, elapsed = detect(frame, args.conf, args.nms, args.input_size)
    annotated = draw(frame, results)
    ok = cv2.imwrite(args.out, annotated)

    print(f"captured: {frame.shape[1]}x{frame.shape[0]}")
    print(f"model: YOLOv4-tiny COCO, input={args.input_size}, conf={args.conf}")
    print(f"inference_seconds: {elapsed:.2f}")
    print(f"detections: {len(results)}")
    for label, conf, x, y, w, h in results:
        print(f"- {label}: {conf:.2f} box=({x},{y},{w},{h})")
    print(f"saved: {args.out} ok={ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
