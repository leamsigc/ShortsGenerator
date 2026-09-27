import os
import subprocess
import numpy as np
from typing import Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class FaceBox:
    x: float
    y: float
    width: float
    height: float
    confidence: float


class FaceDetector:
    """
    Face detection for smart vertical video cropping.
    Uses MediaPipe or OpenCV Haar Cascades as fallback.
    """

    def __init__(self):
        self._detector = None
        self._init_detector()

    def _init_detector(self):
        try:
            from mediapipe.tasks.python.vision import FaceDetector, FaceDetectorOptions, RunningMode
            options = FaceDetectorOptions(
                running_mode=RunningMode.IMAGE,
                num_faces=1,
                min_detection_confidence=0.5,
            )
            self._detector = ("mediapipe", options)
        except ImportError:
            try:
                import cv2
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                if os.path.exists(cascade_path):
                    self._detector = ("opencv", cascade_path)
                else:
                    self._detector = ("none", None)
            except ImportError:
                self._detector = ("none", None)

    def detect_face_frame(self, frame) -> Optional[FaceBox]:
        """
        Detect face in a single frame (numpy array BGR).
        Returns normalized coordinates (0-1) or None if no face found.
        """
        if self._detector is None or self._detector[0] == "none":
            return None

        detector_type, detector_info = self._detector

        if detector_type == "mediapipe":
            try:
                from mediapipe.tasks.python.vision import FaceDetector
                from mediapipe.python import Image as MpImage

                mp_image = MpImage.from_array(frame)
                detector = FaceDetector.create_from_options(detector_info)
                result = detector.detect(mp_image)

                if result.detections:
                    detection = result.detections[0]
                    bbox = detection.bounding_box
                    h, w = frame.shape[:2]

                    x = bbox.origin_x / w
                    y = bbox.origin_y / h
                    width = bbox.width / w
                    height = bbox.height / h

                    return FaceBox(
                        x=x + width / 2,
                        y=y + height / 2,
                        width=width,
                        height=height,
                        confidence=detection.categories[0].score if detection.categories else 0.5
                    )
            except Exception:
                pass

        elif detector_type == "opencv":
            try:
                import cv2
                cascade = cv2.CascadeClassifier(detector_info)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = cascade.detectMultiScale(gray, 1.1, 4)

                if len(faces) > 0:
                    face = max(faces, key=lambda f: f[2] * f[3])
                    h, w = frame.shape[:2]
                    x, y, fw, fh = face
                    return FaceBox(
                        x=(x + fw / 2) / w,
                        y=(y + fh / 2) / h,
                        width=fw / w,
                        height=fh / h,
                        confidence=0.5
                    )
            except Exception:
                pass

        return None

    def detect_face_video(self, video_path: str, sample_times: List[float] = None) -> Optional[Tuple[float, float]]:
        """
        Detect face in video by sampling frames.
        Returns (face_x, face_y) normalized 0-1 or None.
        """
        if sample_times is None:
            sample_times = [0.0, 0.25, 0.5, 0.75, 1.0]

        import cv2
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            return None

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0.0

        face_votes_x = []
        face_votes_y = []
        face_confidences = []

        for t in sample_times:
            frame_time = min(t * duration, duration - 0.1) if duration > 0 else t
            frame_idx = int(frame_time * fps)

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()

            if not ret:
                continue

            face_box = self.detect_face_frame(frame)
            if face_box and face_box.confidence > 0.4:
                face_votes_x.append(face_box.x)
                face_votes_y.append(face_box.y)
                face_confidences.append(face_box.confidence)

        cap.release()

        if not face_votes_x:
            return None

        if len(face_votes_x) == 1:
            return (face_votes_x[0], face_votes_y[0])

        confidences = np.array(face_confidences)
        weights = confidences / confidences.sum()
        avg_x = np.average(face_votes_x, weights=weights)
        avg_y = np.average(face_votes_y, weights=weights)

        return (float(avg_x), float(avg_y))

    def get_face_for_segment(
        self,
        video_path: str,
        start_time: float,
        end_time: float
    ) -> Tuple[float, float]:
        """
        Get best face position for a video segment.
        Samples 4 frames evenly through the segment.
        Returns (face_x, face_y) normalized 0-1.
        """
        duration = end_time - start_time
        if duration <= 0:
            return (0.5, 0.35)

        sample_times = [0.1, 0.35, 0.65, 0.9]

        face_coords = self.detect_face_video(video_path, sample_times)

        if face_coords is None:
            return (0.5, 0.35)

        return face_coords


def smart_crop_coordinates(
    face_x: float,
    face_y: float,
    source_w: int,
    source_h: int,
    target_w: int,
    target_h: int
) -> Tuple[int, int, int, int]:
    """
    Calculate crop window for face-centered vertical (9:16) output.
    Returns (x, y, crop_w, crop_h) in source frame pixels.
    """
    source_ratio = source_w / source_h
    target_ratio = target_w / target_h

    if source_ratio > target_ratio:
        crop_h = source_h
        crop_w = int(source_h * target_ratio)
        x = int(face_x * source_w - crop_w / 2)
        y = 0
        x = max(0, min(x, source_w - crop_w))
    else:
        crop_w = source_w
        crop_h = int(source_w / target_ratio)
        x = 0
        y = int(face_y * source_h - crop_h / 2)
        y = max(0, min(y, source_h - crop_h))

    return (x, y, crop_w, crop_h)


def get_video_dimensions(video_path: str) -> Tuple[int, int]:
    """Get video dimensions using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0",
        video_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            parts = result.stdout.strip().split("x")
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
    except Exception:
        pass
    return 1920, 1080
