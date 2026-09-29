import os
import json
import uuid
import requests
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class WordTimestamp:
    word: str
    start_time: float
    end_time: float
    confidence: float = 1.0


@dataclass
class SentenceTimestamp:
    text: str
    start_time: float
    end_time: float


@dataclass
class Transcript:
    video_url: str
    duration: float
    words: List[WordTimestamp]
    sentences: List[SentenceTimestamp]
    topics: List[str] = field(default_factory=list)
    i_words: int = 0
    engagement_signals: Dict[str, Any] = field(default_factory=dict)
    cached_at: Optional[str] = None
    outline: List[Dict[str, Any]] = field(default_factory=list)
    # ISO 639-1 code detected (or requested) at transcription time, e.g. "es".
    # "auto" is never stored — it resolves to the detected code (or "en" fallback).
    language: str = "en"
    language_probability: float = 0.0

    def to_dict(self) -> dict:
        return {
            "video_url": self.video_url,
            "duration": self.duration,
            "words": [{"word": w.word, "start": w.start_time, "end": w.end_time, "confidence": w.confidence} for w in self.words],
            "sentences": [{"text": s.text, "start": s.start_time, "end": s.end_time} for s in self.sentences],
            "topics": self.topics,
            "i_words": self.i_words,
            "engagement_signals": self.engagement_signals,
            "cached_at": self.cached_at or datetime.utcnow().isoformat(),
            "outline": self.outline,
            "language": self.language,
            "language_probability": self.language_probability,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transcript":
        words: List[WordTimestamp] = []
        for w in data.get("words", []):
            words.append(WordTimestamp(
                word=w.get("word", ""),
                start_time=w.get("start_time", w.get("start", 0.0)),
                end_time=w.get("end_time", w.get("end", 0.0)),
                confidence=w.get("confidence", 1.0),
            ))

        sentences: List[SentenceTimestamp] = []
        for s in data.get("sentences", []):
            sentences.append(SentenceTimestamp(
                text=s.get("text", ""),
                start_time=s.get("start_time", s.get("start", 0.0)),
                end_time=s.get("end_time", s.get("end", 0.0)),
            ))

        return cls(
            video_url=data["video_url"],
            duration=data["duration"],
            words=words,
            sentences=sentences,
            topics=data.get("topics", []),
            i_words=data.get("i_words", 0),
            engagement_signals=data.get("engagement_signals", {}),
            cached_at=data.get("cached_at"),
            outline=data.get("outline", []),
            language=data.get("language", data.get("engagement_signals", {}).get("language", "en")),
            language_probability=float(data.get("language_probability", data.get("engagement_signals", {}).get("language_probability", 0.0) or 0.0)),
        )


@dataclass
class ClipTemplate:
    subtitle_template: str = "classic"
    font: str = "bold_font.ttf"
    font_size: int = 110
    color: str = "#FFFF00"
    stroke_color: str = "black"
    stroke_width: int = 6
    hook_position: str = "top"
    hook_animation: str = "slide_in"
    broll_enabled: bool = False
    broll_keyword: str = ""
    transition_type: str = "cut"
    transition_duration: float = 0.0


@dataclass
class ClipperProject:
    id: str
    name: str
    description: str
    source_urls: List[str]
    training_data: str
    template: ClipTemplate
    target_platform: str
    created_at: str
    updated_at: str
    status: str = "idle"
    source_ids: List[str] = field(default_factory=list)
    golden_urls: List[str] = field(default_factory=list)
    extra_resources: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "source_urls": self.source_urls,
            "training_data": self.training_data,
            "template": asdict(self.template),
            "target_platform": self.target_platform,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "source_ids": self.source_ids,
            "golden_urls": self.golden_urls,
            "extra_resources": self.extra_resources,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClipperProject":
        template_data = data.get("template", {})
        template = ClipTemplate(**template_data) if template_data else ClipTemplate()
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            source_urls=data.get("source_urls", []),
            training_data=data.get("training_data", ""),
            template=template,
            target_platform=data.get("target_platform", "tiktok"),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            status=data.get("status", "idle"),
            source_ids=data.get("source_ids", []),
            golden_urls=data.get("golden_urls", []),
            extra_resources=data.get("extra_resources", []),
        )


