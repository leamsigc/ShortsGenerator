#!/usr/bin/env python3
"""
CLIPPER MCP Server

Provides Model Context Protocol tools for CLIPPER operations.
Run standalone: python -m Backend.mcp.clipper_mcp
Or integrate with existing Flask app.
"""

import os
import sys
import json
import asyncio
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classes.ClipperProject import ClipperProject, ClipTemplate, project_store, ClipSegment
from classes.Clipper import Clipper

# Backend/ root (this file lives in Backend/mcp/) — static assets resolve from here
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ClipperMCPServer:
    """
    MCP server implementation for CLIPPER.
    Exposes tools for project management, clip selection, and rendering.
    """

    def __init__(self):
        self.tools = self._define_tools()

    def _define_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "list_projects",
                "description": "List all CLIPPER projects",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "create_project",
                "description": "Create a new CLIPPER project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Project name"},
                        "description": {"type": "string", "description": "Project description"},
                        "source_urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Source video URLs",
                        },
                        "training_data": {
                            "type": "string",
                            "description": "Content guidelines and viral patterns",
                        },
                        "target_platform": {
                            "type": "string",
                            "enum": ["tiktok", "reels", "shorts"],
                            "default": "tiktok",
                        },
                    },
                    "required": ["name", "source_urls"],
                },
            },
            {
                "name": "get_project",
                "description": "Get project details by ID",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                    },
                    "required": ["project_id"],
                },
            },
            {
                "name": "delete_project",
                "description": "Delete a project by ID",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                    },
                    "required": ["project_id"],
                },
            },
            {
                "name": "process_project",
                "description": "Download and transcribe source videos in a project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "language": {"type": "string", "default": "en"},
                    },
                    "required": ["project_id"],
                },
            },
            {
                "name": "get_clips",
                "description": "Get clips for a project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "min_score": {
                            "type": "number",
                            "description": "Minimum overall score filter",
                            "default": 0.0,
                        },
                    },
                    "required": ["project_id"],
                },
            },
            {
                "name": "select_clips",
                "description": "AI-select top clips from scored segments",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "max_clips": {"type": "number", "default": 7},
                        "ai_model": {"type": "string", "default": "llm"},
                        "min_duration": {"type": "number", "default": 30.0},
                        "max_duration": {"type": "number", "default": 90.0},
                    },
                    "required": ["project_id"],
                },
            },
            {
                "name": "render_clip",
                "description": "Render a specific clip",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "clip_id": {"type": "string"},
                        "face_x": {"type": "number", "default": 0.5},
                        "face_y": {"type": "number", "default": 0.35},
                    },
                    "required": ["clip_id"],
                },
            },
            {
                "name": "trim_clip",
                "description": "Adjust clip start/end times",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "clip_id": {"type": "string"},
                        "start_time": {"type": "number"},
                        "end_time": {"type": "number"},
                    },
                    "required": ["clip_id"],
                },
            },
            {
                "name": "export_clips",
                "description": "Batch export clips with a platform preset",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "clip_ids": {"type": "array", "items": {"type": "string"}},
                        "format": {
                            "type": "string",
                            "enum": ["tiktok", "reels", "shorts", "douyin", "xiaohongshu", "bilibili", "youtube"],
                            "default": "tiktok",
                        },
                        "quality": {"type": "string", "enum": ["high", "medium", "low"], "default": "medium"},
                        "burn_subtitles": {"type": "boolean", "default": True},
                    },
                    "required": ["project_id"],
                },
            },
            {
                "name": "split_clip",
                "description": "Split a clip into two at a given timestamp",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "clip_id": {"type": "string"},
                        "split_time": {"type": "number"},
                    },
                    "required": ["clip_id", "split_time"],
                },
            },
            {
                "name": "merge_clips",
                "description": "Merge clips into a compilation video (rendered via ffmpeg concat)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "clip_ids": {"type": "array", "items": {"type": "string"}},
                        "output_name": {"type": "string", "default": "merged"},
                        "render": {"type": "boolean", "default": True},
                    },
                    "required": ["project_id", "clip_ids"],
                },
            },
            {
                "name": "get_transcript",
                "description": "Get transcript + topic outline for a source video",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "source_id": {"type": "string"},
                    },
                    "required": ["project_id", "source_id"],
                },
            },
        ]

    async def list_tools(self) -> List[Dict[str, Any]]:
        return self.tools

    async def call_tool(
        self, name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route tool call to appropriate handler."""
        handler = getattr(self, f"_handle_{name}", None)
        if handler is None:
            return {"error": f"Unknown tool: {name}"}

        try:
            result = await handler(arguments)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}

    async def _handle_list_projects(self, args: Dict[str, Any]) -> Dict[str, Any]:
        projects = project_store.list_projects()
        return {"projects": [p.to_dict() for p in projects]}

    async def _handle_create_project(self, args: Dict[str, Any]) -> Dict[str, Any]:
        import uuid
        from datetime import datetime

        name = args["name"]
        source_urls = args["source_urls"]
        description = args.get("description", "")
        training_data = args.get("training_data", "")
        target_platform = args.get("target_platform", "tiktok")

        project_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        project = ClipperProject(
            id=project_id,
            name=name,
            description=description,
            source_urls=source_urls,
            training_data=training_data,
            template=ClipTemplate(),
            target_platform=target_platform,
            created_at=now,
            updated_at=now,
            source_ids=[str(uuid.uuid4()) for _ in source_urls],
        )

        project_store.create_project(project)
        return {"project": project.to_dict()}

    async def _handle_get_project(self, args: Dict[str, Any]) -> Dict[str, Any]:
        project_id = args["project_id"]
        project = project_store.get_project(project_id)
        if project is None:
            return {"error": "Project not found"}
        return {"project": project.to_dict()}

    async def _handle_delete_project(self, args: Dict[str, Any]) -> Dict[str, Any]:
        project_id = args["project_id"]
        if project_store.delete_project(project_id):
            return {"message": "Project deleted"}
        return {"error": "Project not found"}

    async def _handle_process_project(self, args: Dict[str, Any]) -> Dict[str, Any]:
        project_id = args["project_id"]
        language = args.get("language", "en")
        model_size = args.get("model_size")

        project = project_store.get_project(project_id)
        if project is None:
            return {"error": "Project not found"}

        from llm_providers import get_clipper_ai_model
        clipper = Clipper(project)
        results = clipper.process_sources(
            language=language,
            model_size=model_size,
            ai_model=get_clipper_ai_model(),
        )

        return {"sources": results}

    async def _handle_get_clips(self, args: Dict[str, Any]) -> Dict[str, Any]:
        project_id = args["project_id"]
        min_score = args.get("min_score", 0.0)

        clips = project_store.get_clips(project_id)
        if min_score > 0:
            clips = [c for c in clips if c.scores.overall_score >= min_score]

        return {"clips": [c.to_dict() for c in clips]}

    async def _handle_select_clips(self, args: Dict[str, Any]) -> Dict[str, Any]:
        project_id = args["project_id"]
        max_clips = args.get("max_clips", 7)
        from llm_providers import get_clipper_ai_model
        ai_model = args.get("ai_model", get_clipper_ai_model())
        min_duration = args.get("min_duration", 30.0)
        max_duration = args.get("max_duration", 90.0)

        project = project_store.get_project(project_id)
        if project is None:
            return {"error": "Project not found"}

        clipper = Clipper(project)
        clips = clipper.generate_clips(max_clips, ai_model, min_duration, max_duration)

        return {"clips": [c.to_dict() for c in clips]}

    async def _handle_render_clip(self, args: Dict[str, Any]) -> Dict[str, Any]:
        clip_id = args["clip_id"]
        face_x = args.get("face_x", 0.5)
        face_y = args.get("face_y", 0.35)

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

        if clip is None:
            return {"error": "Clip not found"}

        output_dir = os.path.join(
            BACKEND_DIR, "static", "clipper", "projects", project.id, "renders"
        )
        os.makedirs(output_dir, exist_ok=True)

        clipper = Clipper(project)
        output_path = clipper.render_clip(clip, output_dir, face_x, face_y)

        if output_path:
            clip.status = "rendered"
            project_store.save_clip(clip)
            return {
                "clip": clip.to_dict(),
                "output_url": f"/static/clipper/projects/{project.id}/renders/{os.path.basename(output_path)}"
            }
        return {"error": "Render failed"}

    async def _handle_trim_clip(self, args: Dict[str, Any]) -> Dict[str, Any]:
        clip_id = args["clip_id"]
        start_time = args.get("start_time")
        end_time = args.get("end_time")

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
                    return {"clip": clip.to_dict()}
        return {"error": "Clip not found"}

    async def _handle_export_clips(self, args: Dict[str, Any]) -> Dict[str, Any]:
        project_id = args["project_id"]
        clip_ids = args.get("clip_ids", [])
        format_type = args.get("format", "tiktok")
        quality = args.get("quality", "medium")
        burn_subtitles = args.get("burn_subtitles", True)

        from classes.Clipper import resolve_export_preset
        preset = resolve_export_preset(format_type, quality)

        project = project_store.get_project(project_id)
        if project is None:
            return {"error": "Project not found"}

        clips = project_store.get_clips(project_id)
        if clip_ids:
            clips = [c for c in clips if c.id in clip_ids]

        output_dir = os.path.join(
            BACKEND_DIR, "static", "clipper", "projects", project_id, "exports", format_type
        )
        os.makedirs(output_dir, exist_ok=True)

        clipper = Clipper(project)
        results = []

        for clip in clips:
            output_path = clipper.render_clip(
                clip, output_dir,
                aspect=preset["aspect"], crf=preset["crf"],
                encode_preset=preset["preset"], burn_subtitles=burn_subtitles,
            )
            results.append({
                "clip_id": clip.id,
                "status": "success" if output_path else "failed",
                "output_url": f"/static/clipper/projects/{project_id}/exports/{format_type}/{os.path.basename(output_path)}" if output_path else None
            })

        return {"results": results, "preset": {k: v for k, v in preset.items()}}

    async def _handle_split_clip(self, args: Dict[str, Any]) -> Dict[str, Any]:
        clip_id = args["clip_id"]
        split_time = float(args["split_time"])

        for project in project_store.list_projects():
            for clip in project_store.get_clips(project.id):
                if clip.id == clip_id:
                    if split_time <= clip.start_time or split_time >= clip.end_time:
                        return {"error": "Invalid split time (must be inside the clip)"}
                    import uuid as _uuid
                    clip1 = ClipSegment(
                        id=str(_uuid.uuid4()), project_id=project.id, source_id=clip.source_id,
                        index=clip.index, start_time=clip.start_time, end_time=split_time,
                        duration=split_time - clip.start_time, transcript=clip.transcript,
                        scores=clip.scores, hook_title=clip.hook_title, status="pending",
                        face_x=clip.face_x, face_y=clip.face_y,
                    )
                    clip2 = ClipSegment(
                        id=str(_uuid.uuid4()), project_id=project.id, source_id=clip.source_id,
                        index=clip.index + 1, start_time=split_time, end_time=clip.end_time,
                        duration=clip.end_time - split_time, transcript="",
                        scores=clip.scores, hook_title="", status="pending",
                        face_x=clip.face_x, face_y=clip.face_y,
                    )
                    clip.status = "split"
                    project_store.save_clip(clip)
                    project_store.save_clip(clip1)
                    project_store.save_clip(clip2)
                    return {"clip1": clip1.to_dict(), "clip2": clip2.to_dict()}
        return {"error": "Clip not found"}

    async def _handle_merge_clips(self, args: Dict[str, Any]) -> Dict[str, Any]:
        project_id = args["project_id"]
        clip_ids = args["clip_ids"]
        output_name = args.get("output_name", "merged")
        render = args.get("render", True)

        project = project_store.get_project(project_id)
        if project is None:
            return {"error": "Project not found"}
        if len(clip_ids) < 2:
            return {"error": "At least 2 clips required"}

        matched = [c for c in project_store.get_clips(project_id) if c.id in clip_ids]
        if len(matched) < 2:
            return {"error": "Matching clips not found"}

        import uuid as _uuid
        best = max(matched, key=lambda c: c.scores.overall_score)
        merged = ClipSegment(
            id=str(_uuid.uuid4()), project_id=project_id,
            source_id=matched[0].source_id,
            index=max(c.index for c in matched),
            start_time=min(c.start_time for c in matched),
            end_time=max(c.end_time for c in matched),
            duration=sum(c.duration for c in matched),
            transcript=" ".join(c.transcript for c in matched if c.transcript),
            scores=best.scores, hook_title=output_name, status="pending",
            is_compilation=True, source_clip_ids=[c.id for c in matched],
        )
        project_store.save_clip(merged)

        output_url = None
        if render:
            clipper = Clipper(project)
            renders_dir = os.path.join(BACKEND_DIR, "static", "clipper", "projects", project_id, "renders")
            output_path = clipper.render_compilation(merged, renders_dir)
            if output_path:
                output_url = f"/static/clipper/projects/{project_id}/renders/{os.path.basename(output_path)}"
            else:
                return {"error": "Compilation render failed", "clip": merged.to_dict()}

        return {**merged.to_dict(), "output_url": output_url}

    async def _handle_get_transcript(self, args: Dict[str, Any]) -> Dict[str, Any]:
        transcript = project_store.get_transcript(args["project_id"], args["source_id"])
        if transcript is None:
            return {"error": "Transcript not found"}
        return {"transcript": transcript.to_dict()}


async def run_stdio_server():
    """Run MCP server with stdio transport (newline-delimited JSON-RPC 2.0)."""
    server = ClipperMCPServer()
    server_info = {"name": "clipper", "version": "1.0.0"}

    def jsonrpc_response(req_id, result):
        return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result})

    def jsonrpc_error(req_id, code, message):
        return json.dumps({"jsonrpc": "2.0", "id": req_id,
                           "error": {"code": code, "message": message}})

    async def handle_request(request: Dict[str, Any]) -> Optional[str]:
        method = request.get("method", "")
        params = request.get("params", {}) or {}
        req_id = request.get("id")

        # Notifications (no id) get no response
        if req_id is None:
            return None

        if method == "initialize":
            return jsonrpc_response(req_id, {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": server_info,
            })
        if method == "ping":
            return jsonrpc_response(req_id, {})
        if method == "tools/list":
            return jsonrpc_response(req_id, {"tools": await server.list_tools()})
        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {}) or {}
            result = await server.call_tool(tool_name, arguments)
            if "error" in result:
                return jsonrpc_response(req_id, {
                    "content": [{"type": "text", "text": json.dumps(result)}],
                    "isError": True,
                })
            return jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result.get("result", result))}],
            })
        return jsonrpc_error(req_id, -32601, f"Method not found: {method}")

    import sys
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = await handle_request(request)
            if response is not None:
                print(response, flush=True)
        except Exception as e:
            try:
                req_id = json.loads(line).get("id")
            except Exception:
                req_id = None
            print(jsonrpc_error(req_id, -32700, str(e)), flush=True)


if __name__ == "__main__":
    asyncio.run(run_stdio_server())
