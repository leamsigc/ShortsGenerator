import os
import subprocess
import requests
from datetime import datetime
from utils import *
from dotenv import load_dotenv

# Load environment variables
# check if .env is in the folder or look one more level up
if os.path.exists(".env"):
    load_dotenv(".env")
else:
    load_dotenv("../.env")
# Check if all required environment variables are set
# This must happen before importing video which uses API keys without checking
check_env_vars()

from gpt import *
from video import *
from search import *
from classes.Shorts import *
from uuid import uuid4
from tiktokvoice import *
from settings import *
from flask_cors import CORS
from termcolor import colored
from youtube import upload_video
from apiclient.errors import HttpError
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from moviepy.config import change_settings
from classes.instagram_downloader import InstagramDownloader
from leadgen.adapters.devtools_adapter import DevToolsAdapter
from leadgen.enrichment import enrich_campaign_description, enrich_campaign_with_website, enhance_profile_analysis, find_related_niche_queries, suggest_engagement, analyze_competitor, analyze_viral_post, generate_lead_keywords, generate_engagement_keywords, generate_synthetic_leads, qualify_search_results
from leadgen.campaign_store import create_campaign, get_campaigns, get_campaign, delete_campaign, add_lead, get_leads, add_competitor, remove_competitor, add_viral_post
from clipper_routes import register_clipper_routes

# Set environment variables
SESSION_ID = os.getenv("TIKTOK_SESSION_ID")
openai_api_key = os.getenv('OPENAI_API_KEY')
change_settings({"IMAGEMAGICK_BINARY": os.getenv("IMAGEMAGICK_BINARY")})


# Initialize Flask
app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app, origins="*", supports_credentials=True, expose_headers=[
    "Content-Range", "Accept-Ranges", "Content-Length",
    "Cache-Control", "Content-Type", "Content-Disposition"
])

register_clipper_routes(app)

# Constants
HOST = "0.0.0.0"
PORT = 8080
AMOUNT_OF_STOCK_VIDEOS = 5
GENERATING = False

# Create a method to create all the required folders
def create_folders():
    """Create all required folders for the application"""
    folders = [
        "static",
        "static/assets",
        "static/assets/temp",
        "static/assets/subtitles",
        "static/assets/custom_audio",
        "static/generated_videos",
        "static/generated_videos/instagram",
        "static/clipper",
        "static/clipper/projects",
    ]
    
    for folder in folders:
        folder_path = os.path.join(os.path.dirname(__file__), folder)
        os.makedirs(folder_path, exist_ok=True)
        print(f"Created/verified folder: {folder_path}")

# Create folders
create_folders()

# Instagram video download endpoint
@app.route("/api/instagram/download", methods=["POST"])
def download_instagram_video():
    try:
        data = request.get_json()
        video_url = data.get('url')
        
        if not video_url:
            return jsonify({
                "status": "error",
                "message": "No Instagram URL provided",
            }), 400

        # Initialize downloader with output path in static/assets
        downloader = InstagramDownloader(
            output_path=os.path.join(os.path.dirname(__file__), "static/generated_videos/instagram"),
            cookies_from_browser='chrome',
        )
        
        # Download the video
        result = downloader.download_video(video_url)
        
        return jsonify({
            "status": "success",
            "message": "Video downloaded successfully",
            "data": result
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


# Generation Endpoint
@app.route("/api/generate", methods=["POST"])
def generate():
    try:
        # Set global variable
        global GENERATING
        GENERATING = True

        # Clean
        clean_dir(os.path.join(os.path.dirname(__file__), "static/assets/temp/"))
        clean_dir(os.path.join(os.path.dirname(__file__), "static/assets/subtitles/"))


        # Parse JSON
        data = request.get_json()
        paragraph_number = int(data.get('paragraphNumber', 1))  # Default to 1 if not provided
        ai_model = data.get('aiModel')  # Get the AI model selected by the user
        n_threads = data.get('threads')  # Amount of threads to use for video generation
        subtitles_position = data.get('subtitlesPosition')  # Position of the subtitles in the video

        # Get 'useMusic' from the request data and default to False if not provided
        use_music = data.get('useMusic', False)

        # Get 'automateYoutubeUpload' from the request data and default to False if not provided
        automate_youtube_upload = data.get('automateYoutubeUpload', False)
        # Print little information about the video which is to be generated
        print(colored("[Video to be generated]", "blue"))
        print(colored("   Subject: " + data["videoSubject"], "blue"))
        print(colored("   AI Model: " + ai_model, "blue"))  # Print the AI model being used
        print(colored("   Custom Prompt: " + data["customPrompt"], "blue"))  # Print the AI model being used



        if not GENERATING:
            return jsonify(
                {
                    "status": "error",
                    "message": "Video generation was cancelled.",
                    "data": [],
                }
            )
        
        voice = data["voice"]
        voice_prefix = voice[:2]


        if not voice:
            print(colored("[!] No voice was selected. Defaulting to \"en_us_001\"", "yellow"))
            voice = "en_us_001"
            voice_prefix = voice[:2]


        script_template = data.get("scriptTemplate", "")
        selectedVideoUrls = data.get("selectedVideoUrls", [])
        directVideoPaths = data.get("directVideoPaths", [])
        images = data.get("images", [])
        image_duration = data.get("imageDuration", 5.0)
        image_durations = data.get("imageDurations", [])
        clip_duration = int(data.get("clipDuration", 10))
        videoClass = Shorts(data["videoSubject"], paragraph_number, ai_model, data["customPrompt"], script_template=script_template)
        videoClass.clip_duration = clip_duration
        # Generate a script
        videoClass.GenerateScript()
        # Generate search terms
        videoClass.GenerateSearchTerms()

        if directVideoPaths and len(directVideoPaths) > 0:
            videoClass.video_paths = directVideoPaths
            print(colored(f"[+] Using {len(directVideoPaths)} pre-downloaded video(s): {directVideoPaths}", "green"))
        else:
            videoClass.DownloadVideos(selectedVideoUrls)

        if images:
            temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "assets", "temp"))
            resolved_images = []
            resolved_durations = []
            for i, img in enumerate(images):
                img_path = os.path.join(temp_dir, os.path.basename(img))
                if os.path.exists(img_path):
                    resolved_images.append(img_path)
                elif os.path.exists(img):
                    resolved_images.append(img)
                dur = float(image_durations[i]) if i < len(image_durations) and image_durations[i] else float(image_duration)
                resolved_durations.append(dur)
            videoClass.image_paths = resolved_images
            videoClass.image_durations = resolved_durations
            videoClass.image_duration = float(image_duration) if image_duration else 5.0
            print(colored(f"[+] Using {len(resolved_images)} image(s) with durations: {resolved_durations}", "green"))

        if not GENERATING:
            return jsonify(
                {
                    "status": "error",
                    "message": "Video generation was cancelled.",
                    "data": [],
                }
            )

        videoClass.GenerateVoice(voice)
        # Concatenate videos
        videoClass.CombineVideos()

        videoClass.GenerateMetadata()

        if automate_youtube_upload:
            # Start Youtube Uploader
            # Check if the CLIENT_SECRETS_FILE exists
            client_secrets_file = os.path.abspath("./client_secret.json")
            SKIP_YT_UPLOAD = False
            if not os.path.exists(client_secrets_file):
                SKIP_YT_UPLOAD = True
                print(colored("[-] Client secrets file missing. YouTube upload will be skipped.", "yellow"))
                print(colored("[-] Please download the client_secret.json from Google Cloud Platform and store this inside the /Backend directory.", "red"))

            # Only proceed with YouTube upload if the toggle is True  and client_secret.json exists.
            if not SKIP_YT_UPLOAD:
                # Choose the appropriate category ID for your videos
                video_category_id = "28"  # Science & Technology
                privacyStatus = "private"  # "public", "private", "unlisted"
                video_metadata = {
                    'video_path': os.path.abspath(f"../temp/{final_video_path}"),
                    'title': title,
                    'description': description,
                    'category': video_category_id,
                    'keywords': ",".join(keywords),
                    'privacyStatus': privacyStatus,
                }

                # Upload the video to YouTube
                try:
                    # Unpack the video_metadata dictionary into individual arguments
                    video_response = upload_video(
                        video_path=video_metadata['video_path'],
                        title=video_metadata['title'],
                        description=video_metadata['description'],
                        category=video_metadata['category'],
                        keywords=video_metadata['keywords'],
                        privacy_status=video_metadata['privacyStatus']
                    )
                    print(f"Uploaded video ID: {video_response.get('id')}")
                except HttpError as e:
                    print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")

        
        videoClass.AddMusic(use_music)
        # Let user know
        print(colored(f"[+] Video generated: {videoClass.get_final_video_path}!", "green"))
        videoClass.Stop()

        final_video_path = "/static" + videoClass.get_final_video_path.split("/static")[1]
        # Return JSON
        return jsonify(
            {
                "status": "success",
                "message": "Video generated! See MoneyPrinter/output.mp4 for result.",
                "data": final_video_path,
            }
        )
    except Exception as err:
        print(colored(f"[-] Error: {str(err)}", "red"))
        return jsonify(
            {
                "status": "error",
                "message": f"Could not retrieve stock videos: {str(err)}",
                "data": [],
            }
        )


