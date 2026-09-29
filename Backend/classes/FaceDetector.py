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

    def detect_faces_at_times(
        self,
        video_path: str,
        abs_times: List[float],
    ) -> List[Optional["FaceBox"]]:
        """Detect faces at absolute timestamps (seconds) in the video.

        Unlike detect_face_video (fraction-of-duration sampling), this samples
        exactly the moments asked for — required for segment tracking where
        the clip is a slice of a much longer source.
        """
        try:
            import cv2
        except ImportError:
            return [None] * len(abs_times)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return [None] * len(abs_times)

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        results: List[Optional["FaceBox"]] = []
        try:
            for t in abs_times:
                cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000.0)
                ret, frame = cap.read()
                if not ret or frame is None:
                    # Fallback: try frame-index seeking once
                    try:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, int(max(0.0, t) * fps))
                        ret, frame = cap.read()
                    except Exception:
                        ret, frame = False, None
                if not ret or frame is None:
                    results.append(None)
                    continue
                try:
                    results.append(self.detect_face_frame(frame))
                except Exception:
                    results.append(None)
        finally:
            cap.release()
        return results

    def get_face_track(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        n_samples: int = 6,
    ) -> List[Tuple[float, float, float, bool]]:
        """Sample face positions across a clip segment for tracking.

        Returns a list of (rel_t, face_x, face_y, found) with rel_t measured
        from the clip start (0..duration). Missing faces are filled with the
        nearest found neighbor (forward-fill then backward-fill) and smoothed
        with a moving average so the crop pans instead of jumping. When no
        face is found in any sample, all entries carry found=False and the
        upper-third fallback position (0.5, 0.35).
        """
        duration = end_time - start_time
        if duration <= 0 or not video_path:
            return [(0.0, 0.5, 0.35, False)]

        n_samples = max(3, min(8, n_samples))
        # Evenly spaced, inset from the edges (avoid transition frames).
        fracs = [0.05 + 0.9 * i / max(1, n_samples - 1) for i in range(n_samples)]
        abs_times = [start_time + f * duration for f in fracs]
        rel_times = [f * duration for f in fracs]

        try:
            boxes = self.detect_faces_at_times(video_path, abs_times)
        except Exception:
            boxes = [None] * n_samples

        xs: List[float] = []
        ys: List[float] = []
        found: List[bool] = []
        for box in boxes:
            if box is not None:
                xs.append(float(box.x))
                ys.append(float(box.y))
                found.append(True)
            else:
                xs.append(0.5)
                ys.append(0.35)
                found.append(False)

        if not any(found):
            return [(rt, 0.5, 0.35, False) for rt in rel_times]

        # Fill gaps: forward-fill from last known, then backward-fill leading gap.
        last_x, last_y = 0.5, 0.35
        for i in range(len(xs)):
            if found[i]:
                last_x, last_y = xs[i], ys[i]
            else:
                xs[i], ys[i] = last_x, last_y
        next_x, next_y = xs[-1], ys[-1]
        for i in range(len(xs) - 1, -1, -1):
            if found[i]:
                next_x, next_y = xs[i], ys[i]
            else:
                xs[i], ys[i] = next_x, next_y

        # Moving-average smoothing (window 3) to avoid jittery pans.
        sm_x = list(xs)
        sm_y = list(ys)
        for i in range(len(xs)):
            lo = max(0, i - 1)
            hi = min(len(xs), i + 2)
            sm_x[i] = sum(xs[lo:hi]) / (hi - lo)
            sm_y[i] = sum(ys[lo:hi]) / (hi - lo)

        return [(rel_times[i], sm_x[i], sm_y[i], True) for i in range(len(xs))]

    def get_face_for_segment(
        self,
        video_path: str,
        start_time: float,
        end_time: float
    ) -> Tuple[float, float]:
        """
        Get best face position for a video segment.
        Samples frames evenly *inside the segment* (absolute timestamps) and
        returns the confidence-weighted average. Falls back to upper-third
        composition (0.5, 0.35) when no face is found.
        """
        duration = end_time - start_time
        if duration <= 0 or not video_path:
            return (0.5, 0.35)

        track = self.get_face_track(video_path, start_time, end_time, n_samples=4)
        found_pts = [(x, y) for (_, x, y, f) in track if f]
        if not found_pts:
            return (0.5, 0.35)
        avg_x = sum(p[0] for p in found_pts) / len(found_pts)
        avg_y = sum(p[1] for p in found_pts) / len(found_pts)
        return (float(avg_x), float(avg_y))


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


