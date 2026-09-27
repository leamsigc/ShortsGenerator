#!/usr/bin/env python3
"""
CLIPPER CLI — batch processing from the terminal.

Usage:
  python clipper_cli.py create --name "My Project" --url https://youtube.com/watch?v=...
  python clipper_cli.py process --project PROJECT_ID [--language en] [--model-size base]
  python clipper_cli.py select  --project PROJECT_ID [--max-clips 7]
  python clipper_cli.py render  --project PROJECT_ID --clip CLIP_ID
  python clipper_cli.py export  --project PROJECT_ID [--clips id1,id2] [--format shorts] [--quality high]
  python clipper_cli.py list
  python clipper_cli.py delete  --project PROJECT_ID
  python clipper_cli.py doctor [--provider ollama]

Mirrors the AutoClip CLI surface (create → process → select → export) on top
of the same pipeline the Flask app and MCP server use.
"""
import os
import sys
import json
import argparse
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from termcolor import colored


def _load_store():
    from classes.ClipperProject import project_store
    return project_store


def _get_project(project_id):
    store = _load_store()
    project = store.get_project(project_id)
    if project is None:
        print(colored(f"[-] Project not found: {project_id}", "red"))
        sys.exit(1)
    return project, store


def cmd_create(args):
    from classes.ClipperProject import ClipperProject, ClipTemplate
    store = _load_store()
    now = datetime.utcnow().isoformat()
    source_urls = [u.strip() for u in (args.url or []) if u.strip()]
    project = ClipperProject(
        id=str(uuid.uuid4()),
        name=args.name,
        description=args.description or "",
        source_urls=source_urls,
        training_data=args.training_data or "",
        template=ClipTemplate(),
        target_platform=args.platform,
        created_at=now,
        updated_at=now,
        source_ids=[str(uuid.uuid4()) for _ in source_urls],
    )
    store.create_project(project)
    print(colored(f"[+] Created project {project.id} ({project.name}) with {len(source_urls)} source(s)", "green"))
    if args.json:
        print(json.dumps(project.to_dict(), indent=2))
    return project.id


def cmd_process(args):
    project, store = _get_project(args.project)
    from classes.Clipper import Clipper
    from llm_providers import get_clipper_ai_model

    clipper = Clipper(project)
    results = clipper.process_sources(
        language=args.language,
        model_size=args.model_size,
        ai_model=get_clipper_ai_model(),
    )
    if args.auto_select:
        clipper.generate_clips(max_clips=args.max_clips, ai_model=get_clipper_ai_model())
    print(colored("[+] Processing complete", "green"))
    if args.json:
        print(json.dumps(results, indent=2, default=str))


def cmd_select(args):
    project, store = _get_project(args.project)
    from classes.Clipper import Clipper
    from llm_providers import get_clipper_ai_model

    clipper = Clipper(project)
    clips = clipper.generate_clips(max_clips=args.max_clips, ai_model=get_clipper_ai_model())
    print(colored(f"[+] Selected {len(clips)} clips", "green"))
    for c in clips:
        print(f"  [{c.scores.overall_score:5.1f}] {c.start_time:7.1f}s-{c.end_time:7.1f}s  {c.hook_title}")
    if args.json:
        print(json.dumps([c.to_dict() for c in clips], indent=2))


def cmd_render(args):
    project, store = _get_project(args.project)
    from classes.Clipper import Clipper
    clipper = Clipper(project)
    clip = next((c for c in store.get_clips(project.id) if c.id == args.clip), None)
    if clip is None:
        print(colored(f"[-] Clip not found: {args.clip}", "red"))
        sys.exit(1)
    output_dir = os.path.join(os.path.dirname(__file__), "static", "clipper", "projects", project.id, "renders")
    os.makedirs(output_dir, exist_ok=True)
    path = clipper.render_clip(clip, output_dir)
    if path:
        print(colored(f"[+] Rendered: {path}", "green"))
    else:
        print(colored("[-] Render failed", "red"))
        sys.exit(1)