@app.route("/api/cancel", methods=["POST"])
def cancel():
    print(colored("[!] Received cancellation request...", "yellow"))

    global GENERATING
    GENERATING = False

    return jsonify({"status": "success", "message": "Cancelled video generation."})

# Route to generate the script and return the video script
@app.route("/api/script", methods=["POST"])
def generate_script_only():
    # Set generating to true
    GENERATING = True

    clean_dir(os.path.join(os.path.dirname(__file__), "static/assets/subtitles/"))
    print(colored("[+] Received script request...", "green"))

    data = request.get_json()
    video_subject = data["videoSubject"]
    extra_prompt = data["extraPrompt"]
    ai_model = data["aiModel"]
    script_template = data.get("scriptTemplate", "")
    script_length = data.get("scriptLength", "standard")

    videoClass = Shorts(video_subject, 1, ai_model, "", extra_prompt=extra_prompt, script_template=script_template, script_length=script_length)
    script = videoClass.GenerateScript()



    search_terms = videoClass.GenerateSearchTerms()
    
    # Show the search terms 
    print(colored(f"Search terms: {', '.join(search_terms)}", "cyan"))

    return jsonify(
        {
            "status": "success",
            "message": "Script generated!",
            "data": {
                "script": script,
                "search": search_terms
            },
        }
    )

# Download the videos and split the script
@app.route("/api/search-and-download", methods=["POST"])
def search_and_download():
    # Set generating to true
    global GENERATING
    GENERATING = True

    
    print(colored("[+] Received search and download request...", "green"))

    data = request.get_json()
    search_terms = data["search"]
    script = data["script"]
    ai_model = data["aiModel"]
    voice = data["voice"]
    selectedVideoUrls = data.get("selectedVideoUrls",[])
    directVideoPaths = data.get("directVideoPaths", [])
    use_music = data.get("useMusic", False)

    # Extra options:
    custom_video = data.get("videoUrls",[])
    custom_voice = data.get("voiceUrl","")
    # Set the default subtitles_position to the center, bottom
    subtitles_position = data.get("subtitlesPosition", "center,bottom")
    n_threads = data.get('threads', 4)
    # Subtitle template, aspect ratio
    subtitle_template = data.get("subtitleTemplate", "classic")
    aspect_ratio = data.get("aspectRatio", "9:16")
    custom_subtitle = data.get("customSubtitle", "")
    custom_audio_path = data.get("customAudioPath", "")
    audio_start_time = data.get("audioStartTime", 0)
    audio_end_time = data.get("audioEndTime", 0)
    images = data.get("images", [])
    image_duration = data.get("imageDuration", 5.0)
    image_durations = data.get("imageDurations", [])

    if not voice:
        print(colored("[!] No voice was selected. Defaulting to \"en_us_001\"", "yellow"))
        voice = "en_us_001"
    # Search for a video of the given search term
    videoClass = Shorts("", 1, ai_model, '', script_template=data.get("scriptTemplate", ""))
    videoClass.search_terms = search_terms
    videoClass.final_script = script
    videoClass.subtitles_position = subtitles_position
    videoClass.subtitle_template = subtitle_template
    videoClass.aspect_ratio = aspect_ratio
    videoClass.custom_subtitle = custom_subtitle
    videoClass.clip_duration = int(data.get("clipDuration", 10))

    if directVideoPaths and len(directVideoPaths) > 0:
        videoClass.video_paths = directVideoPaths
        print(colored(f"[+] Using {len(directVideoPaths)} pre-downloaded video(s): {directVideoPaths}", "green"))
    else:
        videoClass.DownloadVideos(selectedVideoUrls)

    if images:
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "assets", "temp"))
        resolved_images = []
        resolved_durations = []
        for i, img in enumerate(images):
            img_path = os.path.join(temp_dir, os.path.basename(img))
            if os.path.exists(img_path):
                resolved_images.append(img_path)
            elif os.path.exists(img):
                resolved_images.append(img)
            dur = float(image_durations[i]) if i < len(image_durations) and image_durations[i] else float(image_duration)
            resolved_durations.append(dur)
        videoClass.image_paths = resolved_images
        videoClass.image_durations = resolved_durations
        videoClass.image_duration = float(image_duration) if image_duration else 5.0
        print(colored(f"[+] Using {len(resolved_images)} image(s) with durations: {resolved_durations}", "green"))

    tts_quality = data.get("quality", 8)
    tts_speed = data.get("speed", 1.05)
    tts_lang = data.get("tts_lang", None)
    if tts_lang:
        from settings import update_tts_settings
        update_tts_settings({"tts_lang": tts_lang})
    videoClass.GenerateVoice(voice, custom_audio_path=custom_audio_path, audio_start_time=audio_start_time, audio_end_time=audio_end_time, quality=tts_quality, speed=tts_speed)

    videoClass.CombineVideos()

    videoClass.GenerateMetadata()
    
    if use_music:
        videoClass.AddMusic(True)

    videoClass.Stop()



    # FInal videoClass.get_final_video_path
    print(colored(f"[X] Next FInal video: {videoClass.get_final_video_path}", "green"))
    # if final video path is None return status code 500
    if videoClass.get_final_video_path is None:
        return jsonify(
            {
                "status": "error",
                "message": "Video generation was cancelled.",
                "data": [],
            }
        ),500
    
    # Use music video path if music was added
    if use_music and videoClass.get_final_music_video_path:
        final_video_raw = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "generated_videos", videoClass.get_final_music_video_path))
    else:
        final_video_raw = videoClass.get_final_video_path

    # /home/myuser/MoneyPrinter/Backend/static  -> need to return only  /static/**
    final_video_path = "/static" + final_video_raw.split("/static")[1]
    
    # We also have the TTS path and subtitles path, which should be returned as paths accessible via standard static hosting
    final_audio_path = "/static" + videoClass.get_tts_path.split("/static")[1] if videoClass.get_tts_path else None
    final_subtitles_path = "/static" + videoClass.get_subtitles_path.split("/static")[1] if videoClass.get_subtitles_path else None

    return jsonify(
        {
            "status": "success",
            "message": "Search and download complete!",
            "data": {
                "finalAudio": final_audio_path,
                "subtitles": final_subtitles_path,
                # Should remove the complete path and just leave the 
                "finalVideo": final_video_path,
                "metadata": {
                    "title": videoClass.video_title,
                    "description": videoClass.video_description,
                    "tags": videoClass.video_tags if hasattr(videoClass, 'video_tags') else [],
                    "post_content": videoClass.video_post_content if hasattr(videoClass, 'video_post_content') else "",
                    "suggested_schedule": videoClass.suggested_schedule if hasattr(videoClass, 'suggested_schedule') else ""
                }
            }
        }
    )

