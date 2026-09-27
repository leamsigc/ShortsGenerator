"""
CLIPPER Editor - Trim, Split, Merge operations.

Provides a standalone editor module that the Flask routes delegate to,
keeping controller logic thin and business logic testable.
"""

import os
import json
import shutil
import subprocess
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any

from classes.ClipperProject import (
    ClipSegment, ClipTemplate, project_store,
    ViralityScores, WordTimestamp,
)
from classes.Clipper import (
    Clipper, generate_thumbnail, burn_subtitles_and_hook,
    generate_word_synced_srt, resolve_clipper_subtitle_template,
)
from classes.FaceDetector import FaceDetector, smart_crop_coordinates
from video import get_aspect_ratio_dimensions
from classes.FaceDetector import get_video_dimensions
from termcolor import colored


class ClipperEditor:
    """Editor operations for CLIPPER clips: trim, split, merge, preview."""

    def __init__(self, project_id: str):
        from classes.ClipperProject import ClipperProject
        self.project_id = project_id
        self.project = project_store.get_project(project_id)
        self.face_detector = FaceDetector()
        self.base_dir = os.path.join(
            os.path.dirname(__file__),
            "static", "clipper", "projects", project_id,
        )

    def _resolve_source_video(self, source_id: str) -> Optional[str]:
        import glob as _glob

        sources_dir = os.path.join(self.base_dir, "sources")
        candidates = [
            p for p in _glob.glob(os.path.join(sources_dir, f"{source_id}.*"))
            if os.path.splitext(p)[1] in (".mp4", ".mkv", ".webm")
        ]
        if candidates:
            return candidates[0]

        transcript = project_store.get_transcript(self.project_id, source_id)
        if transcript and transcript.video_url and os.path.exists(transcript.video_url):
            return transcript.video_url

        return None

    def _find_clip(self, clip_id: str) -> Tuple[Optional[ClipSegment], Optional[str]]:
        """Search all clips across all projects for the given clip_id.

        Returns (clip, project_id) or (None, None).
        """
        project = self.project or project_store.get_project(self.project_id)
        if project:
            for clip in project_store.get_clips(project.id):
                if clip.id == clip_id:
                    return clip, project.id

        for proj in project_store.list_projects():
            for clip in project_store.get_clips(proj.id):
                if clip.id == clip_id:
                    return clip, proj.id

        return None, None

    def trim_clip(self, clip_id: str, start_time: Optional[float], end_time: Optional[float]) -> Optional[ClipSegment]:
        """Trim a clip's start/end times."""
        clip, _ = self._find_clip(clip_id)
        if clip is None:
            return None

        if start_time is not None:
            clip.start_time = float(start_time)
        if end_time is not None:
            clip.end_time = float(end_time)

        clip.duration = clip.end_time - clip.start_time
        clip.status = "pending"
        project_store.save_clip(clip)
        return clip

    def split_clip(self, clip_id: str, split_time: float) -> Optional[Tuple[ClipSegment, ClipSegment]]:
        """Split a clip into two at a specific time."""
        clip, project_id = self._find_clip(clip_id)
        if clip is None:
            return None

        if split_time <= clip.start_time or split_time >= clip.end_time:
            return None

        clip1 = ClipSegment(
            id=str(os.urandom(16).hex()),
            project_id=project_id,
            source_id=clip.source_id,
            index=clip.index,
            start_time=clip.start_time,
            end_time=split_time,
            duration=split_time - clip.start_time,
            transcript="",
            scores=clip.scores,
            hook_title=clip.hook_title,
            status="pending",
            face_x=clip.face_x,
            face_y=clip.face_y,
        )

        clip2 = ClipSegment(
            id=str(os.urandom(16).hex()),
            project_id=project_id,
            source_id=clip.source_id,
            index=clip.index + 1,
            start_time=split_time,
            end_time=clip.end_time,
            duration=clip.end_time - split_time,
            transcript="",
            scores=clip.scores,
            hook_title="",
            status="pending",
            face_x=clip.face_x,
            face_y=clip.face_y,
        )

        clip.status = "split"
        project_store.save_clip(clip)
        project_store.save_clip(clip1)
        project_store.save_clip(clip2)

        return clip1, clip2

    def merge_clips(self, clip_ids: List[str], output_name: str = "merged") -> Optional[ClipSegment]:
        """Merge multiple clips into one."""
        if len(clip_ids) < 2:
            return None

        clips: List[ClipSegment] = []
        project_id: Optional[str] = None

        for proj in project_store.list_projects():
            for c in project_store.get_clips(proj.id):
                if c.id in clip_ids:
                    clips.append(c)
                    project_id = proj.id

        if len(clips) < 2 or project_id is None:
            return None

        clips.sort(key=lambda c: c.start_time)

        merged_clip = ClipSegment(
            id=str(os.urandom(16).hex()),
            project_id=project_id,
            source_id=clips[0].source_id,
            index=clips[0].index,
            start_time=clips[0].start_time,
            end_time=clips[-1].end_time,
            duration=clips[-1].end_time - clips[0].start_time,
            transcript=" ".join(c.transcript for c in clips if c.transcript),
            scores=ViralityScores(),
            hook_title=output_name or "Merged Clip",
            status="pending",
            face_x=clips[0].face_x or 0.5,
            face_y=clips[0].face_y or 0.35,
        )

        project_store.save_clip(merged_clip)
        return merged_clip

    def generate_preview(self, clip_id: str, width: int = 240) -> Optional[str]:
        """Generate a short preview clip (first ~3 seconds at reduced resolution)."""
        clip, project_id = self._find_clip(clip_id)
        if clip is None:
            return None

        video_path = self._resolve_source_video(clip.source_id)
        if not video_path or not os.path.exists(video_path):
            return None

        project = project_store.get_project(project_id)
        if project is None:
            return None

        preview_dir = os.path.join(self.base_dir, "previews")
        os.makedirs(preview_dir, exist_ok=True)
        preview_path = os.path.join(preview_dir, f"{clip_id}.mp4")

        target_w, target_h = get_aspect_ratio_dimensions("9:16")
        preview_w = min(width, target_w)

        source_w, source_h = get_video_dimensions(video_path)
        crop_x, crop_y, crop_w, crop_h = smart_crop_coordinates(
            clip.face_x or 0.5, clip.face_y or 0.35,
            source_w, source_h, target_w, target_h,
        )

        crop_filter = (
            f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},"
            f"scale={preview_w}:-1,"
            f"setsar=1,format=yuv420p"
        )

        clip_duration = min(3.0, clip.duration)

        cmd = [
            "ffmpeg", "-y",  # software decode (hwaccel breaks on AV1)
            "-ss", str(clip.start_time),
            "-i", video_path,
            "-t", str(clip_duration),
            "-vf", crop_filter,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-an",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            preview_path,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and os.path.exists(preview_path):
                print(colored(f"[+] Preview generated: {preview_path}", "green"))
                return preview_path
            else:
                print(colored(f"[-] Preview failed: {result.stderr[-200:]}", "red"))
        except Exception as e:
            print(colored(f"[-] Preview error: {e}", "red"))

        return None

    def render_clip(self, clip_id: str, face_x: Optional[float] = None, face_y: Optional[float] = None) -> Optional[str]:
        """Render a single clip with crop, captions, and hook title."""
        clip, project_id = self._find_clip(clip_id)
        if clip is None:
            return None

        project = project_store.get_project(project_id)
        if project is None:
            return None

        clipper = Clipper(project)
        output_dir = os.path.join(self.base_dir, "renders")
        os.makedirs(output_dir, exist_ok=True)

        fx = face_x if face_x is not None else clip.face_x
        fy = face_y if face_y is not None else clip.face_y

        return clipper.render_clip(clip, output_dir, face_x=fx, face_y=fy)