@dataclass
class ViralityScores:
    hook_score: float = 0.0
    engagement_score: float = 0.0
    value_score: float = 0.0
    shareability_score: float = 0.0
    overall_score: float = 0.0
    pause_count: int = 0
    excitement_markers: int = 0
    question_marks: int = 0
    has_cta: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ViralityScores":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ClipSegment:
    id: str
    project_id: str
    source_id: str
    index: int
    start_time: float
    end_time: float
    duration: float
    transcript: str
    scores: ViralityScores
    hook_title: str = ""
    thumbnail_url: str = ""
    status: str = "pending"
    face_x: Optional[float] = None
    face_y: Optional[float] = None
    # Metadata for YouTube/social (generated via LLM)
    title: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    post_content: str = ""
    suggested_schedule: str = ""
    # Compilation support: merged clip assembled from rendered segments
    is_compilation: bool = False
    source_clip_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "source_id": self.source_id,
            "index": self.index,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "transcript": self.transcript,
            "scores": self.scores.to_dict(),
            "hook_title": self.hook_title,
            "thumbnail_url": self.thumbnail_url,
            "status": self.status,
            "face_x": self.face_x,
            "face_y": self.face_y,
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "post_content": self.post_content,
            "suggested_schedule": self.suggested_schedule,
            "is_compilation": self.is_compilation,
            "source_clip_ids": self.source_clip_ids,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClipSegment":
        scores_data = data.get("scores", {})
        scores = ViralityScores.from_dict(scores_data) if scores_data else ViralityScores()
        return cls(
            id=data["id"],
            project_id=data["project_id"],
            source_id=data["source_id"],
            index=data["index"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            duration=data["duration"],
            transcript=data["transcript"],
            scores=scores,
            hook_title=data.get("hook_title", ""),
            thumbnail_url=data.get("thumbnail_url", ""),
            status=data.get("status", "pending"),
            face_x=data.get("face_x"),
            face_y=data.get("face_y"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            post_content=data.get("post_content", ""),
            suggested_schedule=data.get("suggested_schedule", ""),
            is_compilation=data.get("is_compilation", False),
            source_clip_ids=data.get("source_clip_ids", []),
        )


class ProjectStore:
    BASE_DIR = Path(__file__).resolve().parent.parent / "static" / "clipper"
    PROJECTS_DIR = BASE_DIR / "projects"

    def __init__(self):
        os.makedirs(self.PROJECTS_DIR, exist_ok=True)

    def _project_path(self, project_id: str) -> Path:
        return Path(self.PROJECTS_DIR) / project_id / "project.json"

    def _clips_path(self, project_id: str) -> Path:
        return Path(self.PROJECTS_DIR) / project_id / "clips.json"

    def _transcripts_dir(self, project_id: str) -> Path:
        return Path(self.PROJECTS_DIR) / project_id / "transcripts"

    def create_project(self, project: ClipperProject) -> ClipperProject:
        project_path = self._project_path(project.id)
        project_path.parent.mkdir(parents=True, exist_ok=True)
        self._transcripts_dir(project.id).mkdir(parents=True, exist_ok=True)
        with open(project_path, "w") as f:
            json.dump(project.to_dict(), f, indent=2)
        self._save_clips(project.id, [])
        return project

    def get_project(self, project_id: str) -> Optional[ClipperProject]:
        project_path = self._project_path(project_id)
        if not project_path.exists():
            return None
        with open(project_path) as f:
            return ClipperProject.from_dict(json.load(f))

    def update_project(self, project: ClipperProject) -> ClipperProject:
        project.updated_at = datetime.utcnow().isoformat()
        project_path = self._project_path(project.id)
        with open(project_path, "w") as f:
            json.dump(project.to_dict(), f, indent=2)
        return project

    def delete_project(self, project_id: str) -> bool:
        import shutil
        project_dir = Path(self.PROJECTS_DIR) / project_id
        if project_dir.exists():
            shutil.rmtree(project_dir)
            return True
        return False

    def list_projects(self) -> List[ClipperProject]:
        projects = []
        if not self.PROJECTS_DIR.exists():
            return projects
        for project_dir in self.PROJECTS_DIR.iterdir():
            if project_dir.is_dir() and (project_dir / "project.json").exists():
                with open(project_dir / "project.json") as f:
                    projects.append(ClipperProject.from_dict(json.load(f)))
        return sorted(projects, key=lambda p: p.updated_at, reverse=True)

    def _save_clips(self, project_id: str, clips: List[ClipSegment]) -> None:
        clips_path = self._clips_path(project_id)
        with open(clips_path, "w") as f:
            json.dump([c.to_dict() for c in clips], f, indent=2)

    def get_clips(self, project_id: str) -> List[ClipSegment]:
        clips_path = self._clips_path(project_id)
        if not clips_path.exists():
            return []
        with open(clips_path) as f:
            return [ClipSegment.from_dict(c) for c in json.load(f)]

    def save_clip(self, clip: ClipSegment) -> ClipSegment:
        clips = self.get_clips(clip.project_id)
        for i, c in enumerate(clips):
            if c.id == clip.id:
                clips[i] = clip
                break
        else:
            clips.append(clip)
        self._save_clips(clip.project_id, clips)
        return clip

    def save_transcript(self, project_id: str, source_id: str, transcript: Transcript) -> str:
        transcripts_dir = self._transcripts_dir(project_id)
        transcripts_dir.mkdir(parents=True, exist_ok=True)
        path = transcripts_dir / f"{source_id}.json"
        with open(path, "w") as f:
            json.dump(transcript.to_dict(), f, indent=2)
        return str(path)

    def _publish_records_path(self, project_id: str) -> Path:
        return Path(self.PROJECTS_DIR) / project_id / "publish_records.json"

    def save_publish_record(self, project_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
        records = self.list_publish_records(project_id)
        record.setdefault("id", str(uuid.uuid4()))
        record["created_at"] = datetime.utcnow().isoformat()
        records.append(record)
        path = self._publish_records_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(records, f, indent=2)
        return record

    def list_publish_records(self, project_id: str) -> List[Dict[str, Any]]:
        path = self._publish_records_path(project_id)
        if not path.exists():
            return []
        with open(path) as f:
            return json.load(f)

    def delete_publish_record(self, project_id: str, record_id: str) -> bool:
        records = self.list_publish_records(project_id)
        remaining = [r for r in records if r.get("id") != record_id]
        if len(remaining) == len(records):
            return False
        with open(self._publish_records_path(project_id), "w") as f:
            json.dump(remaining, f, indent=2)
        return True

    def get_transcript(self, project_id: str, source_id: str) -> Optional[Transcript]:
        path = self._transcripts_dir(project_id) / f"{source_id}.json"
        if not path.exists():
            return None
        with open(path) as f:
            return Transcript.from_dict(json.load(f))

    def get_source_ids(self, project_id: str) -> List[str]:
        transcripts_dir = self._transcripts_dir(project_id)
        if not transcripts_dir.exists():
            return []
        return [p.stem for p in transcripts_dir.glob("*.json")]


project_store = ProjectStore()