# Add audio to the video
@app.route("/api/addAudio", methods=["POST"])
def addAudio():
    GENERATING = True
    data = request.get_json()
    final_video_path = data["finalVideo"]
    song_path = data.get("songPath", "")
    ai_model = data.get("aiModel", "g4f")
    music_source = data.get("musicSource", "library")
    background_music_from_video = data.get("backgroundMusicFromVideo", "")
    aspect_ratio = data.get("aspectRatio", "9:16")
    music_volume = data.get("musicVolume", 0.1)
    sfx_volume = data.get("sfxVolume", 0.9)
    sound_effects = data.get("soundEffects", [])

    # Resolve sound effects: accept library names or direct paths
    sfx_paths = []
    sfx_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "assets", "sfx"))
    for sfx in sound_effects:
        if isinstance(sfx, str):
            sfx = {"path": sfx}
        p = sfx.get("path", "")
        if not p:
            continue
        if not os.path.isabs(p) and not p.startswith("static/"):
            candidate = os.path.join(sfx_dir, p)
            p = candidate if os.path.exists(candidate) else p
        if os.path.exists(p):
            sfx_paths.append({"path": p, "startTime": sfx.get("startTime", 0)})
        else:
            print(colored(f"[-] SFX file not found, skipping: {p}", "yellow"))

    backend_dir = os.path.dirname(os.path.abspath(__file__))
    videoClass = Shorts("", 1, ai_model, '')
    videoClass.aspect_ratio = aspect_ratio
    videoClass.final_video_path = os.path.join(backend_dir, final_video_path.lstrip("/"))

    actual_song_path = song_path
    if music_source == "video":
        if background_music_from_video:
            if background_music_from_video.startswith("http://") or background_music_from_video.startswith("https://"):
                try:
                    temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "assets", "temp"))
                    os.makedirs(temp_dir, exist_ok=True)
                    local_video = save_video(background_music_from_video, directory=temp_dir)
                    if local_video and os.path.exists(local_video):
                        actual_song_path = local_video
                    else:
                        return jsonify(
                            {
                                "status": "error",
                                "message": "Could not download the source video to extract audio.",
                                "data": [],
                            }
                        ), 400
                except Exception as e:
                    return jsonify(
                        {
                            "status": "error",
                            "message": f"Error downloading source video: {str(e)}",
                            "data": [],
                        }
                    ), 500
            else:
                actual_song_path = background_music_from_video
        else:
            return jsonify(
                {
                    "status": "error",
                    "message": "No source video selected for music extraction.",
                    "data": [],
                }
            ), 400

    videoClass.AddMusic(
        True,
        actual_song_path,
        music_source=music_source if music_source == "video" else "library",
        music_volume=float(music_volume),
        sfx_paths=sfx_paths,
        sfx_volume=float(sfx_volume),
    )

    videoClass.Stop()
    final_music_path = videoClass.get_final_music_video_path
    if not final_music_path:
        return jsonify(
            {
                "status": "error",
                "message": "Could not add music to the video.",
                "data": [],
            }
        ), 500
    return jsonify(
        {
            "status": "success",
            "message": "Music added to the video successfully.",
            "data": {
                "finalVideo": "static/generated_videos/" + final_music_path
            }
        }
    )


@app.route("/api/upload-custom-audio", methods=["POST"])
def upload_custom_audio():
    audio_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "assets", "custom_audio"))
    os.makedirs(audio_dir, exist_ok=True)

    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "No file selected"}), 400

    allowed_ext = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".wma", ".mp4", ".mov", ".webm"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        return jsonify({"status": "error", "message": f"Unsupported format: {ext}"}), 400

    file_id = f"{uuid4()}{ext}"
    save_path = os.path.join(audio_dir, file_id)
    file.save(save_path)

    print(colored(f"[+] Uploaded custom audio: {file_id}", "green"))
    return jsonify({
        "status": "success",
        "message": "Audio uploaded",
        "data": {"filename": file_id, "path": os.path.join("static", "assets", "custom_audio", file_id)}
    })


@app.route("/api/upload-music", methods=["POST"])
def upload_music():
    music_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "assets", "music"))
    os.makedirs(music_dir, exist_ok=True)

    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "No file selected"}), 400

    allowed_ext = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".wma"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        return jsonify({"status": "error", "message": f"Unsupported audio format: {ext}. Allowed: {', '.join(allowed_ext)}"}), 400

    filename = secure_filename(file.filename)
    file.save(os.path.join(music_dir, filename))
    print(colored(f"[+] Uploaded music: {filename}", "green"))
    return jsonify({"status": "success", "message": f"Uploaded {filename}", "data": {"filename": filename}})


@app.route("/api/download-music-url", methods=["POST"])
def download_music_url():
    music_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "assets", "music"))
    temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "assets", "temp"))
    os.makedirs(music_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    data = request.get_json()
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"status": "error", "message": "No URL provided"}), 400

    try:
        import yt_dlp
        import subprocess
        import uuid
        import shutil

        print(colored(f"[X] Downloading video from: {url}", "blue"))

        download_id = str(uuid.uuid4())[:8]
        ydl_opts = {
            # Prefer H.264 (avc1): AV1 downloads fail to decode on platforms
            # without hardware AV1 support, and everything is re-encoded to
            # H.264 downstream anyway.
            "format": (
                "bestvideo[vcodec^=avc1]+bestaudio/"
                "best[vcodec^=avc1]/"
                "best[vcodec!^=av01]/"
                "best"
            ),
            "outtmpl": os.path.join(temp_dir, f"{download_id}.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            # `android` is the primary bot-gate bypass; `tv`/`tv_embedded` are
            # cookie-less fallbacks. Override with YTDLP_PLAYER_CLIENT env var.
            "player_client": [c.strip() for c in os.getenv(
                "YTDLP_PLAYER_CLIENT", "android,tv,tv_embedded,ios,mweb,android_vr"
            ).split(",") if c.strip()],
        }

        # Optional cookie auth when the IP is flagged by YouTube's bot-gate
        cookie_file = os.getenv("YTDLP_COOKIES")
        if cookie_file and os.path.exists(cookie_file):
            ydl_opts["cookiefile"] = cookie_file
        cookie_browser = os.getenv("YTDLP_COOKIES_FROM_BROWSER")
        if cookie_browser:
            ydl_opts["cookiesfrombrowser"] = (cookie_browser,)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
            title = info.get("title", "audio")

        if not os.path.exists(video_path):
            # try with mkv extension (yt-dlp merges to mkv sometimes)
            base = os.path.splitext(video_path)[0]
            for ext in [".mkv", ".webm", ".mp4"]:
                candidate = base + ext
                if os.path.exists(candidate):
                    video_path = candidate
                    break

        safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip()[:60]
        output_mp3 = os.path.join(music_dir, f"{safe_title}.mp3")

        print(colored(f"[X] Extracting audio to: {output_mp3}", "blue"))
        subprocess.run(
            ["ffmpeg", "-i", video_path, "-vn", "-acodec", "libmp3lame", "-ab", "192k", output_mp3, "-y"],
            capture_output=True, check=True
        )

        os.remove(video_path)

        final_name = os.path.basename(output_mp3)
        print(colored(f"[+] Downloaded and extracted audio: {final_name}", "green"))
        return jsonify({
            "status": "success",
            "message": f"Downloaded and extracted audio: {final_name}",
            "data": {"filename": final_name, "title": title}
        })

    except subprocess.CalledProcessError as e:
        print(colored(f"[-] FFmpeg error: {e.stderr.decode()[:200]}", "red"))
        return jsonify({"status": "error", "message": f"Audio extraction failed: {e.stderr.decode()[:200]}"}), 500
    except Exception as e:
        print(colored(f"[-] Error downloading audio: {str(e)}", "red"))
        return jsonify({"status": "error", "message": f"Download failed: {str(e)}"}), 500


@app.route("/api/upload-video", methods=["POST"])
def upload_video():
    instagram_dir = os.path.join(os.path.dirname(__file__), "static/generated_videos/instagram")
    os.makedirs(instagram_dir, exist_ok=True)

    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file provided"}), 400

    files = request.files.getlist("file")
    if not files or files[0].filename == "":
        return jsonify({"status": "error", "message": "No files selected"}), 400

    uploaded = []
    allowed_ext = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv"}
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_ext:
            continue
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = secure_filename(file.filename)
        final_name = f"{timestamp}_{safe_name}"
        file.save(os.path.join(instagram_dir, final_name))
        uploaded.append(final_name)

    if not uploaded:
        return jsonify({"status": "error", "message": "No valid video files uploaded"}), 400

    print(colored(f"[+] Uploaded {len(uploaded)} video(s): {', '.join(uploaded)}", "green"))
    return jsonify({
        "status": "success",
        "message": f"Uploaded {len(uploaded)} video(s)",
        "data": {"filenames": uploaded}
    })

@app.route("/api/upload-image", methods=["POST"])
def upload_image():
    temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "assets", "temp"))
    os.makedirs(temp_dir, exist_ok=True)

    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file provided"}), 400

    files = request.files.getlist("file")
    if not files or files[0].filename == "":
        return jsonify({"status": "error", "message": "No files selected"}), 400

    uploaded = []
    allowed_ext = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_ext:
            continue
        safe_name = secure_filename(file.filename)
        final_name = f"{uuid4()}_{safe_name}"
        file.save(os.path.join(temp_dir, final_name))
        uploaded.append(f"static/assets/temp/{final_name}")

    if not uploaded:
        return jsonify({"status": "error", "message": "No valid image files uploaded"}), 400

    print(colored(f"[+] Uploaded {len(uploaded)} image(s): {', '.join(uploaded)}", "green"))
    return jsonify({
        "status": "success",
        "message": f"Uploaded {len(uploaded)} image(s)",
        "data": {"paths": uploaded}
    })


