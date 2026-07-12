#!/usr/bin/env python3
"""Record a sampled one-minute CSI camera video with YOLOv4-tiny annotations."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
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


def load_net():
    net = cv2.dnn.readNetFromDarknet(str(DEFAULT_CFG), str(DEFAULT_WEIGHTS))
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    return net, net.getUnconnectedOutLayersNames(), load_names(DEFAULT_NAMES)


def detect(net, output_names, names, frame: np.ndarray, conf: float, nms: float, size: int):
    h, w = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (size, size), swapRB=True, crop=False)
    net.setInput(blob)
    start = time.time()
    outputs = net.forward(output_names)
    elapsed = time.time() - start

    boxes: list[list[int]] = []
    scores_out: list[float] = []
    class_ids: list[int] = []
    for output in outputs:
        for raw in output:
            scores = raw[5:]
            class_id = int(np.argmax(scores))
            score = float(scores[class_id])
            if score >= conf:
                cx, cy, bw, bh = raw[:4] * np.array([w, h, w, h])
                boxes.append([int(cx - bw / 2), int(cy - bh / 2), int(bw), int(bh)])
                scores_out.append(score)
                class_ids.append(class_id)

    picked = cv2.dnn.NMSBoxes(boxes, scores_out, conf, nms)
    results = []
    if len(picked) > 0:
        for i in np.array(picked).flatten():
            x, y, bw, bh = boxes[i]
            label = names[class_ids[i]] if class_ids[i] < len(names) else str(class_ids[i])
            results.append((label, scores_out[i], x, y, bw, bh))
    return results, elapsed


def draw(frame: np.ndarray, results, elapsed: float, t_rel: float) -> np.ndarray:
    out = frame.copy()
    for label, score, x, y, w, h in results:
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(out.shape[1] - 1, x + w), min(out.shape[0] - 1, y + h)
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(out, f"{label} {score:.2f}", (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

    status = f"t={t_rel:05.1f}s detections={len(results)} infer={elapsed:.2f}s"
    cv2.rectangle(out, (0, 0), (out.shape[1], 28), (0, 0, 0), -1)
    cv2.putText(out, status, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    return out


def camera(width: int, height: int):
    picam2 = Picamera2()
    config = picam2.create_video_configuration(main={"size": (width, height), "format": "RGB888"})
    picam2.configure(config)
    return picam2


def encode_concat(frames: list[Path], times: list[float], duration: float, out: Path, workdir: Path, fps: int) -> None:
    concat = workdir / "concat.txt"
    lines: list[str] = []
    for i, frame in enumerate(frames):
        next_t = times[i + 1] if i + 1 < len(times) else duration
        dur = max(0.1, next_t - times[i])
        lines += [f"file '{frame}'", f"duration {dur:.3f}"]
    lines.append(f"file '{frames[-1]}'")
    concat.write_text("\n".join(lines) + "\n")

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat),
        "-vf", f"fps={fps},format=yuv420p", "-movflags", "+faststart", str(out),
    ]
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--warmup", type=float, default=1.0)
    parser.add_argument("--conf", type=float, default=0.20)
    parser.add_argument("--nms", type=float, default=0.40)
    parser.add_argument("--input-size", type=int, default=224)
    parser.add_argument("--fps", type=int, default=5, help="encoded playback FPS; sampled frames are held between captures")
    parser.add_argument("--out", type=Path, default=Path("/tmp/yolo_tiny_csi_1min.mp4"))
    parser.add_argument("--keep-frames", action="store_true")
    args = parser.parse_args()

    for path in (DEFAULT_CFG, DEFAULT_WEIGHTS, DEFAULT_NAMES):
        if not path.exists():
            raise FileNotFoundError(path)
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required to encode the video")

    net, output_names, names = load_net()
    workdir = Path(tempfile.mkdtemp(prefix="yolo-csi-video-", dir="/tmp"))
    frames: list[Path] = []
    times: list[float] = []
    total_detections = 0
    infer_times: list[float] = []

    picam2 = camera(args.width, args.height)
    picam2.start()
    try:
        time.sleep(args.warmup)
        start = time.time()
        idx = 0
        while True:
            capture_t = time.time() - start
            if capture_t >= args.duration and frames:
                break
            rgb = picam2.capture_array()
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            results, infer_elapsed = detect(net, output_names, names, bgr, args.conf, args.nms, args.input_size)
            done_t = min(time.time() - start, args.duration)
            annotated = draw(bgr, results, infer_elapsed, done_t)
            frame_path = workdir / f"frame_{idx:04d}.jpg"
            if not cv2.imwrite(str(frame_path), annotated):
                raise RuntimeError(f"failed to write {frame_path}")
            frames.append(frame_path)
            times.append(min(capture_t, args.duration))
            total_detections += len(results)
            infer_times.append(infer_elapsed)
            print(f"frame={idx} capture_t={capture_t:.1f}s done_t={done_t:.1f}s infer={infer_elapsed:.2f}s detections={len(results)}")
            idx += 1
    finally:
        picam2.stop()

    if not frames:
        raise RuntimeError("no frames captured")
    encode_concat(frames, times, args.duration, args.out, workdir, args.fps)

    avg = sum(infer_times) / len(infer_times)
    print(f"captured_frames: {len(frames)}")
    print(f"target_duration_seconds: {args.duration:.1f}")
    print(f"average_inference_seconds: {avg:.2f}")
    print(f"total_detections_across_frames: {total_detections}")
    print(f"saved: {args.out}")

    if args.keep_frames:
        print(f"kept_frames_dir: {workdir}")
    else:
        shutil.rmtree(workdir, ignore_errors=True)
        print(f"cleaned_frames_dir: {workdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