def cmd_export(args):
    project, store = _get_project(args.project)
    from classes.Clipper import Clipper, resolve_export_preset, EXPORT_PRESETS
    if args.format not in EXPORT_PRESETS:
        print(colored(f"[-] Unknown format '{args.format}'. Supported: {', '.join(EXPORT_PRESETS)}", "red"))
        sys.exit(1)

    clips = store.get_clips(project.id)
    if args.clips:
        wanted = {c.strip() for c in args.clips.split(",") if c.strip()}
        clips = [c for c in clips if c.id in wanted]
    if not clips:
        print(colored("[-] No clips to export (run 'select' first)", "red"))
        sys.exit(1)

    preset = resolve_export_preset(args.format, args.quality)
    output_dir = os.path.join(
        os.path.dirname(__file__), "static", "clipper", "projects", project.id, "exports", args.format
    )
    os.makedirs(output_dir, exist_ok=True)

    clipper = Clipper(project)
    ok = 0
    for clip in clips:
        path = clipper.render_clip(
            clip, output_dir,
            aspect=preset["aspect"], crf=preset["crf"],
            encode_preset=preset["preset"], burn_subtitles=not args.no_subtitles,
        )
        status = "ok" if path else "FAILED"
        if path:
            ok += 1
        print(f"  {clip.id} ({clip.hook_title}): {status} -> {path or ''}")
    print(colored(f"[+] Exported {ok}/{len(clips)} clips as {args.format}/{args.quality}", "green" if ok else "red"))


def cmd_list(args):
    store = _load_store()
    projects = store.list_projects()
    if not projects:
        print(colored("[*] No projects yet (create one with 'create')", "cyan"))
        return
    for p in projects:
        clips = store.get_clips(p.id)
        print(f"{p.id}  [{p.status:>12}]  {p.name}  ({len(p.source_urls)} sources, {len(clips)} clips)")


def cmd_delete(args):
    store = _load_store()
    if store.delete_project(args.project):
        print(colored(f"[+] Deleted project {args.project}", "green"))
    else:
        print(colored("[-] Project not found", "red"))
        sys.exit(1)


def cmd_doctor(args):
    """Health check: ffmpeg, whisper model, yt-dlp, LLM provider."""
    from shutil import which
    checks = []

    checks.append(("ffmpeg", bool(which("ffmpeg"))))
    checks.append(("ffprobe", bool(which("ffprobe"))))

    try:
        import yt_dlp
        checks.append(("yt-dlp", True))
    except ImportError:
        checks.append(("yt-dlp", False))

    try:
        import faster_whisper
        checks.append(("faster-whisper", True))
    except ImportError:
        checks.append(("faster-whisper", False))

    from llm_providers import get_llm_settings, test_llm_connection, PROVIDERS
    if args.provider:
        update = {"provider": args.provider}
        if args.provider == "ollama" and not get_llm_settings().get("base_url"):
            update["base_url"] = "http://localhost:11434/v1"
        from llm_providers import update_llm_settings
        update_llm_settings(update)

    settings = get_llm_settings()
    llm = test_llm_connection()
    checks.append((f"LLM provider '{settings['provider']}' ({settings['model'] or 'default model'})", llm["ok"]))

    all_ok = True
    for name, ok in checks:
        print(f"  {'[+]' if ok else '[-]'} {name}" + ("" if ok else f"  -- {llm['detail'][:120] if name.startswith('LLM') else 'missing'}"))
        all_ok = all_ok and ok
    print(colored("[+] Doctor: all systems go" if all_ok else "[-] Doctor: issues found", "green" if all_ok else "red"))
    if not all_ok:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(prog="clipper", description="CLIPPER — AI video clip generator (CLI)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create", help="Create a project")
    p.add_argument("--name", required=True)
    p.add_argument("--url", action="append", help="Source URL (repeatable)")
    p.add_argument("--description", default="")
    p.add_argument("--training-data", default="")
    p.add_argument("--platform", default="tiktok", choices=["tiktok", "reels", "shorts"])
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("process", help="Download + transcribe sources")
    p.add_argument("--project", required=True)
    p.add_argument("--language", default="en")
    p.add_argument("--model-size", default=None)
    p.add_argument("--max-clips", type=int, default=7)
    p.add_argument("--auto-select", action="store_true", default=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_process)

    p = sub.add_parser("select", help="Score + select top clips")
    p.add_argument("--project", required=True)
    p.add_argument("--max-clips", type=int, default=7)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_select)

    p = sub.add_parser("render", help="Render one clip")
    p.add_argument("--project", required=True)
    p.add_argument("--clip", required=True)
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("export", help="Batch export clips with a platform preset")
    p.add_argument("--project", required=True)
    p.add_argument("--clips", default="", help="Comma-separated clip ids (default: all)")
    p.add_argument("--format", default="shorts",
                   choices=["tiktok", "reels", "shorts", "douyin", "xiaohongshu", "bilibili", "youtube"])
    p.add_argument("--quality", default="medium", choices=["high", "medium", "low"])
    p.add_argument("--no-subtitles", action="store_true", help="Disable subtitle burn-in")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("list", help="List projects")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("delete", help="Delete a project")
    p.add_argument("--project", required=True)
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("doctor", help="Health check (ffmpeg, whisper, yt-dlp, LLM)")
    p.add_argument("--provider", default=None, choices=["g4f", "openai", "ollama", "gemini", "qwen"])
    p.set_defaults(func=cmd_doctor)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