@app.route("/api/extract-frame", methods=["POST"])
def extract_frame():
    data = request.get_json()
    video_filename = data.get("videoFilename", "")
    video_url = data.get("videoUrl", "")
    timestamp = float(data.get("timestamp", 0.0))

    temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "assets", "temp"))
    os.makedirs(temp_dir, exist_ok=True)

    video_path = None
    source_label = ""

    if video_url:
        source_label = "URL"
        import uuid as uuid_mod
        local_path = os.path.join(temp_dir, f"{uuid_mod.uuid4()}_source.mp4")
        try:
            r = requests.get(video_url, stream=True, timeout=30)
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            video_path = local_path
            print(colored(f"[+] Downloaded video from URL for frame extraction", "green"))
        except Exception as e:
            print(colored(f"[-] Failed to download video URL: {e}", "red"))
            return jsonify({"status": "error", "message": f"Failed to download video: {e}"}), 400
    elif video_filename:
        source_label = video_filename
        video_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "generated_videos"))
        video_path = os.path.join(video_dir, video_filename)
        if not os.path.exists(video_path):
            return jsonify({"status": "error", "message": "Video not found"}), 404
    else:
        return jsonify({"status": "error", "message": "videoFilename or videoUrl is required"}), 400

    output_path = os.path.join(temp_dir, f"thumb_{uuid4()}.jpg")

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0 or not os.path.exists(output_path):
            print(colored(f"[-] Frame extraction failed: {result.stderr[-200:]}", "red"))
            return jsonify({"status": "error", "message": "Frame extraction failed"}), 500
        print(colored(f"[+] Extracted frame at {timestamp}s from {source_label}", "green"))
        return jsonify({
            "status": "success",
            "data": {"path": f"static/assets/temp/{os.path.basename(output_path)}"}
        })
    except Exception as e:
        print(colored(f"[-] Frame extraction error: {e}", "red"))
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if video_url and video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except Exception:
                pass


# Get all available songs
@app.route("/api/getSongs", methods=["GET"])
def get_songs():
    songs = [f for f in os.listdir(os.path.join(os.path.dirname(__file__), "static/assets/music")) if not f.startswith(".")]
    return jsonify({
        "status": "success",
        "message": "Songs retrieved successfully!",
        "data": {
            "songs": songs
        }
    })


# Get all available sound effects
@app.route("/api/getSfx", methods=["GET"])
def get_sfx():
    sfx_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "assets", "sfx"))
    os.makedirs(sfx_dir, exist_ok=True)
    sfx = [f for f in os.listdir(sfx_dir) if not f.startswith(".")]
    return jsonify({
        "status": "success",
        "message": "Sound effects retrieved successfully!",
        "data": {
            "sfx": sfx
        }
    })


# Upload a sound effect into the library
@app.route("/api/upload-sfx", methods=["POST"])
def upload_sfx():
    sfx_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "assets", "sfx"))
    os.makedirs(sfx_dir, exist_ok=True)

    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "No file selected"}), 400

    allowed_ext = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        return jsonify({"status": "error", "message": f"Unsupported audio format: {ext}. Allowed: {', '.join(allowed_ext)}"}), 400

    filename = secure_filename(file.filename)
    file.save(os.path.join(sfx_dir, filename))
    print(colored(f"[+] Uploaded sound effect: {filename}", "green"))
    return jsonify({"status": "success", "message": f"Uploaded {filename}", "data": {"filename": filename}})


# Get all available videos
@app.route("/api/getVideos", methods=["GET"])
def get_videos():
    generated_dir = os.path.join(os.path.dirname(__file__), "static/generated_videos")
    videos = [f for f in os.listdir(generated_dir) if f.endswith(".mp4")]

    def _load_metadata(directory, filename):
        meta_path = os.path.join(directory, filename.replace(".mp4", ".json"))
        if os.path.exists(meta_path):
            try:
                with open(meta_path) as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    video_list = []
    for video in sorted(videos, key=lambda f: os.path.getmtime(os.path.join(generated_dir, f)), reverse=True):
        video_list.append({
            "filename": video,
            "url": f"/api/video/{video}",
            "metadata": _load_metadata(generated_dir, video)
        })

    instagram_dir = os.path.join(generated_dir, "instagram")
    instagram_videos = []
    if os.path.exists(instagram_dir):
        for f in sorted(os.listdir(instagram_dir), key=lambda x: os.path.getmtime(os.path.join(instagram_dir, x)), reverse=True):
            if f.endswith(".mp4"):
                instagram_videos.append({
                    "filename": f,
                    "url": f"/api/video/instagram/{f}",
                    "metadata": _load_metadata(instagram_dir, f)
                })

    # Clipper renders + exports, joined with clip metadata (hook title, thumbnail)
    clipper_videos = _list_clipper_videos()

    # Downloaded/stock assets (Pexels search-and-download, uploads, etc.)
    downloads_list = []
    temp_dir = os.path.join(os.path.dirname(__file__), "static/assets/temp")
    if os.path.exists(temp_dir):
        for f in sorted(os.listdir(temp_dir), key=lambda x: os.path.getmtime(os.path.join(temp_dir, x)), reverse=True):
            if f.endswith(".mp4"):
                fp = os.path.join(temp_dir, f)
                downloads_list.append({
                    "filename": f,
                    "url": f"/static/assets/temp/{f}",
                    "metadata": None,
                    "size_mb": round(os.path.getsize(fp) / (1024 * 1024), 1),
                })

    return jsonify(
        {
        "status": "success",
        "message": "Videos retrieved successfully!",
        "data": {
            "videos": video_list,
            "instagram": instagram_videos,
            "clipper": clipper_videos,
            "downloads": downloads_list,
            }
        }
    )


def _list_clipper_videos():
    """List all rendered/exported CLIPPER videos across projects with clip metadata."""
    try:
        from classes.ClipperProject import project_store
    except ImportError:
        return []

    clipper_root = os.path.join(os.path.dirname(__file__), "static/clipper/projects")
    if not os.path.exists(clipper_root):
        return []

    # Build a clip_id -> clip lookup across all projects
    clip_lookup = {}
    for project in project_store.list_projects():
        for clip in project_store.get_clips(project.id):
            clip_lookup[clip.id] = (clip, project)

    results = []
    for project_dir in os.listdir(clipper_root):
        project_path = os.path.join(clipper_root, project_dir)
        if not os.path.isdir(project_path):
            continue
        # renders/
        renders_dir = os.path.join(project_path, "renders")
        if os.path.exists(renders_dir):
            for f in os.listdir(renders_dir):
                if f.endswith(".mp4"):
                    results.append(_clipper_video_item(project_dir, "renders", f, clip_lookup))
        # exports/<format>/
        exports_dir = os.path.join(project_path, "exports")
        if os.path.exists(exports_dir):
            for fmt in os.listdir(exports_dir):
                fmt_dir = os.path.join(exports_dir, fmt)
                if not os.path.isdir(fmt_dir):
                    continue
                for f in os.listdir(fmt_dir):
                    if f.endswith(".mp4"):
                        results.append(_clipper_video_item(project_dir, f"exports/{fmt}", f, clip_lookup, export_format=fmt))

    results.sort(key=lambda x: x.get("modified", ""), reverse=True)
    return results


def _clipper_video_item(project_id, subpath, filename, clip_lookup, export_format=None):
    clip_id = filename.replace(".mp4", "")
    clip = None
    project = None
    if clip_id in clip_lookup:
        clip, project = clip_lookup[clip_id]
    base_dir = os.path.join(os.path.dirname(__file__), "static/clipper/projects", project_id, subpath)
    item = {
        "filename": filename,
        "url": f"/static/clipper/projects/{project_id}/{subpath}/{filename}",
        "project_id": project_id,
        "project_name": project.name if project else "",
        "clip_id": clip_id,
        "hook_title": clip.hook_title if clip else "",
        "thumbnail_url": clip.thumbnail_url if clip else "",
        "export_format": export_format,
        "metadata": {"title": clip.hook_title} if clip else None,
    }
    try:
        item["modified"] = datetime.fromtimestamp(os.path.getmtime(os.path.join(base_dir, filename))).isoformat()
    except Exception:
        item["modified"] = ""
    return item

# Get all available subtitles
@app.route("/api/getSubtitles", methods=["GET"])
def get_subtitles():
    subtitles = os.listdir(os.path.join(os.path.dirname(__file__), "static/assets/subtitles"))
    return jsonify(
        {
        "status": "success",
        "message": "Songs retrieved successfully!",
        "data": {
            "subtitles": subtitles
            }
        }
    )