def build_tracking_crop_filter(
    face_track: List[Tuple[float, float, float, bool]],
    source_w: int,
    source_h: int,
    target_w: int,
    target_h: int,
    clip_duration: float,
) -> Tuple[str, int, int, int, int]:
    """Build an ffmpeg crop filter that pans to follow the detected face.

    Returns (crop_filter, crop_w, crop_h, static_x, static_y) where
    static_x/y is the fallback position (track average) used when the track
    has no faces. When faces were found, the filter's x (landscape sources)
    or y (portrait sources) is a time-interpolated ffmpeg expression over the
    clip-relative clock `t`, so the 9:16 window glides with the speaker
    instead of sitting on one static crop.

    The expression uses single-quoted if()/lt() nesting — commas inside the
    quotes are preserved by ffmpeg's filter parser (standard pattern:
    x='if(lt(t,5),0,100)').
    """
    # Static geometry first (same math as smart_crop_coordinates).
    source_ratio = source_w / source_h if source_h else 1.0
    target_ratio = target_w / target_h if target_h else 9 / 16
    if source_ratio > target_ratio:
        crop_h = source_h
        crop_w = int(source_h * target_ratio)
    else:
        crop_w = source_w
        crop_h = int(source_w / target_ratio) if target_ratio else source_h

    found_pts = [(rt, fx, fy) for (rt, fx, fy, f) in face_track if f]
    if not found_pts or clip_duration <= 0:
        # No face to track — static upper-third fallback.
        fx, fy = 0.5, 0.35
        if source_ratio > target_ratio:
            sx = int(max(0, min(fx * source_w - crop_w / 2, source_w - crop_w)))
            return (f"crop={crop_w}:{crop_h}:{sx}:0", crop_w, crop_h, sx, 0)
        sy = int(max(0, min(fy * source_h - crop_h / 2, source_h - crop_h)))
        return (f"crop={crop_w}:{crop_h}:0:{sy}", crop_w, crop_h, 0, sy)

    def _clamp_x(fx: float) -> int:
        return int(max(0, min(fx * source_w - crop_w / 2, max(0, source_w - crop_w))))

    def _clamp_y(fy: float) -> int:
        return int(max(0, min(fy * source_h - crop_h / 2, max(0, source_h - crop_h))))

    if source_ratio > target_ratio:
        # Horizontal tracking: y stays 0, x interpolates between samples.
        pts = sorted(found_pts, key=lambda p: p[0])
        xs = [_clamp_x(fx) for (_, fx, _) in pts]
        ts = [max(0.0, min(rt, clip_duration)) for (rt, _, _) in pts]
        # Deduplicate identical timestamps.
        dedup_ts: List[float] = []
        dedup_xs: List[int] = []
        for t, x in zip(ts, xs):
            if dedup_ts and abs(t - dedup_ts[-1]) < 0.05:
                dedup_xs[-1] = int((dedup_xs[-1] + x) / 2)
                continue
            dedup_ts.append(t)
            dedup_xs.append(x)
        ts, xs = dedup_ts, dedup_xs
        if len(xs) == 1 or max(xs) - min(xs) < 4:
            # Effectively static — skip the animated expression.
            sx = xs[0]
            return (f"crop={crop_w}:{crop_h}:{sx}:0", crop_w, crop_h, sx, 0)
        # Piecewise-linear: x(t) lerps between consecutive samples.
        # Build inside-out: expr = lerp_0(t) if t<t1 else (lerp_1(t) if t<t2 else ...).
        tail = str(xs[-1])
        for i in range(len(xs) - 2, -1, -1):
            t0, x0 = ts[i], xs[i]
            t1, x1 = ts[i + 1], xs[i + 1]
            span = max(0.1, t1 - t0)
            lerp = f"{x0}+({x1}-{x0})*(t-{t0:.2f})/{span:.2f}"
            tail = f"if(lt(t,{t1:.2f}),{lerp},{tail})"
        static_x = xs[0]
        return (f"crop={crop_w}:{crop_h}:'{tail}':0", crop_w, crop_h, static_x, 0)
    else:
        # Vertical tracking: x stays 0, y interpolates.
        pts = sorted(found_pts, key=lambda p: p[0])
        ys = [_clamp_y(fy) for (_, _, fy) in pts]
        ts = [max(0.0, min(rt, clip_duration)) for (rt, _, _) in pts]
        dedup_ts = []
        dedup_ys: List[int] = []
        for t, y in zip(ts, ys):
            if dedup_ts and abs(t - dedup_ts[-1]) < 0.05:
                dedup_ys[-1] = int((dedup_ys[-1] + y) / 2)
                continue
            dedup_ts.append(t)
            dedup_ys.append(y)
        ts, ys = dedup_ts, dedup_ys
        if len(ys) == 1 or max(ys) - min(ys) < 4:
            sy = ys[0]
            return (f"crop={crop_w}:{crop_h}:0:{sy}", crop_w, crop_h, 0, sy)
        tail = str(ys[-1])
        for i in range(len(ys) - 2, -1, -1):
            t0, y0 = ts[i], ys[i]
            t1, y1 = ts[i + 1], ys[i + 1]
            span = max(0.1, t1 - t0)
            lerp = f"{y0}+({y1}-{y0})*(t-{t0:.2f})/{span:.2f}"
            tail = f"if(lt(t,{t1:.2f}),{lerp},{tail})"
        static_y = ys[0]
        return (f"crop={crop_w}:{crop_h}:0:'{tail}'", crop_w, crop_h, 0, static_y)


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
