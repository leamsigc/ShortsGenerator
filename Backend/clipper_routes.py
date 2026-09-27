import os
import uuid
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, Response, send_file

from classes.ClipperProject import ClipperProject, ClipTemplate, project_store, ClipSegment
from classes.Clipper import Clipper, set_clipper_progress, CLIPPER_STATE
from clipper_editor import ClipperEditor
from utils import clean_dir
from termcolor import colored

clipper_bp = Blueprint("clipper", __name__, url_prefix="/api/clipper")


@clipper_bp.route("/projects", methods=["GET"])
def list_projects():
    """List all CLIPPER projects."""
    try:
        projects = project_store.list_projects()
        return jsonify({
            "status": "success",
            "data": [p.to_dict() for p in projects]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@clipper_bp.route("/projects", methods=["POST"])
def create_project():
    """Create a new CLIPPER project."""
    try:
        data = request.get_json()
        project_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        template_data = data.get("template", {})
        template = ClipTemplate(
            subtitle_template=template_data.get("subtitle_template", "classic"),
            font=template_data.get("font", "bold_font.ttf"),
            font_size=template_data.get("font_size", 110),
            color=template_data.get("color", "#FFFF00"),
            stroke_color=template_data.get("stroke_color", "black"),
            stroke_width=template_data.get("stroke_width", 6),
            broll_enabled=template_data.get("broll_enabled", False),
            broll_keyword=template_data.get("broll_keyword", ""),
            transition_type=template_data.get("transition_type", "cut"),
        )

        project = ClipperProject(
            id=project_id,
            name=data.get("name", "Untitled Project"),
            description=data.get("description", ""),
            source_urls=data.get("source_urls", []),
            training_data=data.get("training_data", ""),
            template=template,
            target_platform=data.get("target_platform", "tiktok"),
            created_at=now,
            updated_at=now,
            source_ids=[],
            golden_urls=data.get("golden_urls", []),
            extra_resources=data.get("extra_resources", []),
        )

        for _ in project.source_urls:
            project.source_ids.append(str(uuid.uuid4()))

        project_store.create_project(project)

        return jsonify({
            "status": "success",
            "data": project.to_dict()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@clipper_bp.route("/projects/<project_id>", methods=["GET"])
def get_project(project_id):
    """Get a specific project."""
    project = project_store.get_project(project_id)
    if project is None:
        return jsonify({"status": "error", "message": "Project not found"}), 404
    return jsonify({
        "status": "success",
        "data": project.to_dict()
    })


@clipper_bp.route("/projects/<project_id>", methods=["PUT"])
def update_project(project_id):
    """Update a project."""
    project = project_store.get_project(project_id)
    if project is None:
        return jsonify({"status": "error", "message": "Project not found"}), 404

    try:
        data = request.get_json()

        if "name" in data:
            project.name = data["name"]
        if "description" in data:
            project.description = data["description"]
        if "source_urls" in data:
            project.source_urls = data["source_urls"]
            while len(project.source_ids) < len(project.source_urls):
                project.source_ids.append(str(uuid.uuid4()))
        if "training_data" in data:
            project.training_data = data["training_data"]
        if "golden_urls" in data:
            project.golden_urls = data["golden_urls"]
        if "extra_resources" in data:
            project.extra_resources = data["extra_resources"]
        if "target_platform" in data:
            project.target_platform = data["target_platform"]
        if "template" in data:
            for key, value in data["template"].items():
                if hasattr(project.template, key):
                    setattr(project.template, key, value)
        if "status" in data:
            project.status = data["status"]

        project_store.update_project(project)

        return jsonify({
            "status": "success",
            "data": project.to_dict()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@clipper_bp.route("/projects/<project_id>", methods=["DELETE"])
def delete_project(project_id):
    """Delete a project."""
    if project_store.delete_project(project_id):
        return jsonify({"status": "success", "message": "Project deleted"})
    return jsonify({"status": "error", "message": "Project not found"}), 404


@clipper_bp.route("/projects/<project_id>/sources", methods=["POST"])
def add_source(project_id):
    """Add a source URL to a project."""
    project = project_store.get_project(project_id)
    if project is None:
        return jsonify({"status": "error", "message": "Project not found"}), 404

    try:
        data = request.get_json()
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"status": "error", "message": "URL is required"}), 400

        project.source_urls.append(url)
        project.source_ids.append(str(uuid.uuid4()))
        project_store.update_project(project)

        return jsonify({
            "status": "success",
            "data": {"source_id": project.source_ids[-1], "url": url}
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@clipper_bp.route("/projects/<project_id>/sources/<source_id>", methods=["DELETE"])
def remove_source(project_id, source_id):
    """Remove a source from a project."""
    project = project_store.get_project(project_id)
    if project is None:
        return jsonify({"status": "error", "message": "Project not found"}), 404

    try:
        for i, sid in enumerate(project.source_ids):
            if sid == source_id:
                project.source_ids.pop(i)
                if i < len(project.source_urls):
                    project.source_urls.pop(i)
                project_store.update_project(project)
                return jsonify({"status": "success", "message": "Source removed"})
        return jsonify({"status": "error", "message": "Source not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@clipper_bp.route("/projects/<project_id>/upload", methods=["POST"])
def upload_source(project_id):
    """Upload a local video file (and optional SRT subtitles) as a project source.

    Multipart form: `video` (required file), `srt` (optional file).
    """
    project = project_store.get_project(project_id)
    if project is None:
        return jsonify({"status": "error", "message": "Project not found"}), 404

    if "video" not in request.files:
        return jsonify({"status": "error", "message": "No video file provided (field 'video')"}), 400

    video_file = request.files["video"]
    if not video_file.filename:
        return jsonify({"status": "error", "message": "Empty video filename"}), 400

    source_id = str(uuid.uuid4())
    sources_dir = os.path.join(
        os.path.dirname(__file__), "static", "clipper", "projects", project_id, "sources"
    )
    os.makedirs(sources_dir, exist_ok=True)

    ext = os.path.splitext(video_file.filename)[1].lower() or ".mp4"
    if ext not in (".mp4", ".mkv", ".webm", ".mov", ".avi"):
        return jsonify({"status": "error", "message": f"Unsupported video format: {ext}"}), 400

    video_path = os.path.join(sources_dir, f"{source_id}{ext}")
    video_file.save(video_path)

    if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
        return jsonify({"status": "error", "message": "Video upload failed"}), 500

    srt_uploaded = False
    srt_file = request.files.get("srt")
    if srt_file and srt_file.filename:
        srt_path = os.path.join(sources_dir, f"{source_id}.srt")
        srt_file.save(srt_path)
        srt_uploaded = os.path.exists(srt_path)

    # Register as a local pseudo-URL so the pipeline skips downloading
    original_name = os.path.splitext(os.path.basename(video_file.filename))[0][:60]
    project.source_urls.append(f"local://{source_id}/{original_name}")
    project.source_ids.append(source_id)
    project_store.update_project(project)

    return jsonify({
        "status": "success",
        "data": {
            "source_id": source_id,
            "url": f"local://{source_id}/{original_name}",
            "filename": original_name,
            "srt": srt_uploaded,
        }
    })


@clipper_bp.route("/cancel", methods=["POST"])
def cancel_pipeline():
    """Request cancellation of the running CLIPPER pipeline (optionally per project)."""
    from classes.Clipper import request_clipper_cancel, ClipperCancelled
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id", "*")
    request_clipper_cancel(project_id)
    return jsonify({
        "status": "success",
        "data": {"cancelled": True, "project_id": project_id,
                 "note": "Pipeline stops at the next stage boundary (Ctrl-safe: no partial file corruption)"}
    })


@clipper_bp.route("/llm/settings", methods=["GET"])
def get_llm_settings_route():
    """Get the configured CLIPPER LLM provider (API key masked)."""
    from llm_providers import masked_llm_settings, PROVIDERS
    settings = masked_llm_settings()
    return jsonify({"status": "success", "data": {"settings": settings, "providers": PROVIDERS}})


@clipper_bp.route("/llm/settings", methods=["POST"])
def update_llm_settings_route():
    """Update the CLIPPER LLM provider configuration."""
    from llm_providers import update_llm_settings, masked_llm_settings
    try:
        data = request.get_json(silent=True) or {}
        # Empty api_key means "keep the existing one"
        if not str(data.get("api_key", "")).strip():
            data.pop("api_key", None)
        update_llm_settings(data)
        return jsonify({"status": "success", "data": {"settings": masked_llm_settings()}})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@clipper_bp.route("/llm/test", methods=["POST"])
def test_llm_route():
    """Send a tiny prompt to validate the LLM provider configuration."""
    from llm_providers import test_llm_connection
    try:
        data = request.get_json(silent=True) or {}
        result = test_llm_connection(data.get("settings"))
        status_code = 200 if result.get("ok") else 502
        return jsonify({"status": "success" if result.get("ok") else "error", "data": result}), status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@clipper_bp.route("/llm/cookie-status", methods=["GET"])
def g4f_cookie_status_route():
    """Fast check whether stored browser cookies still work for g4f Gemini."""
    from gpt import check_g4f_cookie_status
    try:
        return jsonify({"status": "success", "data": check_g4f_cookie_status()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@clipper_bp.route("/projects/<project_id>/publish-records", methods=["GET"])
def list_publish_records(project_id):
    """List publish/schedule records for a project."""
    records = project_store.list_publish_records(project_id)
    return jsonify({"status": "success", "data": records})


@clipper_bp.route("/projects/<project_id>/publish-records/<record_id>", methods=["DELETE"])
def delete_publish_record(project_id, record_id):
    """Delete a publish record (e.g. cancel a not-yet-posted schedule)."""
    if project_store.delete_publish_record(project_id, record_id):
        return jsonify({"status": "success", "message": "Record deleted"})
    return jsonify({"status": "error", "message": "Record not found"}), 404


@clipper_bp.route("/process", methods=["POST"])
def process_project():
    """Download + transcribe sources, then auto-select top clips."""
    from classes.Clipper import ClipperCancelled
    try:
        data = request.get_json(silent=True) or {}
        project_id = data.get("project_id")
        language = data.get("language", "en")
        auto_select = data.get("auto_select", True)
        model_size = data.get("model_size") or None
        from llm_providers import get_clipper_ai_model
        ai_model = data.get("ai_model", get_clipper_ai_model())
        max_clips = int(data.get("max_clips", 7))
        min_duration = float(data.get("min_duration", 30.0))
        max_duration = float(data.get("max_duration", 90.0))
        min_score = float(data.get("min_score", 30.0))

        if not project_id:
            return jsonify({"status": "error", "message": "project_id is required"}), 400

        if CLIPPER_STATE.get("generating"):
            return jsonify({"status": "error", "message": "A processing job is already running"}), 409

        CLIPPER_STATE["generating"] = True
        from classes.Clipper import clear_clipper_cancel
        clear_clipper_cancel(project_id)

        project = project_store.get_project(project_id)
        if project is None:
            return jsonify({"status": "error", "message": "Project not found"}), 404

        clipper = Clipper(project)
        try:
            results = clipper.process_sources(
                language=language,
                model_size=model_size,
                ai_model=ai_model,
            )
        except ClipperCancelled as e:
            project.status = "cancelled"
            project_store.update_project(project)
            return jsonify({"status": "cancelled", "message": str(e), "data": {"project": project.to_dict()}})

        project.status = "processed"
        project_store.update_project(project)

        clips = []
        if auto_select:
            try:
                clips = clipper.generate_clips(
                    max_clips=max_clips,
                    ai_model=ai_model,
                    min_duration=min_duration,
                    max_duration=max_duration,
                    min_score=min_score,
                )
                project.status = "clips_ready"
                project_store.update_project(project)
            except ClipperCancelled as e:
                project.status = "cancelled"
                project_store.update_project(project)
                return jsonify({"status": "cancelled", "message": str(e), "data": {"project": project.to_dict()}})
            except Exception as e:
                print(colored(f"[-] Auto-select failed: {e}", "yellow"))
                project.status = "ready"
                project_store.update_project(project)

        return jsonify({
            "status": "success",
            "data": {
                "project": project.to_dict(),
                "sources": results,
                "clips": [c.to_dict() for c in clips],
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        CLIPPER_STATE["generating"] = False


@clipper_bp.route("/process/<project_id>/status", methods=["GET"])
def get_process_status(project_id):
    """Get processing status for a project."""
    progress = CLIPPER_STATE["progress"].get(project_id, {})
    return jsonify({
        "status": "success",
        "data": progress
    })


@clipper_bp.route("/pipeline/stream")
def pipeline_stream():
    """SSE endpoint for real-time progress updates."""
    project_id = request.args.get("project_id", "")

    def generate():
        while True:
            import time
            if project_id in CLIPPER_STATE["progress"]:
                progress = CLIPPER_STATE["progress"][project_id]
                yield f"data: {json.dumps(progress)}\n\n"
            else:
                yield f"data: {json.dumps({'stage': 'idle', 'progress': 0})}\n\n"
            time.sleep(0.5)

    return Response(generate(), mimetype='text/event-stream')


@clipper_bp.route("/select", methods=["POST"])
def select_clips():
    """Generate and select top clips for a project."""
    global CLIPPER_STATE
    from classes.Clipper import ClipperCancelled
    CLIPPER_STATE["generating"] = True

    try:
        data = request.get_json()
        project_id = data.get("project_id")
        max_clips = data.get("max_clips", 7)
        from llm_providers import get_clipper_ai_model
        ai_model = data.get("ai_model", get_clipper_ai_model())
        min_duration = data.get("min_duration", 30.0)
        max_duration = data.get("max_duration", 90.0)
        min_score = float(data.get("min_score", 30.0))

        project = project_store.get_project(project_id)
        if project is None:
            return jsonify({"status": "error", "message": "Project not found"}), 404

        clipper = Clipper(project)
        try:
            clips = clipper.generate_clips(max_clips, ai_model, min_duration, max_duration, min_score=min_score)
        except ClipperCancelled as e:
            project.status = "cancelled"
            project_store.update_project(project)
            return jsonify({"status": "cancelled", "message": str(e)})

        project.status = "clips_ready"
        project_store.update_project(project)

        return jsonify({
            "status": "success",
            "data": {
                "clips": [c.to_dict() for c in clips],
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        CLIPPER_STATE["generating"] = False


@clipper_bp.route("/projects/<project_id>/clips", methods=["GET"])
def get_clips(project_id):
    """Get all clips for a project."""
    min_score = request.args.get("min_score", type=float, default=0.0)

    clips = project_store.get_clips(project_id)

    if min_score > 0:
        clips = [c for c in clips if c.scores.overall_score >= min_score]

    return jsonify({
        "status": "success",
        "data": [c.to_dict() for c in clips]
    })


@clipper_bp.route("/clip/<clip_id>", methods=["GET"])
def get_clip(clip_id):
    """Get a specific clip."""
    for project in project_store.list_projects():
        clips = project_store.get_clips(project.id)
        for clip in clips:
            if clip.id == clip_id:
                return jsonify({
                    "status": "success",
                    "data": clip.to_dict()
                })
    return jsonify({"status": "error", "message": "Clip not found"}), 404


@clipper_bp.route("/clip/<clip_id>/render", methods=["POST"])
def render_clip(clip_id):
    """Render a specific clip."""
    global CLIPPER_STATE
    from classes.Clipper import ClipperCancelled, resolve_export_preset
    CLIPPER_STATE["generating"] = True

    try:
        data = request.get_json()
        face_x = data.get("face_x", 0.5)
        face_y = data.get("face_y", 0.35)
        format_type = data.get("format")
        quality = data.get("quality", "medium")
        burn_subtitles = data.get("burn_subtitles", True)

        render_kwargs = {"burn_subtitles": burn_subtitles}
        aspect = data.get("aspect")
        if aspect:
            # Explicit aspect ratio wins (user-selected in the editor)
            render_kwargs["aspect"] = aspect
            if format_type:
                preset = resolve_export_preset(format_type, quality)
                render_kwargs.update({
                    "crf": preset["crf"],
                    "encode_preset": preset["preset"],
                })
        elif format_type:
            preset = resolve_export_preset(format_type, quality)
            render_kwargs.update({
                "aspect": preset["aspect"],
                "crf": preset["crf"],
                "encode_preset": preset["preset"],
            })

        clip = None
        project = None
        for p in project_store.list_projects():
            clips = project_store.get_clips(p.id)
            for c in clips:
                if c.id == clip_id:
                    clip = c
                    project = p
                    break
            if clip:
                break

        if clip is None or project is None:
            return jsonify({"status": "error", "message": "Clip not found"}), 404

        output_dir = os.path.join(
            os.path.dirname(__file__), "static", "clipper", "projects", project.id, "renders"
        )
        os.makedirs(output_dir, exist_ok=True)

        clipper = Clipper(project)
        try:
            output_path = clipper.render_clip(clip, output_dir, face_x, face_y, **render_kwargs)
        except ClipperCancelled as e:
            return jsonify({"status": "cancelled", "message": str(e)})

        if output_path:
            clip.status = "rendered"
            project_store.save_clip(clip)

            static_path = "/static/clipper/projects/" + project.id + "/renders/" + os.path.basename(output_path)

            return jsonify({
                "status": "success",
                "data": {
                    "clip": clip.to_dict(),
                    "output_url": static_path
                }
            })
        else:
            return jsonify({"status": "error", "message": "Render failed"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        CLIPPER_STATE["generating"] = False


@clipper_bp.route("/clip/<clip_id>/trim", methods=["POST"])
def trim_clip(clip_id):
    """Trim a clip's start/end times."""
    data = request.get_json()
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    for project in project_store.list_projects():
        clips = project_store.get_clips(project.id)
        for clip in clips:
            if clip.id == clip_id:
                if start_time is not None:
                    clip.start_time = float(start_time)
                if end_time is not None:
                    clip.end_time = float(end_time)
                clip.duration = clip.end_time - clip.start_time
                clip.status = "pending"
                project_store.save_clip(clip)
                return jsonify({
                    "status": "success",
                    "data": clip.to_dict()
                })
    return jsonify({"status": "error", "message": "Clip not found"}), 404


@clipper_bp.route("/clip/<clip_id>/split", methods=["POST"])
def split_clip(clip_id):
    """Split a clip into two at a specific time."""
    data = request.get_json()
    split_time = data.get("split_time")

    for project in project_store.list_projects():
        clips = project_store.get_clips(project.id)
        for i, clip in enumerate(clips):
            if clip.id == clip_id:
                if split_time <= clip.start_time or split_time >= clip.end_time:
                    return jsonify({"status": "error", "message": "Invalid split time"}), 400

                clip1 = ClipSegment(
                    id=str(uuid.uuid4()),
                    project_id=project.id,
                    source_id=clip.source_id,
                    index=clip.index,
                    start_time=clip.start_time,
                    end_time=split_time,
                    duration=split_time - clip.start_time,
                    transcript="",
                    scores=clip.scores,
                    hook_title=clip.hook_title,
                    status="pending",
                )

                clip2 = ClipSegment(
                    id=str(uuid.uuid4()),
                    project_id=project.id,
                    source_id=clip.source_id,
                    index=clip.index + 1,
                    start_time=split_time,
                    end_time=clip.end_time,
                    duration=clip.end_time - split_time,
                    transcript="",
                    scores=clip.scores,
                    hook_title="",
                    status="pending",
                )

                clip.status = "split"
                project_store.save_clip(clip)
                project_store.save_clip(clip1)
                project_store.save_clip(clip2)

                return jsonify({
                    "status": "success",
                    "data": {"clip1": clip1.to_dict(), "clip2": clip2.to_dict()}
                })
    return jsonify({"status": "error", "message": "Clip not found"}), 404


@clipper_bp.route("/merge", methods=["POST"])
def merge_clips():
    """Merge multiple clips into a compilation (rendered via ffmpeg concat)."""
    data = request.get_json()
    clip_ids = data.get("clip_ids", [])
    output_name = data.get("output_name", "merged")
    render_now = data.get("render", True)

    if len(clip_ids) < 2:
        return jsonify({"status": "error", "message": "At least 2 clips required"}), 400

    clips_by_id = {}
    project = None
    for p in project_store.list_projects():
        for c in project_store.get_clips(p.id):
            if c.id in clip_ids:
                clips_by_id[c.id] = c
                project = p

    matched = [clips_by_id[cid] for cid in clip_ids if cid in clips_by_id]
    if len(matched) < 2 or project is None:
        return jsonify({"status": "error", "message": "No matching clips found"}), 404

    avg_score = sum(c.scores.overall_score for c in matched) / len(matched)
    best = max(matched, key=lambda c: c.scores.overall_score)

    merged_clip = ClipSegment(
        id=str(uuid.uuid4()),
        project_id=project.id,
        source_id=matched[0].source_id,
        index=max(c.index for c in matched),
        start_time=min(c.start_time for c in matched),
        end_time=max(c.end_time for c in matched),
        duration=sum(c.duration for c in matched),
        transcript=" ".join(c.transcript for c in matched if c.transcript),
        scores=best.scores,
        hook_title=output_name or "Compilation",
        status="pending",
        is_compilation=True,
        source_clip_ids=[c.id for c in matched],
    )
    merged_clip.scores.overall_score = avg_score

    project_store.save_clip(merged_clip)

    output_url = None
    if render_now:
        clipper = Clipper(project)
        renders_dir = os.path.join(
            os.path.dirname(__file__), "static", "clipper", "projects", project.id, "renders"
        )
        output_path = clipper.render_compilation(merged_clip, renders_dir)
        if output_path:
            merged_clip = project_store.get_clips(project.id) and next(
                (c for c in project_store.get_clips(project.id) if c.id == merged_clip.id), merged_clip
            )
            output_url = "/static/clipper/projects/" + project.id + "/renders/" + os.path.basename(output_path)
        else:
            return jsonify({
                "status": "error",
                "message": "Compilation metadata created but render failed",
                "data": merged_clip.to_dict(),
            }), 500

    return jsonify({
        "status": "success",
        "data": {**merged_clip.to_dict(), "output_url": output_url}
    })


@clipper_bp.route("/clip/<clip_id>/cover", methods=["POST"])
def generate_cover(clip_id):
    """Generate a cover image (frame + hook title overlay) for a clip."""
    clip = None
    project = None
    for p in project_store.list_projects():
        for c in project_store.get_clips(p.id):
            if c.id == clip_id:
                clip = c
                project = p
                break
        if clip:
            break

    if clip is None or project is None:
        return jsonify({"status": "error", "message": "Clip not found"}), 404

    # Compilations and rendered clips can use the rendered file as the frame source
    video_path = None
    if clip.is_compilation or clip.status == "rendered":
        rendered = os.path.join(
            os.path.dirname(__file__), "static", "clipper", "projects", project.id, "renders", f"{clip_id}.mp4"
        )
        if os.path.exists(rendered):
            video_path = rendered

    clipper = Clipper(project)
    cover_path = clipper.generate_cover(clip, video_path=video_path)

    if cover_path:
        cover_url = f"/static/clipper/projects/{project.id}/covers/{clip_id}.jpg"
        clip.thumbnail_url = cover_url
        project_store.save_clip(clip)
        return jsonify({"status": "success", "data": {"cover_url": cover_url}})

    return jsonify({"status": "error", "message": "Cover generation failed"}), 500


@clipper_bp.route("/clip/<clip_id>/preview", methods=["POST"])
def generate_preview(clip_id):
    """Generate a short preview clip for a given clip."""
    data = request.get_json() or {}
    width = data.get("width", 240)

    editor = ClipperEditor(__get_project_id_for_clip(clip_id))
    preview_path = editor.generate_preview(clip_id, width)

    if preview_path:
        preview_url = "/static/clipper/projects/" + os.path.basename(os.path.dirname(preview_path)) + "/previews/" + os.path.basename(preview_path)
        clip, _ = editor._find_clip(clip_id)
        if clip:
            clip.thumbnail_url = preview_url
            project_store.save_clip(clip)
        return jsonify({
            "status": "success",
            "data": {
                "preview_url": preview_url,
            }
        })

    return jsonify({"status": "error", "message": "Preview generation failed"}), 500


@clipper_bp.route("/projects/<project_id>/sources/<source_id>/video", methods=["GET"])
def get_source_video(project_id, source_id):
    """Stream a source video (HTTP Range supported for seeking/audio)."""
    editor = ClipperEditor(project_id)
    video_path = editor._resolve_source_video(source_id)
    if not video_path or not os.path.exists(video_path):
        return jsonify({"status": "error", "message": "Source video not available"}), 404
    return send_file(video_path, mimetype="video/mp4", conditional=True)


@clipper_bp.route("/clip/<clip_id>/video", methods=["GET"])
def get_clip_video(clip_id):
    """Stream the source video for a clip (HTTP Range supported for seeking).

    Falls back to the rendered clip when the source video is unavailable.
    """
    project_id = __get_project_id_for_clip(clip_id)
    editor = ClipperEditor(project_id)
    clip, resolved_project_id = editor._find_clip(clip_id)
    if clip is None:
        return jsonify({"status": "error", "message": "Clip not found"}), 404

    video_path = editor._resolve_source_video(clip.source_id)

    if not video_path or not os.path.exists(video_path):
        render_dir = os.path.join(
            os.path.dirname(__file__), "static", "clipper", "projects",
            resolved_project_id, "renders"
        )
        rendered = os.path.join(render_dir, f"{clip_id}.mp4")
        if os.path.exists(rendered):
            video_path = rendered

    if not video_path or not os.path.exists(video_path):
        return jsonify({"status": "error", "message": "Video not available"}), 404

    return send_file(video_path, mimetype="video/mp4", conditional=True)


def __get_project_id_for_clip(clip_id: str) -> str:
    """Find the project_id that owns a clip."""
    for project in project_store.list_projects():
        for clip in project_store.get_clips(project.id):
            if clip.id == clip_id:
                return project.id
    return ""


@clipper_bp.route("/clip/<clip_id>/metadata", methods=["POST"])
def generate_clip_metadata(clip_id):
    """Generate YouTube + social metadata for a single clip via LLM."""
    try:
        data = request.get_json(silent=True) or {}
        from llm_providers import get_clipper_ai_model
        ai_model = data.get("ai_model", get_clipper_ai_model())

        clip = None
        project = None
        for p in project_store.list_projects():
            for c in project_store.get_clips(p.id):
                if c.id == clip_id:
                    clip = c
                    project = p
                    break
            if clip:
                break

        if clip is None or project is None:
            return jsonify({"status": "error", "message": "Clip not found"}), 404

        from classes.Clipper import generate_clip_metadata_llm
        meta = generate_clip_metadata_llm(
            transcript_segment=clip.transcript,
            hook_title=clip.hook_title,
            duration=clip.duration,
            target_platform=project.target_platform,
            training_data=project.training_data,
            ai_model=ai_model,
        )

        # Persist to clip
        clip.title = meta.get("title", "")
        clip.description = meta.get("description", "")
        clip.tags = meta.get("tags", [])
        clip.post_content = meta.get("post_content", "")
        clip.suggested_schedule = meta.get("suggested_schedule", "")
        project_store.save_clip(clip)

        return jsonify({"status": "success", "data": meta})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@clipper_bp.route("/clip/<clip_id>/schedule", methods=["POST"])
def schedule_clip(clip_id):
    """Schedule a single clip's rendered video via MagicSync (reuses main schedule logic)."""
    try:
        data = request.get_json(silent=True) or {}
        clip = None
        project = None
        for p in project_store.list_projects():
            for c in project_store.get_clips(p.id):
                if c.id == clip_id:
                    clip = c
                    project = p
                    break
            if clip:
                break
        if clip is None or project is None:
            return jsonify({"status": "error", "message": "Clip not found"}), 404

        # Use same logic as main schedule-to-magicsync but with clip video
        from main import app as _app  # avoid circular
        import requests, json as _json
        video_filename = data.get("videoFilename") or f"{clip_id}.mp4"
        scheduled_at = data.get("scheduledAt")
        content = data.get("content", "") or clip.post_content or clip.title or clip.hook_title
        title = data.get("title", "") or clip.title or clip.hook_title
        description = data.get("description", "") or clip.description or clip.transcript[:150]
        platforms = data.get("platforms", [])
        visibility = data.get("visibility", "")  # "private" | "public" | "" (provider default)
        url = data.get("url", os.getenv("MAGICSYNC_BASE_URL", "http://localhost:3000"))
        api_token = data.get("apiToken", os.getenv("MAGICSYNC_API_TOKEN", ""))
        video_base_url = data.get("videoBaseUrl", "")

        if not platforms:
            return jsonify({"status": "error", "message": "At least one platform required"}), 400
        if not api_token:
            return jsonify({"status": "error", "message": "API token required"}), 400

        # Resolve clip video URL: prefer rendered clip, fallback to schedule endpoint's existing logic
        clip_video_url = None
        # Try rendered path
        render_dir = os.path.join(os.path.dirname(__file__), "static", "clipper", "projects", project.id, "renders")
        rendered = os.path.join(render_dir, f"{clip_id}.mp4")
        # Also check exports
        export_dir = os.path.join(os.path.dirname(__file__), "static", "clipper", "projects", project.id, "exports", project.target_platform)
        exported = os.path.join(export_dir, f"{clip_id}.mp4")

        # Determine which file exists to build URL; if none, use clip_id as filename and rely on clip video endpoint
        if os.path.exists(rendered):
            clip_video_url = f"{video_base_url.rstrip('/')}/static/clipper/projects/{project.id}/renders/{clip_id}.mp4" if video_base_url else f"{request.host_url.rstrip('/')}/static/clipper/projects/{project.id}/renders/{clip_id}.mp4"
        elif os.path.exists(exported):
            clip_video_url = f"{video_base_url.rstrip('/')}/static/clipper/projects/{project.id}/exports/{project.target_platform}/{clip_id}.mp4" if video_base_url else f"{request.host_url.rstrip('/')}/static/clipper/projects/{project.id}/exports/{project.target_platform}/{clip_id}.mp4"
        else:
            # Fallback: stream via clip video endpoint (requires range support, but MagicSync will fetch)
            clip_video_url = f"{video_base_url.rstrip('/')}/api/clipper/clip/{clip_id}/video" if video_base_url else f"{request.host_url.rstrip('/')}/api/clipper/clip/{clip_id}/video"

        payload = {
            "content": content,
            "platforms": platforms,
            "media": {"video": clip_video_url},
        }
        if title: payload["title"] = title
        if description: payload["description"] = description
        if scheduled_at: payload["scheduledAt"] = scheduled_at
        if visibility: payload["visibility"] = visibility

        target_url = f"{url}/api/v1/cli/post"
        resp = requests.post(target_url, headers={"Content-Type": "application/json", "x-api-key": api_token}, json=payload, timeout=30)

        # Persist a publish record either way (success → scheduled, failure → error)
        try:
            project_store.save_publish_record(project.id, {
                "clip_id": clip_id,
                "clip_hook_title": clip.hook_title,
                "platforms": platforms,
                "scheduled_at": scheduled_at or "",
                "visibility": visibility,
                "title": title or clip.hook_title,
                "video_url": clip_video_url,
                "status": "scheduled" if resp.status_code == 200 else "error",
                "response": resp.text[:1000],
            })
        except Exception as rec_err:
            print(colored(f"[-] Failed to save publish record: {rec_err}", "yellow"))

        if resp.status_code == 200:
            return jsonify({"status": "success", "data": resp.json()})
        else:
            return jsonify({"status": "error", "message": f"MagicSync error: {resp.text}"}), 502
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@clipper_bp.route("/transcript/<project_id>/<source_id>", methods=["GET"])
def get_transcript(project_id, source_id):
    """Get transcript for a source video."""
    transcript = project_store.get_transcript(project_id, source_id)
    if transcript is None:
        return jsonify({"status": "error", "message": "Transcript not found"}), 404
    return jsonify({
        "status": "success",
        "data": transcript.to_dict()
    })


@clipper_bp.route("/export", methods=["POST"])
def export_clips():
    """Batch export clips using real per-platform presets.

    Body: {project_id, clip_ids?, format (tiktok|reels|shorts|douyin|xiaohongshu|bilibili|youtube),
           quality (high|medium|low), burn_subtitles (bool, default true)}
    """
    global CLIPPER_STATE
    from classes.Clipper import resolve_export_preset, ClipperCancelled, EXPORT_PRESETS
    CLIPPER_STATE["generating"] = True

    try:
        data = request.get_json()
        project_id = data.get("project_id")
        clip_ids = data.get("clip_ids", [])
        format_type = data.get("format", "tiktok")
        quality = data.get("quality", "medium")
        burn_subtitles = data.get("burn_subtitles", True)

        if format_type not in EXPORT_PRESETS:
            return jsonify({"status": "error",
                            "message": f"Unknown format '{format_type}'. Supported: {', '.join(EXPORT_PRESETS)}"}), 400

        preset = resolve_export_preset(format_type, quality)

        project = project_store.get_project(project_id)
        if project is None:
            return jsonify({"status": "error", "message": "Project not found"}), 404

        clips = project_store.get_clips(project_id)
        if clip_ids:
            clips = [c for c in clips if c.id in clip_ids]

        output_dir = os.path.join(
            os.path.dirname(__file__), "static", "clipper", "projects", project_id, "exports", format_type
        )
        os.makedirs(output_dir, exist_ok=True)

        clipper = Clipper(project)
        results = []

        for i, clip in enumerate(clips):
            set_clipper_progress(
                project_id,
                stage="rendering",
                progress=i / max(1, len(clips)),
                message=f"Exporting clip {i + 1}/{len(clips)} ({format_type}, {quality})",
                current_clip=i + 1,
                total_clips=len(clips),
                preview_url=clip.thumbnail_url or "",
            )

            output_path = clipper.render_clip(
                clip,
                output_dir,
                aspect=preset["aspect"],
                crf=preset["crf"],
                encode_preset=preset["preset"],
                burn_subtitles=burn_subtitles,
            )
            results.append({
                "clip_id": clip.id,
                "status": "success" if output_path else "failed",
                "output_url": f"/static/clipper/projects/{project_id}/exports/{format_type}/{os.path.basename(output_path)}" if output_path else None
            })

        set_clipper_progress(
            project_id,
            stage="done",
            progress=1.0,
            message=f"Exported {sum(1 for r in results if r['status'] == 'success')}/{len(clips)} clips to {format_type}",
        )

        return jsonify({
            "status": "success",
            "data": {
                "results": results,
                "preset": {k: v for k, v in preset.items()},
            }
        })
    except ClipperCancelled as e:
        return jsonify({"status": "cancelled", "message": str(e)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        CLIPPER_STATE["generating"] = False


def register_clipper_routes(app):
    """Register CLIPPER blueprint with Flask app."""
    app.register_blueprint(clipper_bp)