#Get all available models and voices
@app.route("/api/models", methods=["GET"])
def get_models():
    engine = get_tts_engine()
    voices = get_all_voices().get(engine, get_tiktok_voices())
    result = {
        "voices": voices,
        "tts_engine": engine,
    }
    if engine == "supertonic":
        result["voiceStyles"] = get_supertonic_voices_detailed()
        result["languages"] = get_supertonic_languages()
        result["qualityPresets"] = get_supertonic_quality_presets()
    return jsonify(
        {
        "status": "success",
        "message": "Models retrieved successfully!",
        "data": result
        }
    )


@app.route("/api/assets", methods=["GET"])
def get_assets():
    assets_path = os.path.join(os.path.dirname(__file__), "static/assets/temp")
    video_assets = os.listdir(assets_path)
    videos = [video for video in video_assets if video.endswith(".mp4")]
    return jsonify(
        {
        "status": "success",
        "message": "Assets retrieved successfully!",
        "data": {
            "videos": videos
            }
        }
    )



@app.route("/api/settings", methods=["GET"])
def get_global_settings():

    global_settings = get_settings()
    return jsonify(
        {
        "status": "success",
        "message": "System settings retrieved successfully!",
        "data": global_settings
        }
    )


@app.route("/api/settings", methods=["POST"])
def update_global_settings():
    data = request.get_json()
    setting_type = data.get("type", "FONT")
    settings = data.get("settings", {})
    update_settings(settings, setting_type)
    return jsonify(
        {
        "status": "success",
        "message": "Settings updated successfully!",
        "data": get_settings()
        }
    )


@app.route("/api/tts/status", methods=["GET"])
def get_tts_health():
    status = get_tts_status()
    return jsonify(
        {
        "status": "success",
        "message": "TTS status retrieved successfully!",
        "data": status
        }
    )


@app.route("/api/tts/voices", methods=["GET"])
def get_tts_voices():
    engine = request.args.get("engine", get_tts_engine())
    voices = get_all_voices().get(engine, get_tiktok_voices())
    result = {
        "voices": voices,
        "engine": engine,
    }
    if engine == "supertonic":
        result["voiceStyles"] = get_supertonic_voices_detailed()
        result["languages"] = get_supertonic_languages()
        result["qualityPresets"] = get_supertonic_quality_presets()
    return jsonify(
        {
        "status": "success",
        "message": "Voices retrieved successfully!",
        "data": result
        }
    )


@app.route("/api/magicsync/accounts", methods=["POST"])
def magicsync_accounts():
    try:
        data = request.get_json()
        url = data.get("url", os.getenv("MAGICSYNC_BASE_URL", "http://localhost:3000"))
        api_token = data.get("apiToken", os.getenv("MAGICSYNC_API_TOKEN", ""))

        print(colored(f"[X] MagicSync accounts request", "blue"))
        print(colored(f"[X]   URL: {url}", "blue"))
        print(colored(f"[X]   API token present: {'yes' if api_token else 'no'}", "blue"))

        if not api_token:
            print(colored("[-]   MISSING: API token", "red"))
            return jsonify({"status": "error", "message": "API token is required. Provide it in the request or set MAGICSYNC_API_TOKEN in Backend/.env"}), 400

        target_url = f"{url}/api/v1/cli/info"
        print(colored(f"[X]   GETting from: {target_url}", "blue"))

        info_resp = requests.get(
            target_url,
            headers={"x-api-key": api_token},
            timeout=10
        )

        print(colored(f"[X]   Response status: {info_resp.status_code}", "blue"))
        try:
            resp_body = info_resp.json()
            print(colored(f"[X]   Response body: {json.dumps(resp_body, indent=2)[:800]}", "blue"))
        except Exception:
            print(colored(f"[X]   Response text: {info_resp.text[:500]}", "blue"))

        if info_resp.status_code != 200:
            print(colored(f"[-] MagicSync info failed: {info_resp.text[:200]}", "red"))
            return jsonify({"status": "error", "message": f"Failed to connect: {info_resp.text}"}), 502

        platforms_data = info_resp.json()
        accounts = [
            {"platform": platform.get("platform"), "accountName": acc.get("accountName"), "isActive": acc.get("isActive", True)}
            for platform in platforms_data.get("data", {}).get("platforms", [])
            for acc in platform.get("accounts", [])
        ]

        platforms_list = list(dict.fromkeys(a.get("platform") for a in accounts if a.get("isActive")))

        print(colored(f"[+] Found {len(platforms_list)} MagicSync platform(s)", "green"))
        for p in platforms_list:
            print(colored(f"      - {p}", "green"))

        return jsonify({
            "status": "success",
            "message": "Accounts retrieved successfully!",
            "data": {"accounts": accounts, "platforms": platforms_list}
        })

    except requests.exceptions.Timeout:
        print(colored(f"[-] MagicSync info request timed out", "red"))
        return jsonify({"status": "error", "message": "MagicSync API request timed out"}), 504
    except requests.exceptions.ConnectionError as e:
        print(colored(f"[-] MagicSync API connection failed: {e}", "red"))
        return jsonify({"status": "error", "message": f"Cannot connect to MagicSync at {url}. Is the server running?"}), 502
    except Exception as e:
        print(colored(f"[-] Error fetching MagicSync accounts: {str(e)}", "red"))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/video/<path:filename>")
def serve_video(filename):
    video_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "generated_videos"))
    return send_from_directory(video_dir, filename)


@app.route("/api/schedule-to-magicsync", methods=["POST"])
def schedule_to_magicsync():
    try:
        data = request.get_json()
        video_filename = data.get("videoFilename")
        scheduled_at = data.get("scheduledAt")
        content = data.get("content", "")
        title = data.get("title", "")
        description = data.get("description", "")
        platforms = data.get("platforms", [])
        video_base_url = data.get("videoBaseUrl", "")

        print(colored(f"[X] Schedule-to-MagicSync request received", "blue"))
        print(colored(f"[X]   videoFilename: {video_filename}", "blue"))
        print(colored(f"[X]   scheduledAt: {scheduled_at}", "blue"))
        print(colored(f"[X]   title: {title[:60] if title else '(empty)'}", "blue"))
        print(colored(f"[X]   platforms ({len(platforms)}): {platforms}", "blue"))

        if not video_filename:
            print(colored("[-]   MISSING: videoFilename", "red"))
            return jsonify({"status": "error", "message": "videoFilename is required"}), 400
        if not platforms:
            print(colored("[-]   MISSING: platforms is empty", "red"))
            return jsonify({"status": "error", "message": "At least one platform is required"}), 400

        # Resolve folder: a bare filename that exists only under generated_videos/instagram
        # must map to instagram/<name>, otherwise the assembled /api/video/<name> 404s for
        # any client fetching it (MagicSync pulls the video from this URL).
        if "/" not in video_filename and not os.path.exists(
            os.path.join(os.path.dirname(__file__), "static", "generated_videos", video_filename)
        ) and os.path.exists(
            os.path.join(os.path.dirname(__file__), "static", "generated_videos", "instagram", video_filename)
        ):
            video_filename = f"instagram/{video_filename}"
            print(colored(f"[*]   Resolved Instagram video path: {video_filename}", "cyan"))

        url = data.get("url", os.getenv("MAGICSYNC_BASE_URL", "http://localhost:3000"))
        api_token = data.get("apiToken", os.getenv("MAGICSYNC_API_TOKEN", ""))

        print(colored(f"[X]   MagicSync URL: {url}", "blue"))
        print(colored(f"[X]   API token present: {'yes' if api_token else 'no'}", "blue"))
        print(colored(f"[X]   Video base URL: {video_base_url or '(using request host)'}", "blue"))

        if not api_token:
            print(colored("[-]   MISSING: API token", "red"))
            return jsonify({"status": "error", "message": "API token is required. Provide it in the request or set MAGICSYNC_API_TOKEN in Backend/.env"}), 400

        if video_base_url:
            video_url = f"{video_base_url.rstrip('/')}/api/video/{video_filename}"
        else:
            base_url = request.host_url.rstrip("/")
            video_url = f"{base_url}/api/video/{video_filename}"
        if not content:
            content = title or description or f"New video: {video_filename}"

        payload = {
            "content": content,
            "platforms": platforms,
            "media": {"video": video_url},
        }

        if title:
            payload["title"] = title
        if description:
            payload["description"] = description
        if scheduled_at:
            payload["scheduledAt"] = scheduled_at

        print(colored(f"[X]   Payload to MagicSync:", "blue"))
        print(colored(f"       content: {content[:80]}...", "blue"))
        print(colored(f"       media.video: {video_url}", "blue"))
        print(colored(f"       platforms: {platforms}", "blue"))
        if scheduled_at:
            print(colored(f"       scheduledAt: {scheduled_at}", "blue"))

        target_url = f"{url}/api/v1/cli/post"
        print(colored(f"[X]   POSTing to: {target_url}", "blue"))

        post_resp = requests.post(
            target_url,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_token
            },
            json=payload,
            timeout=30
        )

        print(colored(f"[X]   Response status: {post_resp.status_code}", "blue"))
        try:
            resp_body = post_resp.json()
            print(colored(f"[X]   Response body: {json.dumps(resp_body, indent=2)[:500]}", "blue"))
        except Exception:
            print(colored(f"[X]   Response text: {post_resp.text[:500]}", "blue"))

        if post_resp.status_code == 200:
            print(colored(f"[+] Video scheduled successfully!", "green"))
            return jsonify({
                "status": "success",
                "message": "Video scheduled successfully!",
                "data": post_resp.json()
            })
        else:
            print(colored(f"[-] MagicSync API returned {post_resp.status_code}", "red"))
            return jsonify({
                "status": "error",
                "message": f"MagicSync API error: {post_resp.text}"
            }), 502

    except requests.exceptions.Timeout:
        print(colored(f"[-] MagicSync API request timed out after 30s", "red"))
        return jsonify({"status": "error", "message": "MagicSync API request timed out"}), 504
    except requests.exceptions.ConnectionError as e:
        print(colored(f"[-] MagicSync API connection failed: {e}", "red"))
        return jsonify({"status": "error", "message": f"Cannot connect to MagicSync at {url}. Is the server running?"}), 502
    except Exception as e:
        print(colored(f"[-] Error scheduling video: {str(e)}", "red"))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/video/delete", methods=["POST"])
def delete_video():
    data = request.get_json()
    filename = data.get("filename", "")
    category = data.get("category", "generated")  # generated | instagram | clipper | downloads
    if not filename:
        return jsonify({"status": "error", "message": "filename is required"}), 400

    # Sanitize: never allow path traversal
    safe_name = os.path.basename(filename)
    if safe_name != filename:
        return jsonify({"status": "error", "message": "Invalid filename"}), 400

    static_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))

    if category == "instagram":
        target_dir = os.path.join(static_root, "generated_videos", "instagram")
    elif category == "downloads":
        target_dir = os.path.join(static_root, "assets", "temp")
    elif category == "clipper":
        project_id = os.path.basename(data.get("project_id", ""))
        subpath = data.get("subpath", "renders")  # renders | exports/<fmt>
        subparts = [os.path.basename(p) for p in subpath.split("/") if p]
        target_dir = os.path.join(static_root, "clipper", "projects", project_id, *subparts)
    else:
        target_dir = os.path.join(static_root, "generated_videos")

    if not os.path.abspath(target_dir).startswith(static_root):
        return jsonify({"status": "error", "message": "Invalid path"}), 400

    video_path = os.path.join(target_dir, safe_name)
    basename = os.path.splitext(safe_name)[0]
    json_path = os.path.join(target_dir, f"{basename}.json")

    deleted = []
    if os.path.exists(video_path):
        os.remove(video_path)
        deleted.append(safe_name)
    if os.path.exists(json_path):
        os.remove(json_path)
        deleted.append(f"{basename}.json")

    # Deleting a clipper render resets the clip status so it can be re-rendered
    if category == "clipper" and deleted:
        try:
            from classes.ClipperProject import project_store
            project = project_store.get_project(data.get("project_id", ""))
            if project:
                for clip in project_store.get_clips(project.id):
                    if clip.id == basename:
                        clip.status = "selected"
                        project_store.save_clip(clip)
                        break
        except Exception as e:
            print(colored(f"[-] Could not reset clip status after delete: {e}", "yellow"))

    if not deleted:
        return jsonify({"status": "error", "message": "Video file not found"}), 404

    print(colored(f"[+] Deleted ({category}): {', '.join(deleted)}", "green"))
    return jsonify({"status": "success", "message": f"Deleted {', '.join(deleted)}"})


def _clear_mp4_sidecars(target_dir):
    """Delete every .mp4 + its .json sidecar in target_dir. Returns file list."""
    deleted = []
    if not os.path.isdir(target_dir):
        return deleted
    for f in os.listdir(target_dir):
        if not f.endswith(".mp4"):
            continue
        if os.path.basename(f) != f:  # paranoia: flat dir, no traversal
            continue
        video_path = os.path.join(target_dir, f)
        if not os.path.isfile(video_path):
            continue
        os.remove(video_path)
        deleted.append(f)
        json_path = os.path.join(target_dir, f"{os.path.splitext(f)[0]}.json")
        if os.path.exists(json_path):
            os.remove(json_path)
            deleted.append(os.path.basename(json_path))
    return deleted


@app.route("/api/video/clear-category", methods=["POST"])
def clear_video_category():
    data = request.get_json(silent=True) or {}
    category = data.get("category", "")
    if category not in ("generated", "instagram", "clipper", "downloads"):
        return jsonify({"status": "error", "message": "Invalid category"}), 400

    static_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
    deleted_files = []

    def _target(*parts):
        target_dir = os.path.join(static_root, *parts)
        if not os.path.abspath(target_dir).startswith(static_root):
            raise ValueError("Invalid path")
        return target_dir

    try:
        if category == "generated":
            deleted_files += _clear_mp4_sidecars(_target("generated_videos"))
        elif category == "instagram":
            deleted_files += _clear_mp4_sidecars(_target("generated_videos", "instagram"))
        elif category == "downloads":
            deleted_files += _clear_mp4_sidecars(_target("assets", "temp"))
        else:  # clipper: renders + exports across all projects
            projects_root = _target("clipper", "projects")
            reset_ids = set()
            if os.path.isdir(projects_root):
                for project_dir in os.listdir(projects_root):
                    project_path = os.path.join(projects_root, project_dir)
                    if not os.path.isdir(project_path):
                        continue
                    for sub in ["renders"]:
                        deleted_files += _clear_mp4_sidecars(os.path.join(project_path, sub))
                    exports_dir = os.path.join(project_path, "exports")
                    if os.path.isdir(exports_dir):
                        for fmt in os.listdir(exports_dir):
                            fmt_dir = os.path.join(exports_dir, fmt)
                            if os.path.isdir(fmt_dir):
                                deleted_files += _clear_mp4_sidecars(fmt_dir)
            # Reset status of clips whose render/export was removed so they can be re-rendered
            for f in deleted_files:
                if f.endswith(".mp4"):
                    reset_ids.add(os.path.splitext(f)[0])
            if reset_ids:
                try:
                    from classes.ClipperProject import project_store
                    for project in project_store.list_projects():
                        for clip in project_store.get_clips(project.id):
                            if clip.id in reset_ids and getattr(clip, "status", "") != "selected":
                                clip.status = "selected"
                                project_store.save_clip(clip)
                except Exception as e:
                    print(colored(f"[-] Could not reset clip statuses after clear: {e}", "yellow"))
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    print(colored(f"[+] Cleared ({category}): {len(deleted_files)} files", "green"))
    return jsonify({"status": "success", "message": f"Cleared {len(deleted_files)} files from {category}",
                    "data": {"deleted": len(deleted_files), "files": deleted_files}})


@app.route("/api/leadgen/health", methods=["GET"])
def leadgen_health():
    port = request.args.get("port", 9222, type=int)
    import asyncio
    adapter = DevToolsAdapter(chrome_port=port)

    async def check():
        return await adapter.health_check()

    try:
        ok = asyncio.run(check())
        return jsonify({"status": "ok" if ok else "error", "message": "Connected to Chrome" if ok else f"Cannot connect to Chrome on port {port}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/leadgen/twitter-profile", methods=["GET"])
def leadgen_twitter_profile():
    username = request.args.get("username", "")
    port = request.args.get("port", 9222, type=int)
    if not username:
        return jsonify({"status": "error", "message": "username required"}), 400
    import asyncio
    adapter = DevToolsAdapter(chrome_port=port)

    async def fetch():
        return await adapter.get_profile(username, "twitter")

    try:
        profile = asyncio.run(fetch())
        if profile:
            return jsonify({"status": "ok", "data": profile.__dict__})
        return jsonify({"status": "error", "message": "Profile not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/leadgen/scrape-url", methods=["POST"])
def leadgen_scrape_url():
    try:
        data = request.get_json()
        url = data.get("url", "")
        if not url:
            return jsonify({"status": "error", "message": "url is required"}), 400
        from leadgen.scrape import scrape_url as do_scrape
        result = do_scrape(url)
        if "error" in result:
            return jsonify({"status": "error", "message": result["error"]}), 400
        return jsonify({"status": "ok", "data": result})
    except Exception as e:
        print(colored(f"[-] Error scraping URL: {e}", "red"))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/leadgen/campaign/enrich", methods=["POST"])
def leadgen_enrich_campaign():
    try:
        data = request.get_json()
        description = data.get("description", "")
        website_data = data.get("website_data")
        if not description:
            return jsonify({"status": "error", "message": "description is required"}), 400
        if website_data and website_data.get("summary"):
            result = enrich_campaign_with_website(description, website_data)
        else:
            result = enrich_campaign_description(description)
        return jsonify({"status": "ok", "data": result})
    except Exception as e:
        print(colored(f"[-] Error enriching campaign: {e}", "red"))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/leadgen/campaigns", methods=["GET", "POST"])
def leadgen_campaigns():
    if request.method == "GET":
        return jsonify({"status": "ok", "data": get_campaigns()})

    try:
        data = request.get_json()
        name = data.get("name", "")
        description = data.get("description", "")
        keywords = data.get("keywords", [])
        platforms = data.get("platforms", [data.get("platform", "twitter")])
        if isinstance(platforms, str):
            platforms = [platforms]
        enrichment = data.get("enrichment")
        campaign = create_campaign(name, description, keywords, platforms, enrichment)
        return jsonify({"status": "ok", "data": campaign})
    except Exception as e:
        print(colored(f"[-] Error creating campaign: {e}", "red"))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/leadgen/campaigns/<campaign_id>", methods=["GET", "DELETE"])
def leadgen_campaign_detail(campaign_id):
    if request.method == "GET":
        campaign = get_campaign(campaign_id)
        if not campaign:
            return jsonify({"status": "error", "message": "Campaign not found"}), 404
        leads = get_leads(campaign_id)
        campaign["leads"] = leads
        return jsonify({"status": "ok", "data": campaign})

    ok = delete_campaign(campaign_id)
    if not ok:
        return jsonify({"status": "error", "message": "Campaign not found"}), 404
    return jsonify({"status": "ok", "message": "Campaign deleted"})


@app.route("/api/leadgen/campaigns/<campaign_id>/leads", methods=["POST"])
def leadgen_add_lead(campaign_id):
    try:
        campaign = get_campaign(campaign_id)
        if not campaign:
            return jsonify({"status": "error", "message": "Campaign not found"}), 404
        data = request.get_json()
        lead = add_lead(campaign_id, data)
        return jsonify({"status": "ok", "data": lead})
    except Exception as e:
        print(colored(f"[-] Error adding lead: {e}", "red"))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/leadgen/campaigns/<campaign_id>/competitors", methods=["GET", "POST"])
def leadgen_campaign_competitors(campaign_id):
    campaign = get_campaign(campaign_id)
    if not campaign:
        return jsonify({"status": "error", "message": "Campaign not found"}), 404

    if request.method == "GET":
        return jsonify({"status": "ok", "data": campaign.get("competitors", [])})

    try:
        data = request.get_json()
        name = data.get("name", "")
        url = data.get("url", "")
        if not name:
            return jsonify({"status": "error", "message": "Competitor name required"}), 400

        # AI-enrich the competitor analysis
        try:
            analysis = analyze_competitor(name, campaign.get("description", ""))
            competitor = {
                "name": name,
                "url": url,
                "notes": data.get("notes", ""),
                "analysis": analysis,
            }
        except Exception:
            competitor = {
                "name": name,
                "url": url,
                "notes": data.get("notes", ""),
            }

        result = add_competitor(campaign_id, competitor)
        if result:
            return jsonify({"status": "ok", "data": result})
        return jsonify({"status": "error", "message": "Failed to add competitor"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/leadgen/campaigns/<campaign_id>/competitors/<competitor_id>", methods=["DELETE"])
def leadgen_remove_competitor(campaign_id, competitor_id):
    ok = remove_competitor(campaign_id, competitor_id)
    if not ok:
        return jsonify({"status": "error", "message": "Competitor not found"}), 404
    return jsonify({"status": "ok", "message": "Competitor removed"})


@app.route("/api/leadgen/campaigns/<campaign_id>/viral-posts", methods=["GET", "POST"])
def leadgen_campaign_viral_posts(campaign_id):
    campaign = get_campaign(campaign_id)
    if not campaign:
        return jsonify({"status": "error", "message": "Campaign not found"}), 404

    if request.method == "GET":
        return jsonify({"status": "ok", "data": campaign.get("viral_posts", [])})

    try:
        data = request.get_json()
        post_text = data.get("post_text", "")
        post_url = data.get("post_url", "")
        username = data.get("username", "")

        if not post_text:
            return jsonify({"status": "error", "message": "post_text is required"}), 400

        # AI-analyze the viral post
        try:
            analysis = analyze_viral_post(post_text, campaign.get("description", ""))
            post = {
                "post_text": post_text,
                "post_url": post_url,
                "username": username,
                "analysis": analysis,
            }
        except Exception:
            post = {
                "post_text": post_text,
                "post_url": post_url,
                "username": username,
            }

        result = add_viral_post(campaign_id, post)
        if result:
            return jsonify({"status": "ok", "data": result})
        return jsonify({"status": "error", "message": "Failed to save viral post"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/leadgen/twitter-audit", methods=["GET"])
def leadgen_twitter_audit():
    username = request.args.get("username", "")
    port = request.args.get("port", 9222, type=int)
    if not username:
        return jsonify({"status": "error", "message": "username required"}), 400
    import asyncio
    adapter = DevToolsAdapter(chrome_port=port)

    async def fetch():
        profile = await adapter.get_profile(username, "twitter")
        if not profile:
            return None, []
        profile_dict = profile.__dict__
        queries = find_related_niche_queries(profile_dict)
        all_related = []
        seen = set()
        for q in queries:
            try:
                results = await adapter.search_keyword(q, "twitter", max_results=5)
                for r in results:
                    if r.username and r.username.lower() != username.lower() and r.username not in seen:
                        seen.add(r.username)
                        all_related.append(r.__dict__)
            except Exception:
                continue
        return profile_dict, all_related[:10]

    try:
        profile, related = asyncio.run(fetch())
        if not profile:
            return jsonify({"status": "error", "message": "Profile not found"}), 404
        return jsonify({"status": "ok", "data": {"profile": profile, "related_users": related}})
    except Exception as e:
        print(colored(f"[-] Error auditing profile: {e}", "red"))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/leadgen/campaigns/<campaign_id>/search-leads", methods=["POST"])
def leadgen_campaign_search_leads(campaign_id):
    campaign = get_campaign(campaign_id)
    if not campaign:
        return jsonify({"status": "error", "message": "Campaign not found"}), 404

    data = request.get_json() or {}
    port = int(data.get("port", 9222))
    max_results = int(data.get("max_results", 10))
    mode = data.get("mode", "leads")
    custom_keywords = data.get("custom_keywords", [])

    # GPT-generate the best keywords for this campaign + mode
    try:
        if mode == "engagement":
            search_queries = generate_engagement_keywords(campaign)
        else:
            search_queries = generate_lead_keywords(campaign)
    except Exception:
        search_queries = campaign.get("keywords", []) + campaign.get("intent_queries", [])
        search_queries = [q for q in set(search_queries) if q.strip()]

    # Merge with user's custom keywords (at front, prioritized)
    if custom_keywords:
        search_queries = list(custom_keywords) + [q for q in search_queries if q not in custom_keywords]

    if not search_queries:
        return jsonify({"status": "error", "message": "Campaign has no keywords or queries to search for"}), 400

    import asyncio
    adapter = DevToolsAdapter(chrome_port=port)

    async def fetch():
        posts = []
        profiles = {}
        seen_posts = set()
        seen_profiles = set()

        for q in search_queries[:6]:
            try:
                results = await adapter.search_keyword(q, "twitter", max_results=max_results)
                for r in results:
                    if hasattr(r, 'post_url') and r.post_url and r.post_url not in seen_posts:
                        seen_posts.add(r.post_url)
                        posts.append(r.__dict__)
                    if r.username and r.username not in seen_profiles:
                        seen_profiles.add(r.username)
                        if r.username not in profiles:
                            profiles[r.username] = {
                                "username": r.username,
                                "display_name": r.display_name,
                                "avatar_url": r.avatar_url,
                                "bio": r.bio,
                                "follower_count": r.follower_count,
                                "profile_url": r.profile_url,
                                "matched_keyword": q,
                            }
            except Exception:
                continue

        return posts[:30], list(profiles.values())[:15]

    try:
        real_posts, real_profiles = asyncio.run(fetch())

        # If real search returned nothing, fall back to GPT-generated leads
        gpt_fallback_used = False
        if not real_posts and not real_profiles:
            print(colored(f"[!] Real search returned 0 results — using GPT fallback", "yellow"))
            gpt_fallback_used = True
            synthetic = generate_synthetic_leads(campaign, mode=mode, count=12)
            posts = []
            profiles_list = []
            for s in synthetic:
                posts.append(s)
                if s.get("lead_type") == "lead" and s.get("username"):
                    profiles_list.append({
                        "username": s["username"],
                        "display_name": s.get("display_name", ""),
                        "avatar_url": "",
                        "bio": s.get("bio", ""),
                        "follower_count": s.get("follower_count", 0),
                        "profile_url": f"https://twitter.com/{s['username']}",
                        "matched_keyword": "gpt-generated",
                    })
            # Mark posts as GPT-generated
            for p in posts:
                p["_gpt_generated"] = True
        else:
            posts = real_posts
            profiles_list = real_profiles

        # GPT qualify all posts 1-10
        qualifications = []
        if posts:
            try:
                qualifications = qualify_search_results(posts, campaign)
            except Exception as e:
                print(colored(f"[-] Qualification failed: {e}", "red"))

        # Attach qualification to each post
        for q in qualifications:
            idx = q.get("index")
            if idx is not None and idx < len(posts):
                posts[idx]["qualification"] = {
                    "score": q.get("score", 5),
                    "classification": q.get("classification", "warm_lead"),
                    "reason": q.get("reason", ""),
                }

        if mode == "engagement":
            # Engagement mode: don't auto-add profiles as leads
            engagement_suggestions = []
            if posts:
                try:
                    post_texts = [p.get("post_text", "")[:200] for p in posts if p.get("post_text")]
                    if post_texts:
                        engagement_suggestions = suggest_engagement(post_texts, campaign.get("description", ""))
                except Exception:
                    pass

            return jsonify({
                "status": "ok",
                "data": {
                    "posts": posts,
                    "profiles": profiles_list,
                    "engagement_suggestions": engagement_suggestions,
                    "queries_used": search_queries[:6],
                    "mode": "engagement",
                    "gpt_fallback_used": gpt_fallback_used,
                    "qualifications": qualifications,
                }
            })
        else:
            # Leads mode: auto-add found or generated profiles as leads
            for p in profiles_list:
                add_lead(campaign_id, {
                    "platform": "twitter",
                    "username": p["username"],
                    "display_name": p.get("display_name"),
                    "avatar_url": p.get("avatar_url"),
                    "bio": p.get("bio"),
                    "follower_count": p.get("follower_count"),
                    "profile_url": p.get("profile_url"),
                    "matched_keyword": p.get("matched_keyword", "gpt-generated"),
                    "source": "gpt_synthetic" if gpt_fallback_used else "campaign_search",
                    "intent_score": p.get("intent_score", 0.7),
                })

            engagement_suggestions = []
            if posts:
                try:
                    post_texts = [p.get("post_text", "")[:200] for p in posts if p.get("post_text")]
                    if post_texts:
                        engagement_suggestions = suggest_engagement(post_texts, campaign.get("description", ""))
                except Exception:
                    pass

            return jsonify({
                "status": "ok",
                "data": {
                    "posts": posts,
                    "profiles": profiles_list,
                    "engagement_suggestions": engagement_suggestions,
                    "queries_used": search_queries[:6],
                    "leads_added": len(profiles_list),
                    "mode": "leads",
                    "gpt_fallback_used": gpt_fallback_used,
                    "qualifications": qualifications,
                }
            })
    except Exception as e:
        print(colored(f"[-] Error searching leads: {e}", "red"))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/leadgen/enhance-profile", methods=["POST"])
def leadgen_enhance_profile():
    try:
        data = request.get_json()
        profile = data.get("profile", {})
        if not profile:
            return jsonify({"status": "error", "message": "profile data is required"}), 400
        result = enhance_profile_analysis(profile)
        return jsonify({"status": "ok", "data": result})
    except Exception as e:
        print(colored(f"[-] Error enhancing profile: {e}", "red"))
        return jsonify({"status": "error", "message": str(e)}), 500


# ==================== CLIPPER Studio: stock media + AI topics ====================
# Proxies so the browser editor (@elah studio page) never needs vendor API keys.


def _pexels_headers():
    key = os.environ.get("PEXELS_API_KEY")
    return key, {"Authorization": key} if key else None


@app.route("/api/stock/videos", methods=["GET"])
def stock_search_videos():
    """Pexels video search for the editor's Videos panel.
    Returns browser-usable items: {id, url, thumbnail, duration, user, width, height}."""
    query = request.args.get("query", "")
    per_page = int(request.args.get("per_page", 12))
    key, headers = _pexels_headers()
    if not key:
        return jsonify({"status": "error", "message": "PEXELS_API_KEY not configured"}), 400
    if not query.strip():
        return jsonify({"status": "error", "message": "query is required"}), 400
    try:
        from urllib.parse import quote
        resp = requests.get(
            f"https://api.pexels.com/videos/search?query={quote(query)}&per_page={per_page}",
            headers=headers, timeout=20,
        )
        if resp.status_code != 200:
            return jsonify({"status": "error", "message": f"Pexels error {resp.status_code}"}), 502
        data = resp.json()
        items = []
        for v in data.get("videos", []):
            # Prefer an mp4 file around 1080p for editor preview performance
            files = v.get("video_files", [])
            best = None
            for f in sorted(files, key=lambda x: abs((x.get("height") or 1080) - 1080)):
                if f.get("link"):
                    best = f
                    break
            if not best or not best.get("link"):
                continue
            pictures = v.get("video_pictures", [])
            items.append({
                "id": v.get("id"),
                "url": best["link"],
                "thumbnail": pictures[0].get("picture") if pictures else "",
                "duration": v.get("duration", 0),
                "user": (v.get("user") or {}).get("name", ""),
                "width": best.get("width") or v.get("width", 0),
                "height": best.get("height") or v.get("height", 0),
            })
        return jsonify({"status": "success", "data": items})
    except Exception as e:
        print(colored(f"[-] Stock video search failed: {e}", "red"))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/stock/photos", methods=["GET"])
def stock_search_photos():
    """Pexels photo search for the editor's Photos panel."""
    query = request.args.get("query", "")
    per_page = int(request.args.get("per_page", 12))
    key, headers = _pexels_headers()
    if not key:
        return jsonify({"status": "error", "message": "PEXELS_API_KEY not configured"}), 400
    if not query.strip():
        return jsonify({"status": "error", "message": "query is required"}), 400
    try:
        from urllib.parse import quote
        resp = requests.get(
            f"https://api.pexels.com/v1/search?query={quote(query)}&per_page={per_page}",
            headers=headers, timeout=20,
        )
        if resp.status_code != 200:
            return jsonify({"status": "error", "message": f"Pexels error {resp.status_code}"}), 502
        data = resp.json()
        items = []
        for p in data.get("photos", []):
            src = p.get("src", {})
            items.append({
                "id": p.get("id"),
                "url": src.get("large2x") or src.get("large") or src.get("original", ""),
                "thumbnail": src.get("medium") or src.get("small", ""),
                "user": p.get("photographer", ""),
                "width": p.get("width", 0),
                "height": p.get("height", 0),
                "duration": None,
            })
        return jsonify({"status": "success", "data": items})
    except Exception as e:
        print(colored(f"[-] Stock photo search failed: {e}", "red"))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/clipper/ai/topics", methods=["POST"])
def clipper_ai_topics():
    """Agentic AI topic options for the studio: prompt → 4 composable topics.

    Returns: {options: [{name, description, videotags: [str], imagetags: [str], musicQuery: str}]}
    """
    try:
        data = request.get_json(silent=True) or {}
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return jsonify({"status": "error", "message": "prompt is required"}), 400

        from gpt import generate_response
        from llm_providers import get_clipper_ai_model
        ai_model = get_clipper_ai_model()

        sys_prompt = f"""You are a video editor assistant. The user wants to build a short video from a text prompt.

User prompt: "{prompt}"

Return JSON ONLY with 4 topic option objects, no markdown:
{{"options": [
  {{"name": "short topic title (3-5 words)", "description": "one-line concept", "videotags": ["2-3 short english search tags for stock video"], "imagetags": ["2-3 tags"], "musicQuery": "one mood keyword for music"}}
]}}

Rules: topics must be distinct visual angles on the same prompt; videotags/imagetags are lower-case english words the Pexels search API understands; no commentary."""
        text = generate_response(sys_prompt, ai_model).strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        import json as _json
        parsed = _json.loads(text)
        options = parsed.get("options", [])[:4]
        if not options:
            return jsonify({"status": "error", "message": "No options generated"}), 502
        return jsonify({"status": "success", "data": {"options": options}})
    except Exception as e:
        print(colored(f"[-] AI topics failed: {e}", "red"))
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":

    # Run Flask App
    app.run(debug=True, host=HOST, port=PORT)
